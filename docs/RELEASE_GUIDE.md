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

## Required owner catalog signing before a Windows build

The current repository does not contain catalog signature material. Packaged
startup requires it and the portable builder now checks it before building.
The source ZIP can be used for development, but no runnable Windows ZIP is
claimed until the owner signs and the packaged self-test passes.

On your Windows machine, check out release/v0.6.0-beta and install requirements-dev.txt.
If you do not already have an owner catalog key, generate one outside the repository.
Keep it private and backed up; never upload or commit it.

```powershell
$catalogKey = Join-Path $env:USERPROFILE 'SecureAudit-Keys/catalog.key'
.\.venv\Scripts\python.exe tools/sign_catalog.py generate --private-key $catalogKey
.\.venv\Scripts\python.exe tools/sign_catalog.py sign --private-key $catalogKey
git add checks/catalog.pub.pem checks/catalog.sig.json core/catalog_trust.py
git commit -m "security: sign release catalog with owner key"
git push origin release/v0.6.0-beta
```

If you already have the corresponding keypair, use your existing private-key
path and sign; do not overwrite or rotate the key casually. Commit the public
key, signature manifest and trust anchor together. A new build runs after the
push. It must pass both the source tests and extracted-launcher self-test
before its Windows ZIP is published. The public-key anchor protects the
catalog under its stated trust model; it does not sign the entire application.
