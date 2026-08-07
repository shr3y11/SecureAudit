---
title: SecureAudit Windows MVP — Milestone 1 Development Log
project: SecureAudit
branch: feature/windows-mvp
milestone: Scanner, Scoring, SQLite Storage, and HTML Reporting
status: Complete
tests: 61 passed
latest_commit: b250020
tags:
  - secureaudit
  - windows
  - grc
  - compliance
  - powershell
  - python
  - sqlite
  - testing
---

# SecureAudit Windows MVP — Milestone 1 Development Log

> [!success] Milestone status
> This milestone is complete.
>
> SecureAudit can now:
>
> 1. Load an allow-listed catalog of Windows checks.
> 2. Run trusted PowerShell scanner modules.
> 3. Normalize results into `Pass`, `Fail`, or `Error`.
> 4. Calculate compliance score and assessment coverage.
> 5. Store scan history and detailed evidence in SQLite.
> 6. Generate a standalone local HTML compliance report.
>
> Final test result: **61 passed**
> Latest commit: **`b250020 feat(reporting): generate local HTML compliance reports`**

---

## 1. Quick Reference

### Repository state

| Item | Value |
|---|---|
| Repository | `SecureAudit` |
| Local path | `X:\icloud\iCloudDrive\Cyber\Projects\SecureAudit` |
| Active branch | `feature/windows-mvp` |
| Python environment | `.venv` |
| Python version used | Python `3.14.6` |
| Test framework | `pytest 8.4.2` |
| Final test count | `61 passed` |
| Latest milestone commit | `b250020` |
| Working tree after completion | Clean |
| Remote branch | `origin/feature/windows-mvp` |

### Final pipeline

```text
Approved catalog
      ↓
PowerShell checks
      ↓
Python scanner
      ↓
Normalized results
      ↓
Compliance scoring
      ↓
SQLite storage
      ↓
HTML report
```

### Result model

| Status | Meaning |
|---|---|
| `Pass` | The check ran successfully and met the expected condition. |
| `Fail` | The check ran successfully but did not meet the expected condition. |
| `Error` | The check could not be completed reliably. It is not treated as a failure. |

### Scoring formulas

```text
Assessed checks = Passed + Failed

Compliance score =
Passed ÷ Assessed × 100

Assessment coverage =
Assessed ÷ Selected × 100
```

Errored checks are excluded from the compliance-score denominator, but they reduce coverage.

---

## 2. Commit History for This Milestone

| Commit | Feature |
|---|---|
| `e05c3d3` | `chore(project): restructure repository for Windows MVP` |
| `4621fce` | `feat(catalog): add initial Windows compliance checks` |
| `f93571c` | `feat(scanner): add Windows Firewall assessment` |
| `e797419` | `feat(scanner): implement allow-listed PowerShell runner` |
| `6826411` | `test(scanner): cover allow-list and execution errors` |
| `7a2fd0f` | `feat(scanner): add Microsoft Defender assessment` |
| `93364b9` | `feat(scanner): add BitLocker assessment` |
| `73b8b83` | `feat(scanner): add Guest account assessment` |
| `96c9988` | `feat(scanner): add SMBv1 assessment` |
| `aef1148` | `feat(scoring): calculate compliance score and coverage` |
| `b83c627` | `feat(storage): store scan history in SQLite` |
| `b250020` | `feat(reporting): generate local HTML compliance reports` |

---

# 3. Repository Restructure

## Purpose

The earlier FastAPI-oriented prototype was too large for the fastest possible Windows MVP. The repository was reorganized around a small local desktop application while preserving the older prototype.

## Important paths created

```text
SecureAudit/
├── app.py
├── requirements.txt
├── build.bat
├── core/
│   ├── scanner.py
│   ├── scoring.py
│   ├── database.py
│   └── reporting.py
├── checks/
│   ├── catalog.json
│   └── powershell/
│       ├── firewall.ps1
│       ├── defender.ps1
│       ├── bitlocker.ps1
│       ├── guest_account.ps1
│       └── smbv1.ps1
├── data/
│   └── .gitkeep
├── reports/
│   └── .gitkeep
├── tests/
│   ├── test_scanner.py
│   ├── test_scoring.py
│   ├── test_database.py
│   └── test_reporting.py
└── archive/
    └── fastapi-prototype/
```

## Why the old prototype was archived

The old code was not deleted. It was moved under:

```text
archive/fastapi-prototype/
```

This preserved earlier work while preventing FastAPI, PostgreSQL, React, and other future architecture from delaying the standalone Windows MVP.

## Git commands used

```powershell
git branch --show-current
git status
git add .
git commit -m "chore(project): restructure repository for Windows MVP"
git push
```

## Issue encountered

Git displayed some moves as unusual renames because several empty files had identical content.

### Resolution

No corrective action was required. Git was representing file similarity, not corrupting the project.

