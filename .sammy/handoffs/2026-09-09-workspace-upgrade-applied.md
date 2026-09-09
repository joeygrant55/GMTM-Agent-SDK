# Live workspace upgrade applied

Codex executed from the clean existing checkout, branch `codex/athlete-home-first-value`, source commit `e3ce4974901c7affa518c1503c9e05caeb04e003`. Joey answered the concrete two-change approval request with **"Yes you may - please go"**. The [reviewed plan](../../docs/state/workspace-link-upgrade-plan-2026-09-09.md) defines the scope. Fable's GMTM/infrastructure and other active lanes were unchanged.

## Execution result

The fixed reviewed launcher ran once with source digest `2c8b954721e1e9d84656ec49cb8685af05490c6da418c13bcd3c4db5cad6e2c7` and starting schema fingerprint `335530bf605ad93ea6b622245d1af0794c1d26af2eb71814543370856e822d8a`.

Both approved statements were attempted once and acknowledged completed:

1. `add_link_id`: additive `BIGINT UNSIGNED NOT NULL AUTO_INCREMENT id` and exact unique `sparq_link_id(id)`, retaining all four legacy fields, `PRIMARY(user_id)` and `idx_clerk_id(clerk_id)`.
2. `create_athlete_workspaces`: the exact existing seven-column InnoDB saved-work table.

The three exact metadata observations were original → needs_workspace → ready. Final schema fingerprint: `c6534e3586416b6262c0220c63b31c9e89b5fae0ddf319ca212883a027a07aaa`. DDL connection closed; no uncertain outcome, timeout, interruption or output overflow; owned child group dead. Source hashes matched before and after. No retries or manual follow-up SQL were needed.

Target binding was freshly verified: Railway project `27aa6c0a-9218-49ac-a182-08f6fe36249e`, environment `32a909ef-4bb6-4745-a0fe-aa86e7656b3c`, MySQL service `c6becf80-b58f-4fa0-99c6-45f87f405756`, database `railway`, proxy `centerbeam.proxy.rlwy.net:15014`. Server/schema version remained the reviewed 9.4.0 shape. Only Agent configuration was injected into the finite child; secrets were not printed or written.

## Independent post-change compatibility check

The existing schema checker ran separately in explicit read-only `--check` mode using source digest `060d9e7aae25cccd8099854f681dd0b829e3d8cfd99cce5d2ed17efd3e78b411` and a fresh private receipt directory. It returned **readiness=ready, workspace_contract_checked=true** with eight metadata SELECT/ten driver-statement reservations, zero DDL, successful rollback and connection close. Its owned group is dead, with no timeout/interruption/output overflow and matching source hashes before/after.

This verifies actual live schema compatibility with the application's preparation contract. It does not verify authenticated athlete GET/PATCH, media loading, byte-for-byte preservation of preexisting row contents, or useful output. No athlete rows were selected during these metadata inspections; the approved ALTER generated IDs on the existing link rows. No athlete-authored goal/draft was written. The SQL and exact schema checks preserved the expected legacy structure; there was no before/after athlete-content snapshot, so content preservation is not independently asserted.

## Receipts and source evidence

Original exclusive private receipts:

- `/private/tmp/sparq-link-upgrade-approved-2026-09-09-e3ce497/receipt.json`
- `/private/tmp/sparq-workspace-post-upgrade-2026-09-09-e3ce497/receipt.json`

Verified durable copies and reconciliation are in sibling `sparq-workspace-applied-2026-09-09/`, outside Git. `execution-reconciliation.json` records the source matches, exact target, completed operations, ready state and cleanup. `commit-receipt.json` records this documentation checkpoint's local commit and clean-tree state. Receipts contain redacted schema/process metadata only, never credentials or athlete content.

No implementation code changed during execution. The prior final 274-test source matches the executed digest; the offline suite was not unnecessarily rerun. The two actual live operations and separate read-only post-check are the new verification evidence. No live rehearsal or backup operation was added beyond Joey's approved scope.

## Next

Implement the [fresh real-account acceptance setup](../../docs/state/profile-real-account-acceptance-2026-09-09.md). Independent source review identified the current profile app plus a small outer owner-2 guard as the shortest path; real Clerk configuration can follow the existing verified launcher pattern. The setup contract is written, but no runner or server was started. The old synthetic preview remains expired.

No GMTM access, RDS/IAM/API-server change, account reassignment, provider call, outreach, application deployment or Git push occurred. The authorized live schema work is complete. Actual athlete JWT/media/save/reload testing and deployed mapping-writer provenance remain the next separate evidence gaps.
