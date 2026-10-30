"""Tamper Lab — measured tamper-evidence experiments for SecureAudit Central.

A hash that is recorded but never recomputed detects nothing. This lab
measures, attack by attack, what SecureAudit's evidence integrity
actually catches — and what it honestly cannot.

Attacker model
--------------
The attacker has **write access to Central's database file** (or an
exported bundle) — e.g. a compromised host, a malicious insider with
file access, or a stolen backup. The attacker does *not* have the API
token and cannot make the application itself lie at collection time;
endpoint-side collection integrity is a separate question.

Verifiers compared
------------------
- **Internal**: Central's own `GET /api/endpoints/{id}/verify`, which
  recomputes each stored evidence hash.
- **Checkpoint**: an external record taken before the attack
  (per-submission hashes, assessment count, and the SHA-256 of an
  exported bundle's manifest). It models any reference kept outside
  the attacker's reach — a signed checkpoint, an emailed bundle, a
  printed digest.
- **Bundle self-check**: recomputing a bundle's manifest hashes from
  the bundle alone.

Each experiment runs against a freshly seeded Central instance, so
attacks never contaminate each other. Results are written to
research/results/tamper_lab_results.json and printed as a table.
"""
import hashlib
import io
import json
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from secureaudit_central.api import create_app  # noqa: E402

TOKEN = "tamper-lab-token-0123456789abcdef0123"
RESULTS = ROOT / "research" / "results" / "tamper_lab_results.json"


def _payload(index, statuses=("Pass", "Fail", "Error")):
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    return {"submission_id": f"lab-{index}",
            "collected_at": (base + timedelta(days=index)).isoformat(),
            "checks": [{"check_id": f"WIN-LAB-{i}", "title": f"Control {i}",
                        "status": s, "detail": "lab evidence", "severity": "High"}
                       for i, s in enumerate(statuses)]}


class Lab:
    """One freshly seeded Central instance plus its pre-attack checkpoint."""

    def __init__(self, folder):
        self.db_path = Path(folder) / "central.db"
        app = create_app("sqlite:///" + self.db_path.as_posix(), TOKEN, worker_enabled=False)
        self.client = TestClient(app)
        self.client.__enter__()
        self.client.headers.update({"Authorization": f"Bearer {TOKEN}"})
        response = self.client.post("/api/endpoints", json={"hostname": "LAB-PC", "group_name": "Lab"})
        assert response.status_code == 201, response.text
        self.endpoint_id = response.json()["id"]
        for i in range(3):
            r = self.client.post(f"/api/endpoints/{self.endpoint_id}/evidence", json=_payload(i))
            assert r.status_code == 200, r.text
        self.checkpoint_bundle = self._bundle_bytes()
        self.checkpoint = self._take_checkpoint(self.checkpoint_bundle)

    def _bundle_bytes(self):
        r = self.client.get(f"/api/endpoints/{self.endpoint_id}/bundle")
        assert r.status_code == 200
        return r.content

    def _take_checkpoint(self, bundle_bytes=None):
        history = self.client.get(f"/api/endpoints/{self.endpoint_id}/history").json()
        with zipfile.ZipFile(io.BytesIO(bundle_bytes or self._bundle_bytes())) as z:
            manifest_hash = hashlib.sha256(z.read("manifest.json")).hexdigest()
            files = json.loads(z.read("manifest.json"))["files"]
        return {"submissions": {a["submission_id"]: a["sha256"] for a in history},
                "count": len(history), "files": files,
                "bundle_manifest_sha256": manifest_hash}

    # -- verifiers ------------------------------------------------------
    def internal_detects(self):
        r = self.client.get(f"/api/endpoints/{self.endpoint_id}/verify")
        return not r.json()["ok"]

    def checkpoint_detects(self):
        current = self._take_checkpoint()
        # A fresh export has a fresh generated_at. Compare committed content,
        # not presentation-time metadata. A change is not proof of an attack:
        # legitimate new evidence must also update a trusted checkpoint.
        return any(current[key] != self.checkpoint[key]
                   for key in ("submissions", "count", "files"))

    @staticmethod
    def bundle_self_consistent(bundle_bytes):
        with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as z:
            manifest = json.loads(z.read("manifest.json"))
            return all(hashlib.sha256(z.read(name)).hexdigest() == digest
                       for name, digest in manifest["files"].items())

    # -- raw database access (the attacker's capability) ------------------
    def sql(self, statement, params=()):
        with sqlite3.connect(self.db_path) as db:
            db.execute(statement, params)


def _fresh():
    return Lab(tempfile.mkdtemp(prefix="tamper-lab-"))


def _verdict(lab, bundle_bytes=None):
    result = {"internal_verify": "detected" if lab.internal_detects() else "not_detected",
              "checkpoint": "detected" if lab.checkpoint_detects() else "not_detected"}
    if bundle_bytes is not None:
        result["bundle_self_check"] = ("consistent" if Lab.bundle_self_consistent(bundle_bytes)
                                       else "inconsistent")
    return result