---

# 4. Approved Check Catalog

## File

```text
checks/catalog.json
```

## Purpose

The catalog is the allow-list connecting a human-readable security check to one trusted PowerShell script.

The initial approved checks were:

| Check ID | Check | Script |
|---|---|---|
| `WIN-FW-001` | Windows Firewall | `firewall.ps1` |
| `WIN-DEF-001` | Microsoft Defender | `defender.ps1` |
| `WIN-BL-001` | BitLocker | `bitlocker.ps1` |
| `WIN-GUEST-001` | Guest account | `guest_account.ps1` |
| `WIN-SMB1-001` | SMBv1 | `smbv1.ps1` |

## Security importance

The application does not accept arbitrary PowerShell from the GUI.

Allowed flow:

```text
User selects WIN-FW-001
        ↓
Catalog resolves firewall.ps1
        ↓
Scanner validates the path
        ↓
Trusted script runs
```

Disallowed flow:

```text
User types arbitrary PowerShell
        ↓
Application runs it as Administrator
```

## Commit

```powershell
git add .\checks\catalog.json
git commit -m "feat(catalog): add initial Windows compliance checks"
git push
```

---

# 5. PowerShell Result Contract

Every scanner script returns one JSON object with the same core structure.

```powershell
$result = [ordered]@{
    check_id       = $checkId
    check_name     = $checkName
    expected_value = $expectedValue
    observed_value = $ObservedValue
    status          = $Status
    evidence        = $Evidence
    error_message   = $ErrorMessage
    timestamp_utc   = [DateTime]::UtcNow.ToString("o")
}

$result | ConvertTo-Json -Depth 5 -Compress
```

## Why structured JSON was used

JSON gives Python a predictable machine-readable result instead of requiring the scanner to parse formatted PowerShell text.

Each result answers:

- What was checked?
- What was expected?
- What was observed?
- Did it pass, fail, or error?
- What evidence was collected?
- What error occurred?
- When was the evidence collected?

---

# 6. Windows Firewall Assessment

## File

```text
checks/powershell/firewall.ps1
```

## Purpose

The script checks the enabled state of applicable Windows Firewall profiles and returns normalized JSON.

## Status logic

```text
All required profiles enabled → Pass
Any required profile disabled → Fail
Command unavailable/access failure/invalid state → Error
```

## Testing performed

### Syntax and direct execution

```powershell
$errors = $null

[System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path .\checks\powershell\firewall.ps1),
    [ref]$null,
    [ref]$errors
) | Out-Null

$errors
```

Expected: no output.

### Python scanner execution

```powershell
python -c "from core.scanner import run_check; import json; print(json.dumps(run_check('WIN-FW-001'), indent=2))"
```

### Outcome

The real machine returned a valid `Pass` result.

### Error-path testing

A controlled temporary modification was used to force an error without changing the actual firewall configuration.

## Commit

```powershell
git add .\checks\powershell\firewall.ps1
git commit -m "feat(scanner): add Windows Firewall assessment"
git push
```

---

# 7. Allow-Listed Python Scanner

## File

```text
core/scanner.py
```

## Purpose

The scanner is the trusted execution boundary between the user-selected check ID and PowerShell.

It performs the following:

1. Loads `checks/catalog.json`.
2. Finds an exact enabled check ID.
3. Rejects unknown or disabled checks.
4. Rejects absolute paths.
5. Rejects nested or traversal paths.
6. Allows only `.ps1`.
7. Resolves the script inside the trusted PowerShell directory.
8. Runs PowerShell without `shell=True`.
9. Applies a timeout.
10. Parses one JSON result.
11. Normalizes malformed execution into `Error`.
12. Verifies that returned `check_id` matches the requested ID.

## Key security rules

```text
No arbitrary command input
No arbitrary script path input
No absolute script paths
No ../ path traversal
No non-PowerShell scripts
No shell=True
Timeout required
Returned check ID must match requested check ID
```

## PowerShell catalog encoding issue

### Error

The catalog had been written with a UTF-8 byte-order mark by PowerShell. Reading it as plain UTF-8 caused parsing problems.

### Fix

Catalog loading was changed to:

```python
encoding="utf-8-sig"
```

This accepts both normal UTF-8 and UTF-8 with BOM.

## Manual security tests performed

```text
Known enabled check                  → accepted
Unknown check ID                    → rejected
Empty check ID                      → rejected
Disabled check                      → rejected
Absolute script path                → rejected
Traversal path                      → rejected
Non-.ps1 path                       → rejected
Missing script                      → rejected
Invalid JSON                        → normalized Error
Timeout                             → normalized Error
Mismatched returned check ID        → normalized Error
Invalid catalog JSON                → catalog error
```

## Commit

```powershell
git add .\core\scanner.py
git commit -m "feat(scanner): implement allow-listed PowerShell runner"
git push
```

---

