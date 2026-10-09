"""Build a portable folder using an unmodified, signed official interpreter."""
from importlib import metadata
from pathlib import Path
import ctypes
import os
import shutil
import sys
import urllib.request
import zipfile
from packaging.requirements import Requirement

if os.name != "nt" or sys.version_info[:2] != (3, 12):
    raise SystemExit("Portable release builds require Python 3.12 on Windows x64; use the matching runtime for native packages.")

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / ".tools"
DEST = ROOT / "dist" / "SecureAudit-M5"
TOOLS.mkdir(exist_ok=True)
DEST.mkdir(parents=True, exist_ok=True)

archive = TOOLS / "python-3.12.10-embed-amd64.zip"
if not archive.exists():
    urllib.request.urlretrieve("https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip", archive)
with zipfile.ZipFile(archive) as zipped:
    zipped.extractall(DEST)
shutil.copy2(DEST / "pythonw.exe", DEST / "SecureAuditCentral.exe")
(DEST / "python312._pth").write_text("python312.zip\n.\napp\nsite-packages\nimport site\n", encoding="utf-8")

app_dir = DEST / "app"
app_dir.mkdir(exist_ok=True)
ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
for name in ("core", "checks", "secureaudit_central"):
    shutil.copytree(ROOT / name, app_dir / name, dirs_exist_ok=True, ignore=ignore)
shutil.copy2(ROOT / "launcher.py", app_dir / "launcher.py")
shutil.copy2(ROOT / "tools" / "portable_sitecustomize.py", app_dir / "sitecustomize.py")

packages_dir = DEST / "site-packages"
packages_dir.mkdir(exist_ok=True)
seen = set()
def copy_distribution(name):
    normalized = name.lower().replace("_", "-")
    if normalized in seen:
        return
    seen.add(normalized)
    distribution = metadata.distribution(name)
    for entry in distribution.files or []:
        relative = Path(str(entry))
        if ".." in relative.parts or relative.suffix == ".pyc" or "__pycache__" in relative.parts:
            continue
        source = Path(distribution.locate_file(entry))
        if source.is_file():
            destination = packages_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    for requirement_text in distribution.requires or []:
        requirement = Requirement(requirement_text)
        if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
            copy_distribution(requirement.name)

for name in ("fastapi", "uvicorn", "sqlalchemy", "psycopg", "psycopg-binary"):
    copy_distribution(name)

# Official embedded Python excludes Tk. Pair the development runtime's Tcl
# binaries with their exact upstream library version. Licenses are preserved.
base = Path(sys.base_prefix)
shutil.copytree(base / "Lib" / "tkinter", packages_dir / "tkinter", dirs_exist_ok=True, ignore=ignore)
for filename in ("_tkinter.pyd", "tcl86t.dll", "tk86t.dll"):
    shutil.copy2(base / "DLLs" / filename, DEST / filename)

tcl = ctypes.CDLL(str(base / "DLLs" / "tcl86t.dll"))
tcl.Tcl_CreateInterp.restype = ctypes.c_void_p
tcl.Tcl_Eval.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
tcl.Tcl_GetStringResult.argtypes = [ctypes.c_void_p]
tcl.Tcl_GetStringResult.restype = ctypes.c_char_p
tcl.Tcl_DeleteInterp.argtypes = [ctypes.c_void_p]
interpreter = tcl.Tcl_CreateInterp()
tcl.Tcl_Eval(interpreter, b"info patchlevel")
tk_version = tcl.Tcl_GetStringResult(interpreter).decode("ascii")
tcl.Tcl_DeleteInterp(interpreter)
if not tk_version.startswith("8.6."):
    raise SystemExit("This portable builder supports the Tcl/Tk 8.6 runtime only.")
release_tag = "core-" + tk_version.replace(".", "-")
for project, destination in (("tcl", "_tcl_data"), ("tk", "_tk_data")):
    source_dir = TOOLS / f"{project}-{release_tag}"
    if not source_dir.exists():
        source_archive = TOOLS / f"{project}.zip"
        urllib.request.urlretrieve(f"https://github.com/tcltk/{project}/archive/refs/tags/{release_tag}.zip", source_archive)
        with zipfile.ZipFile(source_archive) as zipped:
            zipped.extractall(TOOLS)
    shutil.copytree(source_dir / "library", DEST / destination, dirs_exist_ok=True)
    shutil.copy2(source_dir / "license.terms", DEST / f"{project}-license.terms")

(DEST / "START-HERE.txt").write_text(
    "SecureAudit Central 0.5.0 (M5)\n\n"
    "Double-click SecureAuditCentral.exe. Keep the entire folder together.\n"
    "The desktop launcher opens a local browser dashboard. No Python install is needed.\n"
    "For privileged Windows checks: right-click SecureAuditCentral.exe and select Run as administrator.\n"
    "Local data: %LOCALAPPDATA%\\SecureAuditCentral.\n"
    "The official Python runtime launcher is digitally signed by the Python Software Foundation.\n"
    "SecureAudit application source is bundled separately and is not code-signed.\n"
    "This is a central backend milestone, with 100 synthetic demo endpoints and real local scans.\n"
    "Remote endpoint agents, enterprise RBAC, and AI governance are later milestones.\n",
    encoding="utf-8")
print(f"Portable distribution built: {DEST}")
print(f"Bundled runtime distributions: {', '.join(sorted(seen))}")
