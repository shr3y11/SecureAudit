"""Tamper Lab regression tests: the detection matrix is the result.

These tests re-run the experiments in research/tamper_lab.py against
fresh instances and pin the outcomes the paper reports — including
the negative ones. If a future change silently alters what the
system can or cannot detect, this file fails, which is the point.
"""
from research.tamper_lab import run_experiments, Lab, _payload
import hashlib
import io
import zipfile

import pytest

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture(scope="module")
def results():
    return {e["attack"]: e for e in run_experiments()}


def test_all_seven_experiments_ran(results):
    assert set(results) == {
        "modify_evidence", "modify_and_reforge_hash", "delete_latest_assessment",
        "replay_identical_submission", "replay_same_id_altered_content",
        "replay_new_id_same_content", "forge_bundle_and_manifest",
    }


def test_untouched_system_does_not_trigger_checkpoint(tmp_path):
    lab = Lab(tmp_path)
    try:
        assert not lab.internal_detects()
        assert not lab.checkpoint_detects()
        assert not lab.checkpoint_detects()
        with zipfile.ZipFile(io.BytesIO(lab.checkpoint_bundle)) as z:
            assert hashlib.sha256(z.read("manifest.json")).hexdigest() == lab.checkpoint["bundle_manifest_sha256"]
    finally:
        lab.client.__exit__(None, None, None)


def test_legitimate_new_evidence_changes_checkpoint_but_is_not_tampering(tmp_path):
    lab = Lab(tmp_path)
    try:
        response = lab.client.post(f"/api/endpoints/{lab.endpoint_id}/evidence", json=_payload(5))
        assert response.status_code == 200
        assert lab.checkpoint_detects()  # drift, not a maliciousness classifier
        assert not lab.internal_detects()
        lab.checkpoint = lab._take_checkpoint()
        assert not lab.checkpoint_detects()
    finally:
        lab.client.__exit__(None, None, None)


def test_naive_modification_is_detected_internally(results):
    assert results["modify_evidence"]["internal_verify"] == "detected"


def test_reforged_hash_defeats_internal_verification_only(results):
    """The lab's central negative result: internal checks are not enough."""
    e = results["modify_and_reforge_hash"]
    assert e["internal_verify"] == "not_detected"
    assert e["checkpoint"] == "detected"


def test_deletion_is_invisible_internally_but_not_to_a_checkpoint(results):
    e = results["delete_latest_assessment"]
    assert e["internal_verify"] == "not_detected"
    assert e["checkpoint"] == "detected"


def test_replays_are_neutralised_or_visible(results):
    identical = results["replay_identical_submission"]
    assert identical["api_status"] == 200 and identical["rows_added"] == 0
    altered = results["replay_same_id_altered_content"]
    assert altered["api_status"] == 409
    clone = results["replay_new_id_same_content"]
    assert clone["api_status"] == 200 and clone["rows_added"] == 1
    assert clone["checkpoint"] == "detected"


def test_forged_bundle_is_self_consistent_yet_exposed_by_checkpoint(results):
    e = results["forge_bundle_and_manifest"]
    assert e["bundle_self_check"] == "consistent"
    assert e["checkpoint"] == "detected"
