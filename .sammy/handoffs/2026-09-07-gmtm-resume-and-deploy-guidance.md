# GMTM resume, Fable release guidance and combine navigation

September 7, 2026. Joey reports the cross-machine audit prompt was sent to the separate audit agent and asks to return to GMTM work. During candidate inspection he forwards Fable's request for a session ID and release/deletion decisions, then states he will tell Fable to release PR 73 and wants guidance on database deletions later.

## Release coordination

Codex inspected the actual GMTM session hook: a posted session ID resolves the logged-in session from Redis. It is a credential, not an ordinary profile ID. Native message `codex-gmtm-verification-guidance-20260907-07` returned the final staged deployment review to existing GMTM/Fable and clarified that Joey should not paste the credential into chat. A genuine browser-local probe can be supplemental; if unavailable, authenticated verification remains pending. Pinned disk content, runtime mapping/reload, per-host health, safe read-only data-path checks and timestamped error review are separate evidence. No disk digest alone establishes executed handler behavior.

[Fable's acknowledgment](../../../sparq-gmtm-resume-2026-09-07/fable-verification-guidance-ack.md) accepts those corrections, drops `--update-env`, requires function equivalence, per-host checks and real attended observation, and identifies unresolved live runtime/clean-state gates. It estimates pre-prod auto-restart around September 13 16:20 UTC from the earlier stop receipt, with exact timing still requiring confirmation. No new AWS state was queried here. Raw session credentials or environment dumps must not enter chat/receipts; only required non-secret runtime metadata belongs in verification.

The message was sent before Joey said he would tell Fable to release. It explicitly granted no deployment/deletion/credential access. Codex did not dispatch a duplicate approval afterward. No merge, deployed revision, runtime acceptance or actual deletion is claimed in this continuation. Database deletions stay deferred for their own guidance/decision.

## Product work

Independent read-only backend/frontend inspection identified full-app candidate gaps: three import-time Agent schema helpers, implicit dotenv loading, background matching after workspace bootstrap, and reachable legacy workspace APIs outside the prior restricted acceptance. The [next package](../../docs/state/adult-candidate-next-package-2026-09-07.md) records the outcome and acceptance sequence; it is not implemented yet.

The smallest immediate product fix preserves the current supported combine event on **My next move**. See the [implementation handoff](2026-09-07-sidebar-event-context.md). A mobile menu/link click with explicit adult 1318 and a saved junior 1317 claim reproduced the original failure. The corrected complete component journey passed 89 checks; TypeScript passed; root reviewed the exact incremental source/test diff and receipts and found no blocker.

The original local dependency attempt stalled before the browser; owned attempts were stopped. The existing previously used dependency tree resolved it. Chromium then hit the normal sandbox launch restriction, and the same fully intercepted harness passed through the normal approved-host route. No dependency install or live service fallback was used. Both fixture-only browser runs completed and closed. This is component/React/Chromium evidence, not a live Next/Clerk/MySQL/upload acceptance result. The fix preserves the event present in the current URL; it does not persist context across unrelated routes that omit the query.

## Scope and verification

Application/test changes: `frontend/app/home/components/WorkspaceSidebar.tsx` and `frontend/tests/check-combine-journey.cjs`. Docs: `docs/state/adult-candidate-next-package-2026-09-07.md`, the sidebar handoff, this handoff and the newest `docs/state/current-state.md` section. All remain uncommitted in `codex/athlete-home-first-value` at `6c7e649ce5154f211401ed2e4af03d9691366194`; pre-existing work is preserved. No commit, push, SPARQ deployment, backend startup, source DB read/write, Agent model call or live-test allowance reset occurred.

Sibling `work/sparq-gmtm-resume-2026-09-07/` contains one-message native receipt/readback, failed original-sidebar regression, passing corrected journey, typecheck, incremental patch and final `verification.json`. The original two files are preserved under `work/sparq-sidebar-event-fix-2026-09-07/before/`. Verification checks receipt status and source hashes, exact changed-file scope against the prior 170-file app inventory, links and whitespace. Concurrent audit/infra work is outside this scoped preservation claim.
