# Security Model

## Primary Security Objective

SecureAudit runs Windows technical checks with administrator privileges while preventing the application from becoming a general privileged command-execution interface.

## Core Rule

SecureAudit must never execute arbitrary PowerShell supplied by the user.

## Authorization Model

```text
User selection
    ↓
approved check ID
    ↓
trusted catalog
    ↓
validated bundled .ps1
    ↓
PowerShell
```

Privilege and authorization are separate:

```text
Administrator privilege
≠
permission to execute arbitrary code
```

## Scanner Controls

The scanner enforces:

- approved check IDs only
- enabled catalog entries only
- `.ps1` scripts only
- trusted directory containment
- absolute-path rejection
- traversal rejection
- nested-path rejection
- execution timeout
- structured JSON parsing
- returned check-ID validation

## Administrator Elevation

SecureAudit requests elevation through normal Windows UAC.

It does not:

- bypass UAC
- disable UAC
- permanently grant administrator rights
- modify group membership
- install a privileged service in V1

Source mode:

```text
python.exe
   ↓ UAC
pythonw.exe app.py
```

Frozen mode:

```text
SecureAudit.exe
   ↓ UAC
SecureAudit.exe
```

`pythonw.exe` avoids an unnecessary console window during source development.

## UAC Cancellation

Cancellation is treated as a normal user decision and does not produce an uncontrolled crash.

## Resource Separation

Packaged scanner resources are loaded from the PyInstaller resource directory.

Persistent writable evidence is stored separately under:

```text
%LOCALAPPDATA%\SecureAudit
```

This keeps scanner code separate from mutable evidence.

## HTML Safety

Report values are HTML-escaped before rendering.

This prevents evidence strings from being interpreted as executable markup.

Custom report filenames are constrained so path traversal cannot escape the reports directory.

## Data Integrity

SQLite validation protects:

- summary/result consistency
- timestamp chronology
- valid status values
- unique result identities
- serializable evidence

## Known Limitations

SecureAudit V1 does not provide:

- signed executable verification
- tamper-proof evidence
- endpoint attestation
- secure central transport
- RBAC
- cryptographic script signing
- enterprise agent isolation
- code-signing certificate

These are future security improvements.
