# Profile workspace build and crash recovery

September 8, 2026. Codex resumed after Joey reported a crash. Checkout: `work/sparq-agent-review`, branch `codex/athlete-home-first-value`, starting HEAD `e7750e6`. The uncommitted implementation and earlier receipts survived. This handoff supersedes the earlier statement that no profile workspace exists.

## What is implemented

The explicit `profile` frontend and `profile_candidate_app:app` backend present the athlete's existing evidence and a factual output composer. GMTM remains the combine submission interface. There is no second checklist, chat sidebar or automatic college research in this surface.

The new evidence handler resolves strict forward/reverse Clerk ownership before bounded read-only GMTM queries. It projects canonical identity, unambiguous primary-career context and eligible current numeric measurements with units, dates and attribution. Unsupported or restricted evidence is omitted explicitly; unknown verification remains unknown. Network-only digital events are excluded in both SQL and projection following independent review. No athlete selector, invented percentile, selection result or public sharing claim is admitted.

The athlete selects facts, states a goal, chooses summary or introduction, edits the output and copies the exact text. Introductions require an actual recipient supplied by the athlete. The first three measurements appear initially; expansion exposes up to twenty without losing selected facts on collapse. Account changes, refreshes and stale requests cannot restore earlier private state. Drafts remain page-local and are lost on refresh/navigation. Preparation is deterministic; this is not yet an intelligent assessment or opportunity finder.

Route isolation, sign-in/recovery/claims, explicit configuration and startup isolation remain intact. Claim redemption can write existing Agent data; the new evidence read does not. Default combine and legacy surfaces remain separately selected. The older combine Docker/source manifest does not package this profile entry. See the [runbook](../../docs/state/profile-workspace-runbook-2026-09-08.md) and [completion contract](../../docs/state/profile-workspace-build-contract-2026-09-08.md).

## Verification

All artifact paths below are relative to the outer workspace's `work/`, outside this implementation checkout.

- **762 backend tests pass**, including actual handler ownership/visibility checks, profile ASGI/JWT boundaries, safe startup and the owner-reader/launcher regressions. One existing Starlette deprecation warning remains. Final log/receipt: `sparq-profile-final-2026-09-08/backend-tests.log` and `backend-tests.json`.
- **69 actual React/Chromium component checks pass**: source loading, errors, account changes, stale response/body/copy completion, exact edited output, clipboard fallback, date handling and twenty-result selection. `sparq-profile-workspace-2026-09-08/component-04.json`; browser group and control port closed; external supervisor did not time out. Synthetic identity/data/clipboard, not full CSS or live authentication.
- **81 API policy checks pass**, including profile-only operations and preserved default combine policy.
- **Actual Next production compile/typecheck and same-artifact start pass** with real Clerk packages and synthetic settings: five denied routes return 404 and signed-out inbox redirects to sign-in. `sparq-profile-production-2026-09-08-03/receipt.json`; no changed inputs or network denials, both owned process groups dead and port closed. This build includes the final compact results layout.
- **45 complete-app checks plus five source/safety assertions pass** through actual Next development/RSC and ASGI. They exercise claim/recovery, the profile evidence request, preparation/editing/system clipboard, refresh/logout and a twenty-result phone stress overlay. `sparq-profile-complete-app-2026-09-08-02/receipt.json`. All 124 captured frontend files and captured backend inputs remain unchanged; no runtime errors, real providers or forbidden source operations. Chromium, Next and backend groups exited; all three ports closed. Identity and SQL stores are synthetic; this is not real Clerk or deployed acceptance.
- Independent source review covered the evidence adapter, restricted surface integration, stale-account behavior and supervised reader. Root reviewed subsequent fixed-file credential precedence and the matching tests. Desktop and phone screenshots were visually inspected; controls and text are usable without horizontal overflow, and the twenty-result list collapses before the composer.

Earlier failed receipts remain intact. Production attempt `01` failed at sandbox loopback allocation before compilation; `02` passed before the final list-collapse improvement; `03` passed after it. Complete-app `01` exercised the journey successfully but rejected Next's `localhost` alias after logout. Installed Next source confirms loopback normalization. The harness now admits only the exact owned frontend port under `127.0.0.1` or `localhost`, verifies redirect origins, and continues to reject other destinations. Product middleware was not changed for that fixture issue.

