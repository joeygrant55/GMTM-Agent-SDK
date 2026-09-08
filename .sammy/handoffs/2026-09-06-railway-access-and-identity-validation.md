# Railway access and identity validation

September 6, 2026. Continues the [Fable reconciliation](2026-09-06-fable-live-reconciliation.md) in the same Codex-owned checkout, branch `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`.

## Completion contract

Confirm Joey's completed Railway authorization, link this checkout to the existing SPARQ backend, inspect only relevant configuration through redacted summaries, and run the reviewed two-database read-only check for GMTM user 2 / adult event 1318 using existing connectivity. Do not create or change an identity mapping, open new network access, alter deployed credentials, deploy code, or operate on AWS. Keep all earlier implementation edits intact.

## Railway findings

The device authorization completed successfully. CLI 5.49.2 confirmed the signed-in account, and the checkout was linked to project `sparq-agent-backend`, environment `production`, service `focused-essence`. A subsequent status read confirmed the selected project and service. Only local CLI context changed.

Exact selected identities for repeatable operator calls:

- Project: `27aa6c0a-9218-49ac-a182-08f6fe36249e`
- Environment: `32a909ef-4bb6-4745-a0fe-aa86e7656b3c`
- Backend service: `0669f1fc-2cbe-473b-8c64-bc86f4594cf3`
- MySQL service: `c6becf80-b58f-4fa0-99c6-45f87f405756`

The current backend variable map already has `DB_HOST=db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com`. The suspected pre-prod setting is not present in this observation; no host correction was necessary. This configuration read does not itself prove the running application's connectivity. The deployed account setting is not `gmtmread`; it was not changed, and its privileges were not audited. The isolated GMTM validation instead uses the existing local `gmtmread` credential binding already verified in the prior source-only run.

The selected MySQL service already provides a public TCP proxy. Its private hostname, private port, database name, username and password exactly match the backend's Agent DB configuration. The public URL's host/port also match that service's proxy metadata. All comparison happens in memory. No proxy or SSH key was created and no raw variable output, connection URL or credential was saved.

## Operator artifact and evidence

Artifacts are outside the application repo under the enclosing workspace's `work/sparq-live-reconciliation-2026-09-06/`:

- `verify_railway_link.py` captures CLI variable JSON into process memory, validates exact project/environment/service identities and database binding, substitutes only the existing Agent DB proxy host/port for the local check, and reuses the reviewed GMTM credential parser and query/transaction guards.
- `railway-config-verified.json` records a successful configuration-only check at `2026-09-06T20:44:18Z`, with source hashes, safe boolean observations and no database connection.

The wrapper fixes athlete 2 and event 1318, accepts only an exclusive mode-0600 receipt path plus optional configuration-only mode, and never imports the full application. It uses read-only transactions and the existing SELECT guard, rolls back/closes connections and emits only a bounded projection. Its receipt distinguishes a database mapping from current-browser Clerk authentication and deployed endpoint acceptance.

## Full live result

`railway-live-user2-adult.json` records a successful observation at `2026-09-06T20:50:47Z`. The Agent database contains exactly one nonempty Clerk mapping for GMTM user 2, with reverse lookup resolving uniquely to that same athlete. The actual current `load_current_combine` reader then returned adult event 1318 with nine activities, zero submitted and zero with required fields present. Six SELECT queries executed across guarded read-only transactions. Rollback/close returned successfully for both connections. No identity was minted, redeemed, created or reassigned.

The task IDs and states match the earlier GMTM-only observation. This closes the two-database stored-mapping/source-reader gate for this designated zero-submission case. It does not establish the mapping's creation provenance, match the browser's current Clerk session, exercise an authenticated HTTP endpoint or validate claims/conversation writes.

Root reran all 70 focused offline tests in `test_verify_railway_link.py` successfully (0.10 seconds), after independent review found and root fixed validation of the private port before proxy substitution. Fourteen additional root smoke checks passed using synthetic configuration. These cover operator boundaries, not live identity or application behavior. The actual live result uses the real driver and current source in a separate process. Final frozen hashes:

- Wrapper: `800e8f2296848f0f4cec262e2dd166e6d68c3645ee3dc80b37bedbd3d4f7fc32`
- Tests: `f1d802a640653f277958c4d43c630b25861e5bbb155a1f7c729d2caae7f992ba`

The earlier configuration-only receipt intentionally retains the hash before the additional private-port guard; the live receipt contains the final tested wrapper hash. Application reader/requirements/guard and prior GMTM operator hashes match their earlier verified versions.

`railway-final-verification.json` closes this completion contract: login/link verified, live check passed, all five relevant source hashes match, both configuration/live receipts are mode 0600, and `git diff --check` passed. The broader product acceptance gates below remain open.

## Remaining acceptance and change boundary

The new combine endpoints remain local: the earlier live OpenAPI receipt contains neither `/api/combine/current` nor `/api/combine/help`. Real Clerk browser flow, provider response quality and a reviewed release remain separate acceptance steps. A stored link does not establish that the current browser uses that Clerk identity or prove how a historical link was originally created.

Application edits remain local and uncommitted. This continuation adds an operator wrapper/tests/receipts outside the repo and updates state/handoff documentation inside it. No application source, deployed variable, database record, infrastructure resource, other checkout, commit, push or deployment was changed.
