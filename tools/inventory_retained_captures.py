"""Index legacy retained bytes without rewriting acquisition manifests.

An LF-to-CRLF match explains a transformation; it does not restore provenance.
Missing members remain missing and the original manifest remains unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.capture_archive import write_json


def inventory(directory):
    rows = []
    for case in sorted(Path(directory).glob("runner-*")):
        if not case.is_dir():
            continue
        original_path = case / "sha256.json"
        original = json.loads(original_path.read_text(encoding="utf-8-sig"))
        records = []
        for name, digest in sorted(original.items()):
            portable = name.replace("\\", "/")
            path = case / portable
            entry = {"path": portable, "acquisition_sha256": digest, "present": path.is_file()}
            if path.is_file():
                data = path.read_bytes()
                actual = hashlib.sha256(data).hexdigest()
                entry.update(retained_sha256=actual, acquisition_hash_matches=actual == digest,
                             lf_to_crlf_hash_matches=hashlib.sha256(data.replace(b"\r\n", b"\n")
                                                                     .replace(b"\n", b"\r\n")).hexdigest() == digest)
            records.append(entry)
        rows.append({"case": case.name,
                     "retained_acquisition_manifest_sha256": hashlib.sha256(original_path.read_bytes()).hexdigest(),
                     "acquisition_manifest_verifies": all(r["present"] and r.get("acquisition_hash_matches") for r in records),
                     "files": records})
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    write_json(args.output, {"kind": "derivative inventory of retained Git bytes; not original acquisition verification",
                            "source_commit": args.source_commit,
                            "source_path": "windows-observations/run-40939421976",
                            "manual_review": "PENDING_INDEPENDENT_REVIEW",
                            "cases": inventory(args.directory)})
