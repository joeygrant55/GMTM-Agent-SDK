# Opportunity interest measurement

September 10, 2026. Implemented, independently reviewed and verified locally. Local checkpoint only; final commit is recorded outside Git in `../sparq-engagement-2026-09-10/commit-receipt.json`.

## Completion contract and ownership

Joey wants to surface relevant events, observe athlete interest, and use that evidence for later organizer conversations. Complete a small optional interaction collector and offline aggregate report without introducing athlete tasks, payment-driven ranking, affiliate links or automatic outreach. Verify real component and app mechanics with synthetic identity/data, preserve drafts/navigation, keep capture disabled by default, retain evidence and close every owned test process.

Checkout: `work/sparq-agent-review`, branch `codex/athlete-home-first-value`, remote `joeygrant55/GMTM-Agent-SDK`. Starting HEAD `d123943749a09e74281ee55c167609b55ad19ae6`, initially clean. Root owned collector/integration/full-app tests and final review. Bounded agents owned frontend/component tests, collector test cases/measurement documentation, and offline reporter/tests plus independent collector review. Other checkouts and Fable's lane were untouched.

## Implemented behavior

- `card_visible`: at least 50% continuous geometric intersection for one second in the active, visible Opportunities view. Background tabs, loading/error/stale results, hidden surfaces and open native details/draft-confirmation dialogs pause qualification. Closing them requires a fresh intersection.
- `details_opened`: deliberate successful opening of the actual details drawer. `outbound_activated`: the current primary external link, including keyboard and middle-click. Source citations, context-menu opening and introduction preparation do not become outbound credit.
- Capture attempts each kind once per card in a mounted result, at most nine attempts. Requests have a four-second abort, no retries, no navigation wait, and cancellation on account/link/result teardown. No new visible controls or text are added.
- Exact profile-only authenticated POST `/api/athlete/opportunities/engagement`. The browser supplies only UUID, opportunity ID, event kind, link revision and first source review marker. The server validates the reviewed record, resolves the current unique Agent ownership pair with two SELECTs, closes the connection, and emits the allowlisted pseudonymous payload. No GMTM/workspace access or database write.
- A dedicated stdout lock and complete-line write prevent concurrent collector threads from interleaving JSON records. Process-local rate limits and request bounds limit load; this remains a best-effort log sink, not durable conversion storage.
- Dedicated secret, period/cohort labels and explicit pilot IDs govern account classification. Owner 2 is always internal. The default report excludes internal/fixture records and deduplicates repeated audience across opportunities. Different destination kinds remain separate. No email, name, goal, media, draft, raw identity or URL enters the event payload.
- `backend/opportunity_engagement_report.py` consumes bounded local exports and produces aggregate JSON with counts/denominators, same-window overlaps, missing-view counts and explicit coverage limits. It rejects malformed/conflicting records instead of producing partial audience claims. It is an offline tool, excluded from the deployment source package.

Exact mechanics, activation variables, CLI example and proposed exploratory threshold belong in the [measurement contract](../../docs/state/opportunity-engagement-contract-2026-09-10.md); the [profile runbook](../../docs/state/profile-workspace-runbook-2026-09-08.md) links them and corrects older two-record/no-in-person descriptions to the existing five-record collection. The catalog itself is unchanged by this slice.

## Review findings and retained attempts

- Backend attempt 01: 452 passed, one failed test expectation. The shared date parser accepts a valid UTC `+00:00` timestamp; exact source-marker comparison still rejects its mismatch with the catalog's `Z` string before DB access. Corrected the test and added that endpoint assertion. Attempt 02: 453 passed.
- Independent collector review found split `print` writes could interleave on concurrent threadpool requests and invalidate an export. Replaced that sink with serialized, bounded, newline-terminated writes and added a yielding concurrent-sink regression. Final backend attempt 03: **454 passed**, one existing Starlette deprecation warning.
- Root review found geometric intersection alone would count cards behind a details modal. Separate observation eligibility now pauses those views; the frontend owner also covered the parent draft-confirmation dialog. Both have cancellation/resume regressions. Component attempt 01: 423 passed.
- Production build attempt 01 compiled but failed TypeScript validation because the new helper iterated Map/Set/NodeList directly under the existing target. Converted those three loops with `Array.from`; project configuration was not widened. Final build 02 passed.
- Catalog provenance remains limited: `reviewed_at` pins only the first source timestamp; `catalog_revision` is a hash of the current server-accepted record. Changing other content without advancing that review marker can accept an old tab against new content. The contract explicitly records this limit and requires re-review/marker updates; it does not claim exact rendered-copy proof. A returned-and-echoed full digest is a possible later strengthening.

