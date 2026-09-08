# Release, infrastructure and portfolio next decisions

September 7, 2026 Eastern. Joey asked for a recommendation on PR 73, the outstanding infrastructure information, resuming the paused workspace organization effort and a possible Codex-led Recasa/Saintlings arrangement. This is a decision brief, not approval to deploy, resize, delete, resume a paused task or create new product threads.

## Immediate security release

Codex recommends prioritizing the narrow [PR 73](https://github.com/gmtmsports/gmtm-api-v2/pull/73) deployment independently of the database resize. The fresh GitHub check reports OPEN, MERGEABLE, CLEAN, no merge timestamp and no attached CI checks; head remains the reviewed `c5628bea43a1e5a2019ba6edd4d055bf799f3757`. The actual isolated receipt has all 14 expected passing checks and cleanup. This is sufficient to prepare the narrow release decision, with the previously documented application/session coverage limits.

Fable remains the core deploy executor; Codex owns the release review. The deployment packet must identify the exact release revision/delta, per-server/process order, current-state preflight, read-only application checks and loaded-code verification, observation owner/window and a recovery plan. Treat response body codes separately from HTTP status. Staging shares production data: a successful child-detach test against a real account is not an acceptable smoke test. Reverting to the old handler restores the vulnerability and is a material recovery tradeoff, not an automatically harmless rollback.

Fable returned the [first release packet](../../../sparq-next-decisions-2026-09-07/fable-release-packet.md). Codex's [review](../../../sparq-next-decisions-2026-09-07/release-packet-review.md) rejects guessed-absent-ID mutation probes, a floating deployment revision/destructive reset without drift checks, dependency installation described as a no-op, and unresolved runtime/observation details. The correction request was delivered natively; recipient completion is tracked in the sibling `work/sparq-next-decisions-2026-09-07/` evidence. Joey's standing explicit production-deployment rule supplies the final approval boundary. No approval was inferred from asking for a recommendation.

Fable subsequently returned v2 accepting the findings. The local review records its improvements and remaining execution gates: actual runtime/environment/clean-tree preflight, exact merge-content verification, safe per-host data-path evidence and a timestamped error comparison. Those checks are not completed by a document; no runtime or release success is claimed. The narrowed patch recommendation stands.

## Infrastructure order and information owed

1. Finish the security release decision first. Existing healthy-upgrade reports do not require waiting for the resize.
2. Track `family-test` deletion separately from its completed fixture cleanup. For stopped `pre-prod`, confirm the final snapshot, exact existing deletion approval and fresh meaningful dependency evidence before deletion. The reported restart deadline is September 13; no fresh AWS state was queried here. Reuse existing approval if it actually covers the action rather than asking twice by default.
3. Fable has returned a revised resize proposal. Outstanding evidence is actual buffer-pool configuration and working set/cache misses, swap history, peak memory/CPU/connections, I/O/temp-table pressure and application baseline. The target class, numeric thresholds and proposed seven-day window remain unaccepted assumptions until justified. Name the observer, downtime window and rollback authority, including what happens between acceptance and rollback thresholds.
4. Reconcile real billing after changes settle; any Reserved Instance purchase remains separate. The small harness correction needs a reviewed diff and offline failure checks before reuse, independent of PR 73's saved completed test.

See the [infrastructure review and Fable response](../../../sparq-engineering-lead-2026-09-07/infra-spec-review.md). Codex coordinates follow-up directly; Joey need not copy technical replies between sessions.

## Workspace organization

The existing Codex task is **Audit Mac and agent setup**, thread `01a071bc-3e8d-72a0-88a4-a8bd9f5b8d3e`, cwd `/Users/joey/Documents/Codex/2026-09-05/help-me-organize-my-macbook-mac`. Its live listing is notLoaded; the last completed turn is a read-only instruction/session alignment plan. Its [existing organization plan](/Users/joey/Documents/Codex/2026-09-05/help-me-organize-my-macbook-mac/outputs/organization-plan-2026-09-05.md) and [explicit pause handoff](/Users/joey/clawd/.sammy/handoffs/2026-09-05-organization-paused-for-mysql-migration.md) are the continuation point. No resume message was sent.

Recommend resuming that task first for a refreshed inventory and exact proposal after Joey explicitly resumes it. Compare the MacBook and mini's current repo/worktree ownership, uncommitted work, instruction sources and path-dependent jobs; reconcile the new September 7 engineering-lead decision. Present a minimal diff before applying instruction changes and require session readbacks. Keep physical moves and duplicate removal for a later reviewed batch.

Desired organization: discoverable company/project locations using the existing `~/Companies/<Company>/<repo>` convention for future placements; a machine-qualified canonical checkout/owner registry; isolated Git worktrees for simultaneous implementation; per-project state/handoffs; separately managed local secrets and generated media. Git carries reviewed source/history between machines; do not mirror active working directories as a substitute for version control. The mini can host explicitly assigned persistent services, while the MacBook supports interactive work and reviews. Choose each actual workload after inventory rather than assuming it belongs on the mini.

## Recasa and Saintlings

Joey is considering this ownership transition; do not declare it adopted by those live sessions yet. Recommend one dedicated Codex lead task per product, with the current Fable session reporting context, plans, diffs and verification into that task. Preserve existing Rork/Fable implementation ownership until a documented handoff.

For each transition collect the current repo/branch and dirty changes, exact deployed/submitted build, release and monetization state, pending bugs/decisions, active automation owners and real scoped approvals. Codex independently verifies the relevant build before setting its next milestone. Start with Recasa because the September 7 local state has an active release decision, then Saintlings after reconciling its app branch/build and content-publishing ownership. These are sequencing recommendations, not current App Store verification or permission to submit.

Keep this task responsible for GMTM/SPARQ, the existing Audit task responsible for machine/instruction organization, and product tasks responsible for their own builds. Use Control Tower's shared portfolio overview for priorities and dependencies. This keeps product decisions connected without putting every implementation into one conversation or making Codex a mandatory bottleneck for every routine fix.
