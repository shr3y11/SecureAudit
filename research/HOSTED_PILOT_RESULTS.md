# Hosted Windows pilot results

Completed run: https://github.com/shr3y11/SecureAudit/actions/runs/40999603644
Date: 30 October 2026. Head: 40c7359d1f21f425393ed0aabdbf0a87c85b724c.
Tested merge: 83a2c6cdb1bd6aa4c4dcb929a0d1775409f1c32e.
Both software test jobs and both pilot capture jobs passed.

Two Windows Server Datacenter hosted machines were observed: build 20348,
image win22/20261026.347.1, and build 26100, image win25-vs2026/20261021.278.1.
Three conditions were repeated three times per machine: 18 scans and 66
executed check readings total. These repetitions are not independent endpoints.

| Condition | P | F | E | O | Assessed rate | Baseline coverage |
| --- | --- | --- | --- | --- | --- | --- |
| Full elevated | 4 | 1 | 0 | 0 | 80% | 100% |
| Full standard | 3 | 0 | 2 | 0 | 100% | 60% |
| Elevated firewall only | 1 | 0 | 0 | 4 | 100% | 20% |

Every row pattern occurred in all three repetitions on both images. Elevated
BitLocker returned Fail with protection Off; standard-account collection returned
Access denied. Elevated SMBv1 returned Pass with DisabledWithPayloadRemoved;
standard-account collection required elevation. Firewall, Defender, and Guest
passed in both full-scan conditions. Defender's narrow AntivirusEnabled predicate
passed even though real-time protection was false.

Downloaded archive digests and per-case manifests were verified. Native fields
were unchanged before/after each scan. This is shared-API corroboration, not
independent ground truth. Manual-review sheets remain pending. Different accounts
and fixed condition order limit causal claims; Windows Home/Pro, accuracy,
usability, and enterprise prevalence are not established.

Artifact 12952578632 (2022), SHA-256:
6fdedc0c10837a2d42a98ae1846226be382dfb6e3d9634f8f4b1352e6cc19287

Artifact 12952514042 (2025), SHA-256:
9934316bf7c7601b925fa2a7f9393886dc57b64a433f82ba8b952e25083fff09

Artifacts expire under the workflow's 30-day retention. Preserve downloaded
originals for review. Standard-account child records lack GitHub run/SHA
environment fields; their association is through the enclosing artifacts and
snapshot labels, not retrospectively populated per-process provenance.
