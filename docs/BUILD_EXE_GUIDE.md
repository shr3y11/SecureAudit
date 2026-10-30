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

## Required catalog signing before packaging

Both shipped specs now require signed catalog/PowerShell collector resources
and a public-key fingerprint pinned in `core/catalog_trust.py`. Packaging fails
until the owner completes the signing procedure; unsigned source development
remains available. This policy concerns catalog authenticity, distinct from
Windows executable code signing above.

```powershell
python tools/sign_catalog.py generate --private-key C:\Keys\secureaudit-catalog.key
python tools/sign_catalog.py sign --private-key C:\Keys\secureaudit-catalog.key
```

Generate only once; keep the private key outside the repository. Commit
`checks/catalog.pub.pem`, `checks/catalog.sig.json` and `core/catalog_trust.py`
with the catalog changes. After each covered catalog/PowerShell change, re-sign.
The verifier code and its embedded pin must remain trusted. Replacing both
signature files is rejected under the pinned policy; deleting both is rejected
at release build and runtime. Linux experimental collectors are not covered by
this Windows catalog signature. No owner key was created by the repair work.
