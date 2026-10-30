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
  out="$(ufw status 2>&1)"; rc=$?
  EVIDENCE="manager=ufw; report=${out}"
  if [ "$rc" -ne 0 ]; then
    ERROR_MSG="UFW status could not be read (exit ${rc}): ${out}"
  elif printf '%s\n' "$out" | grep -qiE '^Status:[[:space:]]+active[[:space:]]*$'; then
    STATUS="Pass"; OBSERVED="UFW firewall is active"
  elif printf '%s\n' "$out" | grep -qiE '^Status:[[:space:]]+inactive[[:space:]]*$'; then
    STATUS="Fail"; OBSERVED="UFW firewall is not active (${out})"
  else
    ERROR_MSG="Unrecognised UFW status output: ${out}"
  fi
elif command -v firewall-cmd >/dev/null 2>&1; then
  state="$(firewall-cmd --state 2>&1)"; rc=$?
  EVIDENCE="manager=firewalld; state=${state}"
  if [ "$rc" -eq 0 ] && [ "$state" = "running" ]; then
    STATUS="Pass"; OBSERVED="firewalld is running"
  elif [ "$state" = "not running" ]; then
    STATUS="Fail"; OBSERVED="firewalld state is ${state}"
  else
    ERROR_MSG="firewalld status could not be determined (exit ${rc}): ${state}"
  fi
elif command -v systemctl >/dev/null 2>&1; then
  for manager in nftables firewalld; do
    state="$(systemctl is-active "$manager" 2>&1)"; rc=$?
    EVIDENCE="${EVIDENCE}${manager}=${state}; "
    if [ "$rc" -eq 0 ] && [ "$state" = "active" ]; then
      STATUS="Pass"; OBSERVED="${manager} service is active"; break
    fi
  done
  if [ "$STATUS" = "Error" ]; then
    ERROR_MSG="No supported active firewall service could be established; service-manager errors do not prove a disabled firewall."
  fi
else
  ERROR_MSG="No supported firewall manager (ufw, firewalld, nftables service) could be assessed on this host."
  EVIDENCE="manager=none-detected"
fi
finish
