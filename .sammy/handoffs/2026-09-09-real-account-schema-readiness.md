# Real-account schema readiness

Codex owns the existing SPARQ checkout and `codex/athlete-home-first-value` branch. This checkpoint started clean at `059fc33875eecddaf16647a2b002172f5819d082`. Joey agreed to real-account testing, then advice quality and an athlete pilot. The [completion contract](../../docs/state/real-account-readiness-contract-2026-09-09.md) scopes this checkpoint to configuration and metadata readiness. Fable's GMTM and Audit's machine work remain separate.

## Finding

Current Railway CLI access works; no new login or public-proxy change is needed. The existing fixed loader verified the exact backend/MySQL service binding. The final metadata-only inspection confirmed that live `athlete_profiles` contains `user_id` and `clerk_id`, but **does not contain `id`**. This is an incompatibility introduced by the new saved-work code's assumptions. Existing profile/evidence/materials and claim linkage use the original pair without this surrogate ID.

The check stopped at the athlete-link prerequisite. **`athlete_workspaces` existence and compatibility are unknown.** Creating that table alone is not the next fix. No live schema/data mutation occurred, and the real-account save/reload journey has not run.

## Local implementation

- `backend/prepare_athlete_workspace.py` adds an explicit mutually exclusive `--check` mode. Its default remains an offline plan; the existing apply implementation is unchanged. Inspection uses exact Agent-target acknowledgement, one read-only transaction, four exact metadata SQL shapes restricted to two named tables, at most eight SELECT reservations, rollback and close. It cannot select athlete rows or issue DDL.
- `backend/scripts/run_workspace_schema_check.py` loads the two fixed Railway service configurations into process memory, verifies their binding and passes only five Agent settings to an isolated finite child. It does not read GMTM credentials or include provider keys. Execution requires the current reviewed source digest and an exclusive private output directory outside Git. The wrapper has no apply mode.
- Success output is exact-schema checked. Failure output preserves only bounded known stage/reason tokens, counters, cleanup flags, a numeric driver error code if available, and three known-column presence booleans. Raw errors, arbitrary metadata names and credentials are not retained. Source changes and incomplete process cleanup fail closed.
- Focused synthetic tests cover metadata budgets, target guards, failure/cleanup paths, default/check/apply separation, process failures, source drift, private output and redaction, plus the actual isolated child argument bootstrap.

## Verification and receipts

Offline artifacts are outside Git in sibling `sparq-real-account-readiness-2026-09-09/`. Final `offline-04.log` reports **133 passed in 1.14 seconds**; `offline-04.supervisor.json` records exit 0, no timeout/interruption, owned group dead and 2.75 seconds elapsed under a 180-second deadline. Earlier passing iterations contain 126, 128 and 130 tests. Tests cover the preparation tool, new wrapper and reused owner launcher. No frontend/runtime package source changed, so no repeated Next build was needed.

Independent source review cleared the checker, wrapper, response/receipt safeguards and the final additive three-column diagnostic before live execution. Review confirmed that the diagnostic reused the existing metadata result without adding queries or changing apply behavior.

Live metadata attempts are retained separately, all outside Git:

| Private receipt directory | Result |
| --- | --- |
| `/private/tmp/sparq-workspace-schema-2026-09-09-e81ac383` | Failed child, exit 1, owned group dead, no timeout/interruption/output overflow. Initial wrapper did not retain the redacted child failure, so exact SQL counts and connection-close confirmation are unavailable for this attempt. Fixed source had no DDL/data-query path. This is not a pass. |
| `/private/tmp/sparq-workspace-schema-2026-09-09-7d10e229` | Incompatible required link columns; connected, read-only transaction started, three SELECT/five total driver-statement reservations, rollback and close completed, zero DDL. Owned group dead. |
| `/private/tmp/sparq-workspace-schema-2026-09-09-e98a6d48` | Same controlled failure with exact booleans: `id=false`, `user_id=true`, `clerk_id=true`. Same counts, confirmed rollback/close, zero DDL and owned group dead. No timeout/interruption/output overflow. |

Final reviewed digest: `e98a6d48cbead33c6531c56512bbdd61622d1f58f03e40fa854bfa5c1475d3a9`. Each directory contains `receipt.json`. Counts reserve driver attempts before execution, including START/rollback; they are not a MySQL wire audit. The final failure receipt retains the initial source hashes; the separate checkpoint reconciliation verifies them against current source after execution. No further live inspection ran in this checkpoint.

The exact Agent target is Railway project `27aa6c0a-9218-49ac-a182-08f6fe36249e`, environment `32a909ef-4bb6-4745-a0fe-aa86e7656b3c`, MySQL service `c6becf80-b58f-4fa0-99c6-45f87f405756`, proxy `centerbeam.proxy.rlwy.net:15014`, database `railway`. Credentials remained in process memory. The wrapper used no GMTM connection and read no athlete rows.

The old synthetic preview05 has expired. Its receipt confirms the owned group dead and ports 64308/64309 closed. It is not a current live-account test environment.

## Next completion contract

1. Prepare a separately reviewed bounded metadata inspection of the actual link primary/unique keys, relevant column types/collation/defaults/EXTRA and any existing immutable row-generation key. Inspect workspace existence/shape independently of the failed `id` prerequisite. Do not query athlete contents or apply schema.
2. Reconcile mapping lifecycle writers from source/handoffs. This checkout's `claims_api.py` inserts the original pair and treats duplicates as no-ops; external deletion/relink semantics remain unconfirmed.
3. Adapt workspace persistence to an established generation key if one exists. Otherwise specify an Agent-owned generation mechanism and its writer integration before proposing a migration. Keep the existing forward/reverse ownership checks, conditional writes and old-tab invalidation after relinking. Do not alias `user_id AS id`, remove ownership checks or invoke broad Agent schema preparation.
4. Review and verify that local implementation, then resolve the exact required live schema/write scope and prepare a fresh owner-2 browser runner. Block claims/debrief handlers and omit provider keys; preserve prior saved work. Verify actual footage, goal, useful edited output, explicit save and exact recovery after reload.

The surrogate ID currently participates in `athlete_workspace.py` ownership queries, `_revision`, persisted `athlete_link_id` matching and conditional updates. Its additional purpose is distinguishing deletion/recreation of the same Clerk/GMTM pair when a new row receives a different ID. A pair-only `source_scope` cannot supply that guarantee. An existing timestamp is not assumed to be a unique generation key.

No provider call, outreach, RDS/IAM/API-server action, live schema/data change, push or deployment occurred. This is a local readiness checkpoint, not successful athlete acceptance. Final source reconciliation and local commit/clean-tree provenance are recorded outside Git in sibling `sparq-real-account-readiness-2026-09-09/`.
