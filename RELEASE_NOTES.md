# SecureAudit v0.6.0-beta

Release candidate prepared from main commit 08393dfd1c9509fd0ae5c28586b80849bcf4d640 plus versioned documentation and packaging changes.

## Included since the v0.5.0-beta line

- Current Central evidence service and local Windows scanner.
- Payload/metadata consistency checks and evidence history/trend endpoints.
- Current-user Windows DPAPI protection for the local access key.
- Local desktop fixed-baseline evidence completeness and threshold stability reporting.
- Reproducible research materials and documented hosted Windows observations.
- Versioned Windows ZIP/checksum, source archive and packaged-launcher verification.

## Install

Extract SecureAudit-v0.6.0-beta-Windows-x64.zip completely and launch SecureAudit-v0.6.0-beta/SecureAuditCentral.exe. Keep the folder intact. No separate Python installation is needed.

## Upgrade

Close the previous app, back up applicable local data, and extract to a new folder. Keep the same Windows account for DPAPI-protected keys. Test on a disposable database copy before relying on an existing deployment. See docs/RELEASE_GUIDE.md.

## Known limits

This is a beta, local-first tool. Remote agents, enterprise RBAC, LLM crosswalking and unfinished advanced-platform edits are excluded. Demo fleets are synthetic. The research HTML extension is in the original desktop workflow, not a newly expanded Central dashboard. Hashes are not proof of trustworthy evidence. No full-framework certification or measured enterprise accuracy is claimed.

Build and test evidence is supplied in BUILD-VERIFICATION.txt and packaged-self-test.json. The workflow does not publish the release automatically.

## Current release blocker

Owner catalog signing material is absent. Windows release packaging now fails early until the owner adds the public key, signed catalog manifest and pinned trust anchor. The source package is provided for development/review; do not describe it as a ready standalone Windows binary. See the signing instructions in docs/RELEASE_GUIDE.md. The Tcl/Tk private DLL dependency packaging defect found during candidate testing has been fixed.
