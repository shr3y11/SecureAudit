---
title: SecureAudit Windows MVP — Milestone 3 Research and Report Evidence Guide
project: SecureAudit
branch: feature/admin-elevation
milestone: Administrator Privilege Detection and Windows UAC Elevation
tests: 77 passed
latest_commit: 4918ea3
tags:
  - secureaudit
  - research
  - evidence
  - windows
  - uac
  - administrator
  - grc
---

# SecureAudit Windows MVP — Milestone 3 Research and Report Evidence Guide

> [!important]
> This guide identifies evidence worth preserving for the administrator-elevation milestone.
>
> Do not claim evidence exists unless it was actually captured.

## 1. Current Evidence Status

| Evidence | Status |
|---|---|
| 77-test automated suite | Available now |
| Clean Git history | Available now |
| Standard-user `is_admin() → False` | Available now / can be recreated cleanly |
| UAC approval returning `started` | Available now / can be recreated cleanly |
| UAC cancellation returning `cancelled` | Available now / can be recreated cleanly |
| GUI launches after UAC | Manually verified |
| No extra console after `pythonw.exe` fix | Manually verified |
| Already-elevated launch | Manually verified |
| Clean polished screenshots | Should be recreated cleanly |
| Packaged `.exe` UAC behavior | Not available yet |
| VM comparison | Needed after packaging/demo |

## 2. Screenshots to Capture

### Screenshot A — Standard-user privilege detection

Command:

```powershell
cd "C:\Users\wale1\Projects\SecureAudit"
.\.venv\Scripts\Activate.ps1
python -c "from core.admin import is_admin; print(is_admin())"
```

Expected visible result:

```text
False
```

Suggested filename:

```text
M3_01_standard_user_admin_detection.png
```

Research value:

Demonstrates that SecureAudit can distinguish a non-elevated process before requesting privileged execution.

### Screenshot B — Windows UAC prompt

Launch:

```powershell
python .\app.py
```

Capture the Windows UAC consent dialog.

Suggested filename:

```text
M3_02_windows_uac_prompt.png
```

Redaction:

- Hide unrelated desktop content.
- Do not reveal personal file paths if unnecessary.
- Avoid exposing unrelated usernames or notifications.

Research value:

Shows that SecureAudit uses the operating system's normal consent mechanism rather than bypassing UAC.

### Screenshot C — Elevated SecureAudit GUI

After approving UAC, capture the GUI.

Suggested filename:

```text
M3_03_elevated_secureaudit_gui.png
```

Research value:

Shows successful privilege transition into the normal desktop interface.

### Screenshot D — Privileged five-check assessment

Capture an elevated scan containing:

```text
WIN-FW-001
WIN-DEF-001
WIN-BL-001
WIN-GUEST-001
WIN-SMB1-001
```

Suggested filename:

```text
M3_04_elevated_five_check_scan.png
```

Research value:

Demonstrates that administrator-dependent checks can now be assessed after elevation.

Do not manipulate the host simply to obtain all-Pass results.

### Screenshot E — UAC cancellation

Recreate:

```powershell
python .\app.py
```

Select **No** on UAC and capture SecureAudit's clean cancellation behavior if practical.

Suggested filename:

```text
M3_05_uac_cancelled_cleanly.png
```

### Screenshot F — Automated tests

Command:

```powershell
python -m pytest -v
```

Capture:

```text
77 passed
```

Suggested filename:

```text
M3_06_77_tests_passed.png
```

The recurring pytest cleanup warning may also appear after the successful result. If captured, explain that it occurs during exit-time temporary-directory cleanup after the completed suite.

## 3. Important Code Excerpts

Preserve excerpts from:

```text
core/admin.py
app.py
tests/test_admin.py
tests/test_app.py
```

### Administrator detection

Preserve the function demonstrating use of the Windows Shell API rather than a PowerShell text-parsing command.

### UAC request

Preserve the call path using Windows `runas`.

Research point:

```text
SecureAudit requests privilege through normal Windows consent.
It does not bypass UAC.
```

### Cancellation handling

Preserve the branch that maps Windows cancellation to a controlled application result rather than a crash.

### `pythonw.exe` selection

Preserve the source-mode logic selecting:

```text
pythonw.exe
```

and frozen-mode logic using the packaged executable.

### Startup orchestration

Preserve the `main()` logic showing:

```text
already_elevated → GUI
started          → original exits
cancelled        → clean message/exit
```

## 4. Security Architecture Diagram

Recommended diagram:

```text
User launches SecureAudit
        ↓
Administrator detection
        ↓
Already elevated?
   ┌────┴────┐
   │         │
  Yes        No
   │         │
   │     Windows UAC
   │      ┌──┴──┐
   │      │     │
   │    Approve Cancel
   │      │     │
   │      │   Stop cleanly
   │      ↓
   │  Elevated SecureAudit
   └──────┬──────
          ↓
     Tkinter GUI
          ↓
   Approved catalog
          ↓
 Allow-listed scanner
          ↓
   PowerShell checks
```

Security message:

> Elevation changes process privilege, not scanner authorization.

## 5. Standard-User vs Administrator Comparison

Recommended research table:

