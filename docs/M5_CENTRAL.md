# SecureAudit Central 0.5.0 — Milestone 5

M5 adds a reusable central evidence service to the Milestone 4 Windows scanner. The original scanner, five approved PowerShell modules, UAC helpers, scoring engine, SQLite history and desktop GUI are retained. The existing 89 tests remain unchanged.

## Run the Windows release

1. Extract `SecureAudit-M5-Windows.zip` completely.
2. Open `SecureAudit-M5` and double-click `SecureAuditCentral.exe`.
3. Keep the launcher window open while using the dashboard. Closing it stops the local API.
4. For BitLocker and SMBv1 collection, right-click the executable and choose **Run as administrator**. Cancellation does not change any configuration.

This release is a portable folder, not an installer. Do not move its executable away from its neighbouring files. Python and runtime dependencies are included. The original, unmodified Python Software Foundation signed windowed interpreter is used as the executable launcher. SecureAudit's Python application files are separate and are not code-signed. This does not change Windows trust, security, firewall or application-control settings.

The optional unsigned PyInstaller one-file executable was successfully built, but Windows Application Control blocked its launch on the development PC. It is not the verified runnable release for this machine.

Default browser address: `http://127.0.0.1:8765`. Default storage: `%LOCALAPPDATA%\SecureAuditCentral` (`central.db`, `access.key`, `central.log`). The launcher opens the dashboard with the local access key in a URL fragment; the frontend removes that fragment and keeps the key in tab-scoped session storage. “Lock workspace” removes it from the tab. The key remains in the application's data folder for the next launch. Treat it as a local administrator credential.

## Three-minute demonstration

1. Click **Create demo fleet**. 100 endpoints labelled **Simulated** appear. Repeat creation is idempotent.
2. Click **Assess demo fleet**. The queue processes synthetic evidence in small batches; no network device is scanned.
3. Open **Overview**. Scores, coverage, failures and the assessment distribution update automatically every two seconds.
4. Open `DEMO-PC-001`. Inspect control outcomes, synthetic evidence, collection timestamps, assessment history and the evidence hash.
5. Use **Schedule demo fleet**, choose 15 seconds, and watch jobs remain queued until due. Pending jobs survive a restart.
6. Use **Scan this PC** for the real Windows workflow. This registers only the executing computer and runs the five trusted modules from `core.scanner`. The server accepts no command or script-path input.
7. Use **Register endpoint** then **Import evidence JSON** to submit a central-schema evidence file. Imported evidence is marked `imported`; it is not independently verified.
8. Export **Evidence JSON** or **CSV**. **Print report** opens the browser print dialog, where Save as PDF is available.

Synthetic checks are demonstration fixtures. They do not assert CIS Benchmark coverage or certification. “Endpoints with failures” is a count, not an enterprise risk engine. `risk` in the API is the failed-check percentage, not a severity-weighted business-risk score.

## Architecture and trust boundaries

```text
Portable Windows launcher → local browser dashboard
                                    ↓ access-key authenticated HTTP
                                FastAPI
                             /           \
                    core.scanner       evidence ingestion
                 (5 trusted modules)    (strict schema)
                             \           /
                          core.scoring
                                ↓
                       SQLAlchemy persistence
                     SQLite or PostgreSQL
                                ↓
                 history, hashes, CSV/JSON export
```

The HTTP service binds only to `127.0.0.1`. Localhost Host allow-listing, bearer authorization, request size limits, strict input schemas, CSP, no-store responses and output escaping protect the local workflow. The initial key must contain at least 32 characters; launcher-generated keys have 256 bits of randomness.

Evidence uses `Pass`, `Fail` and `Error` from V1. Scoring reuses `core.scoring.calculate_score`: Pass / (Pass + Fail); coverage is (Pass + Fail) / selected. All-error results have no compliance score. Local results preserve the complete normalized scanner result inside `scanner_result`, including expected/observed values, structured evidence and original timestamps.

Submission IDs are unique. Repeating identical evidence returns the existing assessment. Reusing an ID for different evidence or a different endpoint returns 409. Latest posture is selected by collection time so older imports cannot overwrite newer assessment posture.

