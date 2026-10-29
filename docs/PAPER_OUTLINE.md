# Research Paper — Outline and Evidence Map

**Working title:** *Honest Scores, Verifiable Evidence: Fixed-Baseline
Interval Scoring and Measured Tamper-Evidence for a Windows Compliance
Assessment Tool*

**Status key:** ✅ evidence exists and is reproducible · 🔨 in progress ·
⏳ waiting on the Windows VM captures · ✍️ writing only (no new evidence
needed). No number enters this paper from anywhere except a committed,
reproducible artifact.

## Abstract (draft — ✍️, numbers ✅)

Compliance tools typically report a single score computed over whatever
checks happened to run, overstating compliance when evidence is
missing, and store results with integrity claims that are never
tested. We present SecureAudit, which (1) scores assessments against a
*fixed baseline*, reporting an interval and a three-valued decision
(ABOVE / BELOW / UNRESOLVED) instead of a point score; (2) records
evidence with hashes that are actually *recomputed* by a verification
endpoint, and evaluates — under an explicit attacker model — which
tamperings that detects and which it cannot; and (3) is evaluated
end-to-end: an exhaustive finite-state study of the scoring rule, a
seven-experiment tamper laboratory, and genuine Windows observations
on a Server 2025 host under a pre-registered capture protocol. In the state-space study, a naive selected-checks score
overstates the complete-baseline pass fraction by up to **80 percentage
points**; the interval decision never does. In the tamper laboratory,
internal hash verification detects naive modification but is defeated
by hash reforging and deletion — both of which an external checkpoint
detects, quantifying exactly where the integrity boundary lies.

## 1. Introduction ✍️
- Problem: point scores hide missing evidence; integrity claims go untested.
- Contributions C1–C3 mapped to §3, §4, §5. Scope honesty: a research
  prototype; no certification claims (CIS/ISO/NIST), mappings partial.

## 2. Background and related work ⏳/✍️
- Compliance automation and scoring; interval/imprecise-probability
  treatments of missing data; tamper-evident logging and its known
  limits (a hash chain whose reference can be rewritten proves
  little). [Survey to complete; cite primary sources only.]

## 3. Fixed-baseline interval scoring ✅
- Model: baseline of N required checks; states P/F/E/O; bounds
  lower = P/N, upper = (P+E+O)/N as exact fractions; decision before
  rounding against a fixed threshold; old scans without a baseline
  context are never assigned one retroactively.
- **Evaluation (finite-state study, `research/run_study.py`):**
  - PFE space: 243 states, 21 count classes, 1,024 binary completions
    checked against an independent oracle — **0 mismatches, 0
    containment violations**.
  - PFEO space (with omissions): 1,023 states, 55 count classes,
    7,744 completions, 3,069 oracle classifications — **0 mismatches**.
  - Resolution: 5,110 refinement edges, 0 nesting violations, 0
    stable-decision reversals.
  - Naive-score comparison: maximum overstatement **80.0 percentage
    points** across the selection-truth pairs.
  - All artifacts reproduce byte-for-byte (PR #23/#24); hashes in
    `research/results/sha256.json`.

## 4. Evidence integrity, measured 🔨→✅ (Tamper Lab)
- Design: canonical-JSON evidence + SHA-256 recorded at submission
  (Central); submission IDs bound to first evidence (409 on altered
  replay, idempotent on identical replay); a verification endpoint
  that recomputes stored hashes; self-verifying export bundles;
  owner-signed catalog (Ed25519, PR #19).
- **Attacker model:** write access to Central's database file or an
  exported bundle; no API token; collection-time honesty out of scope.
- **Experiments (`research/tamper_lab.py`, results in
  `research/results/tamper_lab_results.json`):**

  | Attack | Internal verify | External checkpoint |
  |---|---|---|
  | Modify evidence, hash untouched | **detected** | detected |
  | Modify + reforge hash | not detected | **detected** |
  | Delete latest assessment | not detected | **detected** |
  | Replay, identical submission | idempotent (0 rows added) | — |
  | Replay, same ID altered content | rejected (409) | — |
  | Replay, new ID same content | accepted (1 row) | **detected** (unexpected addition) |
  | Forge bundle + manifest | bundle self-check: consistent | **detected** (manifest hash differs) |

- Reading: recording hashes is not detection; recomputation catches
  naive edits only; every stronger attack is caught exactly by the
  reference the attacker cannot reach. This motivates the protected
  checkpoint as future work (§7), stated as a requirement, not a claim.

## 5. Windows observations ✅ (hosted-runner execution; lab-VM replication ⏳)
- Executed 2026-10-29 on a genuine Windows machine — **Windows
  Server 2025 Datacenter (build 26100)**, a GitHub-hosted runner —
  under the protocol in `docs/RESEARCH_VALIDATION.md`. Raw captures
  are committed on the `data/windows-observations` branch; summary in
  `research/windows_observations/README.md`.
- Baseline (administrator, 3 repeats, identical): FW Pass, Defender
  Pass, BitLocker Fail (volume fully decrypted), Guest Pass, SMB1
  Pass — every reading agrees with the independently captured native
  reference. Decision ABOVE, bounds [80, 80] at full coverage.
- Configured cases behave as specified: firewall profile disabled →
  WIN-FW-001 Fail; Guest enabled → WIN-GUEST-001 Fail; selective
  one-check scan → 20% baseline coverage, UNRESOLVED, bounds
  [20, 100] — the protocol's prediction, observed.
- Finding: disabling Defender real-time monitoring does not change
  WIN-DEF-001, whose objective is the narrower `AntivirusEnabled`
  (true throughout, per the same capture's reference). The strict
  `AntivirusEnabled = false` case was not achievable on this runner
  and is reported not executed, as are the unelevated-user,
  BitLocker-on, and SMB1-on cases — with reasons, never simulated.
- Limits, stated in the paper: a hosted runner is not the lab VM;
  Windows 11 and snapshot-based replication remain future work, and
  the protocol's independent manual review of these captures is
  still pending.

## 6. Threats to validity ✍️ (all already documented in-repo)
- Central's fleet score still uses the legacy point score; bounds are
  a desktop (fixed-baseline) property today, and the paper must not
  imply otherwise.
- CIS mappings: 1 of 5 checks mapped (Partial); the rest are labelled
  "Pending validation" — the tool does not certify compliance.
- DPAPI protection is user-scoped; catalog signing is implemented but
  awaits the owner's key ceremony.
- GUI code coverage is the weakest measured area (app.py 15%;
  overall 64%, CI-reported).
- The tamper attacker model grants database write access; weaker
  attackers are strictly easier to detect, stronger ones (collection
  compromise) are out of scope.

## 7. Future work ✍️
Protected checkpoint / trusted verifier for the evidence chain;
per-endpoint baseline policy for Central; recurring real scans for
drift measurement against baselines; the roadmap in
`docs/PLATFORM_ROADMAP.md` (agents, plugins, RBAC) is platform work,
explicitly not claimed as research.

## Reproducibility statement ✅
One checkout reproduces every number in §3 and §4: the study script,
the tamper laboratory, their committed results, and the test suites
that pin them (`tests/test_research_reproducibility.py`,
`tests/test_tamper_lab.py`) all run in CI on Windows and Linux.
