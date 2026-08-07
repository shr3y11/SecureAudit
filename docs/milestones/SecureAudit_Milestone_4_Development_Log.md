---
title: SecureAudit Windows MVP — Milestone 4 Development Log
project: SecureAudit
branch: feature/windows-build
milestone: Standalone Windows Packaging and Runtime Path Hardening
status: Complete on development machine
tests: 89 passed
latest_commit: 5307cff
repository_path: C:\Users\wale1\Projects\SecureAudit
tags:
  - secureaudit
  - windows
  - pyinstaller
  - packaging
  - uac
  - grc
  - compliance
  - sqlite
  - powershell
  - testing
---

# SecureAudit Windows MVP — Milestone 4 Development Log

> [!success] Milestone status
> The Windows packaging milestone is complete on the development machine.
>
> Verified outcomes:
>
> - SecureAudit builds as a single windowed `SecureAudit.exe`.
> - PyInstaller `6.21.0` works with the project environment.
> - Trusted scanner resources are bundled with the executable.
> - Source-mode and frozen-mode paths are separated.
> - Frozen UAC relaunch behavior is covered by automated tests.
> - Packaged scans write persistent SQLite evidence and HTML reports under `%LOCALAPPDATA%\SecureAudit`.
> - The reproducible build configuration is committed and pushed.
> - Final automated test result: **89 passed**.
> - Latest commit: **`5307cff build(windows): package SecureAudit with PyInstaller`**.
>
> Clean Windows VM portability testing is still a separate follow-up activity.

---

## 1. Quick Reference

