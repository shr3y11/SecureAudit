---
title: SecureAudit Milestone 7 Development Log
project: SecureAudit
milestone: 7
date: 2026-10-30
tags: [secureaudit, integrity, research, verification]
---

# Milestone 7: Independent review repairs

Base main: `db5368297dd8361d6b004c2be74a84cb06a526dd`.
Branch: `codex/research-integrity-fixes`. One completed issue per commit;
publication is a PR into main, with no automatic merge. Unrelated local work on
`codex/advanced-audit-platform` was left untouched. Resolve this log's final
commit from Git history rather than embedding a self-referential hash.

## Changes and rationale

| Issue | Repair | Evidence |
| --- | --- | --- |
| Fresh timestamps made checkpoint change with no attack | Compare stable content and use the saved original for forgery | Untouched and benign-addition regression controls |
| Inactive UFW matched active | Exact status and exit-code parsing; inaccessible states Error | Active/inactive/permission/unrecognized fixtures |
| Central score counters outside hash verification | Compare counters/metadata to payload; derive metrics and withhold inconsistent scores | Counter, ID and timestamp tampering tests |
| Integrity failure looked unexplained in dashboard | Visible warnings; suppress healthy-looking aggregate/risk indicators | Actual JS renderers executed in Node DOM harness |
| Optional signing allowed removal or replacement | Strict frozen-release policy and public-key pin outside checks | Removal/key-substitution tests; both specs include signatures |
| Capture text normalization and ignored SQLite | Seal and verify binary capture ZIP before Git | Database byte preservation, tamper/membership/path tests |
| Legacy originals incomplete | Index retained bytes and missing databases, leave originals unchanged | Reproducible derivative inventory, normalization fixture |
| Nine portable tests still excluded from Linux CI | Remove obsolete exclusions | Full local run with only two Windows-specific Central exclusions |
| Research claims exceeded evidence | Reframe outline, attacker capabilities, observation denominators and gates | Artifact-to-claim review; related work still incomplete |

## Validation observed on Linux

Python 3.12.14, pytest 8.4.2: **207 passed, 6 skipped, 2 deselected**.
Coverage over core/Central/app/launcher: **66%** (2,037 statements, 701 missed).
Desktop app coverage 23%, launcher 24%: these remain material GUI gaps.
The six skips are four real PowerShell tests, real DPAPI, and PostgreSQL without
a local service. The two deselections execute the Windows local-scan path.
Remote Windows/PostgreSQL CI results must be read from the PR; no local Windows
or Postgres run is claimed by this log. One Starlette/httpx deprecation warning
was observed; it did not fail the tests.

Commands used (normal dependency installation assumed):

```text
python -m pytest -q --cov=core --cov=secureaudit_central --cov=app --cov=launcher --cov-report=term --deselect tests/test_central.py::test_local_scan_accepts_no_arbitrary_command_and_prevents_duplicate_queue --deselect tests/test_central.py::test_failed_scanner_creates_failed_job_not_false_evidence
python research/run_study.py
python research/tamper_lab.py
python tools/inventory_retained_captures.py PINNED_DATA/windows-observations/run-40939421976 --source-commit b13c644999e933d24d183890a20b84e9c75701a5 --output retained_inventory.json
git diff --check
```

The study rerun preserved all substantive CSV/summary/checksum outputs;
environment metadata changed to describe the local interpreter. The tamper lab
was rerun after the controls/counter fixes. Coherent rewrite and deletion remain
internal negative results, with changed external references. Those references
also change on legitimate additions; they are not maliciousness classifiers.

## Security decisions and open gates

No private owner key was generated. Packaging now deliberately fails until the
owner signs and pins the Windows catalog. Unsigned source development remains
possible. Verifier-code replacement and endpoint collection honesty are outside
the signature/checksum boundaries. Legacy missing SQLite files were not recovered.
Manual Windows review stays pending; no verdicts or real readings were fabricated.
A new byte-preserved capture, Windows 11 replication, faculty review and citation
verification remain separate tasks. Queue-cap concurrency, unbounded exports and
historical catalog retention remain documented limitations, not fixed here.
