# Agent saved-work schema upgrade

Prepared locally; not applied. This is the concrete database change needed before Joey's saved-work acceptance test. It follows the [compatibility contract](workspace-link-compatibility-contract-2026-09-09.md).

## Verified target and starting shape

September 9 metadata-only receipt: `/private/tmp/sparq-link-inventory-2026-09-09-3f9ffa20/receipt.json`. Exact existing Railway project `27aa6c0a-9218-49ac-a182-08f6fe36249e`, environment `32a909ef-4bb6-4745-a0fe-aa86e7656b3c`, MySQL service `c6becf80-b58f-4fa0-99c6-45f87f405756`, database `railway`, proxy `centerbeam.proxy.rlwy.net:15014`. Actual server version: **9.4.0**. No configuration or infrastructure change is needed.

`athlete_profiles` is InnoDB with `PRIMARY(user_id)` and nonunique `idx_clerk_id(clerk_id)`:

| Column | Existing definition |
| --- | --- |
| `user_id` | `INT NOT NULL` |
| `clerk_id` | nullable `VARCHAR(100)`, `utf8mb4_0900_ai_ci` |
| `bio` | nullable `TEXT`, same collation |
| `updated_at` | nullable `TIMESTAMP`, current timestamp default and automatic update |

The metadata estimates three rows, 16 KiB of data and 16 KiB of indexes; these are not exact counts. There is no row-generation identifier. `updated_at` is mutable and cannot supply one. `athlete_workspaces` is absent.

## Exact change

1. Preserve the four existing columns, the primary key and the Clerk index. Add one unique generated internal row identifier:

```sql
ALTER TABLE athlete_profiles
    ADD COLUMN id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ADD UNIQUE KEY sparq_link_id (id),
    ALGORITHM=INPLACE, LOCK=SHARED;
```

2. Create the separate private saved-work table using the existing exact `CREATE_SQL` from `backend/prepare_athlete_workspace.py`:

```sql
CREATE TABLE IF NOT EXISTS athlete_workspaces (
    clerk_id VARBINARY(255) NOT NULL PRIMARY KEY,
    athlete_link_id BIGINT UNSIGNED NOT NULL,
    gmtm_user_id BIGINT UNSIGNED NOT NULL,
    version INT UNSIGNED NOT NULL,
    payload JSON NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL
) ENGINE=InnoDB;
```

The local workspace prerequisite now supports the existing nullable Clerk width and a separate exact unique link ID, rather than requiring replacement of the primary key. Runtime ownership checks still require exactly one positive ID/athlete ID and exact non-null Clerk match in both directions. Ambiguous and unlinked rows cannot reveal or change saved work. No data-import or account-reassignment statement is included.

## Execution and recovery requirements

Use the dedicated `backend/prepare_workspace_link_upgrade.py`, never the broad `prepare_agent_schema.py`. Its default prints an offline plan. Applying requires an explicit apply/live acknowledgement, the exact expected Agent target and a freshly checked schema fingerprint. Only the original, ID-added, or fully-ready shapes are accepted. Other drift stops execution. Size estimates must stay within the tool's small-table limit; they do not prove a hard row-count or duration bound.

The fixed Railway wrapper is `backend/scripts/run_workspace_link_upgrade.py`. Its default is completely offline. For the prepared source, the reviewed digest is `2c8b954721e1e9d84656ec49cb8685af05490c6da418c13bcd3c4db5cad6e2c7`; the observed starting schema fingerprint is `335530bf605ad93ea6b622245d1af0794c1d26af2eb71814543370856e822d8a`. The eventual invocation requires `--apply`, both `--source-digest` and `--schema-fingerprint`, and a new absolute private `--output` directory outside Git. Recompute/review the source digest after any code change. This wrapper retrieves only the two fixed Railway service configurations into memory, verifies their binding and supplies only Agent fields to its isolated child. It never logs or writes credentials. Each CLI call is bounded to 30 seconds; the migration child has a 105-second external deadline and owned-process cleanup. A dead child is not proof an uncertain server-side DDL stopped.

The tool verifies metadata after each statement, records observed partial progress, and does not automatically retry failures. Session metadata-lock waiting is limited to three seconds. **This is not an instant or transactionally reversible change.** Adding an auto-increment column rebuilds the table and can block mapping writes while it runs; closing a client after a timeout does not prove the server stopped its DDL. The source recipe uses `INPLACE, LOCK=SHARED` so an unsupported algorithm fails rather than silently requesting a more permissive fallback. [MySQL online DDL reference](https://dev.mysql.com/doc/refman/9.7/en/innodb-online-ddl-operations.html)

If execution becomes uncertain, inspect the two exact tables before deciding any next action. Do not repeat an ALTER blindly. If only the ID was added, existing explicit pair-insert writers remain compatible and workspace creation can be separately resumed after a new reviewed fingerprint. If both changes completed but app verification fails, keep the additive schema and stop the candidate; no automatic DROP or reversal is authorized. Recovery retains the additive schema and existing application; it does not depend on removing the new identifier. Backup availability was not verified or configured in this checkpoint.

The generated ID detects deletion/recreation of a pair because a new row gets a different value. It does not detect an in-place A-to-B-to-A owner change on the same row. Current local claim code refuses reassignment; historical writers did not. Deployed writer provenance remains a release check, separate from this owner-only test. A unique secondary auto-increment key is supported by InnoDB. [MySQL auto-increment reference](https://dev.mysql.com/doc/refman/9.7/en/innodb-auto-increment-handling.html)

Vendor 9.4 documentation redirects to current 9.7 documentation. No isolated real-9.4 DDL rehearsal has run here; synthetic driver tests establish guard/control-flow behavior, not real migration execution or data preservation.

The final focused suite passes **274 tests**, including legacy/null ownership, exact existing columns/indexes, all three migration states, target/source/schema drift, partial acknowledgements, metadata failure after an acknowledged ALTER, private receipts and no automatic retries. Independent source review found no blocker. A real-driver formatting check uses a deferred connection only; it is not a server-side DDL test.

## Following acceptance

After the exact live change is authorized, applied and rechecked, use a fresh finite run restricted to Joey's current unique GMTM user-2 link. Load actual footage, save a goal, prepare and edit a useful introduction, explicitly save, reload and confirm exact text. Preserve any prior work. Provider calls, claim redemption, other athletes, outreach and deployment remain outside that test.
