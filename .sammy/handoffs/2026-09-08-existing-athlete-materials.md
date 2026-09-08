# Existing athlete submissions and footage

September 8, 2026. Codex continued Joey's approved profile-value build from clean local `29efaf26c48cbb001d423a5af6bbace62b38ecc5` on `codex/athlete-home-first-value`, origin `joeygrant55/GMTM-Agent-SDK`. This is the same SPARQ checkout and writer lane. Fable's infrastructure/security and Audit's computer-organization work were not touched.

## Delivered behavior

The explicit private profile surface adds `GET /api/athlete/materials`. It accepts no query parameters, independently resolves the existing forward/reverse Clerk link, and reads four literal bounded source paths. Original submission snapshots supply supported numeric answers; the append-only answer mirror is not used. Footage ownership must agree through every applicable direct-user, career and submission reference. Personal-film event joins reveal only validated public event context. No media URI, thumbnail, description, raw payload or owner identifier enters the response.

The UI shows up to three material records initially, expandable to20 submitted results and 10 footage records. Source dates retain their meaning; submission dates are not measurement dates. Public source permission and source-marked availability determine whether an athlete can select a result or canonical GMTM page reference for text. Other owner material remains view-only. It is not automatically copied. Plain links open only on the athlete's action; nothing fetches or analyzes media. Independent loading/error/retry leaves profile measurements and the existing draft usable. Refresh/account changes clear the private page state. On phones the composer precedes materials, with direct page anchors in both directions.

This extends the factual composer. It does not implement selection inference, verified athletic benchmarks, film analysis, current opportunity matching, persistent goals/drafts, public sharing or automated outreach.

## Source finding and correction

The first bounded owner read exposed ten projected films with `processed=0`. Our first implementation incorrectly mapped that to processing and blocked their page references. Independent local source review found core `resources/film/film.resolver.js:1185` persists 0 for supported GMTM footage while its response at 1295 presents 1, and the web film page does not gate the player on that flag. The adapter now labels non-dead footage `unchecked`, with no active-processing or playback claim. Canonical public page references can be included when `dead_link` is exact 0 or NULL. Explicit1 is unavailable/no link; malformed dead-link values remain view-only. All ownership/publicity gates and four queries are unchanged. See the dated source map for provenance and query bounds.

## Verification

Artifact paths below are relative to the outer workspace's `work/`, alongside this repo.

- **955 backend tests pass**, including 167 materials tests and 85 owner-reader/launcher tests. `sparq-materials-2026-09-08/backend-02.log` and its supervisor receipt. Existing Starlette deprecation only. Tests are offline; bounded local-child process cleanup is exercised.
- **108 component checks pass**, covering exact selected/edited output, independent failures, response parsing, unsafe links, stale accounts/bodies/copies, timeout/retry, private material exclusions and phone reading order. `sparq-materials-2026-09-08/component-02.json`; Chromium group/control port and harness group closed. Captured application hashes still match the final frontend.
- **88 policy checks pass**. The new GET is allowed only in the explicit profile surface; method variants, selectors, unrelated routes and old combine access remain denied. `sparq-materials-2026-09-08/policy-01.json`.
- **57 actual Next/ASGI journey checks plus five safety assertions pass**. Final run `sparq-materials-app-2026-09-08-03/receipt.json` exercises public/private source records, a real processed-zero fixture, selection/rebuild/copy, failure/retry preserving a draft, twenty-result phone layout, claims/recovery and logout. Synthetic Clerk/SQL; no live authentication claim. All 27 synthetic connections close, no forbidden operations or provider attempts, unchanged source inputs. Three owned groups and all three ports close. External supervisor: `sparq-materials-2026-09-08/app-03.supervisor.json`.
- **Actual Next production compile/typecheck/start pass** with real Clerk packages and synthetic configuration. `sparq-materials-production-2026-09-08-01/receipt.json`; two process groups and its port close, no outbound denials or input changes. All 126 captured production frontend inputs still match after the backend-only legacy-flag correction. The build was not unnecessarily repeated. External supervisor retained.
- Root inspected desktop and phone screenshots, including the twenty-result collapsed view. The composer remains within two phone viewports before drafting; no horizontal overflow. Final React/source review and independent backend/media and reader-scope review completed.

Initial failed checks are retained: component01 stopped at an outdated test expectation of one initial GET after the second independent read was added; the component filename also changed to `ProfileMaterialsPanel.tsx` to avoid Mac case-insensitive resolution against `profileMaterials.ts`. Full-app01 timed out on an overly exact accessible link-name selector; full-app02 passed before the live-data semantic correction; full-app03 verifies the final adapter with a processed-zero fixture. These were corrected and rerun with new artifacts. Every observed failed run also closed its owned processes/ports. No old persistent browser session was revived.

## Live owner validation

Joey's previously designated GMTM athlete 2 is the only live test owner. The explicit materials scope adds no caller-selectable athlete or arbitrary SQL. Each run has a new source digest and separate mode 0700 private directory, mode 0600 projection/receipt files, read-only transactions, fixed service binding and read-only GMTM credentials, two connections, seven SELECTs and eleven explicit statements including transaction setup. No schema/data write or media/provider access occurred. Both runs verified the stored link and closed both connections and their supervised process group. They directly invoke the real handler, not a current Clerk JWT or authenticated browser.

- Initial source digest `abd1c5485fb804ec7467448af1cbf6f912adeab02bababea1489b5ebdbe11ff7`; private directory `/private/tmp/sparq-owner-materials-2026-09-08-01`. It exposed the legacy-flag problem.
- Corrected source digest `a1d190b84f6defb747bee1c137b34e4b421a9f5438296502576871e4ae80d6ac`; private directory `/private/tmp/sparq-owner-materials-2026-09-08-02`. Final module SHA256 `d532d01a1d68630706a8e703dc1dd52b1afbcc6d7f446c2ed54bb6e8c3ba4dee`.
- Both reads returned 19 latest nonremoved submission snapshots,12 submitted-film rows,46 direct-film rows and2 career-film rows. The corrected projection contains 10 footage records, all playback unchecked, with 2 eligible canonical references. No numeric submission answers were accepted by this limited adapter. This is not an assessment of the athlete, proof of absent numeric answers, or verification of all historical content.
- Safe count-only summaries: `sparq-materials-2026-09-08/owner-read-safe-summary.json` and `owner-read-02-safe-summary.json`. The actual private projection, Clerk IDs and credentials are not in Git or a provider input. Do not reuse either ledger or silently add more live reads.

## Checkpoint and next work

The reviewed local commit contains the new adapter/UI, route policy, regression and finite fixture/reader integration, source map, contract, runbook and current-state update. The exact resulting commit is recorded outside the repo in `sparq-materials-2026-09-08/commit-receipt.json`. No push/deployment or production/infrastructure change is authorized by this checkpoint.

Next product contract: take an actual athlete goal and these attributable sources, answer a useful post-combine/profile question, and produce one relevant opportunity action with current primary-source support. Profile packaging and real signed-in acceptance remain release gates. The deterministic composer and this source coverage are foundations, not proof of paid demand. Any model use needs a reviewed minimized input/allowance; the earlier combine-help budget does not cover rich profile or footage data.