# 8. Scanner Test Suite

## File

```text
tests/test_scanner.py
```

## Test count

```text
13 tests
```

## Tests added

| Test | Purpose |
|---|---|
| `test_real_catalog_loads_five_initial_checks` | Confirms the real catalog contains the five initial checks. |
| `test_unknown_check_id_is_rejected` | Prevents execution of unapproved IDs. |
| `test_empty_check_id_is_rejected` | Rejects missing selection values. |
| `test_disabled_check_is_rejected` | Prevents disabled catalog entries from running. |
| `test_absolute_script_path_is_rejected` | Prevents catalog entries from escaping the trusted directory. |
| `test_traversal_script_path_is_rejected` | Blocks `../` path traversal. |
| `test_non_powershell_script_is_rejected` | Restricts execution to `.ps1`. |
| `test_missing_script_is_rejected` | Produces a controlled error if an approved file is absent. |
| `test_invalid_json_becomes_error_result` | Prevents malformed script output from crashing the app. |
| `test_timeout_becomes_error_result` | Prevents a hanging script from blocking SecureAudit indefinitely. |
| `test_valid_result_is_normalized` | Confirms a valid script result is preserved correctly. |
| `test_result_check_id_mismatch_becomes_error` | Prevents a script from claiming evidence for a different check. |
| `test_invalid_catalog_json_raises_catalog_error` | Detects corrupt catalog content. |

## Command

```powershell
python -m pytest .\tests\test_scanner.py -v
```

## Outcome

```text
13 passed
```

## Commit

```powershell
git add .\tests\test_scanner.py
git commit -m "test(scanner): cover allow-list and execution errors"
git push
```

---

# 9. Microsoft Defender Assessment

## File

```text
checks/powershell/defender.ps1
```

## Purpose

The initial Defender check verifies that Microsoft Defender Antivirus is active.

## Real result observed

```text
AntivirusEnabled=True
AntispywareEnabled=True
RealTimeProtectionEnabled=False
BehaviorMonitorEnabled=False
```

The check returned `Pass`.

## Why it still passed

The original catalog objective was:

```text
Microsoft Defender Antivirus is active
```

It was not yet a dedicated real-time protection check.

Real-time protection should later be implemented as a separate control, for example:

```text
WIN-DEF-RT-001
```

This prevents one check from silently expanding beyond its documented purpose.

## Testing

```powershell
python -c "from core.scanner import run_check; import json; print(json.dumps(run_check('WIN-DEF-001'), indent=2))"
python -m pytest -v
```

## Outcome

```text
Defender assessment: Pass
Regression suite: 13 passed
```

## Commit

```powershell
git add .\checks\powershell\defender.ps1
git commit -m "feat(scanner): add Microsoft Defender assessment"
git push
```

---

# 10. BitLocker Assessment

## File

```text
checks/powershell/bitlocker.ps1
```

## Purpose

The script assesses the system drive and passes only when all of the following are true:

```text
Volume status: FullyEncrypted
Protection status: On
Encryption percentage: 100
```

## Evidence collected

```text
Mount point
Volume type
Volume status
Protection status
Encryption percentage
Encryption method
Lock status
Key protector types
```

## Non-administrator test

The non-elevated terminal returned:

```text
Status: Error
Reason: Access denied
```

This was correct because the state could not be assessed reliably.

## Administrator test

The elevated terminal returned:

```text
MountPoint=C:
VolumeStatus=FullyDecrypted
ProtectionStatus=Off
EncryptionPercentage=0
EncryptionMethod=None
Status=Fail
```

## Important distinction demonstrated

```text
No permission to assess BitLocker → Error
BitLocker assessed and found off  → Fail
```

This is one of the most important GRC behaviors in the project. Lack of evidence must not be reported as a failed control.

## Safety decision

BitLocker was not enabled merely to create a passing test. Changing disk encryption requires recovery-key planning and should not be done casually on the main machine.

## Commit

```powershell
git add .\checks\powershell\bitlocker.ps1
git commit -m "feat(scanner): add BitLocker assessment"
git push
```

---

# 11. Guest Account Assessment

## File

```text
checks/powershell/guest_account.ps1
```

## Purpose

The script verifies that the built-in Windows Guest account is disabled.

## Important implementation detail

The built-in Guest account is identified by SID ending in RID `501`, not only by the literal name `Guest`.

```powershell
$guestAccount = @(
    Get-LocalUser -ErrorAction Stop |
    Where-Object {
        $_.SID.Value -match "-501$"
    }
)
```

This remains reliable if the account is renamed.

## Status logic

```text
Built-in Guest account disabled → Pass
Built-in Guest account enabled  → Fail
Account cannot be located/read  → Error
```

## Real result

```text
AccountName=Guest
SID=S-1-5-21-...-501
Enabled=False
Status=Pass
```

## Error-path test

