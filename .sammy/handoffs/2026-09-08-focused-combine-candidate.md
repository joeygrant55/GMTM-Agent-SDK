# Focused combine candidate — September 8, 2026

## Outcome and ownership

Joey authorized continuing SPARQ product implementation. Codex implemented and reviewed the [candidate contract](../../docs/state/combine-candidate-contract-2026-09-08.md), following local commit `c27c708` on `codex/athlete-home-first-value`. This handoff belongs to the next local candidate commit; its exact hash is recorded outside the repo in `../sparq-combine-candidate-2026-09-08/commit-receipt.json`. No push, deployment, live service configuration, production data/infrastructure change or renewed live-test allowance is included. Fable/Audit/portfolio lanes were not changed.

## Product changes

- Explicit `NEXT_PUBLIC_APP_SURFACE=combine` selects a focused home/inbox shell: event-specific requirements, current progress, GMTM continuation and requested help. The candidate does not mount the legacy sidebar/badges, inbox/artifacts or college/recruiting panel. Default legacy composition remains.
- Existing-connection recovery is GET-only and account-scoped. Candidate redemption stays in the combine workspace even for an older event or optional workspace failure. Unavailable public invitation checks now stay unknown instead of incorrectly declaring an invalid link.
- Shared pure frontend configuration requires an explicit canonical backend origin. Candidate API operations/methods are checked before getting a token, and redirects cannot be followed. Public server claim lookup uses the same transport. The ignored Next TypeScript duplicate was removed; Next14 uses the JavaScript config. Narrow gitignore exceptions ensure the shared source and declaration are committed despite the Python `lib/` rule.
- Middleware denies unrelated pages, same-origin APIs and static-looking legacy paths before Clerk/handlers. Candidate emits no API rewrite. Next's optimizer runs before middleware, so the candidate also sets `images.unoptimized=true`; both local and external optimizer requests return404.
- Separate `backend/candidate_app.py` registers five existing handler functions plus health. It validates configuration without service initialization, requires enforced authentication and strict candidate subject/authorized-party claims, and does not expose broad legacy routers, minting or schema/docs endpoints. Claim preview/redemption write Agent records; GMTM remains read-only. Ordinary main app auth/routes are preserved.

The [runbook](../../docs/state/combine-candidate-runbook-2026-09-08.md) records configuration and execution boundaries. Frontend/backend surface settings must be paired and verified during a future release; a frontend flag alone cannot restrict a separately deployed legacy backend.

## Verification

Artifact directories are siblings of this checkout, local-only:

- `../sparq-combine-candidate-2026-09-08/`: backend-suite-01.txt (**578 passed**, one dependency deprecation warning); account-boundaries-03.json (**175**); combine-journey-02.json (**89**); combine-help-02.json (**59**); college-research-02.json (**42**); policy-02.json (**66** configuration/transport checks); focused-ui-typecheck-02.json (**103 files**, zero diagnostics). The final Next image configuration was added after this TypeScript snapshot and verified by the policy and actual Next runs; TS/TSX source did not change afterward.
- `../sparq-candidate-full-next-2026-09-08-run3/`: receipt.json, backend-receipt.json, runtime/overlay/source hashes, HTTP boundary receipts, logs and desktop/phone/phone-help screenshots. **37 behavior assertions +1 source-preservation assertion +5 separate safety assertions passed.** Actual Next14.2.35 development middleware/RSC/browser hydration connected to the real candidate ASGI entry with synthetic interfaces.
- Actual journey: unlinked recovery → public signed invitation rendered by RSC → authenticated redemption → adult0/9 checklist → fixture source update →1/9 refresh → requested SSE help → existing-link recovery. Older event999 plus optional workspace failure reaches event choice in the focused surface. Phone help and Escape focus, selected-event navigation, encoded/static-suffix/API/method exclusions and middleware-header spoof denial pass.
- Backend receipt: 15 requests (including denied probes); preview1, redemption2, current5, recovery2 and help1. All22 synthetic connections closed, one synthetic answer, zero real provider calls and zero forbidden attempts. Node guards recorded no denied service attempt; browser blocked only external Google-font assets. No browser runtime errors.
- All121 frontend and51 backend captured files remained byte-identical through run3. Both owned children exited0, backend received graceful stdin stop, browser closed and ports62881/62882 closed. Backend reviewer independently confirmed no listeners.
- Independent backend receipt review: run3/independent-backend-review.json. UI/code/visual review: candidate-artifact/focused-ui-final-review.json. No blocking issue at1440×1000 or390×844. The full-page desktop PNG includes blank space below the fixed viewport frame; full-document vertical-scroll polish is not established.

The synthetic full-app runner lives in frontend/tests/check-candidate-app.cjs and backend/tests/run_candidate_fixture.py. Its external allowlisted snapshot includes the real middleware and excludes environment files. Clerk adapters are snapshot-only; real locally signed RS256 verification runs against a local JWKS adapter. Database connections and provider output are replaced at declared interfaces, including a no-results combine-results adapter during optional workspace bootstrap. No fixture HTTP route or product authentication bypass is added. Node/Python connection guards and browser interception are instrumentation, not an OS firewall.

## Retained failures and corrections

Run1 failed at the framework image-optimizer boundary; the application-level candidate config now disables that proxy. Its backend receipt also caught a swallowed urllib3 import-time IPv6 capability bind. The IPv4 fixture now temporarily suppresses that dependency probe and restores socket.has_ipv6 before app imports; all guards remain. Separate attribution and zero-attempt receipts are retained in urllib3-probe-attribution.json.

Run2 passed the business flow and safety checks but immediately tested phone visibility before the React open-help effect settled. Run3 uses a visibility wait and passes without UI changes. Failed-run artifacts were preserved. All completed/failed test paths drained their owned services; forced external interruption remains a manual owned-process cleanup case.

## Next and limits

This is a verified local development candidate, not production deployment or live athlete acceptance. Before a pilot: bound profile connector read/write timeouts used by claim/recovery/bootstrap; verify production build/container entry packaging; review paired candidate configuration; complete real Clerk/schema/current-source ownership and actual GMTM submission-return gates under an explicit new live allowance. Guardian delegation is still not implemented. Existing budgets/ledgers and GMTM infrastructure restrictions remain in force.

The commit includes only the candidate app/UI/configuration, focused tests/fixture runners, adapted existing test loaders, README/instruction pointers, runbook/contract/current state and this handoff. Exact staged paths and source hashes are retained in the local commit receipt. No prior user changes were present at baseline; no unrelated changes were included.
