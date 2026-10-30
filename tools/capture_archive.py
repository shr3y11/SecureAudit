"""Preserve capture bytes (including SQLite) before Git text normalization.

The manifest proves internal consistency, not origin. Retain an independently
trusted archive digest for authenticity. This module never extracts ZIP paths.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def write_json(path, content):
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(content, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def seal_capture(directory):
    directory = Path(directory)
    files = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(directory.rglob("*")) if p.is_file() and p.name != "sha256.json"}
    if "scans.db" not in files:
        raise ValueError("Capture is incomplete: scans.db missing")
    write_json(directory / "sha256.json", files)
    archive = directory.with_name(directory.name + ".capture.zip")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in [*files, "sha256.json"]:
            bundle.write(directory / name, name)
    verify_capture(archive)
    return archive


def verify_capture(archive):
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate capture member")
        for name in names:
            path = PurePosixPath(name)
            if "\\" in name or path.is_absolute() or ".." in path.parts or str(path) != name:
                raise ValueError("Unsafe or nonportable capture member")
        manifest = json.loads(bundle.read("sha256.json"))
        if "scans.db" not in manifest or set(names) != set(manifest) | {"sha256.json"}:
            raise ValueError("Capture members differ from manifest or database missing")
        for name, digest in manifest.items():
            if hashlib.sha256(bundle.read(name)).hexdigest() != digest:
                raise ValueError(f"Capture checksum mismatch: {name}")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    manifest = verify_capture(args.archive)
    print(f"Verified {len(manifest)} captured files, including scans.db")