| Item | Value |
|---|---|
| Repository | `SecureAudit` |
| Local path | `C:\Users\wale1\Projects\SecureAudit` |
| Active branch | `feature/windows-build` |
| Python | `3.14.6` |
| PyInstaller | `6.21.0` |
| pytest | `8.4.2` |
| Final test count | `89 passed` |
| Final build output | `dist\SecureAudit.exe` |
| Observed EXE size | `13,250,316` bytes |
| Final commit | `5307cff` |
| Remote branch | `origin/feature/windows-build` |
| Final working tree | Clean |
| Packaged database | `%LOCALAPPDATA%\SecureAudit\data\secureaudit.db` |
| Packaged reports | `%LOCALAPPDATA%\SecureAudit\reports\` |

### Milestone commit sequence

| Commit | Purpose |
|---|---|
| `645212e` | `feat(paths): separate bundled resources from runtime data` |
| `7f84596` | `feat(paths): use packaged resource and runtime paths` |
| `2c11b8a` | `test(admin): cover frozen executable elevation` |
| `5307cff` | `build(windows): package SecureAudit with PyInstaller` |

---

# 2. Milestone Scope

This milestone converted the existing Windows MVP from a source-run Python application into a reproducible standalone Windows executable.

The work focused on four boundaries:

1. **Trusted application resources**
   - `checks/catalog.json`
   - `checks/powershell/*.ps1`

2. **Writable persistent evidence**
   - SQLite scan history
   - generated HTML reports

3. **Administrator elevation**
   - source execution through `pythonw.exe`
   - frozen execution through `SecureAudit.exe`

4. **Reproducible packaging**
   - `SecureAudit.spec`
   - `build.bat`
   - pinned PyInstaller version
   - ignored generated `build/` and `dist/`

The scanner allow-list, structured JSON result model, scoring, database, and report generation were preserved rather than rewritten.

---

# 3. Runtime Path Architecture

## Problem

Development paths such as:

```text
C:\Users\wale1\Projects\SecureAudit\checks\catalog.json
C:\Users\wale1\Projects\SecureAudit\data\secureaudit.db
```

cannot be assumed when SecureAudit is distributed as a standalone executable.

A PyInstaller one-file executable extracts bundled resources into a temporary application-controlled directory at runtime. Persistent evidence must not be stored there because that directory is temporary.

## Design

SecureAudit now separates paths into two classes.

### Trusted bundled resources

```text
checks/catalog.json
checks/powershell/*.ps1
```

Source mode:

```text
repository root
```

Frozen mode:

```text
PyInstaller resource root / sys._MEIPASS
```

### Writable persistent runtime state

Source mode:

```text
repository\data\
repository\reports\
```

Frozen mode:

```text
%LOCALAPPDATA%\SecureAudit\data\
%LOCALAPPDATA%\SecureAudit\reports\
```

## Security rationale

The privileged PowerShell scanner modules remain bundled with the application rather than being copied into a user-editable runtime directory.

This preserves the intended trust boundary:

```text
User selects approved check ID
          ↓
Bundled catalog
          ↓
Bundled approved PowerShell module
          ↓
Scanner path validation
          ↓
PowerShell execution
```

Mutable scan evidence is separated from executable scanner logic.

---

# 4. `core/paths.py`

## Purpose

`core/paths.py` became the central path abstraction for source and frozen execution.

Important responsibilities include:

```python
is_frozen()
source_root()
resource_root()
resource_path()
catalog_path()
powershell_directory()
runtime_root()
data_directory()
reports_directory()
database_path()
```

### Frozen resource root

Conceptually:

```python
if getattr(sys, "frozen", False):
    bundle_root = getattr(sys, "_MEIPASS", None)
```

This allows bundled catalog and PowerShell modules to be located after PyInstaller extraction.

### Frozen writable root

Conceptually:

```text
%LOCALAPPDATA%\SecureAudit
```

This keeps history and reports persistent between application launches.

### Path escape protection

The centralized helper validates that resolved child paths remain under their trusted base directory.

This complements the scanner's existing protection against:

```text
absolute script paths
directory traversal
nested script paths
unapproved scripts
```

---

# 5. Scanner Path Wiring

`core/scanner.py` no longer depends on hard-coded repository constants for its default catalog and PowerShell locations.

The scanner still supports explicit paths for tests, but normal runtime resolution is delegated to:

```python
default_catalog_path()
default_powershell_directory()
```

This preserved existing testability while allowing the same scanner code to function in source and packaged execution.

Security behavior was not relaxed. The scanner continues to enforce the allow-listed catalog and script-path validation.

---

# 6. Database and Reporting Path Wiring

## SQLite

The default database path is now derived through the centralized path layer.

Source mode:

```text
C:\Users\wale1\Projects\SecureAudit\data\secureaudit.db
```

Frozen mode:

```text
%LOCALAPPDATA%\SecureAudit\data\secureaudit.db
```

Observed packaged database:

```text
C:\Users\wale1\AppData\Local\SecureAudit\data\secureaudit.db
```

Observed size during testing:

```text
32768 bytes
```

## HTML reports

The reporting layer now resolves its default directory through the centralized path layer.

Observed packaged report example:

```text
C:\Users\wale1\AppData\Local\SecureAudit\reports\
secureaudit-4439bf10-4885-4293-af74-dfa0d652b3aa.html
```

Observed report size:

```text
15874 bytes
```

This confirms that persistent evidence is stored outside the PyInstaller temporary resource area.

---

# 7. Frozen Administrator Elevation

## Existing implementation

`core/admin.py` already contained the required distinction.

### Source execution

```text
python.exe app.py
      ↓ UAC
pythonw.exe app.py
```

`pythonw.exe` prevents a second console window from appearing behind the GUI during development.

### Frozen execution

```text
SecureAudit.exe
      ↓ UAC
SecureAudit.exe
```

Conceptually:

```python
if getattr(sys, "frozen", False):
    executable = str(sys.executable)
```

This prevents the packaged application from attempting to locate `pythonw.exe` on a machine where Python may not be installed.

## Tests added

Two tests were added:

```text
test_build_relaunch_command_uses_frozen_executable
test_build_relaunch_command_preserves_frozen_arguments
```

These establish that:

- frozen execution relaunches `SecureAudit.exe` directly;
- original arguments remain safely quoted and preserved.

Focused result:

```text
14 passed
```

Full suite after the tests:

```text
89 passed
```

---

# 8. PyInstaller Packaging

## Installed version

```text
PyInstaller 6.21.0
```

Installed inside:

```text
C:\Users\wale1\Projects\SecureAudit\.venv
```

## Packaging model

The build uses:

```text
one-file executable
windowed mode
explicit bundled resources
```

The generated output is:

```text
dist\SecureAudit.exe
```

Observed final rebuild:

```text
Name: SecureAudit.exe
Length: 13250316
LastWriteTime: 8/7/2026 7:02:35 PM
```

---

# 9. `SecureAudit.spec`

`SecureAudit.spec` is now the tracked reproducible PyInstaller configuration.

Explicit data files include:

```text
checks\catalog.json
checks\powershell\firewall.ps1
checks\powershell\defender.ps1
checks\powershell\bitlocker.ps1
checks\powershell\guest_account.ps1
checks\powershell\smbv1.ps1
```

The executable configuration contains:

```python
console=False
```

This creates a Windows GUI executable without a console window.

## Security significance of explicit resource listing

Using an explicit list means an unrelated `.ps1` file placed in the PowerShell directory is not automatically added to the packaged executable.

That supports SecureAudit's allow-list model and reduces accidental expansion of privileged scanner code.

---

# 10. `build.bat`

A reproducible Windows build script was created.

Its main operation is:

```bat
".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm SecureAudit.spec
```

It also validates that:

```text
.venv\Scripts\python.exe
SecureAudit.spec
```

exist before attempting a build.

Expected output:

```text
dist\SecureAudit.exe
```

This removes the need to remember the original long PyInstaller command.

---

# 11. Dependency and Git Configuration

## `requirements.txt`

The milestone pinned:

```text
pytest==8.4.2
pyinstaller==6.21.0
```

## `.gitignore`

Generated build artifacts remain ignored:

```text
build/
dist/
```

The generated Python template originally ignored all `.spec` files:

```text
*.spec
```

An explicit exception was added:

```text
!SecureAudit.spec
```

This allows the reproducible build specification to be committed while keeping generated binaries out of source control.

---

# 12. Automated Tests

## Final result

```text
89 passed
```

The full test suite covered:

```text
administrator elevation
GUI startup behavior
database persistence logic
runtime path handling
HTML reporting
allow-listed PowerShell scanner execution
scoring
```

## Path tests

The path layer includes tests for:

```text
source resource root
frozen resource root
missing _MEIPASS
catalog and PowerShell resource containment
resource traversal rejection
source runtime root
LOCALAPPDATA frozen runtime
missing LOCALAPPDATA
database directory creation
report directory creation
```

These tests matter because packaging changes filesystem assumptions without changing the core security model.

---

# 13. Packaged Runtime Verification

The first real PyInstaller build succeeded and produced:

```text
dist\SecureAudit.exe
```

A packaged application run produced persistent artifacts under:

```text
C:\Users\wale1\AppData\Local\SecureAudit
```

Observed structure:

```text
SecureAudit\
├── data\
│   └── secureaudit.db
└── reports\
    └── secureaudit-4439bf10-4885-4293-af74-dfa0d652b3aa.html
```

This is direct evidence that packaged execution reached the database/reporting pipeline and that persistent data is not stored inside `dist\` or the temporary PyInstaller resource area.

A copy of the executable was also successfully created at:

```text
C:\Users\wale1\OneDrive\Desktop\SecureAudit.exe
```

> [!note]
> The transcript confirms creation of the Desktop copy. A clean Windows VM remains the stronger portability test because the development machine already has the source repository and Python environment installed.

---

# 14. Errors Encountered and Fixes

## Error 1 — pytest temporary cleanup warning

Repeated after otherwise successful full-suite runs:

```text
PermissionError: [WinError 5] Access is denied:
C:\Users\wale1\AppData\Local\Temp\pytest-of-wale1\pytest-current
```

### Observed effect

The test result had already completed successfully:

```text
89 passed
```

### Interpretation

The warning occurred in pytest's `atexit` cleanup callback and did not invalidate the completed test suite.

It remains a development-environment cleanup issue rather than a SecureAudit functional failure.

---

## Error 2 — new frozen tests reported missing fixtures

Initial result:

```text
12 passed, 2 errors
fixture 'mock_frozen' not found
```

### Root cause

`unittest.mock.patch` was used with explicit replacement values. In that form, the decorator does not inject mock objects into the test function.

The function signatures incorrectly declared:

```text
mock_frozen
mock_executable
mock_argv
```

which pytest interpreted as fixtures.

### Fix

The unnecessary parameters were removed from both test functions.

### Verified result

```text
14 passed
89 passed
```

---

## Error 3 — PyInstaller could not overwrite running EXE

Build failure:

```text
PermissionError: [WinError 5] Access is denied:
C:\Users\wale1\Projects\SecureAudit\dist\SecureAudit.exe
```

### Root cause

Two `SecureAudit` processes were still running and Windows had the executable locked.

Observed processes:

```text
SecureAudit PID 30332
SecureAudit PID 33844
```

### Fix

```powershell
Get-Process SecureAudit -ErrorAction SilentlyContinue |
    Stop-Process -Force

Remove-Item .\dist\SecureAudit.exe -Force -ErrorAction SilentlyContinue
```

Verification:

```powershell
Test-Path .\dist\SecureAudit.exe
```

Observed:

```text
False
```

The subsequent `build.bat` run completed successfully.

---

## Error 4 — Desktop path assumption failed

Initial copy attempted to use:

```text
C:\Users\wale1\Desktop
```

but that directory did not exist.

### Root cause

Windows had redirected the user's Desktop to OneDrive.

### Fix

```powershell
$desktop = [Environment]::GetFolderPath("Desktop")
```

Observed:

```text
C:\Users\wale1\OneDrive\Desktop
```

Then:

```powershell
Copy-Item .\dist\SecureAudit.exe `
    (Join-Path $desktop "SecureAudit.exe") -Force
```

---

# 15. Important Commands Used

## Create feature branch baseline

```powershell
git status
git branch --show-current
```

## PyInstaller installation

```powershell
python -m pip install --upgrade pyinstaller
python -m PyInstaller --version
python -m pip show pyinstaller
```

## Initial package generation

```powershell
python -m PyInstaller `
    --name SecureAudit `
    --onefile `
    --windowed `
    --add-data "checks\catalog.json;checks" `
    --add-data "checks\powershell\firewall.ps1;checks\powershell" `
    --add-data "checks\powershell\defender.ps1;checks\powershell" `
    --add-data "checks\powershell\bitlocker.ps1;checks\powershell" `
    --add-data "checks\powershell\guest_account.ps1;checks\powershell" `
    --add-data "checks\powershell\smbv1.ps1;checks\powershell" `
    --specpath . `
    .\app.py
```

## Reproducible build

```powershell
.\build.bat
```

## Inspect executable

```powershell
Get-Item .\dist\SecureAudit.exe |
    Select-Object Name, Length, LastWriteTime
```

## Inspect persistent packaged data

```powershell
Get-ChildItem "$env:LOCALAPPDATA\SecureAudit" -Recurse -Force
```

## Full automated suite

```powershell
python -m pytest -v
```

## Desktop portability copy

```powershell
$desktop = [Environment]::GetFolderPath("Desktop")

Copy-Item .\dist\SecureAudit.exe `
    (Join-Path $desktop "SecureAudit.exe") -Force
```

---

# 16. Git History and Final Commit

Feature commits:

```text
645212e feat(paths): separate bundled resources from runtime data
7f84596 feat(paths): use packaged resource and runtime paths
2c11b8a test(admin): cover frozen executable elevation
5307cff build(windows): package SecureAudit with PyInstaller
```

Build commit:

```powershell
git add .\.gitignore
git add .\build.bat
git add .\requirements.txt
git add .\SecureAudit.spec

git commit -m "build(windows): package SecureAudit with PyInstaller"
git push
```

Verified final state:

```text
On branch feature/windows-build
Your branch is up to date with 'origin/feature/windows-build'.

nothing to commit, working tree clean
```

Latest commit:

```text
5307cff build(windows): package SecureAudit with PyInstaller
```

---

# 17. GRC and Security Interpretation

SecureAudit should be described as:

```text
an automated technical control assessment tool
```

for:

```text
selected Windows baseline checks
```

The packaged application provides point-in-time evidence for the implemented controls.

It does **not** prove:

```text
complete CIS compliance
complete ISO 27001 compliance
complete NIST compliance
certified compliance
overall organizational security
```

Relevant design choices for a GRC/security report include:

1. privileged scanner logic is application-controlled;
2. arbitrary user-supplied PowerShell is not accepted;
3. check execution remains catalog allow-listed;
4. persistent evidence is separated from bundled scanner code;
5. `Error` remains distinct from `Fail`;
6. packaging preserves structured result and scoring behavior;
7. generated evidence is local to the assessed endpoint;
8. clean VM validation is still needed before claiming broad deployment portability.

---

# 18. Definition of Done

## Verified

- [x] Centralized source/frozen path abstraction implemented.
- [x] Bundled resources resolve through the application resource root.
- [x] Writable frozen state resolves through `%LOCALAPPDATA%\SecureAudit`.
- [x] Database and report paths wired into application defaults.
- [x] Frozen executable UAC behavior covered by tests.
- [x] PyInstaller `6.21.0` installed and verified.
- [x] `SecureAudit.spec` created.
- [x] Catalog and all five PowerShell checks explicitly bundled.
- [x] Windowed executable configured with `console=False`.
- [x] `build.bat` created and used successfully.
- [x] `SecureAudit.exe` generated successfully.
- [x] Packaged execution created persistent SQLite database.
- [x] Packaged execution created persistent HTML report.
- [x] `build/` and `dist/` remain ignored by Git.
- [x] Reproducible build configuration committed.
- [x] Commit pushed to `origin/feature/windows-build`.
- [x] Final automated result: `89 passed`.
- [x] Working tree clean after final commit.

## Follow-up validation

- [ ] Clean Windows VM with no project source tree.
- [ ] Clean Windows VM with no Python installation.
- [ ] Capture clean screenshots of UAC approve and cancel paths.
- [ ] Capture Task Manager/process evidence for one-GUI/no-console behavior.
- [ ] Record clean VM scan timing.
- [ ] Record clean VM report and database persistence across restart.
- [ ] Optionally record Windows Defender/SmartScreen behavior for unsigned executable.

---

# 19. Remaining Work

The next work should focus on **deployment validation rather than new architecture**.

Recommended next actions:

1. test `SecureAudit.exe` on a clean Windows VM;
2. verify no Python installation is required;
3. verify all five checks execute;
4. verify UAC behavior;
5. verify SQLite/report persistence;
6. capture evidence for the research/report guide;
7. merge `feature/windows-build` into `develop` after validation;
8. continue final project documentation and release preparation.

> [!important]
> Do not expand into centralized multi-endpoint orchestration until the single-host Windows MVP has been fully validated and documented.
