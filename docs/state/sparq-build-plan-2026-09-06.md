# SPARQ build plan — September 6, 2026

Joey authorized planning and local execution after the repository evaluation. This starts implementation of the reviewed identity/data fixes and the path to a complete athlete product. It supersedes the earlier audit-only stop and pending local linking-draft hold for this authorized work. Production deployment, data changes, messages, billing settings and infrastructure actions retain their explicit approval boundaries.

## Product finish line

The correct registered athlete enters optional Agent help, including before any numeric results; sees the correct active combine and its actual outstanding requirements; continues submission in existing GMTM; returns to truthful, refreshed progress; and controls a useful profile that supports continued development and sharing. A submitted task, completed requirement set, evaluator review and selection remain separate states. GMTM is the authority for its existing combine flow.

## Milestones and acceptance gates

1. **Identity and bounded data access — first local batch implemented and verified.** Legacy name/ID linking now confirms an existing owner; signed-claim recovery handles new connections. Claim acquisition is transactional and conflict-safe in source. Foreign conversations are rejected before work and writes are owner-scoped. Model-selected SQL has been replaced by a typed current-athlete tool. Combined backend suite: 111 passed; current-source frontend typecheck passed; 47 isolated browser assertions passed. Independent review completed. Live database/identity/model and existing-schema gates remain open; no production DB/schema operations occurred.
2. **One current-combine journey.** Read core GMTM source to establish the requirement/submission contract. Preserve active event/registration independently of result rows. Implement the adapter and one next action, deep-link into GMTM, refresh on return, and distinguish unavailable/empty/partial/complete/reviewed. Prove zero-results, partial, complete awaiting review, multi-event and returning-athlete cases. Do not invent schema or infer completion from metrics.
3. **Useful continuing profile and phone experience.** Carry the evidence forward, maintain film/profile edits safely, give the athlete one persisted next step, and repair visitor sharing/visibility/revocation. Verify full mobile shell and account switches. Reconcile relevant verified-data/program-directory work from PR #2 rather than blindly merging or rebuilding it.
4. **Safe actions and dependable operation.** Fix draft save/approval/version handling, isolate demo records, add one durable send operation per approved version, and verify retries/failures without sending real mail. Add recoverable bounded research work, usage limits, readiness and deterministic schema setup. Preserve athlete workflow state on rematching. Close public-rendering, visibility, fetch and middleware issues before exposing affected surfaces.
5. **Measured cohort and commercial package.** Reuse GMTM organization operations; add the minimum scoped view/export for stalled requirements and outcomes. Establish completion/time/staff-effort baseline, optional Agent adoption and continuing value. Validate a small controlled cohort before broader Charles distribution. Implement the selected commercial offer's payment/entitlement flow before charging. Public rollout is a separate explicit release decision after live verification.

Milestones are ordered by dependency, not promised dates. A milestone is complete only when its gate has evidence. A passing test suite alone is not launch readiness. The current goal is to start with a complete, reviewable first batch and leave exact remaining work visible.

## First execution batch and file ownership

All writers operate within the existing Codex-owned task checkout on codex/athlete-home-first-value at baseline 6c7e649. No other checkout/lane is taken over.

- Root: legacy connect handler in backend/profile_api.py; shared isolated test support; build plan/state/handoff; integration and final verification.
- Backend reviewer/executor: backend/agent_api.py plus scoped data-tool module/tests; conversation ownership and typed current-athlete data access. No claims/profile/frontend edits.
- Claims executor: backend/claims_api.py and its claim tests; transaction-safe ownership acquisition. No other source edits.
- Frontend executor: ConnectClient and claim landing/redeem recovery; WorkspaceAIPanel account isolation/authenticated iteration, with bounded tests. Preserve the five existing local home improvements. No backend edits.

The agents have concrete, non-overlapping assignments under this one implementation owner. This first batch is now handed back to root for the recorded checkpoint. No unassigned agent queue or cross-machine dispatch is created.

## Verification and preservation contract

Capture current source hashes before edits. Run backend tests with dotenv loading and outbound connections disabled; use fake DB/model/email interfaces. Typecheck the current frontend snapshot using existing hydrated dependencies. Browser checks must point to synthetic localhost endpoints and block outside requests. No startup against live backend fallback, production DB connections, real model/email calls, or AWS/RDS/IAM/account changes. Use an isolated local database only if its identity and safety are explicit; mock transaction tests do not prove live MySQL races.

Preserve prior local work, separate draft bytes and other writers. Record changed/new files and verification limits. Obtain independent review of correctness-critical fixes, update current-state, and write a dated handoff. Do not commit/push/deploy unless separately authorized by the active task.
