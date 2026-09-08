# USA Football live public event contract — September 6, 2026

Joey supplied `https://usafootball.com/national-team/digital-combine`. Root read the official page, followed its public event links and fetched only unauthenticated event landing HTML. The links confirm junior 1317 and adult 1318; the public page data supplies organization 249002 and nine activities per event. No real session/athlete-submission data was retained. No sign-in, registration, submission, payment, database or configuration mutation occurred.

## Result and scope

See [public contract](../../docs/state/usaf-combine-contract-2026-09-06.md), also copied to task `outputs/usaf-combine-contract-2026-09-06.md`. Source projections and provenance are under task `work/sparq-usaf-events-2026-09-06/`. A normalized source-derived fixture is added at `backend/tests/fixtures/usaf_2027_combine2_public.json`; its empty progress case is synthetic, not an observed athlete.

The public pages serve build ID `b0293a2cc918da59afb53cc75c0cfdd71769c4a3`, equal to the local web HEAD. This improves source freshness evidence but does not verify every deployment asset or private route. Events are public/non-invite-only and lack a GMTM product ID, so public requirements must not depend on paid-product/invitation membership. Personal progress still depends on server-resolved athlete ownership.

Root found published/configured deadline disagreement, unclear mandatory status of the standalone highlight activity, conflicting adult dash labels and stale adult ID-price copy. The deadline and highlight policy were asked asynchronously; no answer is assumed. Source conflicts must remain explicit until resolved. External membership validity and junior actor/delegation remain distinct unresolved contracts.

Astra reviewed the product implications. Backend reviewer checked current result mapping: event-tagged `20 Yard Shuttle` is canonicalized as 20-yard dash and submission fallback uses task title, so the bad adult question caption does not prove a 40-yard stored result. A separate existing limitation skips fallback for an entire event after any recognized metric is present; mixed-ingestion and required-video/direction cases belong in adapter acceptance. No results code was changed or live athlete results inspected.

## Local uncommitted changes

- Added the contract, this handoff and the normalized fixture.
- Updated `docs/state/current-state.md`, `docs/state/combine-adapter-source-map-2026-09-06.md` and `docs/state/sparq-combine-journey-plan-2026-09-06.md`.
- Added the output contract and refreshed the output plan.

Existing writer/branch/HEAD remain `work/sparq-agent-review`, `codex/athlete-home-first-value`, `6c7e649ce5154f211401ed2e4af03d9691366194`, origin `joeygrant55/GMTM-Agent-SDK`. Prior source edits remain in place. No runtime behavior change, commit, push or deployment occurred. Infrastructure and production approval boundaries remain unchanged.

## Completion and next action

This checkpoint completes exact public event/task discovery, not the full adapter or authenticated flow. Verification passed for two events, eighteen distinct tasks, required background-field counts of 11/10, preservation of the adult dash conflict, exclusion of personal/session fields, source/fixture hashes, seven documents/output copies and local links/whitespace; `git diff --check` passed. Receipt: task `work/sparq-usaf-events-2026-09-06/verification.json`. No unrelated application tests were rerun for this source/fixture intake.

Next: use the fixture to implement owner-scoped current-event state and per-activity progress; preserve partial/unknown/conflicting rules, and test return refresh. Resolve policy conflicts before whole-program completion or precise-deadline claims. Trace saved answer keys and junior account behavior before live acceptance.