| Scenario | BitLocker | SMBv1 | Interpretation |
|---|---|---|---|
| Standard user | May return `Error` due to access restriction | May return `Error` because elevation is required | Evidence could not be collected reliably |
| Administrator | `Pass` or `Fail` | `Pass` or `Fail` | Check was actually assessed |

This comparison is more useful than forcing an all-Pass machine.

## 6. Metrics to Preserve

Current automated metric:

```text
77 tests passed
```

Potential milestone metrics:

- Time from application launch to elevated GUI.
- Number of UAC prompts per normal launch: expected `1`.
- Number of GUI instances after elevation: expected `1`.
- UAC cancellation tracebacks: expected `0`.
- Privileged checks assessed before elevation vs after elevation.
- Coverage percentage before elevation vs after elevation.

## 7. Suggested Experiment

### Research question

> How does administrator elevation affect technical assessment coverage without changing the compliance scoring model?

Procedure:

1. Run SecureAudit without automatic elevation or use prior non-elevated evidence.
2. Select all five checks.
3. Record Pass / Fail / Error.
4. Record compliance score.
5. Record assessment coverage.
6. Run elevated SecureAudit.
7. Select the same five checks.
8. Record the same metrics.
9. Compare results.

Expected interpretation:

Elevation may reduce permission-related `Error` results and increase assessment coverage.

It should not be framed as automatically increasing compliance.

## 8. Threats to Validity

Potential limitations:

- Results depend on Windows edition and available cmdlets.
- Local administrator behavior may vary by UAC policy.
- Domain policy may affect elevation or security configuration.
- A single Windows host is not representative of an enterprise fleet.
- Administrator access does not guarantee every Windows security feature exists.
- VM and host configurations may differ.
- Source-mode Python behavior differs from frozen PyInstaller behavior.

## 9. Security Claims to Avoid

Do not claim:

```text
SecureAudit bypasses UAC
SecureAudit grants itself Administrator rights
SecureAudit proves complete CIS compliance
Administrator mode makes the system compliant
All privileged checks always succeed
```

Preferred wording:

```text
SecureAudit requests administrator elevation through Windows UAC.
SecureAudit performs selected technical control assessments.
Administrator elevation can improve assessment coverage for privileged checks.
Pass, Fail, and Error remain separate assessment outcomes.
```

## 10. Report Evidence

For a clean elevated report, preserve:

- hostname,
- scan timestamp,
- selected-check count,
- Pass count,
- Fail count,
- Error count,
- compliance score,
- assessment coverage,
- BitLocker result,
- SMBv1 result,
- scope disclaimer.

Suggested filename:

```text
M3_07_elevated_html_report.png
```

## 11. Git Evidence

Capture:

```powershell
git log -6 --oneline
git status
```

Important commits:

```text
4918ea3 feat(app): require Windows administrator elevation at startup
aa37465 feat(admin): relaunch GUI elevation without console window
a0e90df feat(admin): request Windows UAC elevation
7c2c1ba feat(admin): detect Windows administrator privileges
```

Suggested screenshot:

```text
M3_08_admin_elevation_git_history.png
```

## 12. Evidence Integrity Checklist

- [ ] Standard-user detection screenshot captured cleanly
- [ ] Windows UAC screenshot captured
- [ ] Elevated GUI screenshot captured
- [ ] UAC cancellation behavior captured
- [ ] Elevated five-check scan captured
- [ ] BitLocker privilege comparison preserved
- [ ] SMBv1 privilege comparison preserved
- [ ] Compliance score preserved
- [ ] Assessment coverage preserved
- [ ] HTML report screenshot preserved
- [ ] 77-test result captured
- [ ] Git history captured
- [ ] No passwords, tokens, personal identifiers, or irrelevant desktop content exposed

## 13. Evidence Needed Later

### Not available yet

- Packaged `SecureAudit.exe`.
- Packaged UAC prompt behavior.
- PyInstaller bundled-resource verification.
- Clean-machine execution.
- Windows VM comparison.
- Build artifact hashes.
- Windows Defender false-positive behavior, if any.
- Release build evidence.

These belong primarily to the next milestone:

```text
feature/windows-build
```

## 14. Future Report/Presentation Talking Points

### Architecture

> SecureAudit separates operating-system privilege management from scanner authorization. Windows UAC elevates the application process, while the scanner continues to accept only predefined catalog-controlled PowerShell checks.

### GRC

> Permission failure is represented as `Error`, not `Fail`. After administrator elevation, privileged controls can be assessed, increasing evidence coverage without altering the definition of compliance.

### Security

> The application does not accept arbitrary PowerShell commands, does not bypass UAC, and does not grant persistent administrator rights.

### Engineering

> The elevation helper supports source development through `pythonw.exe` and is structured to reuse the packaged executable when SecureAudit is frozen by PyInstaller.

## 15. Milestone Evidence Summary

```text
Branch:
feature/admin-elevation

Latest commit:
4918ea3

Automated tests:
77 passed

Core evidence:
Administrator detection
Windows UAC elevation
UAC cancellation
Console-free GUI relaunch
Already-elevated behavior
Startup integration
Preserved scanner allow-list
```