The script was copied temporarily and the command name was replaced:

```powershell
$testScript = Join-Path $env:TEMP "secureaudit-guest-error-test.ps1"

(Get-Content .\checks\powershell\guest_account.ps1 -Raw) `
    -replace '"Get-LocalUser"', '"Get-SecureAuditMissingLocalUser"' |
    Set-Content $testScript -Encoding UTF8
```

The temporary script correctly returned:

```text
Status: Error
Error message present: True
```

Cleanup:

```powershell
Remove-Item $testScript
```

## Outcome

```text
Direct PowerShell result: Pass
Python scanner result: Pass
Regression suite: 13 passed
```

## Commit

```powershell
git add .\checks\powershell\guest_account.ps1
git commit -m "feat(scanner): add Guest account assessment"
git push
```

---

# 12. SMBv1 Assessment

## File

```text
checks/powershell/smbv1.ps1
```

## Purpose

The script checks the Windows optional feature:

```text
SMB1Protocol
```

## Status mapping

```powershell
$disabledStates = @(
    "Disabled",
    "DisabledWithPayloadRemoved"
)
```

```text
Enabled                    → Fail
Disabled                   → Pass
DisabledWithPayloadRemoved → Pass
Other/transitional state   → Error
```

## Non-administrator result

```text
Status: Error
Error: The requested operation requires elevation.
Error type: System.Runtime.InteropServices.COMException
```

This was correct because Windows did not allow the optional feature to be queried without elevation.

## Administrator result

```text
FeatureName=SMB1Protocol
State=Disabled
RestartNeeded=False
Status=Pass
```

## Python scanner result

```json
{
  "check_id": "WIN-SMB1-001",
  "status": "Pass",
  "error_message": null
}
```

## Security decision

SMBv1 was not enabled on the main machine just to test a genuine `Fail`. That test belongs in a disposable VM snapshot.

## Outcome

```text
Regression suite: 13 passed
Working tree after commit: clean
```

## Commit

```powershell
git add .\checks\powershell\smbv1.ps1
git commit -m "feat(scanner): add SMBv1 assessment"
git push
```

---

# 13. Compliance Scoring Engine

## Files

```text
core/scoring.py
tests/test_scoring.py
```

## Purpose

The scoring engine calculates an honest technical compliance score without treating errors as failures.

## Core behavior

```python
selected_count = len(result_list)
assessed_count = passed_count + failed_count
unassessed_count = error_count

if assessed_count == 0:
    compliance_score = None
else:
    compliance_score = round(
        passed_count / assessed_count * 100,
        2,
    )

if selected_count == 0:
    coverage_percentage = 0.0
else:
    coverage_percentage = round(
        assessed_count / selected_count * 100,
        2,
    )
```

## Why `None` is used

When all selected checks error, there is no trustworthy compliance score.

```text
Incorrect: 0%
Correct:   None / Not available
```

A score of zero would falsely mean every assessed check failed.

## Manual demonstration

Input:

```text
Pass: 3
Fail: 1
Error: 1
```

Command:

```powershell
python -c "from core.scoring import calculate_score; import json; results=[{'status':'Pass'},{'status':'Pass'},{'status':'Pass'},{'status':'Fail'},{'status':'Error'}]; print(json.dumps(calculate_score(results), indent=2))"
```

Output:

```json
{
  "selected_count": 5,
  "passed_count": 3,
  "failed_count": 1,
  "error_count": 1,
  "assessed_count": 4,
  "unassessed_count": 1,
  "compliance_score": 75.0,
  "coverage_percentage": 80.0
}
```

## Scoring tests added

| Test | Purpose |
|---|---|
| `test_score_excludes_errors_from_compliance_denominator` | Confirms `3 Pass, 1 Fail, 1 Error` becomes `75%` score and `80%` coverage. |
| `test_all_passes_score_one_hundred_percent` | Confirms all passing checks produce `100%`. |
| `test_all_failures_score_zero_percent` | Confirms a real assessed zero remains `0%`. |
| `test_all_errors_have_no_compliance_score` | Confirms all errors produce `None`, not zero. |
| `test_empty_result_list_is_supported` | Produces a neutral empty summary. |
| `test_fractional_score_is_rounded_to_two_decimal_places` | Confirms `66.67%` rounding. |
| `test_fractional_coverage_is_rounded_to_two_decimal_places` | Confirms fractional coverage rounding. |
| `test_generator_input_is_supported` | Accepts iterable input, not only lists. |
| `test_missing_status_is_rejected` | Requires every result to contain `status`. |
| `test_unsupported_status_is_rejected` | Rejects values such as `Skipped`. |
| `test_lowercase_status_is_rejected` | Enforces exact normalized spelling. |
| `test_non_mapping_result_is_rejected` | Rejects strings or other non-dictionary items. |
| `test_string_input_is_rejected` | Prevents treating a string as a result iterable. |
| `test_mapping_input_is_rejected` | Requires a collection of results rather than one dictionary. |
| `test_non_string_status_is_rejected` | Rejects numeric or invalid status types. |

## Commands

```powershell
python -m py_compile .\core\scoring.py
python -m py_compile .\tests\test_scoring.py
python -m pytest .\tests\test_scoring.py -v
python -m pytest -v
```

## Outcome

```text
Scoring tests: 15 passed
Full suite at that stage: 28 passed
```

## Commit

```powershell
git add .\core\scoring.py
git add .\tests\test_scoring.py
git commit -m "feat(scoring): calculate compliance score and coverage"
git push
```

---

# 14. SQLite Scan-History Storage

## Files

```text
core/database.py
tests/test_database.py
```

## Purpose

The database module stores one scan summary and its individual result evidence.

## Database tables

```text
scans
scan_results
```

### `scans`

Stores:

```text
scan_id
started_at_utc
completed_at_utc
hostname
selected_count
passed_count
failed_count
error_count
assessed_count
unassessed_count
compliance_score
coverage_percentage
```

### `scan_results`

Stores:

```text
result_id
scan_id
check_id
check_name
expected_value
observed_value
status
evidence_json
error_message
timestamp_utc
```

## Relationship

```text
scans.scan_id
      ↓
