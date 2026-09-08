# Commit and release plan — September 8, 2026

Joey asked when to commit/deploy and authorized the next product package. Reviewed local work should be committed now and at each coherent verified milestone. A local commit preserves an implementation checkpoint; it is not a production-readiness claim or permission to push/deploy.

## Local history

- `a151b1c`: cumulative identity/combine/help/startup implementation and tests, 63 files. The existing slices share modules/contracts, so this preserves the reviewed combined state rather than inventing historical per-feature commits that never passed together. All 42 backend, 23 latest journey and 93 TypeScript snapshot hashes matched their passing receipts before commit.
- `2ba64c2`: prior product/operating documentation and handoffs, 72 files. Nineteen documents contain internal operational/portfolio context, and some receipt links are machine-local. Review those before sharing a branch or assembling a PR. No credentials or generated/binary artifacts were found by the bounded pattern screen; that is not a universal secret guarantee.
- `c27c708`: separately reviewed combine-onboarding/explicit-research package.
- `5347070`: focused combine frontend/backend boundary with actual Next development and ASGI fixture acceptance.
- Next checkpoint: [candidate release-readiness package](candidate-release-packet-2026-09-08.md), including production frontend build evidence and a separate backend source context. Keep actual verification and limitations in its dated handoff.

Neither checkpoint was pushed. No hooks were active and no signing/hooks-path/fsmonitor/template was configured at the checkpoint. The working checkout and branch remain in place; no other project lane was moved or modified.

## Deployment decision

The first release should be the supported adult-combine candidate. Existing junior GMTM combines continue independently; guardian delegation is not established by self-account tests.

1. The supported candidate route/configuration boundary and local full-app verification are complete. Current checkout inspection confirms `agents/__init__.py` exists; the older missing-input finding is stale. The separate candidate source context excludes agents and does not use the legacy Dockerfile. Verify a clean frontend dependency install and actual backend image build on the chosen release platform. Ordinary `/health` success is not database/schema readiness.
2. Verify the exact candidate: full Next/backend entry and recovery, correct athlete/division, zero/partial/submitted states, failures and phone behavior. Obtain actual authorized current-source identity/schema/source acceptance and a real saved-submission return observation. Synthetic state changes verify mechanics only. Do not reuse exhausted live-test allowances or treat GMTM's production-connected staging as isolated.
3. Prepare the exact source/configuration release and rollback record, review internal documentation before sharing, and obtain Joey's explicit SPARQ deployment instruction. Then verify deployed critical paths and source provenance. Deployment authority must name the SPARQ target; Fable's core PR 73 or database cleanup approval does not authorize a SPARQ rollout.

Timing is milestone-based: commit the reviewed work immediately; release the first candidate once these concrete gates pass. The number of offline tests alone cannot establish a deployment date. Repo README describes Railway deployment on a push to main; current service build/deploy settings still need verification before any publish action. No cloud configuration was queried or changed for this plan.
