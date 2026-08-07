---
title: SecureAudit Windows MVP — Milestone 4 Research, Report, and Evidence Guide
project: SecureAudit
branch: feature/windows-build
milestone: Standalone Windows Packaging and Runtime Path Hardening
status: Evidence plan active
tests: 89 passed
latest_commit: 5307cff
tags:
  - secureaudit
  - research
  - evidence
  - windows
  - pyinstaller
  - uac
  - grc
  - compliance
  - testing
---

# SecureAudit Windows MVP — Milestone 4 Research, Report, and Evidence Guide

> [!info] Purpose
> Preserve defensible technical evidence for the Windows packaging milestone without overstating compliance or deployment readiness.
>
> Current strongest verified facts:
>
> - PyInstaller build succeeded.
> - `SecureAudit.exe` was generated.
> - packaged execution created persistent SQLite and HTML report artifacts under `%LOCALAPPDATA%\SecureAudit`;
> - final automated result was **89 passed**;
> - build configuration was committed and pushed as `5307cff`.
>
> Clean Windows VM evidence is still required before claiming portability to a fresh endpoint.

---

# 1. Evidence Status Summary

| Evidence | Status |
|---|---|
| Final build output | Available now |
| `SecureAudit.exe` metadata | Available now |
| PyInstaller version | Available now |
| `SecureAudit.spec` resource list | Available now |
| `console=False` configuration | Available now |
| `%LOCALAPPDATA%` database/report evidence | Available now |
| 89-test result | Available now |
| Final clean Git state | Available now |
| PyInstaller file-lock failure/fix | Available now |
| Frozen UAC unit tests | Available now |
| Desktop copy path | Available now |
| Clean screenshots of GUI/UAC | Should be recreated cleanly |
| Clean VM without Python | Not available yet |
| Cross-VM comparison | Not available yet |
| SmartScreen/Defender reputation behavior | Not available yet |
| Performance measurements | Needed after demo/VM test |

---

# 2. Screenshot Evidence to Capture

## 2.1 Successful build

### Command

```powershell
.\build.bat
```

### Capture

The final terminal section showing:

```text
Build complete!
[2/2] Build completed successfully.
Output:
C:\Users\wale1\Projects\SecureAudit\dist\SecureAudit.exe
```

### Suggested filename

```text
M4_01_PyInstaller_Build_Success.png
```

### Why it matters

Demonstrates reproducibility from the committed build script rather than a one-off manual packaging command.

---

## 2.2 Executable metadata

### Command

```powershell
Get-Item .\dist\SecureAudit.exe |
    Select-Object Name, Length, LastWriteTime
```

### Expected visible evidence

Observed development-machine build:

```text
SecureAudit.exe
13250316 bytes
8/7/2026 7:02:35 PM
```

### Suggested filename

```text
M4_02_SecureAudit_EXE_Metadata.png
```

---

## 2.3 Persistent local evidence directory

### Command

```powershell
Get-ChildItem "$env:LOCALAPPDATA\SecureAudit" -Recurse -Force
```

### Current verified structure

```text
SecureAudit\
├── data\
│   └── secureaudit.db
└── reports\
    └── secureaudit-4439bf10-4885-4293-af74-dfa0d652b3aa.html
```

### Suggested filename

```text
M4_03_LocalAppData_Persistence.png
```

### Why it matters

Shows that mutable evidence is outside:

```text
dist\
build\
PyInstaller temporary extraction directory
```

This is a meaningful architecture and evidence-integrity point.

---

## 2.4 Final automated tests

### Command

```powershell
python -m pytest -v
```

### Verified result

```text
89 passed
```

### Suggested filename

```text
M4_04_89_Tests_Passed.png
```

### Note

The recurring pytest `atexit` cleanup warning should be visible or documented separately rather than cropped in a misleading way.

It occurs after the successful test result:

```text
PermissionError: [WinError 5] ...
pytest-current
```

Do not present the screenshot as "warning-free".

---

## 2.5 Final Git state

### Commands

```powershell
git status
git log -6 --oneline
```

### Key evidence

```text
nothing to commit, working tree clean
```

and:

```text
5307cff build(windows): package SecureAudit with PyInstaller
2c11b8a test(admin): cover frozen executable elevation
7f84596 feat(paths): use packaged resource and runtime paths
645212e feat(paths): separate bundled resources from runtime data
```

### Suggested filename

```text
M4_05_Final_Git_State.png
```

---

# 3. UAC and Process Evidence

These should be recreated cleanly.

