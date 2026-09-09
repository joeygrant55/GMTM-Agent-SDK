# Athlete media overview

## Outcome and source

Joey asked for a simple, beautiful interface that shows athletes their own media/content and invites useful action. The private profile entry now starts with a large stored footage preview, its actual title, two existing results at most, and an explicit introduction action. Ask about my profile opens the prior focused question flow; profile details remain in the native sheet. There is no second combine checklist.

Starting point: `0f797ee2e01ef6dbfa1e7db42f33b1b021a015c0`, branch `codex/athlete-home-first-value`, origin `joeygrant55/GMTM-Agent-SDK`, in Codex's existing `work/sparq-agent-review` checkout. The working tree was clean. Repo instructions/current state and Control Tower ownership remain in force. Fable's infrastructure/security and Audit's setup lanes were not changed.

## Implementation

- New `AthleteShowcase.tsx` shows only eligible public footage, with previous/next controls when more than one clip is returned. It keeps recorded and submitted result types distinct. No ranking, film judgment, scout interest or playback affordance is invented.
- `ProfileWorkspace.tsx` adds overview/guidance navigation and explicit clip selection into introduction preparation. Selected footage is labeled as a selection, not a claim that an older draft already contains it. Existing edits are preserved until rebuild; reusing the same selected clip does not create a false stale warning. Account/source refresh behavior remains isolated and page-local.
- `athlete_materials.py` adds stored service and a SQL-bounded thumbnail key to the same three owner-scoped film SELECTs. Only existing can_include footage can receive a normalized thumbnail URL. Exact known CDN/YouTube families, conservative raster filenames, safe positive namespace IDs and length/ASCII limits are validated. No new query, server image fetch/proxy or video-URI derivation was added.
- `profileMaterials.ts` accepts the optional nullable field with matching client validation. Old responses without it stay usable. Native images use anonymous CORS and no referrer; failed or missing images keep the title and canonical public-page action without fallback hosts, generic imagery or model/source retries.
- The debrief's server-assembled context and the factual draft generator exclude thumbnail metadata. Private, uncertain-scope and dead footage do not receive public posters.

The [media contract](../../docs/state/profile-media-design-contract-2026-09-08.md), [source map](../../docs/state/athlete-materials-source-map-2026-09-08.md) and [runbook](../../docs/state/profile-workspace-runbook-2026-09-08.md) record exact interpretation and remaining limits.

## Verification

All heavy jobs ran serially under the existing finite external supervisor. The final aggregation is outside Git at sibling `sparq-media-design-2026-09-08/verification.json`.

- Backend: **998 passed**, one existing Starlette deprecation warning. Receipt/log: `backend-supervisor-01.json`, `backend-01.log`; three frozen changed backend test/source hashes retained.
- Components: **262 checks**, including malformed/unsafe URLs, old payloads, public/private/error/empty states, image failure, clip browsing, no automatic AI, exact draft preservation, same-clip reuse, and account isolation. Final `component-02.json` and supervisor receipt have no errors/denials and confirmed Chromium group/port cleanup.
- Complete app: **100 checks plus five safety assertions**, actual Next/ASGI with synthetic identity/SQL/model responses. Final sibling `sparq-media-app-2026-09-08-04/receipt.json` confirms the whole journey and cleanup. One explicit synthetic debrief, zero real application-provider attempts, no forbidden backend operations, all synthetic connections closed.
- Production: actual Next production compile, TypeScript check and unauthenticated startup smoke pass with real installed Clerk packages and synthetic configuration. Final sibling `sparq-media-production-2026-09-08-02/receipt.json` confirms no network denials, changed inputs or remaining owned port/process groups.
- Final hash reconciliation: 10 component inputs, 129 frontend application files, 69 backend source files, production inputs and the synthetic image match the retained receipts. No application files changed after these runs.
- Independent source review found no owner/privacy/URL compatibility blocker. Independent visual review of the same application source found no clipping, confusing playback affordance or blocking hierarchy issue. Final root review included the failed-preview phone state. The phone shows the whole introduction action in its first 390x844 viewport and 89 visible words across the page.

Earlier failed app runs remain retained: runs01/02 stopped at an unsupported expectation that the interception layer expose Sec-Fetch-Mode. Observed cookie/auth/referrer fields were all absent; the corrected test retains those probes and DOM attributes while logging the optional header. Run02 started before the correction handoff arrived and repeated the old assertion. Run03 reached75 checks but its failure injection reused a decoded image in the existing document. Run04 uses a fresh document for the genuinely failed first image load. No check of actual cookie/auth/referrer leakage was removed. All failed-run owned groups and ports also closed.

## Visual evidence and limits

Final desktop/phone initial, answer, editor, profile-sheet and failed-preview captures are in sibling `sparq-media-app-2026-09-08-04/`. These are actual app renders using sample athlete data and one AI-generated sports image from this turn. The image is committed only as `frontend/tests/fixtures/synthetic-footage.png`, with its provenance README. Exact browser request interception serves it locally; there is no real CDN request and it is never bundled as a production media fallback. Its hash is in `media-fixture.json` and the app receipt.

Current real owner thumbnail coverage, real CDN CORS/availability, signed-in usefulness, film playback/analysis and real-model advice quality are not established by these tests. Earlier owner reads predate the added thumbnail fields and are not current thumbnail acceptance. The separate eight-case synthetic model allowance is still unanswered; no earlier app-model ledger or live-read allowance was reopened. One image-generation tool call created the clearly identified sample photo. No application-provider call, live DB read, AWS/IAM/RDS change, production mutation, outreach, push or deployment occurred.

## Checkpoint and next action

Local commit includes only this bounded media adapter/UI/test fixture and the related source/runbook/state/handoff updates. Its exact commit and post-commit status are recorded outside Git in sibling `sparq-media-design-2026-09-08/commit-receipt.json`. No work is pushed. Test servers and browsers are stopped; retained screenshots are previews, not a running pilot.

Next: founder review of the visual interaction, followed by current real-profile thumbnail/usefulness acceptance and the separately pending model-quality evaluation. Persistence, durable quotas and profile release packaging remain separate work. Do not infer a release recommendation or paid demand from these local verification results.
