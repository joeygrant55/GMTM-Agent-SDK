# Candidate release-readiness completion contract

Baseline: clean local `53470702d32ace95fdf02f340f2012b34d8686bf`, branch `codex/athlete-home-first-value`. Codex owns integration; bounded parallel lanes cover profile connectors, production frontend build and packaging review. Joey authorized continued local implementation. No deployment, push, infrastructure changes, production writes, real service/model tests or reset of an exhausted allowance is included.

## Deliverable

1. Add finite connect/read/write socket timeouts to the profile connectors used by claim/recovery/bootstrap, preserving credentials, targets, SQL and existing auth/ownership semantics. Verify real driver behavior with synthetic sockets where feasible. State clearly that socket timeouts are not an overall HTTP request deadline or a server query-cancellation guarantee.
2. Verify the unmodified candidate frontend with an actual production build in a scrubbed, allowlisted external snapshot. No live environment files, Clerk/data/provider calls or package installation. Correct genuine build defects narrowly, if found. Keep any synthetic authentication adapters outside production application source and distinguish fixture runtime tests from the real production build.
3. Prepare an explicit separate backend candidate entry/build package and deployment checklist. Preserve existing main deployment settings. Exclude secrets, test fixtures and unrelated source from the candidate build context. Record exact available toolchain/dependency evidence and honestly distinguish source/package verification from a built/running container if a local container runtime is unavailable.
4. Independently review the resulting diff and evidence, run relevant regression checks, record remaining live release gates, write a handoff/current-state update and commit locally.

The intended product outcome is a reproducible candidate that can progress to a controlled athlete pilot. Missing external tooling or live credentials is a scoped verification limitation, not permission to change another environment or manufacture successful deployment evidence. Complete all available local preparation before asking for any necessary final release authorization.
