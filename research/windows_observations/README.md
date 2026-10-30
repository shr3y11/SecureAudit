# Windows observations — run 40939421976 (2026-10-29 UTC)

Genuine Windows executions of the SecureAudit collectors, run under
the protocol in `docs/RESEARCH_VALIDATION.md`. Full raw captures
(scan JSONs, native before/after references, HTML reports, hashes,
manual-review sheets) live on the **`data/windows-observations`**
branch under `windows-observations/run-40939421976/`.

## Environment (from the committed lab record)

- **Windows Server 2025 Datacenter**, version 10.0.26100, 64-bit —
  a GitHub-hosted `windows-latest` runner (Microsoft-hosted image).
- PowerShell 5.1.26100.33648 · Python 3.12.10 · repo commit `28233be`
- Operator: the `Windows observations` workflow; the capture tool
  itself changed no settings — workflow steps prepared and restored
  each configuration change and recorded the resulting state.

**Provenance limit:** this is a hosted runner, *not* the project's lab
VM. The readings are genuine for this machine. A lab-VM replication
(Windows 11, snapshot cases) remains separate future work, and the
protocol's independent manual review (`manual-review.csv`,
status `PENDING_INDEPENDENT_REVIEW`) is still pending — the agreement
column below is an observed comparison of the two committed
artifacts (scanner output vs the native reference capture), not that
review.

## Results

Baseline, administrator, 3 repeats — **identical in all three**:

| Check | Scanner | Native reference | Agree |
|---|---|---|---|
| WIN-FW-001 | Pass (Domain/Private/Public = True) | All profiles Enabled = 1 | ✅ |
| WIN-DEF-001 | Pass (AntivirusEnabled = True) | AntivirusEnabled = true | ✅ |
| WIN-BL-001 | Fail (FullyDecrypted) | ProtectionStatus = 0, VolumeStatus = 0 | ✅ |
| WIN-GUEST-001 | Pass (Guest disabled) | Guest Enabled = false | ✅ |
| WIN-SMB1-001 | Pass (SMB1Protocol disabled) | Feature state = disabled | ✅ |

Evidence decision for every baseline repeat: **ABOVE**, bounds
[80.0, 80.0] at 100% baseline coverage (4 of 5 checks pass; the
interval is a single point because every baseline check was
assessed).

Configured cases:

| Case | Preparation (recorded) | Scanner reading | Verdict |
|---|---|---|---|
| Firewall failure | Domain profile Enabled = False | **Fail** — "Domain=False, Private=True, Public=True" | ✅ behaves as specified |
| Guest failure | Guest Enabled = True | **Fail** | ✅ behaves as specified |
| Selective scan | Baseline, WIN-FW-001 only | Pass; baseline coverage 20%, bounds [20, 100], decision **UNRESOLVED** | ✅ exactly the protocol's prediction |
| Defender "failure" | RealTimeProtectionEnabled = False achieved via `Set-MpPreference` | **Pass** | ⚠️ see finding |

## Finding — the Defender case tests a narrower objective than it names

Disabling real-time monitoring did not (and by design cannot) flip
WIN-DEF-001: the check's stated objective is `AntivirusEnabled`, which
stayed `true` throughout, and the native reference in the same capture
shows both values side by side (AntivirusEnabled = true,
RealTimeProtectionEnabled = false). The scanner is consistent with
its objective; the case name overpromises. Two honest consequences:

1. The protocol's `AntivirusEnabled = false` state was **not
   achieved** on this runner (no supported, safe way to fully disable
   the AV there), so that case is reported *not executed* in its
   strict form.
2. Anyone reading a WIN-DEF-001 Pass must understand it asserts
   "antivirus enabled", **not** "real-time protection on". The paper
   states this explicitly; a future check revision could assess both
   properties and say so in its name.

## Cases not executed (with reasons, per protocol)

- **Standard user (unelevated):** the hosted runner session is
  administrative; a genuine unelevated capture needs the lab VM or a
  separate logon arrangement. Not simulated.
- **BitLocker protection ON (Pass case):** cannot be enabled on the
  hosted runner (TPM/reboot constraints). The OFF state is the
  baseline reading above.
- **SMBv1 enabled (Fail case):** enabling the optional feature
  requires a reboot the runner session cannot perform.
- **Defender AntivirusEnabled = false:** see the finding above.

## Platform consequence

All five collectors returned structured readings on this Server 2025 host,
consistent with the captured native references for the executed cases. This
is limited execution evidence, pending independent review; Server 2025
was not previously a listed platform. Following the project's rule —
list a platform only where a check was actually observed —
`Windows Server 2025` has been added to each check's
`supported_platforms` in `checks/catalog.json`.

## Preservation correction (30 October 2026)

The acquisition manifests do **not** verify the retained data branch bytes.
All five cases reference an absent `scans.db`; retained text was converted from
CRLF to LF by Git. Reintroducing CRLF reproduces the original text hashes, but
this explanation does not recover the missing databases or certify provenance.
The original manifests are preserved unchanged on data commit
`b13c644999e933d24d183890a20b84e9c75701a5`.

`retained_inventory.json` is a derivative index of available bytes, including
missing members and both hash comparisons. Recreate it from that pinned checkout:

```text
python tools/inventory_retained_captures.py PATH/windows-observations/run-40939421976 --source-commit b13c644999e933d24d183890a20b84e9c75701a5 --output retained_inventory.json
```

Future capture cases create a verified `*.capture.zip` before Git processing,
including SQLite and exact file bytes. This does not retroactively repair this
run. A new byte-preserved Windows replication remains pending.

The run contains seven executions and 19 readings on one machine. No Error
outcomes or genuine standard-user runs were observed; no field error rate or
privilege effect is established. The native-reference agreement above is an
artifact comparison, pending human independent review.