Hashes are SHA-256 over canonical UTF-8 JSON of `submission_id`, normalized `collected_at` and `checks` (sorted object keys; compact separators). They detect content differences; they are not digital signatures or proof against database tampering. The local activity trail is operational history, not a tamper-proof audit log. Source labels distinguish `simulated`, `imported` and `local-scanner`.

Jobs are executed by one in-process worker. Restart requeues interrupted work. This version is intended for one server process and one worker. It does not implement distributed queue ownership, external agents or remote execution.

## PostgreSQL configuration

Provision a dedicated empty database and account, then set the SQLAlchemy Psycopg URL before launching:

```powershell
$env:SECUREAUDIT_DATABASE_URL = 'postgresql+psycopg://secureaudit:YOUR_PASSWORD@127.0.0.1:5432/secureaudit'
.\SecureAuditCentral.exe
```

For source mode, use `python launcher.py --headless --port 8765`. URL-encode special characters in credentials. Never commit the URL or password. PostgreSQL is external to the portable application; no database service is installed by the release. Without this variable, the app runs a complete SQLite workflow.

Initial schema creation is automatic with `central_*` table names, separate from the V1 local scanner database. M5 uses initial schema creation only. Future schema changes need explicit migrations before deploying to existing databases; `create_all` does not upgrade old columns. Do not point a development build at a production database.

For the test run, PostgreSQL 18.6 was downloaded from the vendor's official archive linked by [PostgreSQL's Windows download page](https://www.postgresql.org/download/windows/). A temporary loopback cluster and a new uniquely named database were used; the test database was removed afterward.

## API

Interactive OpenAPI docs are at `/docs`. Select Authorize and enter the access key.

| Route | Purpose |
|---|---|
| `GET /health` | Version, readiness, database dialect, scanner connection |
| `GET /api/summary` | Latest fleet score/coverage and endpoint totals |
| `GET/POST /api/endpoints` | Inventory and registration |
| `POST /api/endpoints/{id}/evidence` | Validated central evidence submission |
| `GET /api/endpoints/{id}/history` | Latest 100 assessments, full evidence |
| `POST /api/local/scan` | Empty JSON object; runs only this PC's approved scanner |
| `POST /api/demo/seed` | 1–500 synthetic inventory records |
| `POST /api/demo/jobs` | Simulated assessments only; delay up to one day |
| `GET /api/jobs` | Latest 2,000 queue records |
| `GET /api/events` | Latest 100 operational events |
| `GET /api/export` | Full evidence JSON with source labels and hashes |
| `GET /api/export.csv` | Inventory/score CSV; spreadsheet formula values neutralized |

Use the dashboard's Schema example button to see the central evidence contract. This is an explicit adapter contract; arbitrary old V1 database exports are not automatically accepted.

## Source, tests and build

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe launcher.py
.\build-central.ps1
```

`tools/build_portable.py` fetches official Python 3.12.10 embedded runtime files and includes the runtime package dependency closure. It reads the development Tcl 8.6 patch version and fetches the matching upstream Tcl/Tk library files; license files are preserved. The verified build uses 8.6.12. Build with Python 3.12 Windows x64; native dependency binaries must match that ABI. Close the application before rebuilding its folder. A normal full Python installation already supplies Tcl/Tk. The alternative PyInstaller spec remains available for environments whose application-control policy permits unsigned builds.

Development baseline: 89 tests passing. Central additions: 36 tests passing (125 total). The disposable PostgreSQL integration test passes separately; it skips unless `SECUREAUDIT_TEST_POSTGRES_URL` is set. Packaged self-test verifies Tcl initialization, all five bundled scanner paths, HTTP assets, queue processing, evidence export, and clean shutdown.

## Remaining milestones

M6: multi-user login/RBAC. M7: authenticated endpoint agents. M8: production scheduler/distributed queues. Later: expanded controls, framework mapping, business risk register, policy parsing, evidence-cited AI governance, real VM accuracy experiments and load research. These are not presented as completed by M5.

Clean-VM portability and formal control ground-truth accuracy testing remain separate validation work. The release is verified on this development machine.
