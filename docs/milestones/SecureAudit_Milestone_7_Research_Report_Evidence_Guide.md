---
title: SecureAudit Milestone 7 Research Report Evidence Guide
project: SecureAudit
milestone: 7
date: 2026-10-30
tags: [secureaudit, research, evidence, reproducibility]
---

# Milestone 7: What the paper can support

The contribution is an implemented audit-reporting design with reproducible
validation and explicit integrity boundaries. The interval formula is elementary
worst-case reasoning. Do not claim it is a new mathematical method. The related
work on partial identification, three-valued logic and imprecise probability
must be completed before a novelty claim or venue submission.

| Claim | Source | Interpretation limit |
| --- | --- | --- |
| 1,023 states / 7,744 completions / 0 model mismatches | research/results/summary.json and study tests | Shared binary assumptions, not external accuracy |
| 80 percentage point worst-case overstatement | selection truth table / summary | Constructed comparator, not observed product behavior |
| Inconsistent evidence/counters detected | tests/test_tamper_lab.py and Central verify endpoint | Coherent rewrite and deletion remain undetectable internally |
| Saved external reference reveals changed bytes/set | tamper_lab_results.json and negative controls | Legitimate additions also change it; not a deployed attestation service |
| Signed release rejects removal and substituted key | tests/test_catalog_sig.py | Owner key and packaged release validation pending |
| New capture archive preserves SQLite/bytes | tests/test_capture_archive.py and mocked runner test | New real Windows capture with archive still needed |
| 19 readings in seven executions on one Server 2025 host | Pinned data branch and Windows README | Shared native APIs; human review blank; no Error/standard-user result |
| Legacy manifests fail retained-byte verification | retained_inventory.json | Missing databases unrecovered; derivative hashes do not repair originals |

## Faculty explanation

SecureAudit keeps the project and studies how to report what its evidence can
support. If only one of five required checks passes and four are unobserved, the
complete-baseline pass fraction can be anywhere from 20% to 100%. At an 80%
threshold, UNRESOLVED follows: the missing readings can change the conclusion.
That is a transparent reporting choice, not proof of compliance.

Central studies a separate question: whether stored/exported evidence stays
consistent. A checksum can expose an edit when the recorded digest is unchanged.
A database writer can edit evidence, counters and digest coherently; internal
checks then pass. A saved reference outside that writer's reach reveals the
change. It must also be updated through an authorized process for legitimate
new evidence. The experiments demonstrate this boundary rather than inventing
a cryptographic guarantee.

## Submission gates

1. Review the raw Windows references using an independent interface/person and
   create a dated review supplement without rewriting acquisition files.
2. Produce a new complete ZIP-backed Windows capture and verify it, with exact
   OS/build/commit provenance; run genuine standard-user cases if feasible.
3. Complete primary-source related work, every DOI/reference check and a clear
   comparison against existing reporting semantics. Do not cite invented tool
   behavior as a baseline.
4. Agree authorship, faculty approval, venue scope and the venue's AI disclosure
   requirements. No claim that an AI detector can certify authorship is supported.

`docs/PAPER_OUTLINE.md` is the current outline. Historical milestone logs describe
their own snapshots and should not be read as current test counts or gates.
