# Workspace link compatibility

Codex owns this checkout and `codex/athlete-home-first-value`, starting clean at `f2563fb447d29eeccc45d823c06568ddfb0f36c2`. Joey asked to fix the persistence mismatch and proceed toward real-account testing. See the [completion contract](../../docs/state/workspace-link-compatibility-contract-2026-09-09.md) and [exact reviewed change](../../docs/state/workspace-link-upgrade-plan-2026-09-09.md). Fable's GMTM and Audit's machine lanes were preserved.

## Observed schema and local fix

The completed read-only inventory confirms Railway Agent MySQL **9.4.0**. `athlete_profiles` has `PRIMARY(user_id)`, nullable `VARCHAR(100)` Clerk linkage, nullable bio and a mutable automatic `updated_at`; no immutable link-generation column exists. Its Clerk index is nonunique. Metadata estimates three rows and 16 KiB each of data/indexes. These are estimates, not row-count proof. `athlete_workspaces` is absent. This resolves both schema unknowns from the earlier handoff without reading athlete contents.

The local one-table preparation now accepts a separate exact unique `id` alongside the existing unique athlete key, and nullable/required `VARCHAR(100/255)` Clerk subjects. It does not replace the legacy primary key or change any mapping data. Runtime code is unchanged: one exact non-null authenticated Clerk match, positive identifiers and identical reverse ownership remain required. A new NULL-owner regression proves an existing draft becomes inaccessible without modifying the saved row.

`prepare_workspace_link_upgrade.py` is the separately gated migration for the exact observed schema. It recognizes only original, ID-added and ready states. It adds one unique auto-increment `id` while preserving all four legacy fields and both indexes, then creates the existing exact workspace table. It checks the schema fingerprint and target before DDL, uses a three-second metadata-lock wait, inspects after each statement, records partial/lost-acknowledgement outcomes and never retries DDL. An acknowledged ALTER followed by failed metadata inspection prevents the CREATE. DDL cannot be rolled back as a transaction.

`scripts/run_workspace_link_upgrade.py` adds fixed Railway binding, source fingerprint, exclusive private receipt and finite isolated child execution. Default is offline; explicit apply requires both reviewed source/schema fingerprints and a new output directory. Only Agent settings enter the child. Parent output retains bounded operation/state names, fingerprints, counters and cleanup flags; arbitrary driver errors and extra strings are omitted. Timeouts require server-side reconciliation, not another attempt. Successful child cleanup alone cannot prove an uncertain server DDL stopped.

The existing schema wrapper additionally supports independent `--inventory`, with exactly seven metadata SELECT attempts plus START/rollback, two named tables, row limits that reject truncation and bounded metadata validation. Server version and size estimates are labeled. SQL suppresses literal defaults, enum/set members and functional-index expressions; no athlete rows or GMTM are queried. Original default/check/apply paths remain distinct. Preparation tools are excluded from the fixed application package; no runtime/frontend source or deployment defaults changed.

## Verification and retained attempts

Artifacts outside Git: sibling `sparq-workspace-compatibility-2026-09-09/`.

| Evidence | Result |
| --- | --- |
| `migration-tests-final.log` | **274 passed**, one upstream Starlette/AnyIO deprecation warning, 1.60 seconds pytest time |
| `migration-tests-final.supervisor.json` | exit 0; no timeout/interruption; owned group dead; 3.43 seconds elapsed; 180-second external deadline |
| `inventory-observation.json` | schema-only copy/reference to the successful private inventory; before/after source hashes agree; read-only connection and owned child closed |
| `lifecycle-source-review.md` | independent current/historical writer audit and limits |
| `source-reconciliation.json`, `commit-receipt.json` | final source/default-plan/clean-tree provenance, written after documentation checkpoint |

The focused suite covers both migration tools/launchers, schema prep/inventory, reused owner config loader, legacy preparation and workspace runtime ownership/save behavior. No frontend change required another Next build. The whole backend suite was not repeated. Driver `mogrify` checks use deferred unconnected objects; they do not establish actual MySQL DDL semantics.

Retained failures are not passes:

1. `/private/tmp/sparq-link-inventory-2026-09-09-e00d82ad/receipt.json`: configuration subprocess blocked under the default sandbox; database child never started. A network-enabled reviewed attempt used a new output directory.
2. `/private/tmp/sparq-link-inventory-2026-09-09-e00d82ad-network/receipt.json`: connected, three SELECT/five statement reservations, failed safely, rollback/close and owned group cleanup confirmed. The parameterized metadata SQL needed escaped percent literals for PyMySQL. Root corrected that template and added a real-driver formatting regression. The failure was not retried unchanged.
3. `/private/tmp/sparq-link-inventory-2026-09-09-3f9ffa20/receipt.json`: corrected reviewed inventory **succeeded**, seven SELECT/nine statement reservations, zero DDL, rollback/close/group dead. Source digest `3f9ffa20f9b2c5f8374b475d8f2342a230e427e4436f5caa2e68edc1356215da`.
4. `migration-tests-01.log`: 271 passed/one failed because a deferred-driver test called the suite-blocked `pymysql.connect` alias. It made no connection. The test now constructs `Connection(defer_connect=True)` and asserts no socket. The corrected suite passed 272, then the final two added failure-evidence cases passed with the full focused set of 274.

Earlier successful iterations (160 inventory tests, 161 after formatting correction, 228 compatibility tests) are historical intermediate checks. Final source hashes are separately reconciled. Independent review cleared the inventory before its live reads, the local legacy guard change, and the migration/wrapper. The reviewer-requested NULL-owner and post-ALTER metadata-failure regressions are in the final passing suite.

## Decision and next action

Live upgrade **not applied**. Prepared wrapper source digest: `2c8b954721e1e9d84656ec49cb8685af05490c6da418c13bcd3c4db5cad6e2c7`. Observed schema fingerprint: `335530bf605ad93ea6b622245d1af0794c1d26af2eb71814543370856e822d8a`. The exact target, SQL, execution and recovery guidance are in the upgrade plan. Global AGENTS.md requires explicit approval for production data changes; Joey's current instruction authorizes preparation/implementation, and the concrete live ALTER/CREATE decision will be requested with the reviewed result. No live mutation follows from local plan flags or this handoff.

After that decision: apply/reinspect the exact Agent-only migration, then prepare a fresh finite user-2 acceptance runner for real footage, goal, useful introduction and explicit save/reload. Preserve prior saved work; block claim/debrief handlers and omit providers. The old synthetic preview remains expired, not a valid test environment.

The new row ID provides the original delete/recreate protection. It cannot detect an in-place owner A-to-B-to-A change of the same row. Current local claim code refuses reassignment; historical writer source did not. Current deployed writer provenance, actual DDL/data preservation, real browser usefulness and real-model quality remain unverified. The migration is additive, but can rebuild/temporarily block mapping writes. No isolated 9.4 server rehearsal or current backup verification is claimed.

No live schema/data change, GMTM/RDS/IAM/API-server action, provider call, outreach, push or deployment occurred. This checkpoint is committed locally with the exact hash in the sibling commit receipt. No generated/private receipt belongs in Git.
