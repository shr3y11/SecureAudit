# SecureAudit — Platform Roadmap and Designs (items #12, #14, #15, #21, #23–#25, #27–#29)

This document records, for each large add-list item, the current state,
a concrete design, a size estimate, its dependencies, and — where the
item is research, not just engineering — the evaluation that would make
it a result rather than a feature. Estimates are relative: S ≈ a day,
M ≈ a week, L ≈ a month of focused work, XL ≈ a project phase.

A standing rule applies to all of it: **a shipped feature is not a
research result.** Each research item below names the evidence it needs.

---

## #21 Remote agents — L/XL

**State:** Central accepts imported evidence and runs the scanner only
on its own host. `POST /api/demo/jobs` refuses real endpoints with 409
("real agent execution is not connected").

**Design:** A small agent service for Windows endpoints that is
*not* a general remote shell:
- Outbound-only, long-poll or WebSocket connection from agent to
  Central (no inbound ports on endpoints).
- The agent receives job messages naming **catalog check IDs only** —
  the same allow-list boundary as the local scanner. It runs the
  existing `core.scanner.run_check` and posts evidence back through the
  existing submission endpoint (which already hashes and deduplicates).
- Enrollment: one-time enrollment token per endpoint, exchanged for a
  per-endpoint credential; Central stores a hash, the agent stores its
  secret with DPAPI. Revocation = deleting the endpoint credential.
- Jobs, results, and failure states reuse the existing Job/Assessment
  tables; the 409 becomes a real path only for endpoints whose agent
  has enrolled and is online.

**Risks:** This turns a local tool into a distributed system: agent
updates, offline endpoints, clock skew on `collected_at`, and a much
larger attack surface. It also changes the trust story — evidence is
only as trustworthy as the endpoint agent.

**First step:** Agent skeleton that enrolls, heartbeats, and executes
one catalog check end-to-end against a test Central.

## #23 Plugin system for checks — M

**State:** Checks are the five catalog entries plus their scripts;
adding one means editing core-shipped files.

**Design:** A plugin is a directory with a `plugin.json` manifest
(id, name, version, platform, entry script, declared permissions) and
one collector script. Plugins live outside the shipped catalog:
- The scanner loads the signed core catalog first, then plugin
  manifests from a plugins directory. Plugin checks appear in the UI
  visually marked as **plugins**, never mixed silently with core checks.
- Plugin results are recorded with their plugin ID and version, and
  **excluded from the fixed baseline** unless a versioned catalog
  update adopts them — otherwise a plugin could shrink or move the
  baseline the research reporting depends on.
- Plugins get the same contract validation and error model. Plugin
  signing reuses the item #7 machinery with a separate, clearly
  labelled trust level: core signature = project owner; plugin
  signature = plugin author, whom the user chooses to trust.

**First step:** Manifest schema + loader that lists (but does not yet
run) a sample plugin, with UI distinction designed in from the start.

## #24 Update infrastructure for catalog/checks — M (depends on #7)

**State:** New checks require a new application release.

