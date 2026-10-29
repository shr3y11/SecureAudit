#!/usr/bin/env bash
# LIN-GUEST-001 — Guest account absent or disabled.
set -u
export CHECK_ID="LIN-GUEST-001"
export CHECK_NAME="Guest Account Disabled"
export EXPECTED="No enabled guest account with an interactive shell exists"
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

if [ ! -r /etc/passwd ]; then
  ERROR_MSG="/etc/passwd is not readable."
else
  line="$(grep '^guest:' /etc/passwd || true)"
  if [ -z "$line" ]; then
    STATUS="Pass"; OBSERVED="No guest account present"; EVIDENCE="guest=absent"
  else
    shell="$(printf '%s' "$line" | awk -F: '{print $NF}')"
    EVIDENCE="guest=present; shell=${shell}"
    case "$shell" in
      *nologin*|*false) STATUS="Pass"; OBSERVED="Guest account exists but its shell is ${shell} (disabled)" ;;
      *) STATUS="Fail"; OBSERVED="Guest account is enabled with shell ${shell}" ;;
    esac
  fi
fi
finish
