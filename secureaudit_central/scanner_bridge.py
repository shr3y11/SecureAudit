"""Reuse the Milestone 4 scanner without extending its execution boundary."""
import json
from datetime import datetime, timezone
from core.scanner import load_catalog, run_check
from core.scoring import calculate_score
from .schemas import EvidenceInput


def collect_local_evidence(submission_id):
    catalog = load_catalog()
    approved = [c for c in catalog["checks"] if c["enabled"]]
    results = [run_check(check["id"]) for check in approved]
    calculate_score(results)  # Reuse validation from the original scoring engine.
    checks = []
    for check, result in zip(approved, results):
        detail = json.dumps({"expected_value": result["expected_value"],
                             "observed_value": result["observed_value"],
                             "evidence": result["evidence"],
                             "error_message": result["error_message"]}, ensure_ascii=False, indent=2)
        checks.append({"check_id": result["check_id"], "title": result["check_name"],
                       "status": result["status"], "detail": detail[:10000],
                       "severity": check.get("severity", "Medium"), "scanner_result": result})
    return EvidenceInput(submission_id=submission_id, collected_at=datetime.now(timezone.utc), checks=checks)
