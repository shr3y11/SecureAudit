---
title: SecureAudit Milestone 6 Development Log
project: SecureAudit
milestone: 6
tags: [secureaudit, research, evidence, reporting]
---

# Milestone 6: Evidence completeness research extension

## Hosted pilot follow-up (30 October 2026)

Completed capture: run 40999603644 passed both Windows pilot and both software
test jobs. The pilot produced 18 scans and 66 actual readings. Full elevated
vectors were 4P/1F/0E; full standard vectors were 3P/0F/2E on both images in
all three repetitions. File hashes and recorded before/after native fields
were checked. Independent reviewer sheets remain pending. See
research/HOSTED_PILOT_RESULTS.md for provenance and limits. These observations
supersede earlier statements below that no hosted outputs were yet available.

The initial code is published in draft PR https://github.com/shr3y11/SecureAudit/pull/8.
This follow-up adds real hosted Windows collection, privilege/version metadata,
and a strict observation summarizer. `tools/run_hosted_study.ps1` requires a
disposable GitHub-hosted runner, temporarily creates an unelevated account,
captures both privilege conditions, then removes that account. It never changes
the five assessed configuration settings. Artifact retention is 30 days.

The study is a small Server-image case study, not Home/Pro validation. A native
reference is not independent ground truth. The reviewer sheets remain pending.
The four summarizer tests reject empty inputs and incorrect/missing privilege
metadata and preserve observed counts without inventing accuracy.

Earlier publication-blocked statements below describe the historical local
handoff and are superseded by this PR link. Hosted observations must be tied
to an actual workflow run; this log alone does not establish a successful run.

Scope: fixed-baseline reporting in the M4 local workflow, reproducible model
analysis, and a Windows validation protocol. The M5 central dashboard remains
on `main`; this feature follows the documented `develop` branching workflow.

- Branch: `codex/evidence-completeness`.
- Start commit: `9669169853a5384c32bb1189a28c857cdc5a5edb`.
- Final commit: the commit containing this log (resolve with `git rev-parse HEAD`).
- Observed Linux result: 108 passed, 4 skipped, Python 3.12, pytest 8.4.2.
- Skipped tests: four existing tests execute real Windows PowerShell scripts.
- Added research/workflow tests: 23, including 12 invalid-input cases.

| Area | Result |
| --- | --- |
| Model evaluation | 243 / 1,023 vectors, 992 truth-selection pairs |
| Production classifier | All 1,023 vectors checked against explicit completions |
| Persistence | Optional baseline context stored with scan transaction |
| HTML | Derived values recomputed, display values escaped |
| Windows VM validation | Prepared, not executed |
| Remote publication | Blocked pending explicit destination authorization |

## Architecture and files

`core/evidence.py` computes exact rational bounds before rounding. It validates
baseline/selection IDs and result states. `app.py` captures the catalog context
before execution and passes it to persistence. `core/database.py` adds an
optional context table in the same scan transaction and recomputes derived
values on retrieval. `core/reporting.py` shows coverage, omissions, bounds,
threshold, decision, versions, and digest. Old scans receive no invented baseline.

`research/run_study.py` and `research/results/` reproduce the offline study.
`tools/validate_windows.py` and `collect_reference.ps1` capture real readings
for later independent review. `docs/RESEARCH_VALIDATION.md` specifies the lab.
`tests/test_evidence.py` checks the production module and report workflow.
The new GitHub Actions workflow runs Linux/Windows tests and enumeration.

## Decisions and important code

Bounds are `Fraction(P,N)` and `Fraction(P+E+O,N)`. ABOVE requires lower >= t;
BELOW requires upper < t; otherwise UNRESOLVED. Missing selected records become
E in the computation and are listed separately. Persistence refuses a context
with missing selected result records. Omitted required IDs remain in N.

Catalog membership is snapshotted with a canonical JSON digest, baseline
version, rational threshold, and decision version. Hashing is an identity aid,
not an authenticity mechanism. Enabled membership is the baseline in this MVP;
approved applicability tailoring needs its own versioned catalog.

No formal compliance, risk, detection-accuracy, or workload benefit is claimed.
The 80% default is an illustrative aggregate threshold. Mandatory control
obligations remain separate. Research output is a reporting decision artifact.

## Verification and fixes

Commands run locally:

```text
python -m pytest -q
python research/run_study.py
python tools/validate_windows.py --help
git diff --check
```

The production routine matched explicit binary completions for all 1,023
P/F/E/O vectors except the empty selection, at 60%, 80%, and 100%. Other tests
cover exact threshold boundaries, missing records, selection omissions,
additive schema upgrade, old-scan behavior, SQLite round-trip, escaping of
untrusted display text, and mocked capture file/report generation. The runner
also refuses a non-Windows host before creating a case folder.

Initial cross-platform verification exposed existing Windows-only assumptions:
ctypes mocks patched a missing Linux attribute, path tests interpreted Windows
paths through the host Path, and four tests required real PowerShell. Mocks now
patch the windll boundary explicitly; script validation recognizes Windows path
syntax on both hosts; CREATE_NO_WINDOW has a non-Windows fallback. The four real
execution tests explicitly skip when powershell.exe is unavailable. They remain
required on the Windows CI runner. These changes do not certify Windows runtime
behavior until that runner executes.

The offline enumeration reproduced 243/1,023 vectors, 992 truth/selection pairs,
5,110 resolution edges, and zero oracle or stability discrepancies. Its generated
records were not placed in a Windows lab-results directory.

## Manual checks and remaining work

Expected real Windows outputs and cases are in RESEARCH_VALIDATION.md. Observed
real VM outputs: none in this environment. A mocked capture test verifies bundle
creation only. Windows VM captures, independent reference review, GUI/packaged EXE
review, assessor comprehension study, and conference review remain outstanding.
The central dashboard does not display these new fields yet.

Git disposition: feature changes prepared for a draft PR into `develop`.
Verify remote publication and CI from the linked PR; do not infer a completed
merge or Windows result from this log. Next milestone: execute the documented
VM cases and add reviewed empirical results without changing the scope of the
computational claims.

## Git handoff and definition of done

Observed local commands included `git switch -c codex/evidence-completeness
origin/develop`, explicit `git add` of changed feature files, and `git commit`.
A `git push -u origin codex/evidence-completeness` attempt was rejected by
automatic approval review because external disclosure to this destination had
not been explicitly authorized in the trusted conversation. No successful push
or PR creation is claimed. The patch was checked against a clean baseline
worktree with `git apply --check`.

- [x] Local extension implemented and tested.
- [x] Computational study regenerated.
- [x] Old-scan compatibility and stored-baseline behavior tested.
- [x] Windows capture and review protocol prepared.
- [ ] Windows execution tests and controlled VM captures completed.
- [ ] Packaged executable and central dashboard integration evaluated.
- [ ] Remote branch/PR published after explicit authorization.
- [ ] Faculty and all coauthors approve the manuscript.

The final local commit is the commit containing this updated log. Use
`git rev-parse HEAD` after applying the supplied patch. Remote state remains
unchanged by this feature handoff. A digest is not an evidence signature, and
the collector execution boundary remains approved catalog scripts only.