scan_results.scan_id
```

The foreign key uses cascading delete, and one scan cannot contain the same `check_id` twice.

## Transaction behavior

The scan summary and all result rows are inserted inside one transaction.

```text
All rows succeed → commit
Any row fails    → rollback everything
```

This avoids partial evidence, such as a summary existing without all detailed results.

## Key validation

The module rejects:

```text
Negative counts
Inconsistent summary counts
Unsupported statuses
Duplicate check IDs
Invalid evidence JSON
Duplicate scan IDs
Invalid limits
Missing required fields
Naive timestamps without timezone
Completion before start time
```

## Timestamp bug discovered

### Manual output

The first manual test generated:

```text
started_at_utc:   2026-08-06T11:59:00+00:00
completed_at_utc: 2026-08-06T11:51:04+00:00
```

The completion time was earlier than the start time.

### Why this mattered

The database was accepting logically impossible audit history. Even though the manual test had used a future start value, the application should reject contradictory timestamps rather than preserve them.

### Fix added

```python
def _parse_utc_timestamp(
    value: str,
    field_name: str,
) -> datetime:
    """Parse and validate an ISO 8601 timezone-aware timestamp."""

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise DatabaseError(
            f"{field_name!r} must be a valid ISO 8601 timestamp."
        ) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DatabaseError(
            f"{field_name!r} must include timezone information."
        )

    return parsed.astimezone(UTC)
```

The validation was connected inside `save_scan()`:

```python
started_at = _parse_utc_timestamp(
    started_at_utc,
    "started_at_utc",
)

completed_at = _parse_utc_timestamp(
    completed_at_utc,
    "completed_at_utc",
)

if completed_at < started_at:
    raise DatabaseError(
        "completed_at_utc cannot be earlier than started_at_utc."
    )
```

## Indentation mistake encountered

The parser function was initially pasted inside `_utc_now()`, and later the timestamp block was pasted outside `save_scan()`.

### Incorrect structure

```python
def _utc_now() -> str:
    def _parse_utc_timestamp(...):
        ...
```

and:

```python
def save_scan(...):
    hostname = ...

