# Next adult-combine candidate package

September 7, 2026. Joey resumed GMTM/SPARQ work while the separate audit proceeds, then chose to tell Fable to release PR 73 and defer database deletion decisions. This product package is local work in the existing Codex checkout. It grants no release, infrastructure action or new live-test allowance.

## User outcome

An athlete entering the adult combine keeps that division while moving through the supported workspace, gets truthful requirements/progress and help, continues to GMTM to submit, then returns to refreshed progress. The existing junior GMTM flow and real guardian acceptance remain separate.

The first small fix is complete: a supported explicit `event_id` survives the sidebar's **My next move** link. The original link lost that context, allowing a saved junior claim to override an adult URL. The corrected actual-click journey passed 89 checks plus TypeScript; ordinary navigation and other sidebar destinations remain unchanged. This is local component verification, not deployed behavior.

The first backend package is also complete locally: implicit schema and dotenv work has been removed from actual app composition, with separate explicit Agent preparation and 481 passing offline tests. See the [startup handoff](../../.sammy/handoffs/2026-09-07-safe-app-startup-and-cleanup-guidance.md). Full candidate acceptance is not complete. Next is separating combine workspace creation from automatic matching, followed by candidate configuration and the supported route/API set. The original planning findings below describe the starting point; import-time issues are resolved in local source, while request-side and full-app gates remain open.

## Next bounded implementation

Make the actual backend safe to compose for an isolated candidate before claiming full-app acceptance. Source inspection found:

- `main.py` imports profile, artifacts and claims modules that immediately attempt Agent DB schema setup. The helpers catch their failures; a passing import can hide attempted connections.
- Several modules implicitly load dotenv files at import. Normal app composition needs an explicit configuration policy so a local candidate cannot accidentally pick up live credentials.
- Successful claim redemption may bootstrap a workspace and immediately start college matching. That is additional model/database work outside the focused combine-help allowance.
- The frontend combine shell also fetches legacy workspace/profile/artifact/badge APIs and exposes recruiting routes. The earlier restricted test backend did not cover all those reachable paths.

Implementation sequence: remove implicit schema work from ordinary app composition and provide explicit Agent-schema preparation; make candidate configuration explicit; separate workspace creation from optional matching; then define and enforce the supported frontend/backend route set. Keep GMTM reads authoritative and existing ownership checks intact. Do not silently substitute an environment flag for actual source/network isolation.

Acceptance for this next package: import and compose the real app under external-access guards, asserting zero attempted DB connections, provider work and background jobs; exercise its actual registered combine/recovery/help handlers with synthetic service interfaces; show no silent live-backend fallback or legacy calls in the supported frontend route. Existing routes outside the candidate must retain their documented behavior or fail truthfully. Document schema and genuine identity/session dependencies rather than manufacturing acceptance.

This is a proposed implementation sequence, not a claim that full startup, real saved-submission return, production schema or deployment has passed. Existing exhausted read/model ledgers remain unchanged. The prior component journey intercepted GMTM navigation, so a true navigation-return test remains an explicit subsequent gate.