## 3.1 Standard-user launch

Capture:

1. double-click `SecureAudit.exe`;
2. Windows UAC prompt;
3. SecureAudit GUI after approval.

Suggested filenames:

```text
M4_06_UAC_Prompt.png
M4_07_GUI_After_Elevation.png
```

Do not include personal Windows account details if unnecessary.

---

## 3.2 UAC cancellation

Capture the user selecting:

```text
No
```

or cancelling the elevation prompt.

Then capture:

```powershell
Get-Process SecureAudit -ErrorAction SilentlyContinue
```

Expected evidence should demonstrate that no unintended SecureAudit process remains.

Suggested filename:

```text
M4_08_UAC_Cancel_Process_State.png
```

---

## 3.3 One-GUI/no-console evidence

Recommended evidence:

```powershell
Get-Process SecureAudit -ErrorAction SilentlyContinue
```

alongside a screenshot of the single GUI.

If possible, capture Task Manager showing the process while no PowerShell, `python.exe`, or `pythonw.exe` window is present for the packaged runtime.

Suggested filename:

```text
M4_09_Single_GUI_Process_Evidence.png
```

> [!warning]
> Process counts can temporarily include both the original and elevated replacement during transition. Capture after startup settles.

---

# 4. Bundled Resource Evidence

## Important `SecureAudit.spec` excerpt

Preserve the section showing:

```text
checks\catalog.json
checks\powershell\firewall.ps1
checks\powershell\defender.ps1
checks\powershell\bitlocker.ps1
checks\powershell\guest_account.ps1
checks\powershell\smbv1.ps1
```

and:

```python
console=False
```

### Suggested filename

```text
M4_10_PyInstaller_Spec_Resources.png
```

### Research relevance

This supports two claims:

1. required scanner resources are packaged with the application;
2. the executable is intentionally built as a GUI application without a console.

It also shows that privileged scanner modules are explicitly enumerated rather than globbing every PowerShell file.

---

# 5. Path Architecture Evidence

Capture focused excerpts from:

```text
core/paths.py
core/scanner.py
core/database.py
core/reporting.py
app.py
```

## Recommended diagram

```text
                    SecureAudit runtime
                           │
             ┌─────────────┴─────────────┐
             │                           │
      Trusted resources             Mutable evidence
             │                           │
   catalog + approved .ps1         database + reports
             │                           │
     source / _MEIPASS            source / LOCALAPPDATA
```

Suggested filename:

```text
M4_Architecture_Resource_vs_Runtime_Path.png
```

## Research explanation

The split prevents temporary packaged resources from being treated as persistent data and avoids placing privileged scanner logic in a user-writable evidence directory.

---

# 6. Security Boundary Evidence

Preserve code and test evidence for:

```text
approved catalog lookup
absolute-path rejection
directory traversal rejection
non-PowerShell rejection
missing script rejection
invalid JSON → Error
timeout → Error
result check-ID mismatch → Error
```

These are more valuable for a security/GRC report than visual GUI styling.

Recommended test names to cite:

```text
test_absolute_script_path_is_rejected
test_traversal_script_path_is_rejected
test_non_powershell_script_is_rejected
test_missing_script_is_rejected
test_invalid_json_becomes_error_result
test_timeout_becomes_error_result
test_result_check_id_mismatch_becomes_error
test_resource_path_rejects_escape_from_trusted_root
```

---

# 7. Frozen Elevation Test Evidence

Preserve the test names:

```text
test_build_relaunch_command_uses_frozen_executable
test_build_relaunch_command_preserves_frozen_arguments
```

These support the transition:

```text
Source:
python.exe → UAC → pythonw.exe app.py

Frozen:
SecureAudit.exe → UAC → SecureAudit.exe
```

Suggested screenshot:

```text
M4_11_Frozen_UAC_Tests.png
```

---

# 8. Packaged Scan Evidence

Capture a full packaged scan showing the five approved checks:

```text
WIN-FW-001
WIN-DEF-001
WIN-BL-001
WIN-GUEST-001
WIN-SMB1-001
```

Recommended screenshots:

```text
M4_12_Packaged_Checklist.png
M4_13_Packaged_Scan_Results.png
M4_14_Packaged_Score_and_Coverage.png
```

Preserve:

```text
check ID
status
observed evidence
mapped safeguard
score
assessment coverage
timestamp
```

Avoid claiming complete framework compliance.

Use wording:

```text
selected Windows baseline checks
automated technical control assessment
point-in-time evidence
partial framework mapping
```

---

# 9. Report Evidence