started_at_utc = ...
```

### Fix

Both functions were separated at module level, and the validation block was indented four spaces inside `save_scan()`.

Correct order:

```text
DatabaseError
_utc_now()
_parse_utc_timestamp()
_connect()
...
save_scan()
```

## Database tests added

| Test | Purpose |
|---|---|
| `test_initialize_database_creates_required_tables` | Confirms both tables exist. |
| `test_initialize_database_is_idempotent` | Initialization can run repeatedly. |
| `test_save_and_get_scan_round_trip` | Confirms a scan and evidence can be saved and reconstructed. |
| `test_save_scan_generates_identifier` | Confirms UUID generation. |
| `test_get_scan_returns_none_for_unknown_identifier` | Missing scan is not treated as database corruption. |
| `test_list_scans_returns_newest_first` | Orders history by completion time. |
| `test_list_scans_honors_limit` | Enforces requested history length. |
| `test_invalid_limit_is_rejected` | Rejects limits outside `1–1000`. |
| `test_summary_result_count_mismatch_is_rejected` | Selected count must equal result rows. |
| `test_inconsistent_summary_is_rejected` | Prevents contradictory totals. |
| `test_unsupported_result_status_is_rejected` | Allows only Pass, Fail, Error. |
| `test_duplicate_check_ids_are_rejected` | Prevents duplicate evidence for one check in a scan. |
| `test_non_serializable_evidence_is_rejected` | Requires valid JSON evidence. |
| `test_duplicate_scan_id_does_not_overwrite_existing_scan` | Protects existing evidence from replacement. |
| `test_completed_time_before_start_time_is_rejected` | Protects chronological integrity. |
| `test_timestamp_without_timezone_is_rejected` | Requires timezone-aware evidence timestamps. |

## Commands

```powershell
python -m py_compile .\core\database.py
python -m py_compile .\tests\test_database.py
python -m pytest .\tests\test_database.py -v
python -m pytest -v
```

## Manual database test

```powershell
python -c "from core.database import save_scan, get_scan; from pathlib import Path; import json; db=Path('data/manual-test.db'); result={'check_id':'WIN-FW-001','check_name':'Windows Firewall Enabled','expected_value':'Firewall enabled','observed_value':'All profiles enabled','status':'Pass','evidence':[{'profile':'Domain','enabled':True}],'error_message':None,'timestamp_utc':'2026-08-06T12:00:00+00:00'}; summary={'selected_count':1,'passed_count':1,'failed_count':0,'error_count':0,'assessed_count':1,'unassessed_count':0,'compliance_score':100.0,'coverage_percentage':100.0}; scan_id=save_scan(hostname='MANUAL-TEST',results=[result],summary=summary,started_at_utc='2026-08-06T11:59:00+00:00',completed_at_utc='2026-08-06T12:01:00+00:00',database_path=db); print(json.dumps(get_scan(scan_id,db),indent=2))"
```

Cleanup:

```powershell
Remove-Item .\data\manual-test.db
```

## Outcome

```text
Database tests: 16 passed
Full suite at that stage: 44 passed
```

## Commit

```powershell
git add .\core\database.py
git add .\tests\test_database.py
git commit -m "feat(storage): store scan history in SQLite"
git push
```

---

# 15. Standalone HTML Reporting

## Files

```text
core/reporting.py
tests/test_reporting.py
```

## Purpose

The reporting module converts a stored scan dictionary into a standalone HTML report and writes it under `reports/`.

The report works without FastAPI or a web server.

## Report contents

```text
SecureAudit title
Hostname
Scan ID
Start time
Completion time
Compliance score
Assessment coverage
Selected count
Pass count
Fail count
Error count
Detailed result cards
Expected values
Observed values
Assessment timestamps
Error details
Expandable JSON evidence
Scope disclaimer
```

## Security behavior

All scanner-controlled values are escaped before insertion into HTML.

```python
def _escape(value: Any) -> str:
    if value is None:
        return ""

    return html.escape(
        str(value),
        quote=True,
    )
```

This prevents values such as:

```html
<script>alert(1)</script>
```

from becoming executable HTML.

## Status styling

```python
def _status_class(status: str) -> str:
    return {
        "Pass": "status-pass",
        "Fail": "status-fail",
        "Error": "status-error",
    }[status]
