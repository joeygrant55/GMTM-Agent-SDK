# GMTM infrastructure baseline — September 6, 2026

## Source and authorization

Joey supplied the following infrastructure-owner context on September 6. It is authoritative task direction, not an independently observed AWS/database result:

- Production GMTM RDS `db2-dev` moved from MySQL 5.7 to 8.4.11 overnight. Hostname remains `db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com`.
- `sql_mode` remains `NO_ENGINE_SUBSTITUTION`; existing queries are reported working unchanged.
- `pre-prod` is stopped and will be deleted. Do not point anything at it. If an actual SPARQ backend `DB_HOST` uses it, replace that host with the unchanged `db2-dev` hostname.
- Agent-owned Convex and Railway MySQL (`AGENT_DB_*`) are untouched. Joey permits work there.
- Do not create, modify or delete AWS RDS, IAM or parameter-group resources. Do not create accounts on `db2-dev`; preserve the current application account password plugin.
- Do not use `OF` as a table alias in MySQL 8 SQL, including future generated queries.
- `gmtm-api-v2` master is reported at deployed commit `1bf4fc02`. Do not deploy to the API servers.

The earlier migration pause is superseded for the specified agent-owned scope. This does not restart the separate organization task, staged queues or an unrequested deployment. The profile-linking authentication patch remains a separate unapplied draft; no approval of that patch is inferred from this infrastructure update.

## Bounded inspection and findings

Completion contract: read current instructions/state and actual Git lane, inspect local host selection and literal SQL aliases without importing or starting the app, replace a confirmed obsolete local host only if found, and preserve the infrastructure directions in a dated handoff/state update.

Owner checkout: `/Users/joey/Documents/Codex/2026-09-04/higgsfield-plugin-app-6a3293e129088191abf0875820e839da-openai-curated/work/sparq-agent-review`. Branch remains `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`, origin `joeygrant55/GMTM-Agent-SDK`. Existing modified frontend files, new AthleteStartingPoint and prior handoffs are preserved. No repo-local CLAUDE.md was found.

Host-only configuration inspection checked `.env`, `.env.local`, `backend/.env`, `backend/.env.local` and corresponding example paths in the owner checkout, `/Users/joey/GMTM-Agent-SDK` and `/Users/joey/GMTM-Agent-SDK-ws2`. Only root `.env.example` files were present, with no DB_HOST/AGENT_DB_HOST/MYSQLHOST assignments. Those keys were also absent from this shell's environment. No live configuration value was found pointing to pre-prod, so no host replacement was made. Other checkout files were not modified; no credentials were printed.

Read-only static inspection across 18 Python files in the owned backend/agents source found no SQL table alias OF and no literal preprod/pre-prod/pre_prod/db2-dev host reference. No SQL files were present in that scope. GMTM host selection uses DB_HOST in profile_api.py, agent_api.py, db_connector.py and the combine-results smoke script. Agent persistence separately uses AGENT_DB_HOST. Claims/bootstrap reuse these connections. An AST scan confirmed DB_HOST reads and the separate localhost/mysql.railway.internal agent defaults without executing modules.

## Limits and next action

Production MySQL, Railway variables and connectivity were not inspected. No database clients or app modules were imported, tests/application flows run, secrets changed, AWS resources accessed or modified, or deployment performed. Literal SQL scans cannot validate model-generated queries or establish overall MySQL 8.4 compatibility. No source correction is indicated by this narrow scan; deployed DB_HOST remains unverified.

Record the actual runtime host before future integration work. For an authorized configuration correction, change only a confirmed pre-prod DB_HOST, preserve AGENT_DB_* and account settings, and do not create a new environment pointing at production by default. Keep future verification isolated and apply the OF restriction to generated SQL as well as checked-in SQL.

New work in this turn consists of this handoff and the dated current-state update, both uncommitted. Prior source changes and the authentication draft remain uncommitted and preserved. No commit or push occurred.
