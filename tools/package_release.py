"""Package the versioned portable release without runtime evidence or credentials."""
import hashlib
from pathlib import Path
import runpy
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = runpy.run_path(str(ROOT / "secureaudit_central" / "__init__.py"))["__version__"]
FOLDER = ROOT / "dist" / f"SecureAudit-v{VERSION}"
ARCHIVE = ROOT / "dist" / f"SecureAudit-v{VERSION}-Windows-x64.zip"
if not (FOLDER / "SecureAuditCentral.exe").is_file():
    raise SystemExit("Build the portable distribution first.")
for source, target in ((ROOT / "README.md", "README.md"),
                       (ROOT / "RELEASE_NOTES.md", "RELEASE_NOTES.md"),
                       (ROOT / "docs/RELEASE_GUIDE.md", "RELEASE_GUIDE.md")):
    shutil.copy2(source, FOLDER / target)

def include(path):
    relative = path.relative_to(FOLDER)
    return (path.is_file() and "__pycache__" not in relative.parts
            and path.suffix.lower() not in {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".log", ".key"}
            and path.name not in {"access.key", ".env", "SHA256SUMS.txt"})

files = sorted(path for path in FOLDER.rglob("*") if include(path))
manifest = FOLDER / "SHA256SUMS.txt"
manifest.write_text("".join(
    f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(FOLDER).as_posix()}\n"
    for path in files), encoding="utf-8")
with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in files + [manifest]:
        archive.write(path, path.relative_to(FOLDER.parent).as_posix())
with zipfile.ZipFile(ARCHIVE) as archive:
    assert archive.testzip() is None
    for path in files:
        assert archive.read(path.relative_to(FOLDER.parent).as_posix()) == path.read_bytes()
digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
ARCHIVE.with_suffix(".zip.sha256").write_text(f"{digest}  {ARCHIVE.name}\n", encoding="utf-8")
print(f"Verified {len(files) + 1} files: {ARCHIVE}")
print(f"SHA-256: {digest}")