Capture:

1. the HTML report opened in a browser;
2. the report file visible in `%LOCALAPPDATA%\SecureAudit\reports`;
3. the corresponding scan history entry.

Suggested filenames:

```text
M4_15_HTML_Report.png
M4_16_Report_File_Persistence.png
M4_17_Scan_History.png
```

Research value:

```text
scanner output
→ structured evidence
→ SQLite record
→ HTML representation
```

This is an end-to-end evidence chain.

---

# 10. Persistence Experiment

## Experimental procedure

1. launch packaged `SecureAudit.exe`;
2. approve UAC;
3. run selected checks;
4. record generated scan ID;
5. close application;
6. verify no SecureAudit process remains;
7. relaunch application;
8. open scan history;
9. load same scan ID;
10. open/regenerate report.

## Record

```text
scan ID
database path
report path
first launch timestamp
second launch timestamp
whether scan persisted
whether report opened
```

## Suggested evidence filename

```text
M4_18_Persistence_Across_Restart.png
```

---

# 11. Clean Windows VM Experiment

> [!important]
> This is the next high-value validation step.

## Minimum environment

Record:

```text
Windows version
VM platform
allocated CPU
allocated RAM
Python installed? yes/no
PowerShell version
SecureAudit EXE hash
SecureAudit EXE size
standard-user/admin starting state
```

The strongest test uses a VM with:

```text
no SecureAudit source repository
no project .venv
no Python installation
```

## Procedure

1. transfer only `SecureAudit.exe`;
2. record SHA-256 before/after transfer;
3. launch from standard-user context;
4. observe UAC;
5. approve;
6. verify GUI;
7. verify five checks;
8. run all checks;
9. verify `%LOCALAPPDATA%\SecureAudit`;
10. restart application;
11. verify history persistence;
12. open report;
13. repeat with UAC cancellation.

## Hash command

```powershell
Get-FileHash .\SecureAudit.exe -Algorithm SHA256
```

Suggested evidence:

```text
M4_VM_01_EXE_Hash.png
M4_VM_02_UAC.png
M4_VM_03_Checklist.png
M4_VM_04_Scan_Results.png
M4_VM_05_LocalAppData.png
M4_VM_06_History_After_Restart.png
```

---

# 12. Performance Measurements for VM Test

Not available yet.

Collect at least:

| Metric | Method |
|---|---|
| EXE startup time | stopwatch or timestamp |
| UAC-to-GUI time | stopwatch |
| full five-check scan duration | start/end timestamps |
| report generation time | timestamp difference |
| EXE size | `Get-Item` |
| database size after N scans | `Get-Item` |
| report size | `Get-Item` |

Repeat at least three scan runs if presenting an average.

Do not invent values before measurement.

---

# 13. Ground-Truth Validation

For research-quality evaluation, compare SecureAudit results against direct Windows commands or GUI state.

Examples:

## Firewall

Compare SecureAudit output with the corresponding Windows Firewall profile state.

## Defender

Compare SecureAudit evidence with native Defender state.

## BitLocker

Compare SecureAudit result with native BitLocker status.

## Guest account

Compare against the local account state.

## SMBv1

Compare against the Windows SMB1 feature/configuration state.

Record:

```text
SecureAudit result
native ground truth
match/mismatch
reason for mismatch
```

This enables an accuracy table rather than merely showing that the software runs.

---

# 14. Accuracy Metrics

Not available yet.

After VM testing, derive:

```text
Correct assessments / total validated assessments
```

Keep `Error` separate from `Fail`.

Recommended table:

| Check | Ground truth | SecureAudit | Match? | Notes |
|---|---|---|---|---|
| WIN-FW-001 | TBD | TBD | TBD | |
| WIN-DEF-001 | TBD | TBD | TBD | |
| WIN-BL-001 | TBD | TBD | TBD | |
| WIN-GUEST-001 | TBD | TBD | TBD | |
| WIN-SMB1-001 | TBD | TBD | TBD | |

Do not call this a compliance-certification accuracy metric. It measures implemented technical-check agreement with selected ground truth.

---

# 15. Standard-User vs Administrator Comparison

Capture both starting conditions.

## Standard user

Expected architecture:

```text
SecureAudit.exe
      ↓
UAC
      ↓
elevated SecureAudit.exe
```

## Already elevated

Expected architecture:

```text
SecureAudit.exe
      ↓
admin detected
      ↓
GUI starts
```

Compare:

```text
number of UAC prompts
number of GUI instances
process behavior
scan results
evidence paths
```

