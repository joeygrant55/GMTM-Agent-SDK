# Current-combine adapter source map — September 6, 2026

Discovery for milestone 2; no core GMTM changes or database requests performed.

## Source freshness

The MacBook core API checkout /Users/joey/mercor-scan/repos/gmtm-api-v2 is on chore/opensearch-v2-host at f2fe121, with an unrelated local ecosystem.deploy.js. It is not the deployed migration revision Joey supplied and was left unchanged. The connector could not access the private repository (404). The existing GitHub CLI session successfully read the explicit commit 1bf4fc0297d5eea56bed6bda54715f2f9c01593f and the following files at that ref:

- resources/submission/submission.resolver.js
- resources/event/event.resolver.js
- schemas.md

Frozen source copies are in the task's work/sparq-build-2026-09-06/core-*-1bf4fc02.* files. This verifies source at the reported deployed revision, not live deployment or schema equivalence.

## Established source facts

- Event definitions live in events; ordered activities live in event_tasks with event_id, task_id, title, type, list_order, payload and visibility. The checked-in schema does not expose a single top-level required flag; payload semantics still need tracing for the target combine.
- Submissions live in event_task_submissions with user_id, task_id, payload, video_uri, approved, visibility and created_on. Distinct task IDs matter; duplicate attempts must not inflate completion.
- Core submission confirmation computes total tasks from event_tasks with visibility <> -1 and completed activities from distinct submitted task IDs with submission visibility > 0 (submission.resolver.js:2150-2160). The numerator does not apply the same deleted-task filter, so the Agent should not blindly copy these aggregate counts into a requirements-satisfied claim.
- Administrative event reporting separately counts submission_reviewed records while filtering task visibility <> -1 and submission visibility > 0 (event.resolver.js:596-628). An approved flag alone must not be described as an evaluator review or selection.
- Core confirmation sends athletes back to /virtuals/{event_id} (submission.resolver.js:2216-2220). A task-specific continuation URL still needs verification in the current web source; do not fabricate one.
- checkRegistrationStatus reads transaction_history.status by transaction ID. That is not an athlete/event authorization lookup, and payment success is not combine completion.

## Adapter contract to implement after identity batch

Input identity must come from the authenticated Clerk-to-GMTM link; active event must come from an authorized saved claim/registration context, independent of numeric result rows. Do not accept an arbitrary event ID as sufficient permission. The user may have multiple events, which need explicit selection and isolation rather than selecting the first result.

Return canonical source IDs, event name/continuation URL, ordered relevant activities, submission/evidence state, and separately grounded review/outcome state. Represent unavailable, no submissions, partial submissions, all required activities satisfied, pending review and verified outcome distinctly. Include source/read timestamp and avoid promising completion where payload validation/requirement rules remain unknown.

Next source work: inspect the target combine's applicable task payload types and current web visibility/validation rules; identify valid pre-submission participant authorization and event context; verify exact deep links. Start with a zero-result fixture, then mixed task types, duplicate attempts, hidden/deleted activities/submissions, partial and complete-awaiting-review fixtures. Live data/schema validation is a separate controlled check.

Charles's exact target event and expected arrival date were requested asynchronously while the identity batch continued. No answer has been assumed. This document is discovery, not an implemented adapter or a statement that the complete current-combine flow now works.

## Fable research reconciliation and additional source — September 6

Joey supplied `/Users/joey/Desktop/gmtm-code-research/` and confirmed adult and junior USA Football programs. The [reconciliation](gmtm-platform-reconciliation-2026-09-06.md) records reused architecture knowledge and freshness limits. Current program IDs/configuration remain unknown.

Additional `virtual`, `limits` and `user` resolver source was fetched at the same reported deployed commit `1bf4fc0297d5eea56bed6bda54715f2f9c01593f` and frozen under the task's `work/sparq-platform-reconciliation-2026-09-06/` directory:

- `virtual.resolver.js:1198–1223`: `getMyVirtuals` includes events from submissions, `invites.invited_id`, and product access in `limits`; final published/public/non-invite-only filters mean it is not a complete authorization or registration adapter.
- `limits.resolver.js:261–272`: product access lookup uses the current GMTM session's user ID and the requested product ID. Trace the event-to-product/access semantics before using it for the target combines.
- `user.resolver.js:803–812,945–955`: family and child-session paths use `user_parents`; `2926–2942,3121–3128`: switching and child listing use `users.parent_id`. Both appear in checked-in schema. Establish the active web/program path before granting delegated SPARQ access. Do not replace the current one-athlete ownership restriction based on repository presence alone.

No database requests, environment exports, live navigation or core checkout modifications were performed. Source at the supplied deployed revision is not live deployment/schema verification.

## Live public event configuration — September 6

Subsequently, Joey supplied the official USA Football digital-combine page. Its links and unauthenticated GETs of the public GMTM event pages confirm junior 1317, adult 1318, organization 249002 and nine activities per event. This supersedes the earlier unknown-target/fixture-only statements for those IDs. See the [public event contract](usaf-combine-contract-2026-09-06.md) for the task map, public data provenance, policy/configuration discrepancies and normalized fixture. No athlete submissions or sessions were retained, and no task/payment/account flow was exercised.

Both targets are public/non-invite-only and have no GMTM product ID: do not force invitation/product membership merely to show their public requirements. Keep all personal progress reads owner-scoped and program eligibility separate. The adult dash question/template conflict is partly accommodated by the existing result canonicalizer, but whole-event fallback suppression can still hide a missing ingested drill; neither behavior establishes requirement completion. The new adapter must preserve event/task/question identity, videos, both shuttle directions and nonnumeric background fields.
