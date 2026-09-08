# Current-combine local implementation — September 6, 2026

## Outcome and completion contract

The [bounded current-combine contract](../../docs/state/current-combine-build-contract-2026-09-06.md) is locally implemented and verified in the existing Codex implementation lane. The [larger athlete journey milestone](../../docs/state/sparq-combine-journey-plan-2026-09-06.md) remains open for live acceptance and the remaining product capabilities below.

Repository: `joeygrant55/GMTM-Agent-SDK`, branch `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`. All changes remain uncommitted. No push, deployment, production data change, external message, billing action, core GMTM edit or infrastructure mutation occurred.

## Implemented behavior

- `GET /api/combine/current?event_id=` is authenticated and read-only. It resolves the uniquely linked caller and public USA Football events 1317/1318 under organization 249002. Unknown or ambiguous ownership cannot expose another athlete's submissions. Explicit public requirements can be read before linking; unavailable personal counts remain null, never fabricated zeroes. One distinct owner-matching redeemed claim may supply default event context; otherwise a choice is required.
- Definitions come from the source tasks, independent of numeric results. Latest visible submissions are chosen per task using timestamp and ID. The projection exposes submitted/unknown/missing-field/present-field observations without personal answer values. It covers background flags, video-only squat, separate playing highlights, both shuttle directions and exact saved `type:title` keys. Malformed definitions or database failures cannot become successful empty progress.
- Home entry no longer waits on `/profile/by-clerk` or redirects zero-profile athletes into recruiting onboarding. Supported redeemed event context reaches the inbox even when workspace bootstrap is not ready. Invalid event queries retain their invalid context and lead to a choice.
- The current-combine card loads independently of profile/inbox failure. It shows activities and organizer instructions, continues through the existing GMTM event and refreshes on foreground return/manual request. Account/event changes abort or ignore late snapshots. Failed refresh retains a labeled last successful check. No optimistic completion or upload side effect occurs.
- The phone shell collapses navigation and chat with accessible controls; the primary GMTM action appears in the first viewport at the tested phone sizes. The former result-derived starter is removed, while performance evidence remains below the card. Organizer instructions are escaped plain text.

Joey's clarification is incorporated: deadline display and adult dash labels are known, nonblocking platform bugs; highlights are separate footage of the athlete playing. The displayed deadline is USA Football's sourced September 21 date, without a precise countdown. The raw configured timestamp is preserved and no UTC/Eastern diagnosis or source repair is claimed. The adult dash's exact source key is retained internally; only its known incorrect missing-field caption is presented as a 20-yard dash time for event 1318/task 4907.

## Verification and review

Root ran the combined offline backend suite: **182 passed**. The existing actual-component account/claim harness passed **47 checks** with its tested bytes unchanged afterward. The new actual-component journey harness passed **75 checks** using React 18, generated repository Tailwind and the full workspace shell at 360, 390, 430 and 1440 pixels. Root inspected the final 390/1440 screenshots. TypeScript passed on a current-source snapshot using the existing dependency tree; no package installation or full Next build occurred.

Root also verified the actual FastAPI app contains exactly one authenticated GET route at `/api/combine/current` under the offline import guards. Twelve actual endpoint responses, generated through the fixture-backed FastAPI handler, were accepted by the actual transpiled frontend parser: both divisions with zero/all/partial/unknown/unlinked states and linked/unlinked event choice.

Independent backend review checked fixed-revision core schema and form source, ownership, SQL restrictions, latest-attempt semantics and answer privacy. Independent frontend review identified invalid-home-event substitution and contradictory parser-state acceptance; both were corrected and covered by the final browser run. Root additionally corrected API response key/count mismatches and moved the phone CTA above secondary controls. No reviewed blocker remains within this bounded local slice.

Receipts in the task workspace:

- `work/sparq-current-combine-2026-09-06/backend-suite-receipt.json`
- `work/sparq-current-combine-2026-09-06/account-boundary-receipt.json`
- `work/sparq-current-combine-2026-09-06/typecheck-receipt.json`
- `work/sparq-current-combine-2026-09-06/router-wiring-receipt.json`
- `work/sparq-current-combine-2026-09-06/api-ui-contract-receipt.json`
- `work/sparq-current-combine-2026-09-06/final-verification.json`
- `work/sparq-combine-frontend-2026-09-06/journey-receipt.json`

The final receipt compares tested source hashes with the closing source. Four scoped root-entry hashes also confirm `frontend/middleware.ts` and the preexisting `backend/claims_api.py`, `profile_api.py`, `agent_api.py` did not change during this slice. This is a scoped preservation receipt, not a full-machine or all-workspace audit.

## Verification limits and next action

These checks use synthetic identity/submissions, fake database behavior and intercepted browser requests. They do not establish actual MySQL execution/query plans/indexes, deployed schema, real Clerk/GMTM session continuity, physical-device uploads or observed athlete outcomes. The public task configuration is real; the athlete displayed in previews and the submissions are invented fixtures.

Next: verify a controlled current athlete's GMTM requirements/submissions and round trip against the new adapter in an appropriate integration environment, retaining the earlier identity/conversation live gates. Confirm the junior guardian/child actor and external USA Football Athlete ID validity separately. No registration, eligibility, review, selection, program completion or conversion lift is inferred here.

The generic chat remains the existing recruiting assistant; this slice provides deterministic organizer instructions, not a new conversational combine tool. The next product integration should give conversational help this same authorized snapshot and remove reliance on unrelated recruiting assumptions. Durable event preference across navigation/devices, safe profile sharing, ongoing development, outreach delivery, jobs, measurement and monetization remain subsequent work. Current selection is URL/claim based. The existing claim endpoint still runs historical workspace bootstrap before responding; the new read endpoint itself does not invoke it.

## Uncommitted changes in this slice

New implementation/test files: `backend/combine_api.py`, `backend/combine_requirements.py`, `backend/tests/test_combine_requirements.py`; `frontend/app/home/components/CurrentCombineCard.tsx`, `currentCombine.ts`, `WorkspaceShell.tsx`; `frontend/tests/check-combine-journey.cjs`.

Existing files updated: `backend/main.py`; `frontend/app/home/HomeClient.tsx`, `layout.tsx`, `components/InboxFeed.tsx`, `components/AthleteStartingPoint.tsx`; `frontend/app/claim/[token]/redeem/page.tsx`; both test READMEs. State/contract/plan documents and this handoff were added or updated. Earlier identity/security and home changes remain uncommitted as described in their own handoff; the git diff against HEAD includes those prior batches as well.

Synthetic phone/desktop previews are copied to `outputs/sparq-current-combine-phone-2026-09-06.png` and `outputs/sparq-current-combine-desktop-2026-09-06.png`. No other SDK checkout or Control Tower file was edited.
