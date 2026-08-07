---
title: SecureAudit Windows MVP — Milestone 2 Development Log
project: SecureAudit
branch: feature/tkinter-gui
milestone: Tkinter GUI and Local Workflow Integration
status: Complete
base_commit: 449c852
latest_commit: d1f18fa
tests: 61 passed
tags: [secureaudit, windows, tkinter, grc, compliance, gui, sqlite, reporting, testing]
---

# SecureAudit Windows MVP — Milestone 2 Development Log

> [!success] Milestone status
> Milestone 2 is complete based on user-provided automated-test output, Git output, database evidence, generated-report evidence, and successful manual GUI acceptance testing.
>
> **Branch:** `feature/tkinter-gui`
> **Base commit:** `449c852`
> **Latest commit:** `d1f18fa feat(ui): run scans without blocking the interface`
> **Final automated result:** `61 passed`

## 1. Scope

Milestone 2 connected the completed SecureAudit backend into a usable local Windows Tkinter application. It implemented:

- Complete workflow orchestration in `app.py`.
- Catalog-driven checklist loading.
- Selection and execution of approved check IDs only.
- Pass / Fail / Error presentation.
- Compliance score and assessment coverage in the GUI.
- Automatic SQLite persistence.
- Scan-history browsing and historical-scan loading.
- HTML report opening and regeneration.
- Background scan execution so Tkinter remains responsive.

No already-working scanner, scoring, database, or reporting module was rewritten.

## 2. Quick Reference

| Item | Value |
|---|---|
| Repository | `C:\Users\wale1\Projects\SecureAudit` |
| Branch | `feature/tkinter-gui` |
| Base commit | `449c852` |
| Final commit | `d1f18fa` |
| Python | `3.14.6` |
| Pytest | `8.4.2` |
| Automated tests | `61 passed` |
| Working tree | Clean |
| Remote branch | Up to date |
| GUI | Tkinter / ttk |
| Database | SQLite |
| Report format | Standalone HTML |

## 3. Final Application Flow

```text
Tkinter checklist
      ↓
Approved catalog entries
      ↓
Selected check IDs
      ↓
app.run_local_scan()
      ↓
core.scanner.run_check()
      ↓
Normalized Pass / Fail / Error
      ↓
core.scoring.calculate_score()
      ↓
core.database.save_scan()
      ↓
core.database.get_scan()
      ↓
core.reporting.write_html_report()
      ↓
Tkinter results + history + report actions
```

The GUI never accepts arbitrary PowerShell commands or arbitrary script paths.

## 4. Milestone Commit History

| Commit | Purpose |
|---|---|
| `cf29daa` | `feat(app): orchestrate complete local scan workflow` |
| `a99a540` | `feat(ui): add catalog-driven compliance checklist` |
| `5a1c230` | `feat(ui): display scan results and compliance summary` |
| `b1acbf6` | `feat(ui): add scan history and report actions` |
| `d1f18fa` | `feat(ui): run scans without blocking the interface` |

The branch was created from the latest `develop` state after Milestone 1 was rebased and merged through a protected GitHub Pull Request.

## 5. File Modified

### `app.py`

`app.py` now acts as the application orchestration and presentation layer. It delegates specialist responsibilities to:

```text
Scanning   → core/scanner.py
Scoring    → core/scoring.py
Storage    → core/database.py
Reporting  → core/reporting.py
```

This preserves reuse and avoids duplicating security-sensitive logic in the GUI.

## 6. Complete Local Scan Orchestration

### Commit

```text
cf29daa feat(app): orchestrate complete local scan workflow
```

The first integration step connected:

```text
selected IDs
→ scanner
→ normalized results
→ scoring
→ SQLite persistence
→ stored-scan retrieval
→ HTML reporting
```

A deliberate design choice was to generate the report from the scan read back from SQLite:

```text
save_scan()
   ↓
get_scan()
   ↓
write_html_report()
```

This makes the persisted evidence record the source for reporting.

## 7. Catalog-Driven Checklist

### Commit

```text
a99a540 feat(ui): add catalog-driven compliance checklist
```

The GUI reuses `load_catalog()` and displays enabled entries from `checks/catalog.json`.

Relevant catalog fields include:

```text
id
name
description
category
severity
requires_administrator
enabled
```

Initial approved check IDs:

```text
WIN-FW-001
WIN-DEF-001
WIN-BL-001
WIN-GUEST-001
WIN-SMB1-001
```

### Security boundary

The GUI passes IDs such as:

