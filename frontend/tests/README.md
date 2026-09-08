# Isolated account-boundary checks

check-account-boundaries.cjs compiles the actual connection, claim, Quick Scan, outreach-draft and workspace-chat components and renders them with React 18 in headless Chromium. Set all three paths explicitly, using an existing dependency tree and Playwright installation:

```sh
SPARQ_TEST_NODE_MODULES=/absolute/path/to/frontend/node_modules \
SPARQ_TEST_PLAYWRIGHT=/absolute/path/to/node_modules/playwright \
SPARQ_TEST_RECEIPT=/absolute/path/to/component-receipt.json \
node frontend/tests/check-account-boundaries.cjs
```

Run from the repository root. The script does not install packages, load .env files or start Next.js. It intercepts browser requests, supplies only local synthetic assets and in-memory API responses, and closes Chromium in finally. The receipt records assertion names and hashes of the tested source.

Coverage includes failed/unconfirmed/mismatched connection responses, account and token switches, late async results, authenticated iteration, visible HTTP/SSE errors, retry and StrictMode. Stale response fixtures are otherwise valid so a malformed-response guard cannot mask a cancellation regression.

The profile-recovery matrix covers HTTP/network/JSON/schema failures in all three consumers of `by-clerk`, selected-combine recovery, retry, account-scoped draft state, wrong-owner workspace responses, rejection of the old unowned onboarding cache, and an account change while clipboard copying is pending. Workspace and college responses are synthetic. It does not send a real email, log real outreach, or establish that copying a draft means a coach received it.

These checks do not establish live Clerk authentication, actual backend/provider behavior, Next middleware, full workspace layout or phone usability. Run TypeScript separately against the current source as part of verification.

## Current-combine journey

Run `frontend/tests/check-combine-journey.cjs` with the same three environment variables and a separate receipt path. It compiles the actual home entry, claim handoff, combine card and full workspace shell, and generates CSS from the repository's Tailwind configuration. It saves screenshots at phone and desktop sizes beside its receipt.

The journey harness uses the public junior/adult task fixture with invented submissions. It checks profile/inbox-independent entry, event choice, submission/evidence distinctions, return refresh, request deduplication, failed refresh, stale account/event responses, source-text safety and phone navigation/help controls. Clerk, Next routing and API responses are synthetic, and every browser network request is intercepted. Existing chat Markdown is rendered as plain text by the harness. These are local component/layout checks, not live sign-in, a real GMTM upload, complete Next middleware behavior or physical-device acceptance.

## Explicit college research

Run `frontend/tests/check-college-research.cjs` with the same three explicit environment paths and a new receipt filename. It renders the actual college page, uses the real API wrapper with synthetic Clerk/Next/API interfaces, and controls polling timers in an isolated browser. No stylesheet/layout or full Next integration is claimed.

Checks cover truthful empty/unavailable research, absence of page-open AI prompts, rejected/accepted matching requests, bounded status checks, late/out-of-order reads and account/unmount cleanup. A legacy `complete` response can reload saved research but does not prove the newly requested job completed. Every service response is synthetic; no model, email, database or live API call occurs.

## Focused candidate policy and actual Next integration

`check-candidate-policy.cjs` uses `SPARQ_TEST_NODE_MODULES` and an optional new `SPARQ_TEST_RECEIPT` to exercise pure origin/route policy plus the compiled API helper. Denied operations must fail before token retrieval; callers cannot override redirect refusal.

`check-candidate-app.cjs` requires a new absolute `SPARQ_CANDIDATE_ARTIFACT_DIR` outside the checkout. It uses the recorded installed MacBook Node/Next/Python/Playwright runtimes without installing packages. It copies an allowlisted frontend snapshot (including middleware) without environment files, adds Clerk identity adapters only in that snapshot, and launches actual Next development routing/RSC with the real candidate ASGI app through `backend/tests/run_candidate_fixture.py`.

The Python fixture scrubs environment, blocks live connections/providers/jobs and accepts fixture changes through stdin only. The actual app has no fixture HTTP routes or auth bypass. Locally signed JWTs use a local JWKS adapter; database interfaces and help output are synthetic. Node DNS/socket/fetch instrumentation and browser interception permit only the selected loopback services. These are test guards, not an OS firewall.

Receipts must include source/overlay hashes, route observations, zero forbidden backend/provider attempts, closed synthetic connections and independent service/browser cleanup. A pass establishes development integration, not a production build, live Clerk/database/model acceptance or a real GMTM upload. Full-app runs use distinct artifact directories and preserve failed-run evidence.
