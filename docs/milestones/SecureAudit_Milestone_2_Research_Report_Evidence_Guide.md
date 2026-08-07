---
title: SecureAudit Windows MVP — Milestone 2 Research, Report, and Evidence Guide
project: SecureAudit
branch: feature/tkinter-gui
milestone: Tkinter GUI and Local Workflow Integration
status: Complete
tests: 61 passed
latest_commit: d1f18fa
tags: [secureaudit, research, evidence, tkinter, grc, compliance, windows, reporting]
---

# SecureAudit Windows MVP — Milestone 2 Research, Report, and Evidence Guide

> [!important]
> This guide identifies the strongest evidence to preserve from the completed Tkinter GUI and workflow-integration milestone.
>
> **Branch:** `feature/tkinter-gui`
> **Latest commit:** `d1f18fa`
> **Automated tests:** `61 passed`
> **Manual GUI acceptance testing:** user-reported successful

## 1. Evidence Status Legend

| Label | Meaning |
|---|---|
| **Available now** | Evidence has already been produced. |
| **Should be recreated cleanly** | Behavior was verified, but a cleaner screenshot/output should be captured. |
| **Not available yet** | Depends on a later milestone. |
| **Needed after the demo** | Useful for research/final reporting but not required before the immediate MVP demo. |

## 2. Core Research Story

Milestone 2 demonstrates that SecureAudit is no longer only a set of backend modules. It now implements the complete local user workflow:

```text
Tkinter GUI
    ↓
Approved catalog
    ↓
Selected check IDs
    ↓
Trusted scanner
    ↓
Structured evidence
    ↓
Pass / Fail / Error
    ↓
Compliance score + coverage
    ↓
SQLite history
    ↓
HTML report
```

Central security/GRC claim:

> A user-facing desktop compliance-assessment workflow can remain usable without weakening the trusted execution boundary established by the backend.

## 3. Screenshots to Capture

### 3.1 Main SecureAudit GUI

**Status:** Should be recreated cleanly

Capture the application with all five approved checks visible.

Suggested filename:

```text
m2_01_main_gui_catalog.png
```

Show:

```text
SecureAudit title
Checklist
Select All / Clear All
Five approved checks
Run Selected Checks
Latest Scan Results
Open HTML Report
Scan History
```

### 3.2 Catalog Metadata

**Status:** Should be recreated cleanly

Capture visible metadata such as:

```text
Check ID
Name
Category
Severity
Administrator required / not required
Description
```

Suggested filename:

```text
m2_02_catalog_metadata.png
```

### 3.3 Selected-Only Execution

**Status:** Available now; should be recreated cleanly

Prefer a clean run with only:

```text
WIN-FW-001
WIN-GUEST-001
```

Suggested filenames:

```text
m2_03_two_checks_selected.png
m2_04_two_check_results.png
```

Database evidence command:

```powershell
python -c "from core.database import list_scans, get_scan; import json; scans=list_scans(limit=1); scan=get_scan(scans[0]['scan_id']); print(json.dumps(scan, indent=2))"
```

### 3.4 Fully Assessed Example

**Status:** Available now

Observed:

```text
Selected: 2
Passed: 2
Failed: 0
Errors: 0
Assessed: 2
Compliance score: 100%
Coverage: 100%
```

Suggested filename:

```text
m2_05_full_coverage_scan.png
```

### 3.5 Administrator-Required Error Example

**Status:** Available now; high priority

Capture a normal non-elevated run of:

```text
WIN-BL-001
WIN-SMB1-001
```

Observed:

```text
Passed: 0
Failed: 0
Errors: 2
Compliance Score: Not available
Assessment Coverage: 0.00%
```

Suggested filename:

```text
m2_06_admin_required_errors.png
```

Research value:

```text
Cannot assess ≠ control failure
```

### 3.6 Mixed Score vs Coverage

**Status:** Available now

Observed:

```text
Selected: 3
Passed: 2
Failed: 0
Errors: 1
Assessed: 2
Compliance score: 100%
Coverage: 66.67%
```

Suggested filename:

```text
m2_07_score_vs_coverage.png
```

### 3.7 Five-Check Scan

**Status:** Available now

Observed:

