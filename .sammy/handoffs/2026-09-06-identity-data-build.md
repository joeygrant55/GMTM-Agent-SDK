# SPARQ identity and data build — September 6, 2026

Joey requested a plan and execution after the full repo audit. This authorizes local implementation of the reviewed identity/data work; it supersedes the prior audit-only stop and pending local draft hold. Existing production, communications, billing and infrastructure boundaries remain. Owner: Codex, task Evaluate Sparq agent project (01a06f58-7203-7f82-a090-3545f126936b), existing work/sparq-agent-review checkout, branch codex/athlete-home-first-value, HEAD 6c7e649ce5154f211401ed2e4af03d9691366194. No branch/lane transfer.

## Delivered

The active five-milestone plan is docs/state/sparq-build-plan-2026-09-06.md. The first local batch is implemented and isolated verification passes:

- Legacy connect is existing-owner confirmation only. Foreign, unclaimed and unknown IDs receive the same invitation recovery response; no mapping writes occur. The reviewed draft's relevant behavior is adopted and extended; its original files remain intact.
- Claim redemption acquires a bounded per-Clerk advisory lock, locks the token in a transaction, matches stored athlete/event to the signed token, refuses unrelated or ambiguous Clerk mappings, uses a no-op duplicate athlete insert followed by locked owner verification, and commits the claim/link together. Failures roll back before lock release/close; same-owner retries preserve original timestamps. No implicit multi-athlete account model or live cleanup was introduced.
- Explicit conversation IDs are checked before profile/model work. Message inserts include conversation and owner predicates. Default history uses one default thread, not all forks. Forking locks an owned parent and copies messages in one transaction; request-time DDL is removed. Schema incompatibility is surfaced as an error, not success.
- The model SQL executor, table schema prompt and query_database tool are removed from the active agent API. get_current_athlete takes no arguments and returns the server-loaded request profile. The caller/model cannot choose SQL or another athlete ID. Demo chat does not load profiles/history or query databases.
- Connect, claim redemption and chat have owner-keyed lifetimes, abort in-flight requests and ignore late completions. Success requires confirmed connection to the expected account. Claim copy works before results; 409 is neutral and retryable. Missing tokens prevent redemption requests. Artifact iteration uses the authenticated request helper and reports failures. SSE errors are visible.
- Offline backend test support and a persistent actual-component frontend harness are checked into the working tree; README/current-state point to the current architecture and plan.

No active-event requirement adapter is implemented yet. Root verified three core API source files at the user-reported deployed revision 1bf4fc0297d5eea56bed6bda54715f2f9c01593f using the existing GitHub CLI session. The older MacBook API checkout and unrelated ecosystem.deploy.js were left untouched. docs/state/combine-adapter-source-map-2026-09-06.md records current task/submission evidence and unresolved payload/visibility/registration rules.

## Verification and review

- Actual-current-checkout backend suite: 111 passed in the root combined run. Coverage includes the 42 agent boundary, 52 claim, six legacy link and 11 combine tests. dotenv, real model/DB clients and outbound DNS/TCP are blocked; absent PyMySQL/Anthropic imports have fail-closed shims. These tests are not live SDK/MySQL verification.
- Current frontend snapshot TypeScript passed with the existing hydrated dependency tree; no full Next build.
- Forty-seven current-source React 18/Chromium component assertions passed, using synthetic Clerk, navigation, Markdown and API responses and intercepted browser networking. Coverage includes HTTP/SSE errors, mismatched/unconfirmed success, late valid responses, account/token switches, retries, missing tokens and StrictMode. No full Next middleware/layout, live auth/backend/provider or phone acceptance is implied. The headless browser closes in finally.
- Root reviewed claims and frontend; a second reviewer reviewed agent changes; the agent reviewer independently reviewed root's connect/test support. Review fixes included deterministic tamper tests, malformed Unicode/oversized conversation IDs, SSE save/provider failures, neutral 409 copy, redemption cancellation/StrictMode and matching-account success checks. No blocking issue remains within this bounded local batch.
- All five pre-existing local home implementation files remain hash-identical. Final preservation receipt compares the 174 captured baseline files with the explicit changed-file list and records new files and git status. Source remains uncommitted; no commit/push/deploy.

Receipts: task-root work/sparq-build-2026-09-06/backend-verification.json, work/sparq-frontend-boundaries-2026-09-06/{component-receipt,typecheck-receipt,preservation-receipt}.json, and the aggregate outputs/sparq-build-verification-2026-09-06.json. Root's browser rerun first hit macOS sandbox process restrictions; the approved isolated rerun is recorded separately. No production-service call was substituted for a fixture.

## Remaining gates and next action

Next milestone: preserve authorized active-event context independently of results, establish applicable requirement/validation/visibility semantics, and implement the zero-result athlete's one grounded next step with a return into existing GMTM and refreshed progress. Do not copy metric counts or core notification aggregates as proof of requirements satisfied. Charles's exact target event/URL and expected athlete arrival date were requested asynchronously; no answer was assumed.

Before rollout: verify actual Agent MySQL transaction engine, unique user_id constraint, advisory-lock behavior and concurrent races in an isolated integration environment. The existing conversation schema may lack required tables/fork columns or enforce one conversation per Clerk; deterministic migrations and initial-thread concurrency are unresolved. Historical incorrect/ambiguous mappings have not been repaired. Verify real Clerk/model behavior and full athlete/mobile flows. Other audit blockers remain: public visibility/sharing and unsafe HTML/fetch paths, reliable outreach send/version/idempotency, durable jobs/budgets, authoritative outcomes and commercial entitlements. This local first-batch pass does not close the entire audit or authorize launch.

## Uncommitted scope

This batch modifies README.md, AGENT_SDK_ARCHITECTURE.md, backend/agent_api.py, backend/claims_api.py, backend/profile_api.py, backend/tests/test_claims.py, frontend/app/connect/ConnectClient.tsx, both claim page files, WorkspaceAIPanel.tsx and docs/state/current-state.md. It adds athlete_context.py, backend test dependencies/support/tests/readme, frontend account-boundary harness/readme, the build plan/source map and this handoff. The pre-existing five home files and earlier instructions/handoffs remain uncommitted and preserved. Exact paths and hashes are in the aggregate receipt. No other checkout or Control Tower file was changed.
