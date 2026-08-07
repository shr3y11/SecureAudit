# Windows VM Testing Guide

## Status

Clean VM validation is planned but was deferred during the current MVP completion cycle.

Therefore, the project must not yet claim broad clean-machine portability as a verified result.

## Recommended Environments

### VM 1 — Mostly Compliant

Example:

- Firewall enabled
- Defender enabled
- Guest account disabled
- SMBv1 disabled
- BitLocker enabled where supported

Expected:

- mostly passing controls
- high assessment coverage
- few or no unexpected errors

### VM 2 — Deliberately Misconfigured

Example:

- one firewall profile disabled
- Guest account enabled
- SMBv1 enabled
- BitLocker disabled
- Defender configuration altered where safe

Expected:

- genuine `Fail` results
- lower compliance score
- findings visible in the report

Use disposable VM snapshots rather than weakening the main development machine.

## Clean-Machine Test

Strongest setup:

```text
No SecureAudit source repository
No .venv
No Python installation
Only SecureAudit.exe transferred
```

Procedure:

1. Copy `SecureAudit.exe` to the VM.
2. Record SHA-256.
3. Launch as a standard user.
4. Observe UAC.
5. Approve elevation.
6. Confirm one GUI.
7. Confirm all five approved checks.
8. Run all checks.
9. Verify `%LOCALAPPDATA%\SecureAudit`.
10. Close/reopen the application.
11. Verify history persists.
12. Open the HTML report.
13. Repeat launch and cancel UAC.

## Hash Command

```powershell
Get-FileHash .\SecureAudit.exe -Algorithm SHA256
```

## Ground-Truth Validation

For each check, compare SecureAudit with the corresponding native Windows state.

Recommended table:

| Check | Ground truth | SecureAudit | Match |
|---|---|---|---|
| Firewall | TBD | TBD | TBD |
| Defender | TBD | TBD | TBD |
| BitLocker | TBD | TBD | TBD |
| Guest | TBD | TBD | TBD |
| SMBv1 | TBD | TBD | TBD |

## Performance Measurements

Record:

- startup time
- UAC-to-GUI time
- five-check scan duration
- report-generation time
- executable size
- database size
- report size

Do not invent these values before testing.

## Threats to Validity

Consider:

- Windows edition
- PowerShell version
- virtualization platform
- UAC policy
- domain policy
- feature availability
- antivirus/SmartScreen reputation
- development-machine bias
