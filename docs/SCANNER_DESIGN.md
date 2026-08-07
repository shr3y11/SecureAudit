# Scanner Design

## Objective

The scanner converts an approved check ID into a controlled PowerShell execution and a normalized technical-assessment result.

## Approved Execution Flow

```text
WIN-FW-001
    ↓
catalog lookup
    ↓
firewall.ps1
    ↓
trusted path validation
    ↓
PowerShell
    ↓
JSON
    ↓
normalized result
```

## Security Requirements

The scanner must reject:

- unknown check IDs
- disabled catalog entries
- absolute script paths
- directory traversal
- nested script paths
- non-`.ps1` scripts
- missing approved scripts
- malformed JSON
- timed-out execution
- returned check IDs that do not match the requested check

The application never accepts arbitrary PowerShell command text from the user.

## Catalog

`checks/catalog.json` is the authorization bridge between the GUI and scanner modules.

Initial approved checks:

| ID | Script |
|---|---|
| `WIN-FW-001` | `firewall.ps1` |
| `WIN-DEF-001` | `defender.ps1` |
| `WIN-BL-001` | `bitlocker.ps1` |
| `WIN-GUEST-001` | `guest_account.ps1` |
| `WIN-SMB1-001` | `smbv1.ps1` |

## PowerShell Result Contract

Each script returns one JSON object containing fields such as:

```text
check_id
check_name
expected_value
observed_value
status
evidence
error_message
timestamp_utc
```

JSON was chosen because it creates a predictable machine-readable interface between PowerShell and Python.

## Result Semantics

### Pass

The script successfully assessed the configuration and the expected condition was met.

### Fail

The script successfully assessed the configuration and the expected condition was not met.

### Error

The script could not obtain a reliable assessment.

Examples:

```text
Access denied
Unsupported feature
Invalid JSON
Timeout
Command unavailable
```

An `Error` is not a control failure.

## Process Execution

PowerShell is invoked as a subprocess rather than through arbitrary shell interpolation.

The scanner applies an execution timeout so a hanging script cannot block the application indefinitely.

## Check-ID Validation

A PowerShell module must not be able to return evidence under another check identity.

Conceptually:

```text
requested: WIN-FW-001
returned:  WIN-BL-001
```

becomes a controlled `Error`.

## Path Security

The scanner validates script resolution against the trusted PowerShell directory.

This protects against values such as:

```text
..\evil.ps1
C:\Temp\evil.ps1
subfolder\evil.ps1
```

## Current Scanner Scope

SecureAudit V1 contains five Windows technical checks.

The project intentionally validates a small end-to-end workflow rather than attempting complete CIS Benchmark coverage.
