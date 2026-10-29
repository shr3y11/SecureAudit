# SecureAudit evidence completeness study

This is a finite-state computational study of reporting semantics. Generated
vectors are not Windows machines, observed incidents, or field error rates.

## Reproduce

From the repository root using Python 3.12:

```powershell
python -m pip install pytest==8.4.2
python -m pytest -q
python research/run_study.py
```

No additional dependency is needed for the enumeration. `results/` contains
six CSV files, summary JSON, and SHA-256 checksums. Environment metadata can
change between operating systems; compare substantive counts as well as hashes.

Expected model sizes: 243 full-selection vectors, 1,023 vectors allowing errors
and omissions, 992 truth/selection pairs, and 5,110 evidence-resolution edges.
The completion oracle must report zero classification/containment discrepancies
and zero stable-decision reversals. The oracle is algorithmically separate from
the bounds, but shares the binary model assumptions.

The independently executable study adapter is in `run_study.py`. The application
implementation is `core/evidence.py`. The production-module test explicitly
checks all 1,023 vectors against every binary completion at 60%, 80%, and 100%.

## Interpret

For a fixed baseline of N checks, record P passes, F failures, E errors, and O
omitted required checks. Baseline coverage is `(P+F)/N`. The possible complete
pass fraction lies in `[P/N, (P+E+O)/N]`. ABOVE means its lower bound meets the
chosen threshold, BELOW means its upper bound falls below it, and UNRESOLVED
means the missing readings could change the aggregate conclusion.

The default 80% is illustrative, not a regulatory requirement. All original
Error states stay visible. Mandatory controls need separate review. Correct
P/F observations are an assumption. Bounds are logical, not confidence intervals.

## Application scope

This feature branch follows the project's documented `develop` workflow and
extends the M4 local scan, SQLite history, and HTML report. It does not change
the M5 central dashboard or its six-check synthetic demo catalog on `main`.
It does not produce OSCAL/XCCDF output or benchmark other scanners.

Every new local scan snapshots enabled catalog IDs, catalog version/digest,
selection, rational threshold, and decision version. The additive SQLite
context table preserves old records, whose original baselines remain unknown.
HTML recomputes the summary from stored context and results. The digest
identifies a catalog snapshot and does not authenticate the endpoint.

See [Windows validation protocol](../docs/RESEARCH_VALIDATION.md). No real
Windows ground-truth captures accompany this feature yet. Four existing
PowerShell integration tests require a Windows runner.

## Reproducibility of the committed artifacts

Re-running `run_study.py` must reproduce `results/*.csv`,
`results/summary.json` and `results/sha256.json` byte-for-byte on any
machine — that diff is the reviewer's check on the numbers.
Environment provenance (interpreter version, platform) is therefore
written to `results/environment.json`, which is deliberately **not**
part of the hashed set: it describes a run, not a result.
`tests/test_research_reproducibility.py` enforces both properties.

## Tamper Lab

`tamper_lab.py` measures what Central's evidence integrity actually
detects under an explicit attacker model (write access to the
database file or an exported bundle). Seven experiments — modify,
modify+reforge, delete, three replay shapes, and bundle forgery —
compare Central's internal hash verification against an external
checkpoint. Results are committed in `results/tamper_lab_results.json`
and pinned by `tests/test_tamper_lab.py`. The honest headline:
internal verification catches naive edits; reforging and deletion are
invisible to it and are caught only by a reference outside the
attacker's reach.
