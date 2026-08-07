# SecureAudit Project Walkthrough

## 1. Launch

SecureAudit starts from:

```text
app.py
```

or the packaged:

```text
SecureAudit.exe
```

## 2. Administrator Elevation

Startup checks whether the process is already elevated.

If not:

```text
Windows UAC
```

is requested.

Approval launches an elevated replacement. Cancellation exits cleanly.

## 3. Catalog

The application loads:

```text
checks/catalog.json
```

The GUI displays enabled approved controls from this catalog.

## 4. Selection

The administrator selects check IDs.

The GUI sends only those IDs into the scan workflow.

It does not submit raw PowerShell or arbitrary paths.

## 5. Scanner

For each selected ID:

```text
core/scanner.py
```

finds the approved catalog entry, validates the configured `.ps1`, executes PowerShell, applies a timeout, parses JSON, and normalizes the result.

## 6. Technical Checks

Current checks:

```text
WIN-FW-001
WIN-DEF-001
WIN-BL-001
WIN-GUEST-001
WIN-SMB1-001
```

## 7. Result Normalization

Each result becomes:

```text
Pass
Fail
Error
```

`Error` means the system could not be reliably assessed and is not equivalent to `Fail`.

## 8. Scoring

`core/scoring.py` calculates:

```text
passed
failed
errors
assessed
unassessed
compliance score
assessment coverage
```

## 9. Persistence

`core/database.py` stores:

```text
scan summary
+
individual technical evidence
```

inside SQLite.

## 10. Reporting

`core/reporting.py` generates standalone HTML from validated stored scan data.

The report includes:

- hostname
- timestamps
- selected/assessed counts
- Pass/Fail/Error totals
- compliance score
- coverage
- detailed findings
- evidence
- error messages
- scope disclaimer

## 11. History

The Tkinter GUI can list historical scans from SQLite and load them back into the result view.

A historical HTML report can be opened or regenerated from stored evidence.

## 12. Packaging

PyInstaller packages:

```text
Python application
Tkinter runtime dependencies
catalog
approved PowerShell scripts
```

into:

```text
dist\SecureAudit.exe
```

## 13. Persistent Packaged State

Because PyInstaller one-file extraction is temporary, persistent data uses:

```text
%LOCALAPPDATA%\SecureAudit
```

while bundled scanner resources use the PyInstaller application resource directory.

## 14. Current Testing State

Latest verified development-machine regression result:

```text
89 passed
```

The Windows standalone build has also been generated successfully on the development machine.

Clean Windows VM testing remains deferred and should be treated as future validation rather than completed evidence.

## 15. Future Architecture

The reusable core is intended to support:

```text
FastAPI
centralized database
endpoint agents
authenticated result submission
multi-device management
```

without rewriting the core assessment concepts established in V1.
