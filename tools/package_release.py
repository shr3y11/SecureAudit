"""Package the portable release without runtime evidence or Python caches."""
import hashlib
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "dist" / "SecureAudit-M5"
ARCHIVE = ROOT / "dist" / "SecureAudit-M5-Windows.zip"
if not (FOLDER / "SecureAuditCentral.exe").is_file():
    raise SystemExit("Build the portable distribution first.")
shutil.copy2(ROOT / "docs" / "M5_CENTRAL.md", FOLDER / "M5-GUIDE.md")

def include(path):
    relative = path.relative_to(FOLDER)
    return (path.is_file() and "__pycache__" not in relative.parts
            and path.suffix not in {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".log"}
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
    damaged = archive.testzip()
    if damaged:
        raise RuntimeError(f"Damaged archive entry: {damaged}")
    for path in files:
        if archive.read(path.relative_to(FOLDER.parent).as_posix()) != path.read_bytes():
            raise RuntimeError(f"Archive content differs: {path.name}")
digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
ARCHIVE.with_suffix(".zip.sha256").write_text(f"{digest}  {ARCHIVE.name}\n", encoding="utf-8")
print(f"Verified {len(files) + 1} files: {ARCHIVE}")
print(f"Size: {ARCHIVE.stat().st_size / 1024 / 1024:.1f} MiB; SHA-256: {digest}")
