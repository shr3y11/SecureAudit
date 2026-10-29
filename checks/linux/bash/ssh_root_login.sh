#!/usr/bin/env bash
# LIN-SSH-001 — Password-based root SSH login disabled.
set -u
export CHECK_ID="LIN-SSH-001"
export CHECK_NAME="SSH Root Password Login Disabled"
export EXPECTED="sshd does not allow password-based root login (PermitRootLogin no or prohibit-password)"
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

if ! command -v sshd >/dev/null 2>&1 && [ ! -f /etc/ssh/sshd_config ]; then
  ERROR_MSG="OpenSSH server does not appear to be installed on this host; there is no sshd configuration to assess."
else
  # sshd uses the FIRST obtained value for most keywords.
  value="$(grep -h -i -m1 '^[[:space:]]*PermitRootLogin' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null | awk '{print tolower($2)}')"
  if [ -z "$value" ]; then
    # No explicit setting: the compiled default is prohibit-password.
    STATUS="Pass"; OBSERVED="PermitRootLogin not set; sshd default (prohibit-password) applies"
    EVIDENCE="permit_root_login=default(prohibit-password)"
  else
    EVIDENCE="permit_root_login=${value}"
    case "$value" in
      no|prohibit-password|forced-commands-only) STATUS="Pass"; OBSERVED="PermitRootLogin is ${value}" ;;
      yes) STATUS="Fail"; OBSERVED="PermitRootLogin is yes (root login, including password, allowed)" ;;
      *) ERROR_MSG="Unrecognised PermitRootLogin value: ${value}" ;;
    esac
  fi
fi
finish
