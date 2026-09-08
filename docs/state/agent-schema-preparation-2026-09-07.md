# Explicit Agent schema preparation — September 7, 2026

The startup package removes automatic schema work from route-module import. [The preparation command](../../backend/prepare_agent_schema.py) replaces the old implicit attempts with an explicit operator step for an **existing Agent installation**. It is local implementation, not an applied database change or a deployment approval. Nothing in this package uses AWS, GMTM's source database, provider models, or credentials from dotenv files.

## What the command does

The default invocation prints a fixed plan. It does not read database configuration, import the MySQL driver, connect, or execute SQL:

```sh
python backend/prepare_agent_schema.py
```

Applying requires every `AGENT_DB_HOST`, `AGENT_DB_PORT`, `AGENT_DB_USER`, `AGENT_DB_PASSWORD`, and `AGENT_DB_NAME` value explicitly in the process environment. There is no `DB_*` fallback or default Railway/root target. The exact host and database must also be supplied as acknowledgments. An example for an already prepared, authorized isolated environment is:

```sh
python backend/prepare_agent_schema.py --apply \
  --expected-host 127.0.0.1 --expected-database sparq_isolated
```

This is not a connection setup command: credentials must already be injected through the approved environment mechanism, with no password in shell arguments or logs. It does not load `.env` files. GMTM-like database/host names and AWS RDS hostnames are rejected. This name check helps prevent a mistaken target; it cannot prove an arbitrary hostname or IP is an isolated service. The operator must verify that separately. Host acknowledgment is exact, including case; ports must be decimal integers between 1 and 65535. Connections use five-second connect and ten-second read/write timeouts.

Before any DDL, the command confirms the selected database and the existing `agent_conversations` base table, with `id`, `clerk_id`, `fork_scenario`, `parent_id`, `created_at`, and `updated_at` columns. A unique index on `clerk_id` alone fails the preflight because it prevents multiple fork conversations for an athlete. The command does not remove or change that index. Historical production may contain it; discovering it would require a separate reviewed schema decision, not an automatic repair.

The old profile initializer never created `agent_conversations`, and it silently swallowed both missing-table and other ALTER failures. Its conversation column ALTER and unsafe unique-index addition are intentionally excluded. Missing conversation prerequisites cause failure before any DDL. This command therefore cannot initialize an empty database and must not be presented as a complete migration system.

After preflight, the command executes the original eleven `CREATE TABLE IF NOT EXISTS` definitions and three non-conversation `ADD COLUMN` alterations, in their original deterministic order. Definitions are preserved from the September 7 pre-change profile, artifacts, and claims modules. Only MySQL error 1060, duplicate column, is an expected outcome for the three ADD COLUMN statements. Unexpected connection, table, index, duplicate-data, permission, SQL, and cleanup failures return nonzero.

## Evidence and limitations

A successful report says `preparation_applied`, lists statements that completed, and says the limited conversation prerequisites passed. **`CREATE TABLE IF NOT EXISTS` does not verify an existing table's definition**, and a duplicate-column outcome does not verify its type/default. The command does not assert complete schema validity, application acceptance, deployment readiness, index/engine/collation parity, real authorization, or transaction integration.

MySQL DDL commits implicitly. There is no rollback claim: if the fifth statement fails, earlier successful operations may remain applied, and the failed statement's actual state still requires inspection. Reports include statement names and numeric driver error codes/types, never exception messages, SQL parameters, credentials, or athlete data. Connection closure is always attempted. A closure failure is reported even after all DDL returned successfully; it does not turn partial or uncertain work into a success.

The focused offline run passed **55 tests** on September 7 using the installed backend Python environment with the repository no-network guards. The offline test suite uses only a fake connector. It verifies no-connection dry runs, explicit target requirements and rejection before connection, conversation preflight before DDL, bounded connection settings, expected duplicate handling, partial-progress reporting, redacted nonzero failure, and cleanup error preservation. These tests do not establish real MySQL compatibility or apply any schema.

Root owns the related app-composition and startup verification; this file documents only explicit schema preparation. Actual Agent schema inspection, an isolated database run, any conversation-schema change, and a release remain separate steps.
