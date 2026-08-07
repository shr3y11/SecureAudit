# Windows EXE Build Guide

## Requirements

- Windows
- project virtual environment
- Python
- PyInstaller `6.21.0`
- tracked `SecureAudit.spec`

## Build

From the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
.\build.bat
```

Expected output:

```text
dist\SecureAudit.exe
```

## Build Script

`build.bat` invokes:

```text
.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm SecureAudit.spec
```

It also verifies that the virtual-environment Python and `SecureAudit.spec` exist.

## Packaged Resources

The spec explicitly includes:

```text
checks\catalog.json
checks\powershell\firewall.ps1
checks\powershell\defender.ps1
checks\powershell\bitlocker.ps1
checks\powershell\guest_account.ps1
checks\powershell\smbv1.ps1
```

Using an explicit resource list is preferable to automatically bundling every `.ps1` file because additions require an intentional build-configuration change.

## Windowed Build

The PyInstaller spec uses:

```python
console=False
```

so the packaged GUI does not require a console window.

## Runtime Paths

Trusted packaged files are resolved from PyInstaller's runtime resource directory.

Writable state is stored under:

```text
%LOCALAPPDATA%\SecureAudit
```

## Common Build Error: EXE Locked

Observed error:

```text
PermissionError: [WinError 5] Access is denied:
...\dist\SecureAudit.exe
```

Cause:

A running `SecureAudit.exe` process is locking the existing output file.

Fix:

```powershell
Get-Process SecureAudit -ErrorAction SilentlyContinue |
    Stop-Process -Force

Remove-Item .\dist\SecureAudit.exe -Force -ErrorAction SilentlyContinue

.\build.bat
```

## Verify Build

```powershell
Get-Item .\dist\SecureAudit.exe |
    Select-Object Name, Length, LastWriteTime
```

A verified development-machine build was approximately 13.25 MB.

## Git Rules

Commit:

```text
SecureAudit.spec
build.bat
requirements.txt
.gitignore
```

Do not commit:

```text
build\
dist\
SecureAudit.exe
```

## Code Signing

V1 is not code-signed.

Unsigned executables may trigger Windows reputation or SmartScreen warnings on other systems. Code signing is a future release-hardening task.