**Design:**
- The catalog + collectors ship as a versioned **bundle** (the same
  ZIP shape as the evidence bundle: manifest + SHA-256 per file +
  Ed25519 signature from item #7).
- Central/app checks a configurable update source, downloads a bundle,
  verifies signature and hashes, and only then stages it. Activation
  is atomic (directory swap) and keeps the previous version.
- **Rollback:** the previous bundle is retained; a failed verification
  or a failed self-check after activation restores it automatically
  and records an event.
- Every scan already snapshots the catalog version + SHA (item #11),
  so historical results stay interpretable after updates.

**First step:** Bundle format + a local "install from file" path with
verification and rollback, before any network update source exists.

## #25 Catalog expansion — M per batch (Windows validation is the cost)

**State:** Five Windows checks; platforms list Windows 10/11 and
Server 2019/2022.

**Design:** Expand in validated batches, not by volume:
- Batch A (same-platform, low risk): password/audit policy
  (`WIN-PWD-001`), account lockout (`WIN-LOCK-001`), UAC enabled
  (`WIN-UAC-001`), Windows Update service state (`WIN-WU-001`),
  Remote Desktop exposure (`WIN-RDP-001`).
- Each new collector follows the existing pattern (single-purpose
  `.ps1`, contract JSON, Error-not-Fail) and ships with a VM test case:
  one configuration that must Pass and one that must Fail, recorded
  like the item #13 captures.
- Server 2025 support = re-running the whole catalog's VM matrix on
  Server 2025 and updating `supported_platforms` only where a check
  was actually observed. Listing a platform without an observation
  would repeat the mistake this project keeps correcting.
- Mapping status stays "Pending validation" until each mapping is
  individually validated (fix-list item #5's rule).

**First step:** `WIN-UAC-001` + `WIN-LOCK-001` with VM pass/fail cases.

## #27 Multi-user RBAC — L

**State:** One shared bearer token; local-first single user. The token
model is documented as such; this item changes the product's nature
and should be a deliberate decision, not an incremental patch.

**Design:**
- Users table with hashed credentials (argon2id), sessions as
  server-side tokens with expiry; roles: `admin` (manage users,
  endpoints, signing keys), `assessor` (run scans, submit evidence,
  export), `viewer` (read-only).
- Authorization middleware per route group; the current single token
  becomes a bootstrap/admin recovery credential, then is retired.
- Every Event row gains an actor field — the audit trail is a feature
  of RBAC, not a side effect.
- The desktop app stays single-user; RBAC applies to Central only.

**First step:** Threat/scope note deciding whether Central is still
"local-first" once multiple users exist, because that answer changes
the rate-limiting and transport-security requirements too (item #9).

## #28 Policy ingestion (CIS/STIG) — L

**State:** Mappings are hand-written per check; four of five are
honestly "Pending validation".

**Design:**
- Importers for machine-readable sources where licences permit
  (e.g. STIG XCCDF from public sources; CIS Benchmark content is
  licence-restricted — ingestion must handle "user supplies the file
  they are entitled to", never bundle CIS content).
- An imported rule becomes a **mapping candidate**, never an automatic
  check: a human confirms (a) the rule's intent matches what a
  collector actually observes, and (b) the mapping type
  (Full/Partial). The catalog records the source document + version +
  rule ID for every confirmed mapping.
- Output is a mapping report: rules with candidate checks, rules with
  no possible automated check (the majority, honestly reported), and
  checks with no rule.

**First step:** XCCDF importer that produces the candidate report for
one STIG, with no catalog changes.

## #29 Safe auto-remediation — XL, research-grade

**State:** Not present. Collectors are read-only by design.

**Position:** This is the riskiest item on the list and the one where
"it worked on my machine" evidence is worthless. It proceeds in
stages, each gated on evidence from the previous one:

1. **Dry-run plans only.** For a failed check, generate the exact
   remediation action (from catalog remediation text, made machine-
   readable) and show it. Nothing executes.
2. **Reversible actions on VM snapshots.** Execute → re-scan →
   record: did the check flip to Pass, did anything else change
   (two-scan diff, item #20, over a defined observation set), does
   rollback restore the exact prior state?
3. **Evaluation before any real use:** across controlled
   configurations, measure fix-success rate, unintended-change rate,
   rollback-success rate. A sandbox pass does not guarantee identical
   behaviour on the target; the report must say so.
4. Only then: opt-in, per-check (never bulk), admin-confirmed
   remediation in the product, with the before/after evidence stored
   like any other assessment.

**First step:** Stage 1 — machine-readable remediation actions for the
five existing checks, as data, plus the diff-based verification plan.

---

## Research items already designed elsewhere

- **#12 Tamper-evident evidence chain + protected checkpoint:**
  attacker model (modify / delete / replay / full-chain rewrite) and
  the checkpoint design live with the evidence work in PR #8's
  `docs/RESEARCH_VALIDATION.md` lineage; the decisive point is that a
  chain alone proves nothing when the whole chain and its reference
  can be rewritten — a protected checkpoint or a separate trusted
  verifier is part of the design, and the evaluation is the four
  attack experiments, not the chain code.
- **#14 Drift detection:** builds directly on items #19/#20
  (selective re-scan, two-scan diff) plus recurring *real* scans.
  The research question is the detection quality — drift rate and
  false-alarm rate against existing scheduling/detection baselines
  under realistic workloads — not the scheduler itself, whose demo
  version (delayed jobs) already exists.
- **#15 AI governance module (narrow):** before any code — one
  specific assessment question, a source of credible reference labels,
  and a measurable evaluation. A generic questionnaire is explicitly
  not this item, and neither is an AI assistant that explains
  SecureAudit findings (that is AI-assisted auditing, a different
  project with different evidence requirements).
