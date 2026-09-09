# Saved-work compatibility completion contract

Codex owns the existing SPARQ checkout on `codex/athlete-home-first-value`, starting clean at `f2563fb447d29eeccc45d823c06568ddfb0f36c2`. Joey asked to fix the confirmed link-schema mismatch and proceed toward his real-account journey. Fable's GMTM/infrastructure lane remains unchanged.

1. Inspect only metadata for the verified Railway Agent `athlete_profiles` and `athlete_workspaces` tables, independently of the old compatibility prerequisite. One connection, explicit read-only transaction, at most seven exact metadata SELECT attempts, rollback and close. Use the existing reviewed source/binding/private-receipt/finite-child safeguards. No athlete rows, GMTM, providers, DDL or configuration changes in this inspection.
2. Reconcile local source and handoffs for mapping creation/relinking. Choose the smallest design that preserves exact forward/reverse ownership, concurrent-save conflicts and invalidation after recreation of the same link. A timestamp or `user_id` alias is not assumed to supply an immutable link generation.
3. Implement the compatible persistence/preparation path locally with focused failure, ownership and lifecycle verification plus independent review. Preserve unrelated routes, existing mapping data and athlete-visible draft behavior. No automatic repair or startup DDL.
4. If the evidence requires a live schema change, prepare the exact target, statements, preconditions, effects and recovery procedure for review before execution. The existing broad Agent schema command and all GMTM/RDS/IAM/API-server mutations remain excluded. Do not claim live compatibility from offline tests.
5. Once live prerequisites are compatible and the precise write scope is authorized, prepare a fresh finite owner-2 acceptance run for actual footage, goal, useful output and exact save/reload. Preserve prior work, reject other accounts, block claim/debrief handlers and omit provider credentials. Do not reuse historical ledgers or synthetic previews as live acceptance.

Finish with current-state/handoff evidence and a local commit or exact uncommitted file list. No push, deployment or outreach is included.
