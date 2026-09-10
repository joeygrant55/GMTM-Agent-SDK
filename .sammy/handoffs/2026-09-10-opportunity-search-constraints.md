# Opportunity search focus, travel and participation

September 10, 2026. Status: implemented, independently reviewed and verified locally; ready for the local checkpoint. Local checkout only. Root will record the final commit separately in `../sparq-opportunity-search-2026-09-10/commit-receipt.json`.

## Completion contract and ownership

Following Joey's instruction to keep moving autonomously, expand the existing reviewed opportunity collection using explicit athlete search choices, distinguish team competitions from individual evaluations, and preserve the useful profile-to-inquiry journey. Complete backend, component, actual-app, production-build and visual checks; retain raw evidence and confirm cleanup. No speculative fit scores, invented events, automatic research, outreach or live mutation.

Codex owns this SPARQ checkout on `codex/athlete-home-first-value`, remote `joeygrant55/GMTM-Agent-SDK`; starting HEAD `2e2539ccbee0c8883b149bcb4e67406e2a803ffd`, initially clean. Root implemented the backend, catalog integration, actual-app journey and integration/docs. Assigned agents implemented the opportunity controls/component tests, researched primary organizer sources and backend cases, and reviewed the authentication contract and parser. No Fable or other active checkout was edited.

## Product result

- Explicit **National team / Places to compete / Both** search focus. Optional US state/DC travel destination and individual/team participation live under **Refine search**. Category/format retain their existing choices. Nothing is inferred from a goal, address or profile media.
- The query accepts seven bounded fields; old four-field requests default to national-team focus, any participation and no destination. Changing any filter withholds old cards until another explicit Find, including changing away and back. Account/link changes reset every filter and abort old results.
- Five reviewed records: the two original USA Football routes, two upcoming Florida team tournaments and one public International Flag League inquiry about team access. These competitions do not establish national-team or Olympic qualification. The [source review](../../docs/research/adult-flag-events-2026-09-10.md) preserves official pages, actual venue cities, cost basis, deadlines and unknowns.
- A solo in-person search excludes team tournaments; a remote organizer inquiry can help ask about free-agent/team access without claiming that registration or placement exists. A selected destination filters in-person venues only. Remote information remains useful across destinations. Up to three matches are shown with an explicit count when truncated.
- Event cards keep dates, actual venue and a short team requirement. **Costs, eligibility & sources** opens complete, unabridged payment terms, eligibility and numbered evidence. No substring-derived prices or dates. Assessment/contact cards retain their previous presentation.
- Source-bound actions retain the athlete's existing goal and eligible featured work. Keep my draft preserves exact text; only explicit replacement prepares a different organizer inquiry. Exploring never creates an implicit save, model call or source refresh.
- Strict source projections require published eligibility facts for individual/team labels and published location for state filtering. New organizer URLs use only canonical `iflag.org`/`www.iflag.org`. No broad registration-host allowance was added.

## Review and verification

Evidence is outside Git in `../sparq-opportunity-search-2026-09-10/` and sibling `sparq-opportunity-search-app-2026-09-10-*` / `sparq-opportunity-search-build-2026-09-10-*` directories. Raw failed attempts are retained. Jobs ran serially under finite external supervision.

- **256 backend tests passed**: opportunities, profile candidate routes/package, profile acceptance and launcher. One existing Starlette deprecation warning. No backend source changed after that pass.
- Independent review found frontend participation validation weaker than the backend. Root added the same source-backed eligibility condition; component checks cover both team and individual rejection when evidence is missing.
- Actual-app attempt 01 stopped at 65 checks when Playwright could not retrieve a response body. The harness now captures it immediately when the response arrives, before subsequent UI waiting. No application error was observed; the failure was not waived. Attempt 02 passed **147 journey checks plus five safety assertions**.
- Component attempt 01 passed **371 checks**. Production build 01 passed before final parser/visual changes and is retained as intermediate evidence only.
- Desktop/phone inspection prompted a final event-only reduction of duplicate relevance/team text and long payment paragraphs. Dates and venue stay visible; all full facts remain in the drawer. Final verification results follow below.

Final accepted results: **256 backend tests**, **373 component checks** (run 02), **153 actual-app journey checks plus five safety assertions** (run 03), and the real Next production compile/typecheck/unauthenticated same-artifact start (build 02). Final desktop and 390-pixel phone screenshots were visually inspected; event cards retain dates/actual venue, omit duplicate explanations and have no horizontal overflow. The actual-app journey opens both event drawers and verifies exact full payment/eligibility text and keyboard focus return. Assessment/contact paths and draft-preserving transitions still pass.

`source-reconciliation.json` confirms **135 frontend files** match both accepted app/build snapshots, **92 backend files** match the actual-app snapshot, all **16 component sources** match, and seven recorded backend/test inputs remain unchanged. Both accepted browser receipts have no browser errors or unexpected network denials. The build reports no denials or modified snapshot inputs. All owned test groups and ports are closed; every external supervisor reports its harness group dead, including the failed attempt. No preview was left running. Policy source was unchanged and its prior 108-check result was not reclassified as a fresh run.

## Authentication work and next milestone

The [GMTM authentication implementation contract](../../docs/state/gmtm-auth-implementation-contract-2026-09-10.md) verifies the installed Clerk ticket capabilities against official docs and identifies existing-link, new-account, conflict, revocation and parent/child boundaries. It is a specification; no auth code or live provider operation was implemented.

Independent architecture review split the first work into a small offline existing-link authorization planner (`backend/gmtm_auth.py` and its tests): validate self-owned adult authority and exact linkage, then decide matching-session reuse, ticket-required, account-conflict or deny. Inject clock/link reader. Complete that matrix before distributed stores, provider issuance or browser routes. The current Clerk-ID dependency interface can remain while session/grant checks are added at its boundary. Agent MySQL and GMTM Redis ownership, served deployment commits and instance settings remain owner-confirmation items for later integration.

## Runtime state and limits

The previous real-owner preview at localhost:64493 expired as scheduled. Its supervisor reports both owned groups dead and unchanged sources; permitted connection checks confirmed ports 64493/64494 closed. This turn did not restart it or repeat real identity acceptance. Current acceptance is synthetic Clerk/SQL/provider fixtures through actual Next/ASGI, plus a real production compile/typecheck and unauthenticated same-artifact start. It does not prove real athlete participation, paid value, configured SSO or a deployed release.

No push, deployment, GMTM source/data change, AWS change, message, registration, payment, provider request, account/link write or live workspace save. The three-save founder allowance remains exhausted; any separately launched founder view must stay read-only with PATCH cap zero until an explicit new scoped allowance.

This is a manually reviewed collection, not autonomous discovery. New organizer evidence expires September 17 at 17:41:56 UTC; the two original USA Football records retain their earlier September 17 16:30:06 UTC expiry. Sources require an actual re-review before timestamps are refreshed. No recurring freshness process was activated. Results/filters are not persisted across full reload. Existing explicit saved-draft behavior remains.

Release requires matching frontend/backend because response participation is required by the new parser. Current source/test and local commit evidence is not permission to deploy or recruit. Next implementation is the small auth planner above, followed by independently reviewed ticket/session and browser integration; genuine adult pilot and commercial demand remain separate acceptance gates.
