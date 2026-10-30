"""Capture real Windows scanner evidence without changing system settings.

Run from an authorized lab VM. Raw native references share some Windows APIs
with collectors, so manual independent review is required before accuracy claims.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from os import environ
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.database import get_scan, save_scan
from core.evidence import make_context
from core.reporting import write_html_report
from core.scanner import load_catalog, run_check
from core.scoring import calculate_score
from tools.capture_archive import seal_capture, write_json


def reference():
    process = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
         "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "tools/collect_reference.ps1")],
        capture_output=True, text=True, encoding="utf-8-sig", errors="replace",
        timeout=120, check=True, shell=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return json.loads(process.stdout)


def main():
    catalog = load_catalog()
    ids = [c["id"] for c in catalog["checks"] if c["enabled"]]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True, help="Lab case label, e.g. baseline-admin")
    parser.add_argument("--snapshot-id", required=True, help="VM snapshot identifier from the lab record")
    parser.add_argument("--output", type=Path, required=True, help="New output folder, never overwritten")
    parser.add_argument("--select", nargs="+", choices=ids, default=ids)
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Real evidence capture requires Windows. No VM results were generated.")
    if not 1 <= args.repeat <= 10:
        parser.error("repeat must be between 1 and 10")
    context = make_context(catalog, args.select)
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "case.json", {
        "case_id": args.case_id, "snapshot_id": args.snapshot_id,
        "python": platform.python_version(), "platform": platform.platform(),
        "provenance": {key: environ.get(key) for key in
                       ("GITHUB_SHA", "GITHUB_RUN_ID", "RUNNER_OS", "ImageOS", "ImageVersion")},
        "catalog_context": context, "review_status": "PENDING_INDEPENDENT_REVIEW"})
    review_rows = []
    for repeat in range(1, args.repeat + 1):
        folder = args.output / f"repeat-{repeat}"
        folder.mkdir()
        before = reference()
        started = datetime.now(timezone.utc).isoformat()
        results = [run_check(cid) for cid in args.select]
        ended = datetime.now(timezone.utc).isoformat()
        after = reference()
        write_json(folder / "reference-before.json", before)
        write_json(folder / "reference-after.json", after)
        database = args.output / "scans.db"
        sid = save_scan(hostname=platform.node(), results=results, summary=calculate_score(results),
                        started_at_utc=started, completed_at_utc=ended,
                        database_path=database, evidence_context=context)
        scan = get_scan(sid, database)
        write_json(folder / "scan.json", scan)
        write_html_report(scan, output_directory=folder)
        for row in results:
            review_rows.append({"repeat": repeat, "check_id": row["check_id"],
                                "scanner_status": row["status"], "reference_status": "",
                                "second_interface_evidence": "", "reviewer": "",
                                "reviewed_at_utc": "", "notes": ""})
    with (args.output / "manual-review.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=review_rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(review_rows)
    archive = seal_capture(args.output)
    print(f"Byte-preserving capture archive: {archive}")
    print(f"Captured {len(review_rows)} check readings. Independent manual review is pending.")


if __name__ == "__main__":
    main()
