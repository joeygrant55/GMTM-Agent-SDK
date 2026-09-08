# Focused combine candidate completion contract

Owner: Codex. Baseline: `c27c708` on `codex/athlete-home-first-value`. Local implementation and verification only; no push, deployment, infrastructure change or renewed live-test allowance.

## Outcome

A separately configured combine frontend and backend expose the supported athlete journey: invitation, authenticated redemption, recovery of an existing connection, event-specific checklist, explicitly requested help, GMTM continuation and refreshed source progress. Ordinary legacy routing remains available only in its normal surface.

Frontend `NEXT_PUBLIC_APP_SURFACE=combine` uses existing home/inbox/claim/connect paths with focused components. It rejects unrelated pages and all same-origin API/trpc routes before authentication or proxy execution. An explicit backend origin is mandatory; no implicit production fallback. Candidate API transport permits only the supported methods/paths at that origin, before acquiring a token, and rejects redirects. Normal legacy builds preserve configured routing.

Backend `candidate_app:app` registers only health and five business operations using the existing handlers: GET current combine, POST combine help, GET existing by-Clerk connection, GET claim preview and POST claim redemption. It does not mount legacy routers or expose minting. Startup configuration validation is pure and authentication is enforced. Claim preview records opened_at and redemption writes ownership/optional workspace data in the Agent database; this is not an entirely read-only surface. GMTM access remains read-only.

## Verification and completion

- Test origin validation, allowed routes/methods, direct and encoded legacy paths, same-origin API denial, and unchanged default legacy composition.
- Test candidate imports/lifespan without dotenv/database/provider work, exact route manifest and authenticated owner boundaries using synthetic interfaces.
- Exercise actual Next middleware, routes, layouts and browser rendering against the candidate backend with synthetic identity/data/provider adapters confined to the test snapshot/runner. Record source hashes and every test seam. Permit only intended loopback transport; no secrets or dotenv files enter the snapshot.
- Check phone/desktop composition, claim/recovery/event context, explicit help, fixture submission-return refresh, and absence of legacy workspace/research requests.
- Run relevant existing backend/component/type checks; review changes independently. Write a handoff, update current state and commit this package locally.

Passing isolated tests does not establish real Clerk/JWT acceptance, live database/schema readiness, model delivery, real GMTM submission or deployment readiness. A build flag is a product boundary; the test runner's connection guards provide test network isolation. Remaining real acceptance gates must stay explicit.
