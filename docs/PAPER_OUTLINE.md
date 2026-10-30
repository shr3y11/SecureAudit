# Research paper — outline and evidence map

**Working title:** *Evidence Completeness and Integrity Boundaries in
SecureAudit: An Evaluated Audit-Reporting Prototype*

**Status:** prototype and reproducible computational evaluations available;
Windows independent review, related-work survey and full manuscript pending.
This outline is not a publication-ready paper. Reuse of worst-case bounds and
three-valued decisions is not claimed as new mathematics.

## Abstract (draft)

SecureAudit implements fixed-baseline interval reporting in its Windows desktop
workflow and evidence-consistency verification in its separate Central service.
For unobserved required checks, desktop reporting gives the minimum and maximum
possible complete-baseline pass fractions under a binary outcome model. An
exhaustive study covers 1,023 nonempty-selection evidence states and 7,744 binary
completions, with zero classification mismatches under the model assumptions.
A defined selected-check point-score rule can overstate the complete-baseline
pass fraction by up to 80 percentage points in this state space; this is a
constructed worst case, not an observed endpoint error rate. Seven controlled
Central experiments examine modification, coherent rewriting, deletion, replay
and bundle rewriting. Internal checks detect inconsistent records but not a
coherent database rewrite or deletion. A protected external reference reveals
changes to the committed set; it does not distinguish malicious changes from
legitimate new evidence. Windows observations comprise 19 check readings from
seven executions on one hosted Server 2025 machine. Independent review remains
pending, and the legacy acquisition manifests do not verify the retained Git
bytes. The contribution is an implemented reporting design and a reproducible
evaluation of its scope and failure boundaries.

## 1. Research questions and contributions

- RQ1: Does the implementation classify all states consistently with the
  possible binary completions of its fixed baseline? Answered within the model.
- RQ2: Which defined storage/export changes are visible to internal checks and
  to a reference outside the writer's control? Answered for the listed cases.
- RQ3: How do incomplete evidence and privilege limitations occur in actual
  Windows collection? Only partially explored: no unelevated run or Error outcome
  was captured. Frequencies and general collector accuracy remain unanswered.

Contribution: implement and evaluate a reporting design with explicit evidence
completeness and integrity boundaries in SecureAudit. A general novelty claim
requires a completed related-work comparison; an interval formula alone is
insufficient.

## 2. Background and related work — incomplete

Review primary sources on partial identification/worst-case missing-data bounds
(including Manski), three-valued logic (including Kleene), imprecise probability,
compliance assessment semantics and tamper-evident logging. Verify every citation
and DOI before submission. No OpenSCAP, Wazuh or CIS-CAT benchmark was executed;
do not attribute the constructed comparator's behavior to those products.

## 3. Desktop fixed-baseline semantics and finite-state validation

For N required checks, P/F/E/O denote passes, failures, errors and omissions.
The exact interval is [P/N, (P+E+O)/N]. ABOVE requires the lower bound to meet the
threshold; BELOW requires the upper bound to fall below it; otherwise the result
is UNRESOLVED. Correct P/F readings are assumed. The interval is a logical bound,
not a confidence interval. The 60%, 80% and 100% thresholds are illustrative,
not prescribed compliance criteria. Mandatory controls need separate decisions.

`research/run_study.py` and `research/results/` provide:

| Evaluation | Reproducible count/result |
| --- | --- |
| Full-selection PFE states | 243 states; 21 count classes; 1,024 completions |
| PFEO states (excluding empty selection) | 1,023 states; 55 count classes |
| PFEO completion/classification checks | 7,744 completions; 3,069 classifications; 0 mismatches |
| Refinement edges | 5,110; 0 nesting violations or stable-decision reversals |
| Defined selected-check score comparison | 992 truth/selection pairs; maximum overstatement 80 percentage points |

The completion routine is algorithmically separate but shares the model's
assumptions. Enumeration validates implementation consistency; it does not
establish prevalence, user benefit or a new theorem. The bounds contain all
modeled complete pass fractions; decision labels themselves are not fractions.
Historical desktop scans without baseline context retain that unknown status.
Central still uses its separately documented point-score/coverage semantics.

