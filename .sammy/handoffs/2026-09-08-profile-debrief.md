# Goal-based profile debrief

Joey asked Codex to keep building from `bb2871c` on `codex/athlete-home-first-value`. This checkpoint implements one question-based debrief and one actionable result in the private profile surface. Codex retains this checkout; Fable retains GMTM infrastructure/security and Audit retains workspace organization.

## What is implemented

The primary panel asks for a focus and a real question. An explicit Ask SPARQ request reads current owner evidence and returns a fully buffered, validated answer with observations, unknowns, numbered citations and one server-defined action. The three focuses are profile understanding, the adult USA Football pathway and preparation for an introduction. Sources expand on demand. Local actions open the existing manual composer without selecting facts or overwriting a draft; only an explicit rebuild replaces edits. Manual preparation remains available independently of AI.

The new profile-only `POST /api/athlete/debrief` accepts only track/question, with no query selectors. It resolves the strict forward/reverse Clerk link once, uses the existing two Agent and seven GMTM SELECT helpers, and closes both connections before model work. It adds no SQL source path or schema. Four global source slots are reserved before scheduling and survive a timeout until the actual worker ends. One actor request is in flight, with finite per-process rate and model limits.

Provider context contains at most 24 supported public facts, interleaving recorded/submitted numbers and retaining up to 10 eligible footage records. Numeric precision and recorded/submitted/published date distinctions are preserved. Server-derived identity/contact/location/school/DOB/account IDs, private material, raw answers, film titles/descriptions/URLs and scout records are excluded. The freeform athlete question is included after trimming and may itself contain identifying content; this is not anonymous processing. Footage is neither fetched nor analyzed.

The separate profile ledger uses `PROFILE_DEBRIEF_ENABLED=true` plus an allowlisted model and explicit positive call/concurrency caps. Default is disabled. The provider transport accepts an optional injected ledger; combine defaults and earlier allowances remain unchanged. One bounded provider attempt, no tools, fallback or retries. Every complete model response must pass strict JSON, paragraph, reference and action validation before rendering. Reference validity does not establish that a claim is supported.

USA Football facts and official destinations are reviewed, dated and expire October 8, 2026 at 22:51 UTC. Expired national-team sources produce a specific refresh-needed error; other focuses remain usable. External actions open only the reviewed public support or development-resource page, without sending, booking or promising access. See [contract](../../docs/state/profile-debrief-contract-2026-09-08.md) and [runbook](../../docs/state/profile-workspace-runbook-2026-09-08.md).

## Verification and evidence

Final retained artifacts are siblings of this checkout under `../sparq-debrief-2026-09-08/`, `../sparq-debrief-app-2026-09-08-04/` and `../sparq-debrief-production-2026-09-08-02/`:

- Complete offline backend suite: **986 passed** (`backend-01.log` and supervisor receipt). The debrief-focused 28 cases are included. One existing Starlette/AnyIO deprecation warning remains.
- Final intercepted component journey: **185 checks passed**, `component-05.json`; exact actor/refresh/timeout behavior, strict parsing, no automatic calls and edit-preserving actions. Browser group and port closed.
- Shared route/transport policy: **93 checks passed**, `policy-01.json`.
- Actual Next/ASGI journey: **61 checks plus five safety assertions passed**, `receipt.json` in the final app artifact directory. Includes synthetic signed auth, claim/linking, all source helpers, one explicit buffered synthetic debrief, action-to-composer, clipboard, independent material failures, phone expansion and sign-out. Zero real provider attempts; all synthetic connections and all three owned groups/ports closed.
- Actual Next production compilation/typecheck/start: **passed**, final production receipt. Real installed Clerk packages with synthetic settings; no deployment. Both owned groups and the port closed. The aggregate receipt confirms 128 frontend and 69 backend source files match the tested inputs.
- Independent backend/client contract review found no blocker after fixing source concurrency and numeric precision. Independent final desktop/phone review confirmed readable controls and corrected materials navigation/card spacing. Screenshots use synthetic athlete data and AI prose.

All heavy jobs ran serially under finite external supervision. Earlier receipts remain: component-02 caught an omitted carriage-return guard; full-app-01 used an exact text locator that omitted the appended citation button; full-app-02 retained the former two-viewport requirement for the now-secondary manual composer. The corrected test checks reachability of the primary debrief. No failed receipt was replaced or counted as a pass.

The aggregate `verification.json` validates final source hashes against the retained component, policy, full-app and production artifacts. `commit-receipt.json` records the local commit hash after this handoff is committed. No push or release was performed.

## Remaining acceptance and next action

Real-model advice quality is **not yet tested**. Eight exact synthetic cases and their complete prompts are packaged outside Git at `../sparq-debrief-2026-09-08/quality-prompts-01.json`, with source hashes and a proposed eight-attempt Sonnet ceiling, 1200 output tokens and 30 seconds per attempt, no retries. Package SHA256: `bae0bd33057d985d42242c456a8f2d169f6a142cc7a130b141f410eb5d6e79ce`. The separate [quality protocol](../../docs/state/profile-debrief-quality-evaluation-2026-09-08.md) distinguishes structure from evidence support and usefulness. Joey has been asked asynchronously to approve this finite new allowance because the earlier model test allowance is exhausted; no answer or new provider authorization was received at this checkpoint. Do not infer approval from elapsed time or reuse the old ledger.

After approval, evaluate those exact synthetic prompts, retain every attempt and perform independent semantic review before testing a real athlete. Existing user 2 evidence reads predate this new debrief path and are not its current signed-in acceptance. Profile deployment packaging, real-account acceptance, durable quotas across workers/restarts, retention/persistence and real-athlete usefulness remain release gates. This feature does not discover a broad opportunity market, verify film/selection, send outreach or establish paid demand.

This continuation made no live database read, provider call, external message, deployment, production-data mutation or infrastructure change. All model/source/browser fixtures are explicitly synthetic. App code, tests, source registry, runbook/current state and this handoff are committed locally together; large test artifacts stay outside Git.