```

## Safe report filenames

The default report name is based on the scan ID after unsafe characters are removed.

Custom filenames are reduced to their basename so values such as:

```text
../outside-report.html
```

cannot escape the configured report directory.

## First reporting test failures

Two tests failed initially.

### Failure 1: exact status substring

The test expected:

```python
assert ">Pass<" in report
```

But the rendered HTML contained indentation and line breaks around `Pass`.

### Fix

The assertions were changed to:

```python
assert "Pass" in report
assert "Fail" in report
assert "Error" in report
```

### Failure 2: wrong validation error reached first

The result-count mismatch test changed:

```python
scan["selected_count"] = 4
scan["passed_count"] = 2
```

This made the assessed count inconsistent before validation reached the intended result-length mismatch.

### Fix

The test was changed to preserve internal arithmetic:

```python
scan["selected_count"] = 4
scan["error_count"] = 2
scan["unassessed_count"] = 2
```

Now:

```text
Passed + Failed + Error = 1 + 1 + 2 = 4
Assessed = Passed + Failed = 2
Unassessed = Error = 2
```

The summary is internally valid, but only three result objects exist, so the intended validation path is tested.

## Reporting tests added

| Test | Purpose |
|---|---|
| `test_build_report_contains_scan_summary` | Confirms scan metadata and percentages appear. |
| `test_build_report_contains_all_results` | Confirms every result and status appears. |
| `test_build_report_contains_evidence` | Confirms technical evidence is present. |
| `test_html_special_characters_are_escaped` | Prevents HTML/script injection. |
| `test_none_compliance_score_is_not_reported_as_zero` | Displays unavailable score honestly. |
| `test_empty_scan_displays_empty_state` | Supports a scan with no selected checks. |
| `test_write_report_creates_utf8_html_file` | Confirms a readable UTF-8 file is created. |
| `test_custom_filename_gets_html_extension` | Adds `.html` when omitted. |
| `test_custom_filename_cannot_escape_output_directory` | Prevents filename path traversal. |
| `test_missing_scan_field_is_rejected` | Requires report metadata. |
| `test_inconsistent_result_counts_are_rejected` | Rejects contradictory totals. |
| `test_result_count_mismatch_is_rejected` | Requires selected count to match result objects. |
| `test_unsupported_status_is_rejected` | Allows only Pass, Fail, Error. |
| `test_duplicate_check_ids_are_rejected` | Prevents duplicate result evidence. |
| `test_non_serializable_evidence_is_rejected` | Requires valid JSON evidence. |
| `test_invalid_percentage_is_rejected` | Restricts percentages to `0–100`. |
| `test_non_mapping_scan_is_rejected` | Requires a stored-scan mapping. |

## Commands

```powershell
python -m py_compile .\core\reporting.py
python -m py_compile .\tests\test_reporting.py
python -m pytest .\tests\test_reporting.py -v
python -m pytest -v
```

## Manual report generation

```powershell
python -c "from core.reporting import write_html_report; scan={'scan_id':'manual-report-001','started_at_utc':'2026-08-06T12:00:00+00:00','completed_at_utc':'2026-08-06T12:01:00+00:00','hostname':'MANUAL-TEST-PC','selected_count':3,'passed_count':1,'failed_count':1,'error_count':1,'assessed_count':2,'unassessed_count':1,'compliance_score':50.0,'coverage_percentage':66.67,'results':[{'check_id':'WIN-FW-001','check_name':'Windows Firewall Enabled','expected_value':'All profiles enabled','observed_value':'All profiles enabled','status':'Pass','evidence':[{'profile':'Domain','enabled':True}],'error_message':None,'timestamp_utc':'2026-08-06T12:00:10+00:00'},{'check_id':'WIN-BL-001','check_name':'BitLocker Protection Enabled','expected_value':'System drive protected','observed_value':'ProtectionStatus=Off','status':'Fail','evidence':[{'mount_point':'C:','protection_status':'Off'}],'error_message':None,'timestamp_utc':'2026-08-06T12:00:20+00:00'},{'check_id':'WIN-SMB1-001','check_name':'SMBv1 Disabled','expected_value':'SMBv1 disabled','observed_value':'Could not assess','status':'Error','evidence':[{'error_type':'PermissionError'}],'error_message':'Administrator rights required','timestamp_utc':'2026-08-06T12:00:30+00:00'}]}; path=write_html_report(scan); print(path.resolve())"
```

Open:

```powershell
Start-Process .\reports\secureaudit-manual-report-001.html
```

Cleanup:

```powershell
Remove-Item .\reports\secureaudit-manual-report-001.html
```

## Manual output verified

```text
Host: MANUAL-TEST-PC
Compliance score: 50.00%
Coverage: 66.67%
Selected: 3
Passed: 1
Failed: 1
Errors: 1
```

The report showed:

- Firewall as `Pass`
- BitLocker as `Fail`
- SMBv1 as `Error`
- `Administrator rights required`
- Expandable technical evidence
- Scope disclaimer

## Outcome

```text
Reporting tests: 17 passed
Final full suite: 61 passed
```

## Commit

```powershell
git add .\core\reporting.py
git add .\tests\test_reporting.py
git commit -m "feat(reporting): generate local HTML compliance reports"
git push
```

---

# 16. Repeated Pytest Cleanup Warning

## Warning

After successful test completion, pytest sometimes displayed:

```text
Exception ignored in atexit callback
PermissionError: [WinError 5] Access is denied:
C:\Users\wale1\AppData\Local\Temp\pytest-of-wale1\pytest-current
```

## Interpretation

The warning occurred after the actual tests had completed and passed.

Examples:

```text
13 passed
28 passed
42 passed
44 passed
61 passed
```

Therefore, it did not invalidate test outcomes.

## Likely cause

A Windows file lock, temporary symlink cleanup issue, antivirus scan, or interaction with synced storage.

## Optional workaround

Run pytest with a repository-local temporary directory:

```powershell
python -m pytest -v --basetemp=.\.pytest-temp
```

Then remove it:

```powershell
Remove-Item .\.pytest-temp -Recurse -Force
```

If used regularly, add:

```text
.pytest-temp/
```

to `.gitignore`.

---

# 17. Final Test Inventory

| Suite | Tests |
|---|---:|
| Scanner | 13 |
| Scoring | 15 |
| Database | 16 |
| Reporting | 17 |
| **Total** | **61** |

Final command:

```powershell
python -m pytest -v
```

Final result:

```text
61 passed
```

---

# 18. Standard Git Workflow Used

## Before editing

```powershell
git branch --show-current
git status
git log -3 --oneline
```

## Compile and test

```powershell
python -m py_compile .\path\to\module.py
python -m py_compile .\tests\test_module.py
python -m pytest .\tests\test_module.py -v
python -m pytest -v
```

## Review changes

```powershell
git status --short
git add .\path\to\module.py
git add .\tests\test_module.py
git diff --cached --check
git diff --cached --stat
git status
```

## Commit and push

```powershell
git commit -m "type(scope): focused description"
git push
```

## Verify

```powershell
git status
git log -5 --oneline
```

Expected:

```text
nothing to commit, working tree clean
```

---

# 19. GRC and Security Lessons

## Technical assessment is not certification

SecureAudit reports selected technical configuration checks. It does not prove complete compliance with CIS Controls, CIS Benchmarks, ISO 27001, or NIST CSF.

## Error is not failure

```text
Fail  = the system was assessed and did not meet the condition
Error = the system could not be assessed reliably
```

This distinction protects the integrity of the compliance score.

## Coverage must be shown separately

A high score with low coverage can be misleading.

Example:

```text
1 Pass
0 Fail
4 Error