```text
Selected: 5
Passed: 3
Failed: 0
Errors: 2
Assessed: 3
Compliance score: 100%
Coverage: 60%
```

Suggested filename:

```text
m2_08_five_check_scan.png
```

### 3.8 Scan History

**Status:** Manually verified; should be recreated cleanly

Capture the history window with multiple scans and differing score/coverage values.

Suggested filename:

```text
m2_09_scan_history.png
```

### 3.9 Historical Scan Loaded

**Status:** Manually verified; should be recreated cleanly

Suggested filename:

```text
m2_10_historical_scan_loaded.png
```

### 3.10 Open HTML Report

**Status:** Manually verified; should be recreated cleanly

Suggested filenames:

```text
m2_11_open_report_button.png
m2_12_report_browser.png
```

### 3.11 Responsive Scan State

**Status:** Manually verified; should be recreated cleanly

Capture:

```text
Scanning 5 selected checks...
```

with the Run button disabled.

Suggested filename:

```text
m2_13_background_scan_progress.png
```

## 4. Terminal Evidence

### 4.1 Final automated regression suite

**Status:** Available now

Command:

```powershell
python -m pytest -v
```

Observed:

```text
61 passed in 1.83s
```

Suggested screenshot:

```text
m2_14_61_tests_passed.png
```

### 4.2 Final clean Git state

**Status:** Available now

Observed:

```text
On branch feature/tkinter-gui
Your branch is up to date with 'origin/feature/tkinter-gui'.

nothing to commit, working tree clean
```

Latest commit:

```text
d1f18fa feat(ui): run scans without blocking the interface
```

Suggested screenshot:

```text
m2_15_git_clean_final_commit.png
```

### 4.3 Recent scan-history output

**Status:** Available now

Command:

```powershell
python -c "from core.database import list_scans; import json; print(json.dumps(list_scans(limit=5), indent=2))"
```

Preserve the combinations:

```text
5 selected / 3 pass / 2 error / 100% score / 60% coverage
3 selected / 2 pass / 1 error / 100% score / 66.67% coverage
2 selected / 2 pass / 0 error / 100% score / 100% coverage
2 selected / 0 pass / 2 error / N/A score / 0% coverage
```

Suggested filename:

```text
m2_16_database_history_terminal.png
```

## 5. Important Code Excerpts

Preserve excerpts from `app.py` showing:

### Application orchestration

```text
run_local_scan()
```

with calls to:

```text
run_check()
calculate_score()
save_scan()
get_scan()
write_html_report()
```

### Catalog loading

```python
catalog = load_catalog()
```

and filtering `enabled: true` entries.

### Check-ID-only selection

Preserve `_selected_check_ids()` and the call to `run_local_scan(selected_check_ids)`.

### Thread boundary

Preserve:

```text
_run_selected_checks()
_scan_worker()
_handle_scan_success()
_handle_scan_error()
```

especially:

```python
threading.Thread(...)
self.root.after(...)
```

### Historical evidence retrieval

Preserve:

```python
list_scans(limit=100)
get_scan(scan_id)
```

### Report regeneration

Preserve the `write_html_report(scan)` path used when a historical report file is missing.

## 6. Architecture Diagram

```text
┌────────────────────────────────────┐
│           Tkinter Interface         │
│ checklist / results / history       │
└──────────────────┬─────────────────┘
                   │ selected check IDs
                   ▼
┌────────────────────────────────────┐
│             app.py                  │
│ orchestration + UI workflow         │
└───────┬──────────┬─────────┬───────┘
        │          │         │
        ▼          ▼         ▼
   scanner.py  scoring.py database.py
        │                    │
        ▼                    ▼
 trusted PowerShell         SQLite
        │                    │
        └──────────┬─────────┘
                   ▼
              reporting.py
                   │
                   ▼
             HTML report
```

Suggested caption:

> SecureAudit V1 separates presentation from trusted assessment logic. The Tkinter interface passes approved check identifiers into reusable core modules while scanner execution, scoring, evidence storage, and report generation remain isolated.

## 7. Database Diagram