This is useful because many selected Windows checks require elevated visibility.

---

# 16. Error Evidence Worth Preserving

## PyInstaller file-lock error

Preserve:

```text
PermissionError: [WinError 5] Access is denied:
...\dist\SecureAudit.exe
```

and process evidence showing two SecureAudit processes.

### Research value

Demonstrates a build-environment failure, not a packaging-code failure, and shows how Windows file locking affects reproducible builds.

---

## Frozen test fixture error

Preserve the initial:

```text
fixture 'mock_frozen' not found
```

and final:

```text
14 passed
```

### Research value

Useful as development-method evidence showing test debugging and correct use of `unittest.mock.patch`.

---

## pytest cleanup warning

Preserve separately:

```text
PermissionError ... pytest-current
```

but always show that it occurs after:

```text
89 passed
```

Do not misrepresent it as a SecureAudit runtime crash.

---

# 17. Redaction Guidance

Before screenshots or reports are submitted publicly, inspect for:

```text
Windows username
full personal home path
device hostname
scan UUIDs if considered sensitive
local account names
BitLocker volume identifiers
Defender configuration details
GitHub authentication information
private repository URLs
OneDrive paths
```

Usually safe to retain:

```text
check IDs
generic project paths
test names
commit hashes
PyInstaller version
result-status model
architecture diagrams
```

---

# 18. Research Questions Supported by This Milestone

Potential questions:

1. Can a local Windows compliance scanner be packaged into a self-contained executable while preserving an allow-listed execution model?
2. Can privileged scanner resources remain application-controlled while evidence is stored persistently in a writable user-local directory?
3. Does packaging change the scanner's Pass/Fail/Error semantics or scoring behavior?
4. Can a frozen Windows executable relaunch itself through normal UAC without requiring Python on the endpoint?
5. How accurately do the five implemented checks match native Windows ground truth across VM configurations?
6. What deployment limitations arise from unsigned PyInstaller executables, UAC, Windows Defender, and SmartScreen?

---

# 19. Threats to Validity

Current threats include:

```text
development-machine bias
single Windows host
only five implemented checks
no large endpoint sample
no clean-VM results yet
unsigned executable reputation behavior
environment-specific permissions
point-in-time configuration evidence
possible PowerShell/version differences
```

The current milestone proves a working development-machine package, not enterprise deployment readiness.

---

# 20. Limitations

SecureAudit currently provides:

```text
local single-host assessment
five Windows checks
local SQLite evidence
local HTML reporting
UAC-based privilege elevation
```

It does not currently provide:

```text
centralized endpoint orchestration
remote agent management
enterprise authentication
code signing
installer/MSI
full CIS benchmark coverage
full ISO/NIST compliance determination
continuous monitoring
tamper-proof evidence storage
```

---

# 21. Future Evidence

After the demo or next milestone, collect:

```text
clean Windows VM portability
multiple Windows versions if practical
code-signing behavior if implemented
SmartScreen/Defender behavior
EXE SHA-256
scan timing
accuracy against native ground truth
failure behavior on unsupported/missing Windows features
database growth across repeated scans
multi-endpoint architecture proposal
```

---

# 22. Final Evidence Checklist

## Available now

- [x] PyInstaller `6.21.0`.
- [x] successful standalone build.
- [x] final EXE metadata.
- [x] explicit bundled resource list.
- [x] `console=False`.
- [x] frozen UAC unit tests.
- [x] `89 passed`.
- [x] `%LOCALAPPDATA%` database evidence.
- [x] `%LOCALAPPDATA%` report evidence.
- [x] build file-lock error and fix.
- [x] final Git commit `5307cff`.
- [x] clean final working tree.
- [x] Desktop copy created.

## Should be recreated cleanly

- [ ] build-success screenshot.
- [ ] UAC approval screenshot.
- [ ] UAC cancellation evidence.
- [ ] single-GUI/no-console evidence.
- [ ] packaged five-check checklist.
- [ ] packaged scan results.
- [ ] score/coverage view.
- [ ] history after restart.
- [ ] HTML report browser view.

## Not available yet

- [ ] clean VM with no Python.
- [ ] clean VM accuracy table.
- [ ] performance measurements.
- [ ] Windows-version comparison.
- [ ] SmartScreen/Defender reputation evidence.

## Needed before strong deployment claims

- [ ] clean endpoint portability.
- [ ] native Windows ground-truth comparison.
- [ ] repeated-run persistence.
- [ ] documented limitations.
- [ ] EXE integrity hash.