## 4. Central integrity evaluation

Internal verification recomputes the evidence digest and checks reporting counts,
submission ID and collection time against the stored payload. Inconsistent
records withhold scores and carry visible integrity warnings. Endpoint/source
attribution is outside this payload checksum's scope.

Two separate capabilities are evaluated: database/bundle writer without an API
token, and authenticated API submitter for replay experiments. Collection-time
honesty and replacement of the trusted verifier/reference are out of scope.

| Experiment | Internal/API outcome | Protected-reference comparison |
| --- | --- | --- |
| Modify evidence, leave digest untouched | Inconsistency detected | Changed |
| Modify evidence, digest and counts coherently | Not detected | Changed |
| Delete latest assessment | Not detected | Changed |
| Identical submission ID and content | Idempotent; 0 rows added | Unchanged |
| Same submission ID, changed content | Rejected (409) | Unchanged |
| New submission ID, same check content | Accepted; 1 row added | Changed |
| Rewrite saved bundle and its manifest | Bundle remains self-consistent | Saved original manifest digest differs |

Negative controls (`tests/test_tamper_lab.py`) require an untouched instance to
remain unchanged across repeated comparisons. A legitimate new submission also
changes the reference; updating the trusted checkpoint resolves that difference.
Fresh export timestamps are excluded from content comparison. Bundle forgery is
compared against the exact saved original, not another timestamped export.

This is a local experimental reference, not a deployed external attestation
service. The seven cases are controlled examples, not detection-rate estimates.
Owner catalog signing is implemented with a pinned release key and downgrade
rejection; an owner key ceremony and signed release validation remain pending.

## 5. Windows observations and preservation limits

Run 40939421976 (2026-10-29): one GitHub-hosted Windows Server 2025 Datacenter
host, build 26100. Baseline repeated three times: firewall/Defender/Guest/SMB1
Pass, BitLocker Fail, interval [80,80] and ABOVE. Additional single executions:
firewall disabled → Fail; Guest enabled → Fail; firewall-only selection →
UNRESOLVED [20,100]; Defender real-time monitoring disabled → Pass because the
collector checks the narrower AntivirusEnabled property, which remained true.

There were seven executions and 19 check readings, not 19 independent hosts.
The native references share Windows APIs with collectors; their agreement is
corroboration, not independent ground truth. Manual review CSVs remain blank.
No standard-user, BitLocker-on, SMB1-on or AntivirusEnabled=false case was run.
No observed Error rate or privilege effect can be inferred from these captures.

Pinned data commit: `b13c644999e933d24d183890a20b84e9c75701a5`, path
`windows-observations/run-40939421976/`. Each of five original case manifests
references a missing SQLite database and text changed by Git CRLF→LF conversion.
The retained bytes remain readable; none of those acquisition manifests verify.
`research/windows_observations/retained_inventory.json` records the derivative
hashes, original hash comparisons and missing members without rewriting history.
Future captures use verified byte-preserving ZIPs containing SQLite before Git
normalization. A new Windows capture is still needed to demonstrate that complete
acquisition path on an actual runner.

## 6. Limits and submission gates

The five-check catalog is small. Missing-evidence frequency, broader collector
accuracy, assessor interpretation, weighted/dependent controls and comparisons
with actual tools have not been evaluated. Existing tests do not establish
production readiness. Historical coverage percentages are not current evidence;
use the current CI report. The project does not certify ISO/CIS/NIST compliance.

Before submission: complete the related-work survey and citation verification;
obtain independent Windows review; collect a byte-preserved replication; align
authorship and AI disclosure with the chosen venue. A student demonstration or
poster is a reasonable target to discuss with faculty. Journal readiness is not
established by this work.

## Reproducibility

Run `python research/run_study.py`, `python research/tamper_lab.py` and the tests.
The study's substantive outputs reproduce byte-for-byte; environment metadata is
separate. Tamper results are deterministic in meaning and pinned by regression
tests. Windows captures are observations, not reproducible generated fixtures.
