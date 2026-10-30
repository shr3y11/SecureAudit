import sqlite3
import zipfile

import pytest

from tools.capture_archive import seal_capture, verify_capture, write_json


def test_capture_preserves_database_and_portable_text(tmp_path):
    folder = tmp_path / "case"
    (folder / "repeat-1").mkdir(parents=True)
    write_json(folder / "repeat-1/reference.json", {"status": "Pass"})
    assert b"\r\n" not in (folder / "repeat-1/reference.json").read_bytes()
    with sqlite3.connect(folder / "scans.db") as db:
        db.execute("CREATE TABLE retained (reading TEXT)")
        db.execute("INSERT INTO retained VALUES ('real bytes')")
    archive = seal_capture(folder)
    manifest = verify_capture(archive)
    assert "repeat-1/reference.json" in manifest
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.read("scans.db") == (folder / "scans.db").read_bytes()


@pytest.mark.parametrize("attack", ["replace", "remove", "extra", "traversal", "duplicate"])
def test_capture_rejects_changed_or_ambiguous_members(tmp_path, attack):
    folder = tmp_path / "case"
    folder.mkdir()
    (folder / "scans.db").write_bytes(b"database fixture")
    archive = seal_capture(folder)
    with zipfile.ZipFile(archive) as bundle:
        members = {n: bundle.read(n) for n in bundle.namelist()}
    if attack == "replace":
        members["scans.db"] = b"changed"
    elif attack == "remove":
        members.pop("scans.db")
    elif attack == "extra":
        members["uncommitted.txt"] = b"extra"
    elif attack == "traversal":
        members["../outside"] = b"unsafe"
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, data in members.items():
            bundle.writestr(name, data)
        if attack == "duplicate":
            with pytest.warns(UserWarning):
                bundle.writestr("scans.db", b"ambiguous")
    with pytest.raises(ValueError):
        verify_capture(archive)


def test_incomplete_capture_not_sealed(tmp_path):
    with pytest.raises(ValueError, match="scans.db"):
        seal_capture(tmp_path)