```text
WIN-FW-001
WIN-GUEST-001
```

It does not pass script names or user-entered PowerShell. `core.scanner` remains responsible for allow-list enforcement, trusted-path resolution, `.ps1` enforcement, path-traversal prevention, timeout handling, JSON parsing, and returned check-ID validation.

## 8. Selected-Only Execution

A stored scan verified that GUI selection controlled actual execution.

Observed two-check administrator-required run:

```text
Selected: 2
Passed: 0
Failed: 0
Errors: 2
Assessed: 0
Unassessed: 2
Compliance score: N/A
Coverage: 0%
```

The detailed stored result IDs were exactly:

```text
WIN-BL-001
WIN-SMB1-001
```

No unselected results were present.

## 9. Results and Compliance Summary

### Commit

```text
5a1c230 feat(ui): display scan results and compliance summary
```

The GUI displays:

```text
Passed
Failed
Errors
Compliance Score
Assessment Coverage
```

The result table displays:

```text
Check ID
Check name
Status
Expected value
Observed value
```

The presentation layer displays normalized backend values rather than independently interpreting evidence.

## 10. GRC Scoring Integrity

The GUI preserves the existing scoring model:

```text
Assessed = Pass + Fail
Compliance score = Pass / Assessed × 100
Coverage = Assessed / Selected × 100
```

Errors remain outside the compliance-score denominator.

### Verified examples

| Scenario | Selected | Pass | Fail | Error | Assessed | Score | Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fully assessed | 2 | 2 | 0 | 0 | 2 | 100% | 100% |
| Mixed | 3 | 2 | 0 | 1 | 2 | 100% | 66.67% |
| Five checks | 5 | 3 | 0 | 2 | 3 | 100% | 60% |
| No assessable controls | 2 | 0 | 0 | 2 | 0 | N/A | 0% |

This demonstrates why score and coverage must be displayed separately.

## 11. Administrator-Required Check Behavior

The non-elevated GUI run for:

```text
WIN-BL-001
WIN-SMB1-001
```

produced normalized `Error` results.

Observed evidence included:

```text
BitLocker → Access denied
SMBv1     → The requested operation requires elevation.
```

The GUI correctly displayed:

```text
Errors: 2
Compliance Score: Not available
Assessment Coverage: 0.00%
```

This preserves the important distinction:

```text
Cannot assess ≠ control failure
```

UAC elevation remains deferred to `feature/admin-elevation`.

## 12. SQLite Scan History

### Commit

```text
b1acbf6 feat(ui): add scan history and report actions
```

The GUI uses the existing database API:

```python
list_scans()
get_scan()
```

It does not execute SQL directly.

The history view supports recent scans, newest-first ordering, hostname, counts, score, coverage, and loading a selected historical scan into the main results panel.

## 13. HTML Report Actions

The GUI provides `Open HTML Report`.

For a newly completed scan, the generated report is opened with the Windows default browser.

For a historical scan:

```text
historical scan selected
    ↓
existing report found?
    ├── yes → open
    └── no  → regenerate from SQLite → open
```

This establishes the evidence model:

```text
SQLite scan record = durable evidence
HTML report        = derived presentation artifact
```

## 14. Responsive Background Scanning

### Commit

```text
d1f18fa feat(ui): run scans without blocking the interface
```

The final GUI runs the scan workflow in a worker thread and sends GUI updates back to Tkinter's main thread using `root.after(...)`.

```text
Tkinter main thread
      ↓
start worker
      ↓
run_local_scan()
      ↓
scanner / PowerShell / scoring / SQLite / report
      ↓
root.after(...)
      ↓
main-thread UI update
```

The worker does not directly modify widgets.

User-visible states include:

```text
Ready
Scanning 5 selected checks...
Scan completed — 5 selected, 3 assessed
```

The Run button is disabled during execution to prevent accidental duplicate scans.

## 15. Manual Acceptance Testing

The user reported that the complete manual GUI acceptance set succeeded.

Verified manually:

- [x] GUI launches.
- [x] Catalog-driven checks appear.
- [x] Select All works.
- [x] Clear All works.
- [x] Selection counter updates.
- [x] Empty selection warning works.
- [x] Selected-only execution works.
- [x] Pass results display.
- [x] Error results display.
- [x] Compliance score displays.
- [x] Assessment coverage displays.
- [x] Completed scans save automatically to SQLite.
- [x] Scan History opens.
- [x] Historical scans can be loaded.
- [x] HTML reports can be opened.
- [x] GUI remains responsive during scans.
- [x] Administrator-required checks remain `Error` when not assessable.

