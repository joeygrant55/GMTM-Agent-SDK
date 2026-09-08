# Local signed-in combine acceptance

September 7, 2026. Same Codex writer, checkout, branch `codex/athlete-home-first-value` and HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`. Joey asked to continue after the Railway check. The [completion contract](../../docs/state/live-combine-browser-contract-2026-09-07.md) covers real Clerk → current-combine → bounded AI help in an isolated local server.

## Current result and next action

Local preparation and unauthenticated boundary verification passed. The existing SPARQ sign-in page is ready at **http://localhost:3218/home/inbox?event_id=1318**. Joey was asked through the input panel to sign in with his existing SPARQ account. The Codex browser-panel open request returned `queued`. The test browser remains signed out at this checkpoint. No current-browser match to user 2, authenticated checklist response, provider generation or full journey acceptance is claimed.

After Joey signs in, inspect the actual browser and redacted server receipt. Verify the existing authenticated subject resolves uniquely to user 2, the adult card shows nine activities and zero submissions, a task-specific help question streams a grounded answer and `done`, a second question respects source limitations, and refresh preserves the active event. Inspect the GMTM destination without navigating a potentially write-capable authenticated GMTM route. If identity differs, stop that personal-data path; do not create or reassign a link.

## Verified this continuation

- Fresh branch, remote, HEAD, status, local AGENTS/current-state and Control Tower operating contracts read. Existing application edits preserved.
- Railway auth configuration and live Vercel sign-in page agree on the Clerk development instance. The Vercel CLI is signed in. Live alias `sparq-agent.vercel.app` resolves to project `frontend`, ID `prj_sJqoTAT5ncQV8fCDktWCM27I1mbD`, team `team_MWkBYZjV9ioig70uN2z1aXFe`.
- Only the two existing Clerk environment keys were decrypted for the frontend process, without a secrets/config file. Both had outer whitespace; the operator launcher normalizes only these key tokens in memory. The normalized public key exactly matches the live sign-in page and backend issuer. No Vercel/Railway value changed.
- Frontend snapshot contains 121 source/config/assets/test files; every source hash still matches the owned checkout. It points explicitly to `http://127.0.0.1:8118` before Next startup.
- The first Node startup stalled while reading the task checkout's Next dependency tree. That owned process was stopped. Reusing `/Users/joey/GMTM-Agent-SDK/frontend/node_modules` read-only resolved startup: all 13 direct dependency versions match, and Next 14.2.35 became ready in 1072 ms. This identifies a working runtime, not a proven cause of the original stall. No other checkout/dependency was modified.
- The real sign-in route compiled and returned 200. The browser rendered the Clerk form; no framework overlay or browser exceptions were observed. Screenshot inspected: `sign-in.png`.
- Nineteen focused offline harness tests passed independently and in root's run (0.48 seconds), with actual routes/readers and fake database/model/verified-claim seams.
- Live local rejection tests returned 401 for missing/invalid bearer tokens and 403 for a wrong Origin. Receipt showed zero source reads/successes, zero help requests and zero model calls after those tests.
- The existing Anthropic key successfully retrieved metadata for `claude-sonnet-4-6`. This confirms model-metadata access only; no generation or athlete data was sent by that check.

## Local runtime and guard scope

Backend: `127.0.0.1:8118`, one worker, no reload/access logging. Only the actual combine GET/help POST routers are mounted; no `main`, profile/claims startup, DDL, bootstrap, source writes or proxy to production. All requests require exact Host and Origin `http://localhost:3218`; real Clerk signature/issuer verification additionally requires exact `azp` and an unexpired session. The original identity lookup plus reverse uniqueness must map the authenticated caller to user 2 before GMTM access. Event 1318 is mandatory. Database factories use the existing read-only transaction/SELECT guard and rollback/close, with db2-dev/gmtmread and the already-existing Railway proxy. Shutdown waits for retained source workers.

The server allows at most five authenticated help attempts, using actual provider streaming and existing per-request limits. Other workspace/profile/inbox/badge routes return local 503, so their unavailable states are expected and are not backend production findings. The current card/help are independent of those routes. The test browser blocks `https://gmtm.com/*` and the deployed Railway backend origin. No authenticated GMTM continuation was opened.

Processes remain running for the requested human sign-in. Unified exec session IDs at this checkpoint: frontend `93390`, backend `99001`. Browser CLI session: `sparq-live-0907`. Use fresh process/port observations on resume; session IDs may become stale. Browser tool installed only in `/tmp/sparq-browser-tools-20260907/`; no project package change. Do not close unrelated browser sessions.

## Artifacts and uncommitted changes

All operator artifacts are in the enclosing workspace's `work/sparq-live-browser-2026-09-07/` (directory mode 700). Receipts use mode 600:

- `read_only_app.py`, `test_read_only_app.py`
- `launch_backend.py`, `launch_frontend.py`
- `frontend/` current-source snapshot and `frontend-source-hashes.json`
- `live-server-receipt.json` ongoing redacted counters; no token, Clerk ID, private answer or model text
- `provider-model-metadata.json`, `acceptance-checkpoint.json`, `sign-in.png`

Frozen harness SHA256: `424e8a0cf16123715a37522dff0d16bf4931ac2b72b28caea083546bcd346e90`. Tests: `39f8e7c8815cbdd96b4434ec6208400a91012bbac96057c9216fb08830a03f01`.

Inside the repo, this continuation adds the completion contract and this handoff, and updates `docs/state/current-state.md`. Application implementation remains unchanged and uncommitted. No commit, push, deployment, production record change, identity mutation, infrastructure change or deployed credential edit occurred. The signed-in/AI acceptance contract remains open pending the existing athlete login and subsequent checks.
