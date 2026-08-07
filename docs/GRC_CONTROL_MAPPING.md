# GRC Control Mapping

## Positioning

SecureAudit V1 performs automated technical control assessment for selected Windows baseline checks.

It should not be described as a compliance-certification engine.

## CIS Controls vs CIS Benchmarks

### CIS Controls

Broad organizational safeguards covering areas such as:

- asset management
- account management
- data protection
- vulnerability management
- secure configuration

Many safeguards cannot be fully validated from one local Windows endpoint.

### CIS Benchmarks

Specific technical configuration recommendations for operating systems and software.

SecureAudit's scanner is technically closer to a lightweight Windows security-baseline assessment tool.

## Mapping Principle

A local technical check may support a broader safeguard without fully proving it.

Example:

```text
Technical check:
Windows Firewall profiles enabled

Framework reference:
Relevant CIS Controls safeguard

Mapping:
Partial
```

The local check does not establish that every organizational requirement of the broader safeguard is satisfied.

## Preferred Wording

Use:

> SecureAudit uses selected Windows technical baseline checks with mappings to relevant security safeguards.

Use:

> Framework mappings may be partial.

Use:

> The assessment provides point-in-time technical evidence.

Avoid:

> SecureAudit proves complete CIS IG1 compliance.

Avoid:

> The system is certified compliant.

## Current Technical Checks

| Check ID | Technical objective |
|---|---|
| `WIN-FW-001` | Windows Firewall enabled |
| `WIN-DEF-001` | Microsoft Defender Antivirus active |
| `WIN-BL-001` | BitLocker protection active |
| `WIN-GUEST-001` | Built-in Guest account disabled |
| `WIN-SMB1-001` | SMBv1 disabled |

## Evidence Model

Each result should answer:

- what was checked
- expected state
- observed state
- status
- timestamp
- supporting technical evidence
- error information
- mapped safeguard reference where applicable

## Interpretation of Error

A permission problem or unsupported state should be reported as:

```text
Error
```

rather than:

```text
Fail
```

This prevents lack of evidence from being misrepresented as control non-compliance.

## Scope Disclaimer

Recommended wording:

> This report presents automated technical configuration assessment results for selected checks. It does not constitute certification of complete compliance with CIS Controls, CIS Benchmarks, ISO 27001, NIST CSF, or any other security framework.