## Real owner-profile result

One new bounded read of Joey's designated user 2 completed under the [owner read contract](../../docs/state/owner-profile-read-contract-2026-09-08.md). It confirmed the stored unique ownership link and returned a ready projection with profile identity and **two eligible measurements: height and weight**. Other source records were omitted by the adapter or lie outside its scope. This does not establish that the broader profile lacks performance results, submissions or film.

The run used exactly two connections, six SELECT attempts and ten explicit SQL statements including transaction setup. Both connections rolled back/closed; zero denials, data writes or provider calls; supervisor completed with its owned group dead. This directly invokes the real handler and verifies live source projection. It does **not** verify a current Clerk JWT, signed-in browser, authenticated HTTP route or a deployed profile service.

Private projection and private receipts remain mode 0600 under `/private/tmp/sparq-owner-profile-2026-09-08-2138` (directory mode 0700), outside Git. Do not copy them into a repository, share them or send them to a model provider. A safe counts/hash/cleanup summary without the projection is in `sparq-profile-final-2026-09-08/owner-read-safe-summary.json`.

Reviewed reader digest: `a7a024c156e3819d5bc73a089fed1975aee4fde61e4b26b9093c285018ab7729`. Launcher SHA256: `c5455878fa2eb87ba4c262f515dd6d42f5d910de06e4e38c65f2bde8862c2391`.

Railway configuration preflight confirmed the existing project/service/database binding and public proxy. Its GMTM hostname is db2-dev but its configured user differs from gmtmread. This local read used the exact previously documented Fable credential source, matching the wrapper's first-definition precedence, and changed no deployed setting. The initial strict duplicate-key parser stopped before database access; the corrected parser and 43 launcher tests passed before the single live read. No credential values were printed or retained in source/receipts.

## Crash and lifecycle boundaries

The separate Audit task reported cleanup of an old persistent browser and cleared this task for one heavy verification job at a time. That report is not independent proof of the crash's cause. This task did not restart `sparq-live-0907`, offload to the Mac mini, change global browser/agent settings or stop unrelated Chrome processes.

The current ephemeral test harnesses now have whole-run and cleanup budgets, signal handling, bounded browser close, fsynced PID/PGID journals and verified owned-group/port cleanup. Final browser runs also used finite external Python supervisors; their receipts sit beside the test artifacts. The reader has a soft 90-second interruption alarm and a separately supervised 105-second process limit plus bounded termination grace. Cancellation is durable before raising and cannot be swallowed into a successful observation. Abrupt machine loss/SIGKILL can leave incomplete receipts; only observed cleanup is claimed. Audit received the successful final cleanup readback.

## Next product priority and release state

The live result establishes why more generic summary polish is not the priority. Extend the evidence mapping to the athlete's richer existing structured submissions and available footage, maintaining ownership, field provenance and visibility. Then answer a real athlete question with that evidence and identify one sourced, relevant opportunity or next action. Do not turn height/weight alone into potential, eligibility or selection predictions. A factual composer is not evidence of willingness to pay.

Organizer-confirmed selection outcomes, film interpretation, current opportunity discovery, persistent goals/drafts, real signed-in profile acceptance and profile deployment packaging remain open. Previous combine-help model allowances are not renewed by this read. Any next live source scope needs its own bounded contract/receipt, and any release still requires Joey's explicit decision.

This checkpoint includes the profile backend, UI/parser, route/configuration integration, test harnesses, supervised owner-reader/launcher and their tests, README/AGENTS pointers, contracts/runbook/current state and this handoff. It is prepared for a **local commit only**; the exact resulting commit is recorded in `sparq-profile-final-2026-09-08/commit-receipt.json`. No push, deployment, infrastructure change, AWS action, production data mutation, paid model call or external athlete outreach occurred. Fable's infrastructure/security and the Audit/portfolio lanes remain separate.