## Final accepted verification

Evidence is outside Git in sibling `sparq-engagement-2026-09-10/`, `sparq-engagement-app-2026-09-10-01/` and `sparq-engagement-build-2026-09-10-02/`. Failed/intermediate attempts remain intact. Heavy jobs ran serially under finite external supervision.

| Check | Final evidence |
| --- | --- |
| Backend | `backend-03.log`: 454 tests covering collector/report, opportunities, candidate routes/configuration/package, read-only founder wrapper and launcher. |
| Components | `component-02.json`: 423 checks, no runtime errors/denials, cleanup verified. Includes qualified dwell, modal/background/scope cancellation, default off, precise payloads, activation distinctions, failures/timeouts and draft preservation. |
| Route policy | `policy-01.json`: 113 checks; only the exact new profile POST is allowed. |
| Actual app | App `receipt.json`: 156 journey checks plus five safety assertions through actual Next and authenticated ASGI with synthetic ownership/data/provider fixtures. The exact organizer document is intercepted locally; no organizer is contacted. |
| Production | Build 02 `receipt.json`: actual Next compile/typecheck and unauthenticated same-artifact startup pass, source inputs unchanged, no network denials. Existing dependencies and synthetic configuration; not a deployable or signed-in production acceptance claim. |
| Aggregate pipeline | `aggregate-cli-01-receipt.json`: offline CLI consumed the actual app's captured fixture log. One synthetic account produced one card view, five details actions and one outbound action across four opportunity groups. Battle Orlando has one view/details/outbound account each. Default pilot report correctly returns `no_data` and zero audience. These are QA counts only. |

`source-reconciliation.json` confirms 136 frontend files match both app/build snapshots, 96 backend files match the app snapshot, all 17 component sources, 15 recorded backend verification inputs and three policy sources match. All owned verification groups and ports are closed, including failed attempts; no preview remains. Actual-app browser errors and unexpected blocks are zero; twelve pre-existing Google stylesheet requests were deliberately blocked by the harness. No real provider attempts or unclosed synthetic connections were recorded.

## Runtime boundaries and next action

Both frontend and backend measurement flags remain default off. No live configuration was read/changed, real audience measured, telemetry vendor added, schema created, production data touched, AWS/GMTM service changed, model invoked, registration attempted, message sent, affiliate contract entered, push made or deployment performed.

The current real-owner wrapper still denies this new route; its launcher omits the settings and discards stdout. It cannot be used as a pilot collector/export path. Earlier owner-2 previews are expired and the previous three-save allowance remains exhausted. Nothing in this change resets that allowance.

Next is relevance and pilot readiness: founder review of actual useful options, then a small explicitly admitted adult cohort on a reviewed hosted build with functioning identity/entry, freshly reviewed sources, paired build/server capture flags, a fixed reporting window and private log retention/export. Confirm those operational pieces before treating absent logs as zero interest or using counts in an organizer conversation. The current reviewed collection is limited adult flag coverage, not autonomous discovery. Source expiry is unchanged; do not extend it without revisiting official pages.

The proposed 20 viewed / 5 outbound-account threshold is a judgment for exploratory outreach, not a significance test, registration proof or price signal. Activation does not prove destination arrival, qualification, selection, payment or incremental demand. The separate GMTM SSO/auth planner contract remains unimplemented and is not expanded by this measurement work.