Compliance score: 100%
Coverage: 20%
```

The separate coverage value makes the limitation visible.

## Evidence must remain traceable

Each result includes:

```text
Check ID
Expected state
Observed state
Status
Evidence
Error message
Timestamp
```

## Privileged execution must be restricted

SecureAudit executes only allow-listed scripts from the trusted catalog. It must never become an arbitrary administrator command runner.

## Audit records must be internally consistent

The database rejects:

```text
Impossible timestamps
Contradictory counts
Duplicate evidence
Invalid statuses
Invalid JSON
Partial transactions
```

## Reports must treat evidence as untrusted text

Even locally collected values are escaped before insertion into HTML. This prevents malformed or malicious data from becoming executable content.

---

# 20. Current Definition of Done

Completed:

- [x] Repository restructured for the Windows MVP
- [x] Five approved Windows checks in the catalog
- [x] Windows Firewall scanner
- [x] Microsoft Defender scanner
- [x] BitLocker scanner
- [x] Guest account scanner
- [x] SMBv1 scanner
- [x] Allow-listed Python scanner
- [x] Timeout and malformed-output handling
- [x] Pass/Fail/Error normalization
- [x] Compliance scoring
- [x] Assessment coverage
- [x] SQLite scan history
- [x] Evidence persistence
- [x] Timestamp integrity validation
- [x] Local HTML reporting
- [x] HTML escaping
- [x] Safe report filenames
- [x] 61 automated tests
- [x] Clean focused Git commits
- [x] Remote branch updated

Not yet completed:

- [ ] Tkinter GUI
- [ ] Catalog-driven checklist UI
- [ ] End-to-end scan button
- [ ] Live result table
- [ ] Scan-history screen
- [ ] Generate-report button in GUI
- [ ] UAC administrator elevation
- [ ] Windows VM test matrix
- [ ] PyInstaller `.exe`
- [ ] Build script and packaging verification
- [ ] Final architecture and GRC documentation
- [ ] README completion

---

# 21. Next Milestone

The next stage is the Tkinter application.

Planned flow:

```text
Launch app.py
    ↓
Load approved checks from catalog
    ↓
Display selectable checklist
    ↓
Run selected checks
    ↓
Show Pass / Fail / Error
    ↓
Calculate score and coverage
    ↓
Store scan in SQLite
    ↓
Generate HTML report
```

Likely next commit:

```text
feat(ui): add selectable compliance checklist
```

Suggested starting command:

```powershell
git branch --show-current
git status
code .\app.py
```

---

# 22. Fast Command Reference

## Activate environment

```powershell
cd "X:\icloud\iCloudDrive\Cyber\Projects\SecureAudit"
.\.venv\Scripts\Activate.ps1
```

## Run all tests

```powershell
python -m pytest -v
```

## Run one suite

```powershell
python -m pytest .\tests\test_scanner.py -v
python -m pytest .\tests\test_scoring.py -v
python -m pytest .\tests\test_database.py -v
python -m pytest .\tests\test_reporting.py -v
```

## Compile a file

```powershell
python -m py_compile .\core\scanner.py
```

## Check Git state

```powershell
git branch --show-current
git status
git log -5 --oneline
```

## Stage, review, commit, and push

```powershell
git add .\path\to\file
git diff --cached --check
git diff --cached --stat
git commit -m "type(scope): description"
git push
git status
```

---

# 23. Milestone Summary

SecureAudit now has a complete reusable backend pipeline for the standalone Windows MVP:

```text
Five Windows checks
        ↓
Allow-listed PowerShell execution
        ↓
Normalized technical evidence
        ↓
Honest Pass / Fail / Error handling
        ↓
Compliance score and coverage
        ↓
Transactional SQLite storage
        ↓
Escaped standalone HTML reporting
```

The milestone closed with:

```text
Branch: feature/windows-mvp
Latest commit: b250020
Automated tests: 61 passed
Working tree: clean
Remote branch: up to date
```

The project is ready for the Tkinter GUI integration milestone.
