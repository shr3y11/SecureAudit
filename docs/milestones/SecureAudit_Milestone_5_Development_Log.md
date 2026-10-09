---
title: SecureAudit — Milestone 5 Central Backend
branch: codex/m5-central
version: 0.5.0
date: 2026-10-09
baseline: 669f061
commit_status: Approved by user
---

# Milestone 5 — Central backend and runnable Windows release

The `main` baseline was fetched from `shr3y11/SecureAudit`. All 89 baseline tests pass unchanged. M5 extends the application with FastAPI, SQLAlchemy, PostgreSQL support, endpoint inventory, evidence validation, assessment history, central scoring, exports and a local browser dashboard.

## Verified release behavior

| Check | Observed outcome |
|---|---|
| Baseline regression suite | 89 passed |
| Combined baseline and central suite | 125 passed; optional PostgreSQL test skipped without its URL |
| Disposable PostgreSQL 18.6 integration | Passed: registration, evidence, score/coverage, retry idempotence, demo queue, restart persistence, exports |
| Portable EXE with PostgreSQL | Passed: actual release launcher connected to a new PostgreSQL database, completed 10 synthetic assessments, exported stored evidence |
| Portable EXE smoke test | Passed: Tcl/Tk, five scanner resource paths, HTTP assets, 10 jobs, evidence storage/export, server shutdown |
| Extracted release ZIP | Passed: archive integrity and exact file content verified; extracted EXE passed the same disposable self-test from a different working directory |
| Real non-elevated local scan | Completed: 3 Pass, 0 Fail, 2 Error; score 100%, coverage 60% |
| Real scan error semantics | Privileged checks reported collection errors; no false Fail or fabricated Pass |
| Browser demo | 100 synthetic endpoints, 100 completed jobs, 600 evidence checks, score 74.47%, coverage 94%, 77 endpoints with failures |
| Combined demo and real PC | 101 endpoints; 605 latest checks; score 74.60%, coverage 93.72%; sources visibly distinguished |
| Browser console | No errors in the inspected demo session |
| Launcher signature | Original, unmodified Python Software Foundation signature valid |
| Unsigned PyInstaller executable | Build succeeded; Windows Application Control blocked execution |

The synthetic fleet results are fixtures, not physical-device measurements or a load benchmark. The local scan records operational collection behavior only; it is not a controlled VM ground-truth accuracy experiment. Raw real-machine identifiers and configuration evidence remain in ignored local runtime storage and are excluded from the release package and public project documentation.

The verified release is the `SecureAudit-M5` portable folder. It includes an `.exe` launcher and all necessary files, so no installed Python is required. The launcher binary's vendor signature does not sign SecureAudit's application source. No Windows protection settings were changed.

`dist/SecureAudit-M5-Windows.zip` is 23.7 MiB. It includes a file hash manifest and has a companion ZIP SHA-256 file. The packaging script excludes Python caches, runtime databases, logs and the local access key. Screenshots of the live executable dashboard and synthetic evidence detail are in `docs/demo/`.

## Architecture delivered

- Reuses `core.scanner` and `core.scoring`; original desktop pipeline remains intact.
- Local access-key authentication; loopback Host boundary and 2 MB submission limit.
- Strict typed endpoint and evidence contracts; no arbitrary command or script path accepted.
- PostgreSQL/SQLite persistence in separate `central_*` tables.
- Canonical JSON hashes, idempotent submission IDs, collection-time ordering, provenance labels.
- Persistent local assessment queue for synthetic demonstration and the real local scan.
- Endpoint history, JSON/CSV exports, printable dashboard report.
- Portable deployment compatible with the development machine's application-control policy.

## Scope carried forward

This is M5. Distributed agents, remote orchestration, enterprise RBAC, production scheduling, business-risk scoring, expanded control/framework mappings, policy parsing, AI governance and research experiments remain subsequent milestones. Initial table creation is supported; later schema upgrades require explicit migrations.

The user approved the final M5 commit after receiving the runnable package and live demo on 2026-10-09. A push was not requested.
