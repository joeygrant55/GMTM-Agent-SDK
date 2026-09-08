# Fable handoff reconciliation and live GMTM source check

September 6, 2026. Existing Codex writer/checkout/branch retained: `work/sparq-agent-review`, `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`. Joey supplied Fable's handoff at `/Users/joey/Desktop/gmtm-code-research/sparq-live-validation-handoff.md`, requested Railway login/link/read-only validation, and identified his GMTM Chrome profile/GitHub SSO.

## Completion contract for this continuation

Reconcile Fable's claims with actual receipts and source; use only the approved GMTM host and existing read-only account for user 2/adult event 1318; distinguish source validation from Railway identity, auth, model and deployment acceptance; establish Railway CLI access through the normal user-authorized login; read actual service configuration before treating the suspected pre-prod setting as confirmed. No production writes, deployments, proxy enablement, database-account changes, AWS operations or source-code publication are included. Preserve all application edits and the current checkout location.

## Verified live

Root executed the actual current `_public_events`, `_activities`, `_submissions` and `project_activity` helpers in a guarded read-only GMTM transaction. Result: server handshake reports MySQL 8.4.11; event 1318 has nine public activities; user 2 has zero visible submissions and zero activities with required fields present. Three SELECTs executed, followed by successful rollback/close. Public metadata selection includes both supported events; activity and personal submission reads are fixed to 1318/user 2. No user lookup, other-athlete submissions, source writes, main import, model calls or Railway data read occurred.

The successful private receipt is in the enclosing task workspace: `work/sparq-live-reconciliation-2026-09-06/gmtm-source-live-user2-adult-retry.json`. It explicitly records `clerk_link_verified:false` and `deployed_endpoints_verified:false`, and stores bounded task IDs/states/counts plus source hashes. The first receipt, `gmtm-source-live-user2-adult.json`, records a preconnection configuration rejection and is retained.

Root also read the deployed backend's public `/health` and `/openapi.json`. Health returned healthy with Agent/GMTM configured flags and auth enforced; its implementation checks variable presence, not actual DB reachability. OpenAPI contains neither `/api/combine/current` nor `/api/combine/help`; these remain local uncommitted features. Receipt: `work/sparq-live-reconciliation-2026-09-06/public-deployment-metadata.json`.

## Local validation artifact

`work/sparq-live-reconciliation-2026-09-06/verify_gmtm_side.py` is an operator artifact outside the application repo. It fixes the host to db2-dev, the account to gmtmread, athlete to 2 and event to 1318. Only a new private receipt path is accepted. It imports the reviewed helper modules and existing read-only query guard, with no fake Clerk mapping or full application startup.

The existing credential file contains two DB_USER entries; the first is the documented gmtmread account, while generic dotenv loading selects a different later entry. The first attempt safely stopped before connection. The reviewed retry uses dotenv's parser to preserve Fable's documented first-user selection, requires exactly one nonempty password binding, rejects parse errors/ambiguous passwords, preserves literal characters and does not interpolate or mutate environment values. No actual credential value was printed or saved. No existing credential file was modified.

Twenty-eight offline tests passed using actual helpers/transaction guard and fake connections, including duplicate-user selection, forbidden later-user substitution, ambiguous passwords, parse errors, rollback/close failures and receipt privacy. Root reviewed the frozen code before live execution. Frozen artifact SHA256: `18b259641e59becf7cdc4f5cf6c7eb9b3fcd7ef2b0276068216af6b7e8364436`; test SHA256: `067898043ff9bd0056d790a8868ac0f5231e4b419309f47116aa252a57040091`.

## Fable evidence corrections

- Fable's raw GMTM receipt supports the underlying event/task/count observations; it does not prove actual local adapter execution or Railway identity. Root's successful source-only receipt adds adapter evidence, still not ownership/auth acceptance.
- Fable's descriptions of existing-owner-only connection and the new combine endpoints refer to local uncommitted code. They are not proven deployed behavior. The live OpenAPI check confirms the new endpoints are absent.
- A Google Cloud source IP in old RDS logs is insufficient to identify this backend's active DB_HOST. The supplied handoff does not include a current Railway host observation. Do not report a confirmed outage or make a speculative host change.
- The handoff asserts SELECT-only grants; its supplied receipt does not contain grants evidence. This run relied on explicit read-only transactions and fixed SELECT guards, and does not claim a fresh privilege audit.
- The original text receipt is mode 644 within a mode-700 receipts directory; newly generated operator receipts use exclusive 0600 files.
- Avoid raw Railway variable output, which includes secrets/credential URLs. Read variables into an in-memory subprocess result and emit only selected nonsecret keys or presence flags. The original shell wrapper strips quotes/spaces; the new source-only artifact preserves parsed literal credentials instead.

## Railway authorization and next action

CLI 5.49.2 was installed/invoked through the requested npm package. Cached binary: `/Users/joey/.npm/_npx/739c187f0ba6f7b9/node_modules/@railway/cli/bin/railway`. The initial browser opened in slateworks.io, where Railway was signed out. Root switched through Chrome's Profiles menu to GMTM, followed GitHub SSO, and Joey completed sign-in. Both five-minute localhost callback attempts expired without CLI completion; Joey saw a 127.0.0.1 error on the first. Device-code login is now pending in the normal Railway activation flow. Do not persist temporary device codes or authorization URLs in handoffs.

After authorization, confirm `whoami`, identify the actual SPARQ project/environment/backend, link the checkout if needed or use explicit IDs, and safely read only DB_HOST plus connection metadata. Existing user instruction permits correcting an actually observed pre-prod DB_HOST to db2-dev; it does not justify a speculative edit or unrelated credential/deployment changes. Confirm the exact application effect and existing deployment boundary before applying any change.

Check for an existing MySQL proxy, or prefer an existing private-network SSH path where available. Official current Railway docs describe piped-stdin remote commands and explicit project/service/environment IDs, but SSH may require a registered key. No new proxy/key is authorized by this handoff. A proposed ephemeral remote bootstrap for the current local reader must be implemented/reviewed before use; deployed code is older, and Fable's local gmtmread file does not exist remotely by assumption. Require actual sentinel/source-hash receipts, not exit code alone. Relevant primary docs: https://docs.railway.com/cli/ssh and https://docs.railway.com/cli/run.

Then run the full two-database operator check for user 2/event 1318, reporting linked/unlinked/ambiguous accurately. A missing link must not be created during validation. Live Clerk/model acceptance and deployment of the new build remain subsequent explicit gates.

## Files and boundaries

Application source is unchanged from the previous verified build (29 backend source/test hashes rechecked). New artifacts/tests/receipts live outside the application repo; only current-state routing and this handoff were added/updated inside it. Prior implementation remains uncommitted. No move, commit, push, service linking, proxy change, credential-setting change, production write or deployment occurred. No other clone was edited. Existing Python dependencies from the home checkout were reused without modification.
