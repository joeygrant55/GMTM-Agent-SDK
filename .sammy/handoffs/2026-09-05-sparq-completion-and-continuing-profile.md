# SPARQ: complete the combine, then continue the athlete relationship — 2026-09-05

## User direction
Joey explicitly wants SPARQ to help athletes COMPLETE the current USA Football digital combine, then continue working with them and enable profile sharing with other coaches to create further opportunities. This supersedes the prior assistant recommendation to restrict Agent introduction to after submitted results. Charles's promotion still enters the existing GMTM combine flow; >500 remains a goal, not guaranteed participants or Agent users.

## Product contract
Optional early Agent assistance during GMTM registration/participation, useful with ZERO results. Preserve original task flow and carry identity + event. First job: help finish actual requirements. Next: athlete-controlled reusable performance/film profile and sharing. Then: relevant sourced opportunities, athlete-reviewed introductions and meaningful follow-through. Track combine completion and staff effort plus post-completion activity, sharing and documented coach responses. Anonymous link opens are not coach interest. Preserve distinct submitted / requirements satisfied / reviewed / selected states.

Updated authoritative launch brief in place: outputs/sparq-usa-football-cohort-test-2026-09-04.md (revised September5). This avoids adding another competing launch plan.

## Read-only implementation findings
- claims_api.mint_claims accepts explicit user_ids + event_id; numeric results are not required. Bootstrap can create a workspace from GMTM identity with no results.
- bootstrap sport detection currently depends partly on result event metadata and can fall back to Football. Early flag-combine starters must get sport context from actual event metadata, not inferred from missing results.
- redeem_claim returns event_id, but frontend claim redemption discards it when routing /home/inbox. Preserve durable event context in next implementation so zero-result athlete sees active combine steps instead of unrelated profile work.
- Reusable core profile URL identified by backend agent: https://gmtm.com/athletes/{user_id}, resolves to named /feed route. Core respects public/coaches/private profile visibility. Sharing a URL alone does not make it public; preserve athlete choice and confirm intended coach access.
- Agent search_api returns a /profile/{id} URL rather than verified /athletes/{id}; alias behavior not checked live. Public Agent search visibility also needs alignment with core before exposure. No production behavior tested.

## Status and boundaries
No additional application source changes made during this clarification turn. Existing local branch codex/athlete-home-first-value remains at base6c7e649 with five uncommitted frontend files and prior handoffs. Existing TypeScript/14 browser assertions cover that earlier local home slice only, not completion guidance or safe sharing. No deployment, push, external message or production data mutation. Control Tower handoff and repo handoff are local/uncommitted. No existing docs/state/current-state.md found in earlier inspections.

Next implementation: preserve event-aware identity for zero-result starters, close existing ownership gap, add task/submission reconciliation, then reuse visibility-controlled profile sharing. Do not replace actual requirement progress with metric counts or link-click completion.
