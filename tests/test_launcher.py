"""Tests for launcher access-key storage (audit finding #6).

The real DPAPI calls only exist on Windows, so the storage-format logic
is exercised everywhere with a reversible stand-in transform, and the
genuine DPAPI round-trip is covered by a Windows-only test.
"""
import os

import pytest

import launcher


@pytest.fixture
def fake_dpapi(monkeypatch):
    """Pretend to be Windows with a reversible DPAPI stand-in."""
    monkeypatch.setattr(launcher.os, "name", "nt")
    monkeypatch.setattr(launcher, "_dpapi_protect", lambda data: data[::-1])
    monkeypatch.setattr(launcher, "_dpapi_unprotect", lambda data: data[::-1])


def test_new_key_is_stored_dpapi_protected(tmp_path, fake_dpapi):
    token = launcher.access_key(tmp_path)
    assert len(token) >= 32
    stored = (tmp_path / "access.key").read_text(encoding="utf-8")
    assert stored.startswith(launcher._DPAPI_PREFIX)
    assert token not in stored, "the plaintext token must not appear in access.key"
    # A second start reads the same key back.
    assert launcher.access_key(tmp_path) == token


def test_legacy_plaintext_key_is_read_and_upgraded(tmp_path, fake_dpapi):
    legacy = "a" * 64
    (tmp_path / "access.key").write_text(legacy, encoding="utf-8")
    assert launcher.access_key(tmp_path) == legacy
    stored = (tmp_path / "access.key").read_text(encoding="utf-8")
    assert stored.startswith(launcher._DPAPI_PREFIX), "legacy key should be upgraded in place"
    assert launcher.access_key(tmp_path) == legacy


def test_short_key_is_rejected(tmp_path):
    (tmp_path / "access.key").write_text("too-short", encoding="utf-8")
    with pytest.raises(ValueError):
        launcher.access_key(tmp_path)


def test_plaintext_still_used_off_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher.os, "name", "posix")
    token = launcher.access_key(tmp_path)
    assert (tmp_path / "access.key").read_text(encoding="utf-8") == token


@pytest.mark.skipif(os.name != "nt", reason="DPAPI exists only on Windows")
def test_real_dpapi_round_trip():
    secret = b"secureaudit-dpapi-test" * 4
    assert launcher._dpapi_unprotect(launcher._dpapi_protect(secret)) == secret
