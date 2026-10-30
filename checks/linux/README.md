# Experimental Linux collectors

Written fresh in October 2026 for SecureAudit. The archived prototype
scanner files (`archive/fastapi-prototype/scanners/...`) are **0-byte
placeholders** — there was no implementation in them to revive, so
these collectors were written from scratch against the same JSON result
contract as the Windows PowerShell collectors:

`check_id, check_name, expected_value, observed_value, status
(Pass/Fail/Error), evidence, error_message, timestamp_utc`

## Checks

| ID | What it assesses | Mechanism |
|----|------------------|-----------|
| LIN-FW-001 | Host firewall active | ufw, firewalld, or nftables service state |
| LIN-ENC-001 | Disk encryption present | `lsblk` reports a `crypto_LUKS` device |
| LIN-GUEST-001 | Guest account disabled | `/etc/passwd` guest entry absent or non-interactive shell |
| LIN-SSH-001 | Root password SSH login disabled | Effective `PermitRootLogin` (first match, sshd semantics) |
| LIN-UPD-001 | Automatic security updates on | unattended-upgrades (APT) or dnf-automatic (DNF) |

Run them with:

```bash
python tools/run_linux_checks.py            # all enabled checks
python tools/run_linux_checks.py LIN-FW-001 # one check
```

Semantics match the Windows side: a check that cannot be assessed
returns **Error**, never Fail. For example, a host with no supported
firewall manager reports Error for LIN-FW-001 — SecureAudit does not
pretend to know its firewall state.

## Status and limits

- **Experimental.** Verified so far on Ubuntu 24.04 only.
- **No framework mappings are claimed.** Every entry's mapping is
  "Pending validation", the same honest status as the unvalidated
  Windows checks. Validating CIS Benchmark for Linux mappings is
  separate research work.
- Collectors need `bash` and `python3` on the target (used only to emit
  the JSON contract safely). They change nothing on the host.
- macOS is **not** covered: its firewall, disk-encryption (FileVault),
  and update mechanisms are different (`socketfilterfw`, `fdesetup`,
  `softwareupdate`) and need their own collectors, not ports of these.
