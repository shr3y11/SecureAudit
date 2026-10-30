import hashlib
import json

from tools.inventory_retained_captures import inventory


def test_inventory_explains_normalization_without_claiming_recovery(tmp_path):
    case = tmp_path / "runner-fixture"
    (case / "repeat-1").mkdir(parents=True)
    data = b'{"reading": "Pass"}\n'
    (case / "repeat-1/scan.json").write_bytes(data)
    manifest = {"repeat-1\\scan.json": hashlib.sha256(data.replace(b"\n", b"\r\n")).hexdigest(),
                "scans.db": "unavailable-original-digest"}
    original = json.dumps(manifest).encode()
    (case / "sha256.json").write_bytes(original)
    row = inventory(tmp_path)[0]
    assert not row["acquisition_manifest_verifies"]
    text, missing = row["files"]
    assert not text["acquisition_hash_matches"] and text["lf_to_crlf_hash_matches"]
    assert missing["present"] is False and "retained_sha256" not in missing
    assert (case / "sha256.json").read_bytes() == original
