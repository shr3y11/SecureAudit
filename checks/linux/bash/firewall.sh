#!/usr/bin/env bash
# LIN-FW-001 — Linux firewall active (ufw, firewalld, or nftables service).
set -u
export CHECK_ID="LIN-FW-001"
export CHECK_NAME="Linux Firewall Active"
export EXPECTED="A host firewall (ufw, firewalld, or nftables) is active"
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

if command -v ufw >/dev/null 2>&1; then
  out="$(ufw status 2>/dev/null | head -1)"
  EVIDENCE="manager=ufw; report=${out}"
  if printf '%s' "$out" | grep -qi "active"; then
    STATUS="Pass"; OBSERVED="UFW firewall is active"
  else
    STATUS="Fail"; OBSERVED="UFW firewall is not active (${out})"
  fi
elif command -v firewall-cmd >/dev/null 2>&1; then
  state="$(firewall-cmd --state 2>/dev/null || echo unknown)"
  EVIDENCE="manager=firewalld; state=${state}"
  if [ "$state" = "running" ]; then
    STATUS="Pass"; OBSERVED="firewalld is running"
  else
    STATUS="Fail"; OBSERVED="firewalld state is ${state}"
  fi
elif systemctl is-active --quiet nftables 2>/dev/null; then
  STATUS="Pass"; OBSERVED="nftables service is active"; EVIDENCE="manager=nftables-service; active=true"
elif systemctl is-active --quiet firewalld 2>/dev/null; then
  STATUS="Pass"; OBSERVED="firewalld service is active"; EVIDENCE="manager=firewalld-service; active=true"
else
  ERROR_MSG="No supported firewall manager (ufw, firewalld, nftables service) could be assessed on this host."
  EVIDENCE="manager=none-detected"
fi
finish
