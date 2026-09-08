# Focused combine candidate

This package is local and not deployed. It provides a supported route boundary; configuration alone does not provide database or network isolation. The default legacy app and `main:app` keep their broader behavior. A future release must pair the combine frontend with `candidate_app:app` and verify both surfaces; the frontend flag alone does not restrict a separately deployed legacy backend.

## Frontend selection

Set `NEXT_PUBLIC_APP_SURFACE=combine`, an explicit `NEXT_PUBLIC_BACKEND_URL` HTTP(S) origin, and `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` before Next starts or builds. Public variables are part of the frontend build; changing only the deployed runtime environment does not rebuild a browser bundle. Only loopback backends may use HTTP. Missing/invalid origin or surface configuration fails; no live backend fallback is selected.

The focused UI supports `/home`, `/home/inbox`, `/connect`, invitation `/claim/<token>` and `/claim/<token>/redeem`, plus Clerk sign-in/up routes. Root redirects to home. The middleware covers all paths, including static-looking dynamic URLs, and rejects unrelated pages and same-origin API/trpc routes before Clerk or handlers. The candidate has no catch-all API rewrite. Only required static assets/framework chunks are exempt. The candidate disables Next image optimization: the framework handles that proxy before page middleware, so a middleware rule alone is insufficient. Ordinary static images remain available.

The actual browser API helper checks configured origin, candidate operation and method before obtaining a token, and refuses redirects. Public server-side claim preview uses the same policy. The normal legacy build still requires an explicit backend origin and retains its configured API rewrite.

## Backend selection

`candidate_app:app` is a separate Uvicorn entry point. Do not switch an existing service's startup command or environment as part of local verification. A future explicitly authorized service would use:

```sh
cd backend
python -m uvicorn candidate_app:app --host 0.0.0.0 --port "$PORT" --no-access-log
```

Disable access logs because invitation URLs contain signed claim tokens. Do not print secrets or pass them in command arguments. No dotenv, schema preparation, connection, provider request or background job runs during import/lifespan; lifespan performs pure configuration validation.

Required configuration:

- `AUTH_ENFORCED=true`; HTTPS `CLERK_ISSUER`; explicit, matching `CLERK_AUTHORIZED_PARTIES` and `ALLOWED_ORIGINS` lists with exact origins. Candidate JWTs require a valid subject and an allowed `azp`, in addition to existing signature/issuer verification.
- GMTM host is pinned to the reviewed `db2-dev` hostname and `DB_USER=gmtmread`, with injected `DB_PASSWORD`. Database/port remain `gmtm`/3306. This does not authorize a live request or prove connectivity/read-only grants.
- Explicit separate `AGENT_DB_HOST`, `AGENT_DB_PORT`, `AGENT_DB_NAME`, `AGENT_DB_USER`, `AGENT_DB_PASSWORD`, plus `SHARE_TOKEN_SECRET`.
- Explicit finite `COMBINE_HELP_MAX_MODEL_CALLS` and `COMBINE_HELP_MAX_CONCURRENT_CALLS`. Existing supported `COMBINE_HELP_MODEL` and provider configuration apply. Missing provider credentials is reported separately and does not invalidate checklist configuration. Existing usage ledgers and exhausted allowances must not be reset.

Only GET current combine, POST help, GET by-Clerk recovery, GET claim preview and POST redemption are registered, plus `/health`. No minting, generic agent, workspace editing, artifacts, college research, outreach, API docs or schema endpoint is exposed. Preview records `opened_at`; redemption writes claims/ownership and may create a workspace in the Agent database. GMTM remains read-only.

`/health` distinguishes declared configuration from connectivity, schema and provider delivery. It never claims database readiness. Critical configuration changes after startup make business routes unavailable until a validated restart. Existing profile connectors used by invitation/recovery/bootstrap still lack bounded read/write timeouts; resolve this before a live candidate release. Ordinary app authentication and routes are not changed by candidate dependency overrides.

## Local verification

`frontend/tests/check-candidate-policy.cjs` checks pure configuration/route policy and actual compiled transport without networking. Existing component harnesses remain separate regression evidence.

`frontend/tests/check-candidate-app.cjs` runs actual Next development middleware, RSC/routes and browser rendering against `backend/tests/run_candidate_fixture.py`, which launches the real candidate ASGI app with synthetic service interfaces. Use a new absolute `SPARQ_CANDIDATE_ARTIFACT_DIR`; it refuses existing output. It uses installed dependency runtimes without package installation. All identity overlays belong to the external snapshot; no fixture authentication flag or fixture HTTP route is added to application source. The IPv4-only Python fixture temporarily suppresses urllib3’s import-time IPv6 capability probe, restores the capability flag before app imports, and retains all connection guards. Node/Python connection guards and browser routing restrict test service traffic; these are test instrumentation, not an OS firewall.

The harness must record its source hashes, overlays, synthetic data/provider seams, owned-process cleanup, route/network observations and functional results. A pass establishes local integration only. Real Clerk login/JWKS, deployed schema/current source ownership, model delivery, actual GMTM submission-return, production build/container readiness and rollout decisions remain separate gates.

Forced external interruption is not a tested graceful-cleanup path in the harness. If its controlling process is forcibly stopped, explicitly inspect and clean only the recorded owned child processes and ports before rerunning. Normal completed/failed test paths independently close browser and services, with receipt verification.