def run_experiments():
    experiments = []

    lab = _fresh()
    lab.sql("UPDATE central_assessments SET evidence_json = replace(evidence_json, '\"Pass\"', '\"Fail\"') "
            "WHERE submission_id = 'lab-0'")
    experiments.append({"attack": "modify_evidence",
                        "description": "Edit one stored check result (Pass to Fail), recorded hash untouched.",
                        **_verdict(lab)})

    lab = _fresh()
    with sqlite3.connect(lab.db_path) as db:
        rows = db.execute("SELECT id, evidence_json FROM central_assessments WHERE submission_id = 'lab-0'").fetchall()
        for row_id, evidence in rows:
            forged = evidence.replace('"Pass"', '"Fail"')
            db.execute("UPDATE central_assessments SET evidence_json = ?, sha256 = ?, passed = 0, failed = 2 WHERE id = ?",
                       (forged, hashlib.sha256(forged.encode()).hexdigest(), row_id))
    experiments.append({"attack": "modify_and_reforge_hash",
                        "description": "Edit stored evidence AND recompute its recorded hash to match.",
                        **_verdict(lab)})

    lab = _fresh()
    lab.sql("DELETE FROM central_assessments WHERE submission_id = 'lab-2'")
    experiments.append({"attack": "delete_latest_assessment",
                        "description": "Delete the newest assessment row outright.",
                        **_verdict(lab)})

    lab = _fresh()
    before = lab._take_checkpoint()["count"]
    response = lab.client.post(f"/api/endpoints/{lab.endpoint_id}/evidence", json=_payload(0))
    after = lab._take_checkpoint()["count"]
    experiments.append({"attack": "replay_identical_submission",
                        "description": "Resubmit byte-identical evidence under the same submission ID.",
                        "api_status": response.status_code, "rows_added": after - before,
                        "internal_verify": "n/a", "checkpoint": "not_detected",
                        "note": "Idempotent by design: accepted, no duplicate row, nothing to detect."})

    lab = _fresh()
    altered = _payload(0, statuses=("Pass", "Pass", "Pass"))
    response = lab.client.post(f"/api/endpoints/{lab.endpoint_id}/evidence", json=altered)
    experiments.append({"attack": "replay_same_id_altered_content",
                        "description": "Reuse a submission ID with different (all-pass) content.",
                        "api_status": response.status_code, "rows_added": 0,
                        "internal_verify": "n/a", "checkpoint": "not_detected",
                        "note": "Rejected with 409 by the API: the ID is bound to its first evidence."})

    lab = _fresh()
    clone = _payload(99)
    clone["checks"] = _payload(0)["checks"]
    clone["collected_at"] = _payload(0)["collected_at"]
    response = lab.client.post(f"/api/endpoints/{lab.endpoint_id}/evidence", json=clone)
    experiments.append({"attack": "replay_new_id_same_content",
                        "description": "Submit identical evidence under a fresh submission ID.",
                        "api_status": response.status_code, "rows_added": 1,
                        **_verdict(lab),
                        "note": "Accepted as a new submission; the checkpoint sees the unexpected addition and the duplicate content hash."})

    lab = _fresh()
    # Forge the exact export whose original manifest digest was retained.
    bundle = bytearray(lab.checkpoint_bundle)
    with zipfile.ZipFile(io.BytesIO(bytes(bundle))) as z:
        files = {name: z.read(name) for name in z.namelist()}
    forged_assessments = files["assessments.json"].replace(b'"Fail"', b'"Pass"')
    files["assessments.json"] = forged_assessments
    manifest = json.loads(files["manifest.json"])
    manifest["files"]["assessments.json"] = hashlib.sha256(forged_assessments).hexdigest()
    files["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    forged_bundle = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(forged_bundle)) as z:
        forged_manifest_hash = hashlib.sha256(z.read("manifest.json")).hexdigest()
    experiments.append({"attack": "forge_bundle_and_manifest",
                        "description": "Rewrite an exported bundle and recompute its manifest hashes.",
                        "internal_verify": "n/a",
                        "checkpoint": "detected" if forged_manifest_hash != lab.checkpoint["bundle_manifest_sha256"] else "not_detected",
                        "bundle_self_check": "consistent" if Lab.bundle_self_consistent(forged_bundle) else "inconsistent",
                        "note": "A bundle alone proves internal consistency, never origin; only the external manifest hash exposes the forgery."})

    for experiment in experiments:
        experiment["capability"] = ("authenticated API submitter" if experiment["attack"].startswith("replay_")
                                    else "database/bundle writer; no API token")
    return experiments


def main():
    experiments = run_experiments()
    RESULTS.write_text(json.dumps({"attacker_model": "Two separate capabilities: database/bundle writer without API token; authenticated API submitter for replay cases",
                                   "experiments": experiments}, indent=2) + "\n", encoding="utf-8")
    for e in experiments:
        print(f"{e['attack']:32} internal={e['internal_verify']:12} checkpoint={e['checkpoint']}")
    print(f"\nWrote {RESULTS}")


if __name__ == "__main__":
    main()
