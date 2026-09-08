# Safe app composition completion contract

September 7, 2026. First bounded implementation from the adult candidate package. Local work only; no schema command is applied to a database and no deployment is authorized by this contract.

## Outcome

The actual `main:app` imports and enters its FastAPI lifespan without attempting database connections, schema writes, dotenv credential loading, model construction, outbound requests or application background jobs. Configuration comes from the process environment; a local operator can explicitly select an isolated env file. Preserve existing route registration, order and authentication behavior.

Remove the three route-module schema initializers and six implicit dotenv loaders, including the lazily imported enrichment worker. Provide a separate, opt-in Agent-only schema preparation command with dry-run as its default. Require explicit Agent target settings and matching expected target on apply; reject GMTM/RDS targets. Surface unexpected database failures without printing secrets and close connections. Its tests use synthetic interfaces only.

The existing source does not define `agent_conversations`; the old initializer blindly altered it and attempted a unique Clerk index incompatible with forks. Do not guess that table or repair existing indexes in this package. Require an appropriate existing conversation baseline before preparation; document that this command is not an empty-database migration. MySQL DDL may persist partially after a later failure.

## Evidence required

- A fresh-process regression imports the real app under recording blockers and asserts zero attempted side effects. The pre-fix app must fail this check.
- Actual registered combine, help and recovery endpoints retain unauthenticated/configuration/ownership denial behavior under synthetic service interfaces.
- Explicit preparation tests cover dry-run, target validation, baseline rejection before DDL, expected duplicate-column handling, unexpected failures and connection closure.
- Run the full offline backend suite with installed application dependencies; preserve source hashes and list the incremental changes against the pre-package local state.

## Remaining candidate gates

Safe composition is not full frontend/backend acceptance, live schema verification, provider delivery or deployment readiness. Request-time college matching during claim bootstrap, the supported frontend/backend route boundary and live-backend fallback remain subsequent packages. The Dockerfile references a missing `agents/` directory; container build readiness remains open. Real Clerk ownership acceptance on the latest source, an actual saved GMTM submission followed by return/refresh, and organizer/guardian acceptance remain separate. Existing stopped/exhausted live-test allowances are unchanged.