```text
scans
│
├── scan_id
├── hostname
├── timestamps
├── selected_count
├── passed_count
├── failed_count
├── error_count
├── assessed_count
├── compliance_score
└── coverage_percentage
       │
       │ 1-to-many
       ▼
scan_results
│
├── check_id
├── check_name
├── expected_value
├── observed_value
├── status
├── evidence_json
├── error_message
└── timestamp_utc
```

## 8. Metrics Available Now

### Functional metrics

```text
Approved checks: 5
Automated regression tests: 61
GUI milestone commits: 5
```

### Assessment examples

| Scenario | Selected | Assessed | Errors | Score | Coverage |
|---|---:|---:|---:|---:|---:|
| Fully assessed | 2 | 2 | 0 | 100% | 100% |
| Mixed | 3 | 2 | 1 | 100% | 66.67% |
| Five checks | 5 | 3 | 2 | 100% | 60% |
| No assessable controls | 2 | 0 | 2 | N/A | 0% |

These describe observed technical-check results on the test machine and do not imply complete framework compliance.

## 9. Performance Evidence

Observed five-check scan timestamps:

```text
2026-08-07T11:10:48.421437+00:00
→ 2026-08-07T11:10:55.593123+00:00
```

Approximate elapsed time: **7.17 seconds**.

Another five-check scan:

```text
2026-08-07T11:07:57.791365+00:00
→ 2026-08-07T11:08:04.989835+00:00
```

Approximate elapsed time: **7.20 seconds**.

### Needed after the demo

Repeat at least 10 controlled scans and calculate:

```text
Mean duration
Median duration
Minimum
Maximum
Standard deviation
```

Do not present the two current runs as statistically representative.

## 10. Accuracy / Ground-Truth Evidence

### Available now

Administrator-required controls produced permission-related `Error` results in a non-elevated session.

### Not available yet

A controlled VM matrix containing known Pass and known Fail states for every check.

Future matrix:

| Check | Ground truth | SecureAudit result | Correct? |
|---|---|---|---|
| Firewall | Enabled | Pass | |
| Firewall | Disabled | Fail | |
| Defender | Enabled | Pass | |
| Defender | Disabled | Fail | |
| BitLocker | Enabled | Pass | |
| BitLocker | Disabled | Fail | |
| Guest | Disabled | Pass | |
| Guest | Enabled | Fail | |
| SMBv1 | Disabled | Pass | |
| SMBv1 | Enabled | Fail | |

## 11. Standard-User vs Administrator Comparison

### Available now

Standard-user behavior:

```text
BitLocker → Error: Access denied
SMBv1     → Error: operation requires elevation
```

### Not available yet

Elevated GUI workflow through SecureAudit's own UAC handling.

That belongs to:

```text
feature/admin-elevation
```

## 12. Report Evidence

### Available now

- Standalone HTML reports generated automatically.
- GUI opens current reports.
- Historical reports can be regenerated from SQLite.

Capture:

```text
Report summary header
Compliance score
Coverage
Pass / Fail / Error counts
Detailed findings
Technical evidence
Scope disclaimer
```

Suggested filenames:

```text
m2_report_01_summary.png
m2_report_02_findings.png
m2_report_03_evidence.png
m2_report_04_disclaimer.png
```

## 13. Security Decisions to Highlight

- Allow-listed execution remains enforced.
- No user-supplied PowerShell command text.
- No user-supplied script path.
- GUI does not reimplement scanner security validation.
- `Error` remains separate from `Fail`.
- Score and coverage remain independent.
- Historical scans are read from SQLite.
- Report generation remains inside the tested reporting module.
- Threading improves responsiveness only and does not alter execution trust boundaries.

## 14. Research Questions

1. Can a lightweight local Windows compliance scanner provide useful point-in-time technical evidence without allowing arbitrary privileged command execution?
2. How does separating assessment coverage from compliance score reduce misleading interpretations of partial scans?
3. Can historical technical-control evidence be preserved locally using SQLite while remaining reconstructable for reporting?
4. How should a compliance scanner distinguish technical control failure from inability to assess?
5. Can a desktop compliance workflow remain responsive while multiple PowerShell-based checks execute?
6. How effectively does a catalog-driven interface constrain user actions to approved assessment modules?

## 15. Threats to Validity

Current limitations:

