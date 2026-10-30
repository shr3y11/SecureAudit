# Windows validation protocol

## Purpose and current evidence

The executed study tests aggregate reporting semantics. This protocol tests
whether real scanner readings and saved reports behave as specified on an
authorized lab Windows VM. It has not yet produced field results. Linux tests
of mocked capture files do not count as Windows validation.

## Lab record

Record VM platform, snapshot identifier, OS edition/build, Python version,
Windows PowerShell version/bitness, privilege level, catalog version/digest,
repository commit, date, and operator/reviewer. Use a disposable VM snapshot
for intentional configuration changes. Do not change a production endpoint.

Start with Windows 11 Pro (or record the actual supported edition). A second
OS build such as Server 2022 can be a separate replication, not a claim of
coverage until executed. Unsupported features remain Error, not Fail.

## Cases

Run three repetitions per case and record each repetition separately. Repeated
readings of one VM do not constitute independent endpoints.

| Case | Snapshot/configuration | Required comparison |
| --- | --- | --- |
| Baseline, administrator | Operator records all five actual native states | Every check against its exact objective |
| Firewall failure | Lab snapshot with one returned firewall profile disabled | All-profile enablement versus original profile readings |
| Defender failure | Supported lab state with AntivirusEnabled false | Narrow antivirus objective, separate real-time protection reading |
| BitLocker failure | Lab snapshot with OS-drive ProtectionStatus Off | Protection state, not encryption percentage alone |
| Guest failure | Lab snapshot with built-in RID-501 account enabled | Account identity by SID even after rename |
| SMBv1 failure | Isolated lab snapshot with SMB1Protocol Enabled | Exact optional-feature state |
| Standard user | Same baseline snapshot, unelevated console | Record actual errors; never assume which checks must error |
| Selective scan | Same baseline, select firewall only | Selected coverage can be 100%, baseline coverage only 20% |

The capture runner makes no configuration changes. A lab operator prepares
and restores snapshots separately. If a case cannot be created, report it as
not executed with its reason. Never fill a missing case with a generated vector.

## Capture commands

Check out the research feature branch, open 64-bit Windows PowerShell, and
run these commands from the repository root. Use a fresh output folder for
each case; the runner refuses to overwrite an existing folder.

```powershell
python -m pip install pytest==8.4.2
python -m pytest -q
python research/run_study.py
python tools/validate_windows.py --case-id baseline-admin --snapshot-id YOUR_SNAPSHOT --output lab-results/baseline-admin
python tools/validate_windows.py --case-id firewall-only --snapshot-id YOUR_SNAPSHOT --output lab-results/firewall-only --select WIN-FW-001
```

Use an unelevated console for the standard-user case. It deliberately bypasses
the desktop's elevation request, using the same approved `run_check` function.

Each case creates `case.json`, SQLite history, before/after native reference
JSON, normalized scan JSON, HTML reports, a blank `manual-review.csv`, and an
initial SHA-256 manifest. Review edits change the review file's hash; retain the
initial manifest and record a second manifest after review. Neither manifest
proves provenance against a malicious host.

Each completed case also creates a sibling `CASE.capture.zip` before Git can
normalize text or exclude SQLite. This archive is the authoritative byte copy;
`sha256.json` uses POSIX paths and JSON/CSV are explicitly written with LF.
Verify with `python tools/capture_archive.py PATH/CASE.capture.zip`. The verifier
requires the database, exact manifest membership and matching file checksums.
Commit/archive the ZIP (marked binary in `.gitattributes`) and keep a trusted
archive digest separately. Never modify a sealed archive to add review verdicts;
retain it and publish a separately identified review supplement.

Historical run 40939421976 predates this fix: its retained text differs from the
original manifests after Git normalization, and its referenced databases were
excluded by `.gitignore`. See `research/windows_observations/retained_inventory.json`
for an inventory of the retained bytes. It is a derivative index, not recovery
of the missing databases or proof that the original manifests verify.

## Independent review

Native reference capture uses separately written collection code, but shares
Windows cmdlets/APIs with the scanners. This is corroboration, not an independent
ground-truth implementation. A second person must inspect a separate interface
where available and cite its screenshot/record in the review CSV:

| ID | Exact objective | Suggested corroboration |
| --- | --- | --- |
| WIN-FW-001 | All returned firewall profiles enabled | Windows Defender Firewall with Advanced Security properties |
| WIN-DEF-001 | AntivirusEnabled true for Microsoft Defender | Windows Security status plus native reference reading |
| WIN-BL-001 | OS-drive protection On | BitLocker control panel / `manage-bde -status` without recovery-key output |
| WIN-GUEST-001 | Built-in SID ending -501 disabled | Local Users and Groups, verified against account SID |
| WIN-SMB1-001 | SMB1Protocol Disabled or DisabledWithPayloadRemoved | Windows Features / DISM feature information |

Review the exact scanner predicates in `checks/powershell`. Treat transitional,
unavailable, conflicting, or changed before/after states as undetermined. Record
the reviewer and review time. Avoid capturing credentials or recovery keys.

## Report results

Keep raw per-case readings and denominators. Report determined-reference
agreements/disagreements and scanner Errors separately. Do not convert Error
into an inaccurate binary prediction. For report correctness, independently
count P/F/E/O and verify baseline membership, both coverages, bounds, and labels.
Check the saved HTML and a reopened historical scan. A known unresolved case
must remain unresolved after reopening. Include actual executed OS builds only.

Any accuracy percentage must name the objective, number of determined cases,
and limitations of the shared native APIs. Add VM outcomes to the manuscript
only after independent review. A usability or time-saving claim needs its own
assessor study and is not supported by these captures.