## 16. Recent Database Evidence

Latest observed scan summaries included:

| Selected | Pass | Fail | Error | Assessed | Score | Coverage |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 3 | 0 | 2 | 3 | 100% | 60% |
| 5 | 3 | 0 | 2 | 3 | 100% | 60% |
| 3 | 2 | 0 | 1 | 2 | 100% | 66.67% |
| 2 | 2 | 0 | 0 | 2 | 100% | 100% |
| 2 | 0 | 0 | 2 | 0 | N/A | 0% |

## 17. Automated Testing

Final command:

```powershell
python -m pytest -v
```

Observed:

```text
61 passed in 1.83s
```

Test inventory remains:

| Suite | Tests |
|---|---:|
| Scanner | 13 |
| Scoring | 15 |
| Database | 16 |
| Reporting | 17 |
| **Total** | **61** |

## 18. Known Pytest Cleanup Warning

After successful completion, pytest may report:

```text
PermissionError: [WinError 5] Access is denied:
C:\Users\wale1\AppData\Local\Temp\pytest-of-wale1\pytest-current
```

This occurs in pytest's `atexit` temporary-directory cleanup after the reported `61 passed` result. It has not invalidated the regression suite.

## 19. Important Commands Used

```powershell
cd "C:\Users\wale1\Projects\SecureAudit"
.\.venv\Scripts\Activate.ps1

git status
git branch --show-current
python -m py_compile .\app.py
python -m pytest -v
python .\app.py
```

Recent scan history:

```powershell
python -c "from core.database import list_scans; import json; print(json.dumps(list_scans(limit=5), indent=2))"
```

Git workflow:

```powershell
git status --short
git diff -- .\app.py
git add .\app.py
git diff --cached --check
git diff --cached --stat
git commit -m "type(scope): description"
git push
```

## 20. Errors and Fixes

### Wrong Python interpreter

Symptom:

```text
No module named pytest
```

Cause: project virtual environment was not active.

Fix:

```powershell
.\.venv\Scripts\Activate.ps1
```

### EOF whitespace warning

Git reported trailing whitespace/new blank line at EOF in `app.py`.

Fix: remove the whitespace, restage, and verify:

```powershell
git diff --cached --check
```

### Administrator-required controls returned `Error`

This was expected behavior in a non-elevated session and not a defect.

## 21. Security and GRC Decisions

- The GUI never becomes an arbitrary privileged-command interface.
- Check selection is limited to approved IDs from the catalog.
- `Error` remains distinct from `Fail`.
- Compliance score and assessment coverage remain independent.
- Historical evidence is read from SQLite.
- HTML remains a derived artifact generated by the tested reporting module.
- Threading changes responsiveness only; it does not bypass the trusted scanner boundary.

## 22. Final Git State

Observed:

```text
On branch feature/tkinter-gui
Your branch is up to date with 'origin/feature/tkinter-gui'.

nothing to commit, working tree clean
```

Final commit:

```text
d1f18fa feat(ui): run scans without blocking the interface
```

## 23. Definition of Done

- [x] Complete local scan workflow connected.
- [x] Tkinter application launches.
- [x] Checklist comes from approved catalog.
- [x] Only selected approved IDs run.
- [x] Pass / Fail / Error displayed.
- [x] Compliance score displayed.
- [x] Assessment coverage displayed.
- [x] Completed scans saved automatically to SQLite.
- [x] Scan history available.
- [x] Historical scans load into results view.
- [x] HTML reports generated and opened.
- [x] Historical reports can be regenerated from stored evidence.
- [x] Scanning does not block the Tkinter interface.
- [x] 61 backend regression tests pass.
- [x] Manual GUI acceptance testing successful.
- [x] Feature branch clean and pushed.

## 24. Remaining Work

Not part of Milestone 2:

```text
UAC administrator elevation
PyInstaller Windows .exe
Bundled resource-path handling
Windows VM comparison testing
Deliberately misconfigured VM Fail evidence
Final project documentation
README completion
Final release PR
```

## 25. Next Milestone

Next branch after merging this milestone into `develop`:

```text
feature/admin-elevation
```

Planned flow:

```text
Detect administrator privilege
        ↓
Request elevation through Windows UAC
        ↓
Restart SecureAudit elevated when approved
        ↓
Run administrator-required assessments
```

SecureAudit must never silently bypass UAC or grant itself permanent administrative access.
