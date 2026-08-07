# Database and Evidence

## Purpose

SecureAudit stores local point-in-time technical assessment evidence in SQLite.

The durable evidence record is the database. HTML reports are derived presentation artifacts.

## Main Tables

```text
scans
scan_results
```

## Scan Summary

The `scans` table stores fields such as:

```text
scan_id
hostname
started_at_utc
completed_at_utc
selected_count
passed_count
failed_count
error_count
assessed_count
unassessed_count
compliance_score
coverage_percentage
```

## Detailed Results

The `scan_results` table stores fields such as:

```text
scan_id
check_id
check_name
expected_value
observed_value
status
evidence_json
error_message
timestamp_utc
```

## Relationship

```text
scans
  │
  │ 1-to-many
  ▼
scan_results
```

## Transaction Integrity

A scan summary and all associated results are stored in one transaction.

```text
Everything succeeds → commit
Any insert fails     → rollback
```

This reduces the chance of a summary existing without complete detail evidence.

## Validation

The database rejects inconsistent or unsafe data including:

- contradictory counts
- negative counts
- unsupported statuses
- duplicate check IDs
- duplicate scan IDs
- non-serializable evidence
- impossible completion/start chronology
- timestamps without timezone information

## Timestamp Integrity

Evidence timestamps must be timezone-aware.

A completion timestamp earlier than the start timestamp is rejected.

## Runtime Storage

Source mode:

```text
data\secureaudit.db
```

Packaged mode:

```text
%LOCALAPPDATA%\SecureAudit\data\secureaudit.db
```

This allows packaged history to persist between one-file PyInstaller launches.

## Report Relationship

The GUI can:

```text
save scan
  ↓
read stored scan
  ↓
generate report
```

Historical reports can also be regenerated from SQLite when needed.

## Evidence Interpretation

SecureAudit stores point-in-time technical configuration evidence.

It does not provide:

- immutable forensic storage
- cryptographic evidence signing
- centralized audit-log retention
- chain-of-custody guarantees

Those capabilities belong to future versions.
