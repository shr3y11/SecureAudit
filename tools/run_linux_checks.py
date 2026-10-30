"""Run the experimental Linux collectors and print scored results.

Usage:  python tools/run_linux_checks.py [CHECK_ID ...]

With no arguments every enabled check in checks/linux/catalog.json
runs. Each collector emits the same JSON result contract as the Windows
PowerShell collectors; results are validated with the same contract
validator the Windows scanner uses, scored with core.scoring, and
printed as one JSON document. This runner is experimental: the Linux
checks carry no framework mappings yet.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.scanner import build_error_result, load_catalog, validate_and_normalize_result  # noqa: E402
from core.scoring import calculate_score  # noqa: E402

CATALOG = ROOT / "checks" / "linux" / "catalog.json"
SCRIPTS = ROOT / "checks" / "linux" / "bash"
TIMEOUT = 30


def run_linux_check(check: dict) -> dict:
    script = SCRIPTS / check["script"]
    try:
        process = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True,
            timeout=TIMEOUT, check=False, shell=False,
        )
        if process.returncode != 0:
            raise ValueError(f"collector exited with code {process.returncode}: {process.stderr.strip()}")
        return validate_and_normalize_result(json.loads(process.stdout), check)
    except Exception as exc:  # execution problems become Error results, never Fail
        return build_error_result(check, str(exc))


def main() -> int:
    catalog = load_catalog(CATALOG)
    wanted = sys.argv[1:]
    checks = [c for c in catalog["checks"] if c["enabled"] and (not wanted or c["id"] in wanted)]
    if wanted and len(checks) != len(set(wanted)):
        print(f"Unknown or disabled check ID in {wanted}", file=sys.stderr)
        return 2
    results = [run_linux_check(check) for check in checks]
    print(json.dumps({"catalog_version": catalog["catalog_version"],
                      "summary": calculate_score(results),
                      "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
