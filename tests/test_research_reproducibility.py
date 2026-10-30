"""Reproducibility guard for the committed research artifacts.

The study's committed outputs (CSVs, summary.json, sha256.json) must be
reproducible byte-for-byte on any machine: re-running the study and
diffing is how a reviewer checks the numbers. That only works if no
environment-specific value (interpreter version, platform) leaks into
a hashed artifact — exactly the leak this test guards against.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "research" / "results"


def test_summary_contains_no_environment_fields():
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    assert "python_version" not in summary
    assert "platform" not in summary
    assert "environment" not in summary


def test_committed_hashes_match_committed_files():
    hashes = json.loads((RESULTS / "sha256.json").read_text(encoding="utf-8"))
    assert hashes, "sha256.json must not be empty"
    research_dir = ROOT / "research"  # sha256.json paths are relative to here
    for relative, expected in hashes.items():
        path = research_dir / relative
        assert path.is_file(), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative
    # Provenance is not a result: it must stay outside the hash set.
    assert not any(name.endswith("environment.json") for name in hashes)
