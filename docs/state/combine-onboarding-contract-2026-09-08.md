# Combine onboarding and explicit college research

September 8, 2026. Joey authorized continuing the product work and asked when to commit/deploy. Begin local reviewed commits; no push or deployment is included. Joey separately reports authorizing Fable to delete `family-test`; `pre-prod` remains a separate decision. No Codex infrastructure execution is part of this package.

## Athlete outcome

Redeeming a combine invitation links the correct athlete and can prepare their workspace without automatically starting college matching, research or model work. Workspace readiness is independent of college research. Existing combine entry and progress must remain usable when optional workspace preparation fails. College surfaces must not announce running/completed work without evidence.

## Bounded changes

- Make `ensure_workspace_profile` creation-only. Preserve identity/metrics and its ready/created/profile contract; remove the automatic worker, matching payload and unused inferred sport. Leave enrichment incomplete rather than pretending research finished.
- Validate exact Clerk ownership on existing and post-insert workspace rows. A conflicting insert is a no-op, and a concurrent same-owner creation must not falsely report a second creation. The claim's existing transaction and ownership rules stay intact; optional bootstrap failure does not undo the established claim.
- Preserve valid explicitly requested research. The manual matching endpoint must reject missing usable stored sport context before dispatch instead of guessing a sport from a position or defaulting to Basketball. Do not label GMTM data as MaxPreps data or create a schema migration to store inferred sport.
- Make the existing college page's empty/unavailable research copy truthful, remove its automatic page-open AI prompt, check the matching POST result before announcing a start, and bound/clean up polling. Do not infer a durable job state from the existing `complete` boolean. The wider recruiting surfaces and supported candidate route boundary remain a later package.

## Verification and completion

Retain a failing baseline showing that an actual bootstrap creates/starts a matching thread. Verify corrected bootstrap with recording fakes for Agent/GMTM interfaces and worker/provider starts, including existing/missing identity, metrics error, retry, case collision and concurrent creation. Exercise real claim-to-bootstrap composition and real combine handlers against a mutable synthetic submission fixture; distinguish this from an actual saved GMTM submission.

Verify valid explicit matching still dispatches after a user request, while missing sport/foreign ownership fails before dispatch. Exercise actual college UI with intercepted synthetic APIs: empty state, HTTP rejection, accepted request, polling completion/timeout and cleanup. Run the full offline backend suite and relevant current-source frontend checks. Review the incremental diff and commit this bounded package locally after verification.

The accumulated prior work will be committed first as a clearly labeled local checkpoint because its identity/combine/help dependencies cross files and cannot safely be split by final filenames. Preserve older receipts and avoid including credentials or generated artifacts. Keep operational handoffs distinct where useful; list anything intentionally uncommitted.

Deployment follows a recorded candidate, supported full frontend/backend journey, actual identity/source/schema acceptance, release/rollback evidence and Joey's explicit deployment approval. Existing live-read/model allowances remain unchanged. No current check proves real Clerk, MySQL transactions, provider delivery, deployed behavior or a real submission-return journey.