```text
Single primary Windows development machine
Only five technical checks
No dedicated misconfigured VM evidence yet
No integrated UAC elevation yet
No packaged .exe yet
No per-check performance instrumentation
No external benchmark against CIS-CAT/Nessus/Wazuh
No multi-endpoint testing
```

Current evidence supports functional behavior of selected Windows technical assessments, not universal compatibility or complete framework compliance.

## 16. Wording for Reports

Prefer:

> SecureAudit performs automated point-in-time technical configuration assessment for selected Windows controls.

> Framework mappings may be partial and do not establish complete framework compliance.

> Compliance score reflects successfully assessed selected checks only.

> Assessment coverage reports the proportion of selected checks for which a reliable Pass or Fail determination was obtained.

Avoid:

```text
System is CIS compliant
Certified secure
Audit passed
Complete compliance
Guaranteed configuration security
```

## 17. Later Milestone Evidence

### Administrator elevation — Not available yet

Capture:

```text
UAC prompt
Privilege detection
Standard vs elevated result comparison
User declining UAC
Successful elevated assessment
```

### Windows `.exe` — Not available yet

Capture:

```text
PyInstaller build output
dist\SecureAudit.exe
Launch without Python terminal
Bundled catalog loading
Bundled PowerShell scripts
SQLite creation
Report creation
```

### VM comparison — Not available yet

Capture:

```text
Mostly compliant VM
Deliberately misconfigured VM
Known ground-truth settings
SecureAudit output
Generated reports
Pass/Fail accuracy table
```

## 18. Suggested Demo Sequence

```text
1. Launch SecureAudit.
2. Show catalog-driven checklist.
3. Select Firewall + Guest.
4. Run scan.
5. Show responsive scanning state.
6. Show result rows.
7. Explain score vs coverage.
8. Open Scan History.
9. Load an older scan.
10. Open HTML Report.
11. Show BitLocker/SMBv1 Error example.
12. Explain why Error is not Fail.
13. Show 61 passing tests.
14. Show clean Git history.
```

## 19. Redaction Guidance

Consider redacting before publication:

```text
Windows username
Full local filesystem paths
Sensitive machine names
Unrelated browser tabs
Any tokens, credentials, or recovery keys
```

Normally safe to show:

```text
SecureAudit check IDs
Statuses
Scores
Coverage
Test counts
Commit hashes
Catalog metadata
```

## 20. Final Evidence Checklist

### Available now

- [x] Five approved GUI checklist entries.
- [x] Selected-only execution evidence.
- [x] Pass example.
- [x] Error example.
- [x] Score/coverage examples.
- [x] SQLite history.
- [x] Multiple point-in-time scans.
- [x] HTML report generation.
- [x] Scan-history functionality.
- [x] Historical-scan loading.
- [x] Report-opening functionality.
- [x] Responsive background scan execution.
- [x] 61 passing automated tests.
- [x] Clean final Git state.
- [x] Final GUI commit `d1f18fa`.

### Should be recreated cleanly

- [ ] Main GUI screenshot.
- [ ] Two-check selection screenshot.
- [ ] Full-coverage result screenshot.
- [ ] Error-only result screenshot.
- [ ] Mixed score/coverage screenshot.
- [ ] Scan-history screenshot.
- [ ] Historical-scan screenshot.
- [ ] Browser report screenshot.
- [ ] Background-scanning screenshot.
- [ ] Final pytest screenshot.
- [ ] Final Git-history screenshot.

### Not available yet

- [ ] UAC elevation screenshots.
- [ ] Standard-user vs elevated comparison.
- [ ] `.exe` packaging evidence.
- [ ] VM misconfiguration Fail evidence.
- [ ] Per-check accuracy matrix.
- [ ] Multi-environment compatibility results.

## 21. Milestone Research Summary

Milestone 2 demonstrates that SecureAudit can expose its trusted Windows technical-assessment backend through a usable desktop workflow without moving sensitive execution logic into the GUI.

The strongest demonstrated behaviors are:

```text
Catalog-controlled selection
Selected-only execution
Pass / Fail / Error preservation
Independent score and coverage
Automatic SQLite persistence
Historical evidence retrieval
Report generation from stored evidence
Responsive background execution
```

The next evidence milestone should focus on administrator elevation and comparing non-elevated `Error` results with elevated technical assessment results.
