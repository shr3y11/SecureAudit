# SecureAudit Architecture

## Purpose

SecureAudit V1 is intentionally a small, local Windows compliance-assessment application. Its architecture separates presentation, privilege handling, scanner authorization, scoring, persistence, and reporting so that the security-sensitive core can later be reused by a FastAPI service.

## High-Level Architecture

```text
SecureAudit.exe / app.py
        ↓
Administrator elevation
        ↓
Tkinter presentation layer
        ↓
Selected approved check IDs
        ↓
core/scanner.py
        ↓
checks/catalog.json
        ↓
Approved PowerShell modules
        ↓
Structured JSON results
        ↓
core/scoring.py
        ↓
core/database.py
        ↓
core/reporting.py
```

## Presentation Layer

`app.py` owns:

- Tkinter window creation
- checklist rendering
- selected check IDs
- scan progress state
- result presentation
- scan-history interaction
- report-opening actions

It does not implement PowerShell authorization, scoring formulas, SQL validation, or report escaping.

## Core Modules

### `core/admin.py`

Handles:

- Windows administrator detection
- UAC request
- source-mode `pythonw.exe` relaunch
- frozen `SecureAudit.exe` relaunch
- clean cancellation handling

### `core/scanner.py`

Handles:

- catalog loading
- approved check lookup
- approved script-path resolution
- path traversal prevention
- PowerShell execution
- timeouts
- JSON parsing
- returned check-ID validation
- normalized results

### `core/scoring.py`

Handles:

- Pass/Fail/Error counts
- assessed/unassessed counts
- compliance score
- assessment coverage

### `core/database.py`

Handles:

- SQLite initialization
- scan summary storage
- detailed evidence storage
- validation
- transaction integrity
- scan retrieval/history

### `core/reporting.py`

Handles:

- HTML rendering
- escaping
- report validation
- safe filenames
- writing local standalone reports

### `core/paths.py`

Separates:

```text
trusted bundled resources
```

from:

```text
persistent writable runtime data
```

## Source vs Packaged Runtime

### Source mode

```text
Repository root
├── checks\
├── data\
└── reports\
```

### PyInstaller one-file mode

Trusted resources:

```text
sys._MEIPASS
└── checks\
```

Persistent writable data:

```text
%LOCALAPPDATA%\SecureAudit\
├── data\
└── reports\
```

## Trust Boundaries

The most important boundary is:

```text
GUI selection
    ↓
check ID only
    ↓
trusted catalog
    ↓
validated approved script
```

The GUI never supplies executable command text.

Another important boundary is:

```text
Bundled resources ≠ writable evidence
```

PowerShell scanner modules remain application-controlled while SQLite and reports remain persistent and writable.

## Future Reuse

The current design intentionally supports:

```text
Current:
Tkinter → core modules

Future:
FastAPI → same core modules
```

A centralized version can replace the presentation and storage/deployment layers without discarding the assessment logic.
