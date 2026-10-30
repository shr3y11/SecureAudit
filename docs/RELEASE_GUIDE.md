# SecureAudit v0.6.0-beta release guide

## Install

Download SecureAudit-v0.6.0-beta-Windows-x64.zip and its .sha256 file from the same build. Verify the ZIP with PowerShell:

```powershell
Get-FileHash .\SecureAudit-v0.6.0-beta-Windows-x64.zip -Algorithm SHA256
```

Compare the result with the .sha256 file. Extract the whole ZIP, open SecureAudit-v0.6.0-beta, then launch SecureAuditCentral.exe. Keep all neighbouring files. Windows x64 is required. Keep the launcher open while the local dashboard is in use.

Use Scan this PC for real approved checks. Demo endpoints are simulated. Elevation can be required for particular collectors; launch as administrator when appropriate. The application does not change the assessed settings.

## Upgrade from v0.5.0-beta

1. Close the old launcher and any source-mode server.
2. Back up the applicable %LOCALAPPDATA%\\SecureAuditCentral and %LOCALAPPDATA%\\SecureAudit folders, including databases, access key and reports.
3. Extract the new ZIP into a separate application folder. Never merge it into an old runtime folder.
4. Start the new launcher using the same Windows account.
5. Check health/version, existing inventory/history and evidence export. Record any startup error before changing data.
6. Retain the backup and old application folder until the new version is checked.

Current-user DPAPI keys cannot be transferred to another user/machine merely by copying access.key. Back up the data securely. Do not include databases, credentials, logs or exports in public release uploads. A backup is not a guarantee of cross-version database migration; test upgrades on a disposable copy first.

## Source and original desktop

The source ZIP includes app.py for the original checklist/history/HTML workflow. Install requirements-dev.txt in a Python 3.12 virtual environment. Run launcher.py for Central or app.py for the original desktop. The portable Central package is not the original one-file SecureAudit.exe.

## Build

On Windows x64 with full Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\build-central.ps1
```

The GitHub Windows release candidate workflow also builds, tests and packages the application. Its artifact contains the Windows ZIP, checksum, source ZIP, notes and verification records. Download and extract the artifact wrapper before uploading individual assets to a release.

## Publish after review

Choose tag v0.6.0-beta at the exact reviewed release-preparation commit (not an older main head). Mark the GitHub release as a prerelease. Use RELEASE_NOTES.md as its description and attach the Windows ZIP plus its checksum, the source ZIP and BUILD-VERIFICATION.txt. Do not upload the outer Actions artifact wrapper as though it were the Windows application ZIP.

The workflow prepares files only. It does not create a tag, publish a release or merge the preparation PR.

## Validation limits

Packaged startup/demo/API tests and automated software tests do not establish Windows collector accuracy, formal compliance, full UI usability or deployment compatibility on all machines. Independent review of hosted observations and additional Home/Pro testing remain separate tasks.
