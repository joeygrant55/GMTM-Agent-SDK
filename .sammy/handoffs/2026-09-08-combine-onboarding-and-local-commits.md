# Combine onboarding and local commits

September 8, 2026. Joey asked when to commit/deploy and authorized continuing onboarding separation and athlete-journey verification. He reports authorizing Fable to delete `family-test`; `pre-prod` is a separate forthcoming decision. Codex performed no infrastructure operation and does not claim deletion completion.

## Outcome

Combine claim redemption now prepares an owned workspace without starting college matching/research. Identity/metric capture and the ready/created/profile response remain. Exact Clerk ownership is checked on existing and post-insert workspace rows. A duplicate insert is a no-op; concurrent same-owner creation reports `created=false` and raced foreign-owner rows cannot become ready. This depends on the declared unique Clerk constraint and current PyMySQL defaults, which do not enable `FOUND_ROWS`; live schema/concurrency acceptance remains separate.

The claim transaction and executable handler code are unchanged; its comment reflects creation-only bootstrap. Optional bootstrap failure still leaves the established claim intact and same-owner retries recover safely. Explicit college matching requires the returned workspace's exact owner and usable stored sport text. It no longer guesses sport from position or Basketball. Valid explicit gendered sport metadata and worker arguments remain supported. This validates stored text, not sport verification or eligibility.

The college page no longer schedules an automatic AI prompt on opening saved matches. It describes empty/unavailable research truthfully, checks POST acceptance, and bounds subsequent saved-status checks. Account changes/unmount abort requests and clear timers; a 30-second acceptance timeout and three-minute polling deadline report uncertainty. The legacy `complete` boolean can reload saved research but does not establish completion of the new request. Overlapping saved-list reads use generations, so older success/failure cannot overwrite newer state; superseded polling reloads finish neutrally. My next move preserves a supported explicit combine event.

## Verification

- **540 offline backend tests pass**, including 21 new actual-bootstrap/claim/combine tests and 38 explicit-matching cases. The real `main.app` handlers run against synthetic adapters. Adult progress changes from 0/9 to 1/9 after a fixture submission update, excluding junior and other-athlete records. Insert/commit failures retain the owned claim and recover on retry. Recording guards verify zero matching/provider/application-thread work during bootstrap.
- The original helper baseline constructed and started one fake matching thread. The pinned original manual handler fails 31 of the same 38 final tests; the corrected handler passes all. No worker/provider actually runs.
- **42 actual React component checks pass** for the college page, using controlled timers, synthetic Clerk/Next/API interfaces and intercepted browser networking. Account/token scope, HTTP failures, accepted requests, timeout/cleanup, stale results, query context and absence of automatic AI prompts are covered.
- **TypeScript passes across 93 source files.** All 44 tested backend Python hashes and the final frontend test/typecheck hashes match. Backend suite reports only the pre-existing Starlette/AnyIO deprecation warning.
- Independent review found an overlapping saved-list response race; it was fixed and four regression cases added. Final backend/frontend technical review has no blocking finding. Claim executable AST remains identical; only `trigger_matching` changed among existing profile handlers.

Receipts: [`work/sparq-combine-onboarding-2026-09-08`](../../../sparq-combine-onboarding-2026-09-08), including `bootstrap-baseline.json`, `bootstrap-tests.json`, `explicit-matching-{baseline,current}-receipt.json`, `backend-suite.json`/`.txt`, `college-research-component-02.json`, `college-research-typecheck-02.json`, `college-research-verification.json`, and commit/packaging manifests. Older and initial receipts remain unchanged. No real GMTM submission, Clerk login, live DB/transaction, model/email call or deployment was performed. All owned browser/typecheck processes ended; no app server was left running.

## Git and source scope

Same checkout and branch: `work/sparq-agent-review`, `codex/athlete-home-first-value`, origin `joeygrant55/GMTM-Agent-SDK`. Started at `6c7e649`; reviewed prior work is now checkpointed locally:

- `a151b1c`: accumulated identity/combine/help/startup code and tests, 63 explicitly staged files. Shared dependencies required a cumulative checkpoint rather than artificial per-file historical slices.
- `2ba64c2`: prior product/operating documentation and handoffs, 72 explicitly staged files. Internal operational/portfolio context and machine-local receipt references need review before sharing.
- This package is the next local commit after `2ba64c2`; its exact commit receipt is saved outside the repo to avoid a self-referential hash. No commit was pushed, and no deploy was triggered.

Changed existing files: `backend/workspace_bootstrap.py`, `backend/claims_api.py`, `backend/profile_api.py`, `frontend/app/home/colleges/page.tsx`, both test READMEs and `docs/state/current-state.md`. Added: `backend/tests/test_workspace_bootstrap.py`, `backend/tests/test_explicit_matching.py`, `frontend/tests/check-college-research.cjs`, the [completion contract](../../docs/state/combine-onboarding-contract-2026-09-08.md), [commit/release plan](../../docs/state/commit-and-release-plan-2026-09-08.md), and this handoff. No other application files were changed by this package. Prior code, test and documentation work remains in its commits.

## Next

Continue with explicit isolated candidate configuration and the supported frontend/backend route/API surface, then full Next/backend athlete acceptance. The legacy frontend backend fallback, missing Docker build input, broader recruiting surfaces, actual Agent schema, current-source live identity and real saved-submission return remain open. Guardian delegation, authoritative GMTM sport resolution, durable matching job state and legacy research correctness are separate work. These results establish synthetic journey mechanics, not a public rollout.

Follow the [release plan](../../docs/state/commit-and-release-plan-2026-09-08.md): commit reviewed milestones now, prepare the exact candidate and rollback record, obtain the existing required deployment instruction when ready, and verify deployed critical paths. Existing stopped/exhausted live-read/model allowances and production boundaries remain unchanged.
