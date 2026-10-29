#!/usr/bin/env bash
# LIN-UPD-001 — Automatic security updates enabled.
set -u
export CHECK_ID="LIN-UPD-001"
export CHECK_NAME="Automatic Security Updates Enabled"
export EXPECTED="Automatic security updates are enabled (unattended-upgrades or dnf-automatic)"
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

if [ -d /etc/apt ]; then
  conf="/etc/apt/apt.conf.d/20auto-upgrades"
  if [ -f "$conf" ] && grep -q 'APT::Periodic::Unattended-Upgrade "1"' "$conf"; then
    STATUS="Pass"; OBSERVED="unattended-upgrades is enabled"; EVIDENCE="mechanism=unattended-upgrades; enabled=1"
  elif [ -f "$conf" ]; then
    STATUS="Fail"; OBSERVED="unattended-upgrades is configured off"; EVIDENCE="mechanism=unattended-upgrades; enabled=0"
  else
    ERROR_MSG="APT host without a 20auto-upgrades configuration; automatic update posture could not be determined."
    EVIDENCE="mechanism=apt; config=absent"
  fi
elif command -v dnf >/dev/null 2>&1; then
  if systemctl is-enabled --quiet dnf-automatic.timer 2>/dev/null || systemctl is-active --quiet dnf-automatic.timer 2>/dev/null; then
    STATUS="Pass"; OBSERVED="dnf-automatic timer is enabled/active"; EVIDENCE="mechanism=dnf-automatic"
  else
    STATUS="Fail"; OBSERVED="dnf-automatic timer is neither enabled nor active"; EVIDENCE="mechanism=dnf-automatic"
  fi
else
  ERROR_MSG="No supported update mechanism (APT or DNF) found on this host."
fi
finish
