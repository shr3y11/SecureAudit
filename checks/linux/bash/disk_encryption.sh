#!/usr/bin/env bash
# LIN-ENC-001 — LUKS disk encryption present.
set -u
export CHECK_ID="LIN-ENC-001"
export CHECK_NAME="Disk Encryption (LUKS) Present"
export EXPECTED="At least one block device is LUKS-encrypted"
export STATUS="Error" OBSERVED="Assessment could not be completed" ERROR_MSG="" EVIDENCE=""

finish() {
  python3 - <<'PY'
import json, os
from datetime import datetime, timezone
evidence = [line for line in os.environ.get("EVIDENCE", "").splitlines() if line]
print(json.dumps({
    "check_id": os.environ["CHECK_ID"], "check_name": os.environ["CHECK_NAME"],
    "expected_value": os.environ["EXPECTED"], "observed_value": os.environ["OBSERVED"],
    "status": os.environ["STATUS"], "evidence": evidence,
    "error_message": os.environ.get("ERROR_MSG") or None,
    "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}))
PY
  exit 0
}

if ! command -v lsblk >/dev/null 2>&1; then
  ERROR_MSG="lsblk is not available on this host."
else
  table="$(lsblk -o TYPE,FSTYPE -n 2>/dev/null)"
  EVIDENCE="lsblk=$(printf '%s' "$table" | tr '\n' ';')"
  if printf '%s' "$table" | grep -q "crypto_LUKS"; then
    STATUS="Pass"; OBSERVED="LUKS-encrypted device present"
  else
    STATUS="Fail"; OBSERVED="No LUKS-encrypted device found"
  fi
fi
finish
