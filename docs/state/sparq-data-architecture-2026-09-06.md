# SPARQ data architecture recommendation — September 6, 2026

Keep the existing GMTM database and the separate SPARQ Agent database. Make their ownership explicit and connect them through a small, tested integration boundary. This preserves the operating product while letting two people improve the Agent without synchronizing a platform rewrite.

This is a design recommendation based on local source and dated research, not a deployed-system certification. No database, infrastructure, account, deployment or production changes were performed. Joey has designated GMTM user 2 as his own profile; root owns that separate validation.

## Product destination

Give the athlete one continuous experience: join an opportunity, complete its requirements, improve, add evidence, and choose what to share with coaches. GMTM and SPARQ can remain separate internally without exposing that separation as repeated onboarding or competing profiles. For this pilot, the existing GMTM submission flow remains in place; a unified sign-in and identity experience requires a separately verified integration, not a shared password or an assumption that a Clerk session authenticates GMTM.

The reusable business capability is an organization launching a program with clear requirements, athletes receiving relevant help, and the organization seeing authorized participation and outcomes. Prove it with the two USA Football combines, then generalize the working configuration to clubs and other NGBs. Avoid turning every organization into a custom software project.

Record the sequence from invitation through submission, review and selection as distinct, source-attributed events. Instrument progress and source freshness before making lift claims; measuring visits or AI messages alone cannot show that SPARQ helped athletes finish. This supports renewal and expansion conversations with evidence while keeping private athlete conversations out of organization reports.

The valuable asset is the trusted history connecting assessments, development and opportunities, together with workflows that reliably help people use it. A larger copied database or an autonomous chat interface alone does not establish that value.

## What exists

The owned SDK uses Railway-oriented MySQL connections selected by `AGENT_DB_*`, alongside GMTM connections selected by `DB_*`. Agent source defines `sparq_profiles` (including copied identity and `combine_metrics`, plus recruiting goals), `college_targets`, `agent_sessions`, `outreach_log`, `agent_messages`, `athlete_profiles` (Clerk-to-GMTM mapping), `athlete_links`, and `agent_reports`. Conversation code also uses `agent_conversations`. These are actual source contracts, not verified live schemas: `backend/profile_api.py:94–114,145–281`; `backend/agent_api.py:618–634`.

Convex appears in infrastructure permission notes, but a scoped source search of backend/frontend/agents found no Convex integration. It is not an evidenced third production datastore for this app. Keep the currently implemented Agent MySQL unless a concrete requirement proves it inadequate; do not migrate merely because Convex was mentioned (`docs/state/current-state.md:35–39`).

There is already drift risk: workspace bootstrap copies GMTM identity/metrics once and returns immediately when the Agent profile exists (`backend/workspace_bootstrap.py:73–103,121–151`). The new current-combine adapter instead reads task definitions and latest visible submissions through owner-scoped queries (`backend/combine_api.py:50–169`). Build on that adapter direction.

## Data ownership

| Owner | Authoritative records | Agent treatment |
| --- | --- | --- |
| GMTM | GMTM athlete identity, event/organization definitions, task requirements, registrations where established, submission attempts, media references and measurement provenance | Read through typed adapters; preserve source IDs, visibility and timestamps. An existing number or approved flag alone does not prove device verification or evaluator review. |
| SPARQ Agent | Conversations, athlete goals/preferences, plans and drafts; approved action versions, receipts, durable jobs and usage accounting as they are implemented | Own and evolve these records in Agent MySQL. Reference GMTM entities rather than cloning their lifecycle. Some target records in this row are planned, not present today. |
| Explicit identity bridge | Clerk actor → GMTM athlete link and its verification/revocation history | Server-resolved authorization boundary. Public athlete IDs, model output and names cannot establish ownership. |
| Source-specific external authority | USA Football ID validity, published program eligibility policy; originating provider for other external facts | Store source and observation status, not an invented verified boolean. Keep membership-number presence separate from ID validity. |

Treat `sparq_profiles.combine_metrics` and copied demographic fields as attributed snapshots or athlete-entered overrides, never a second silently competing GMTM master. Separate `source_observation` from `athlete_preference`; refresh the former without overwriting goals, notes or approved work. Agent-originated links should remain explicit private suggestions until the athlete chooses a supported canonical-profile update.

Use namespaced source references such as `(gmtm, user_id)`, plus event/task/submission IDs. Preserve exact `type:title` question keys and a task-definition hash until GMTM offers stable question IDs. Never use a metric-template ID as answer identity: the two shuttle directions share a template. Do not rekey GMTM or introduce cross-database foreign keys. Validate references in the adapter and reconcile missing/deleted entities.

Clerk actor, represented athlete and organization role must remain distinct concepts. Preserve the current one-linked-athlete rule until actual guardian delegation is verified. A future delegation record needs actor, athlete, scope, granting authority, evidence and revocation; junior age alone is not permission. Private goals/conversations must not flow to organization dashboards by default. Sharing needs an explicit audience/field selection and revocation, with source visibility checked again when read.

## Integration and freshness

For now, centralize direct GMTM reads behind the bounded adapter; do not let every feature add SQL. Return source IDs, definition version/hash, observed-at time and explicit unknown/stale states. Use the same snapshot for the checklist and conversational help. Recheck on return from GMTM; ordinary missing results must remain different from a failed source read.

Next, move one proven capability at a time behind narrow GMTM-owned APIs. A future write must validate actor and athlete scope, expected source version, idempotency key and the exact approved action. GMTM commits its own record; Agent records the receipt. Avoid synchronous writes to both databases pretending to be one transaction. Keep existing GMTM submission UI during this transition.

Start with request-time reads and bounded polling only for active, consented workflows. Timestamp/ID cursors alone can miss edits and visibility removals; periodically reconcile current source state and use definition hashes. Add source events only when freshness/load measurements justify them. Prefer a transactional outbox written alongside the owning service's change, then an idempotent consumer. The outbox pattern addresses divergence between persisted state and emitted events; it does not eliminate retries or make two databases one transaction ([Debezium primary documentation](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)). An Agent outbox cannot atomically describe a GMTM transaction: that event must originate in GMTM.

Defer raw-table CDC. For this team it adds change-stream operations and broad schema/privacy coupling before a demonstrated need. Outbox and CDC are not mutually exclusive: CDC can later transport a deliberately narrow outbox if scale warrants it. No Kafka, Debezium deployment or new vendor is proposed now.

## Reliability and cost

Replace daemon-thread matching with a small durable job table and one bounded worker using the existing Agent database. Store job key, status, lease expiry, attempts, next-run time, input version and result/error reference. Recover expired leases and cap retries; approved external actions need a version-specific idempotency key and delivery receipt. The current `threading.Thread(..., daemon=True)` is not durable (`backend/workspace_bootstrap.py:146–151`).

Verify the actual Agent MySQL version and indexes before choosing worker-locking SQL. MySQL documents `SKIP LOCKED` as suitable for queue-like tables, while warning its view is unsuitable for general transactional reads; use it only if supported and needed for concurrent workers ([MySQL primary documentation](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)). Begin with one worker and measured concurrency, not a new orchestration platform.

Record model tokens/cost estimates per request and job; reserve a budget before dispatch and reconcile actual usage afterward. Cap per-athlete daily spend, research breadth, tool calls, retry count and concurrent jobs. Reuse matching results only for equivalent, versioned inputs. Never launch expensive recruiting bootstrap merely to show current combine requirements.

## First 30 / 60 / 90 days

| Window | Priority and exit evidence |
| --- | --- |
| 0–30 days | Validate user 2 through a controlled read-only path; finish checklist/chat snapshot consistency; establish live schema/ownership/freshness receipts; document copied-field ownership; move import-time DDL to explicit versioned migrations; add source-unavailable monitoring and budget limits. Keep source writes in GMTM. |
| 31–60 days | Add durable Agent jobs and action-version receipts; persist athlete event preference; implement private-by-default sharing and revocation; trace guardian roles with real permitted actors; replace stale bootstrap facts with attributed observations. Test restart/retry and account-switch scenarios before broad rollout. |
| 61–90 days | Implement at most one justified narrow GMTM API integration, with approval and idempotency. Add outbox events only where measured polling/freshness pain exists. Build organization reporting from authorized source records, not private chat. Retire a duplicate path only after parity checks and rollback evidence. |

Dates are sequencing targets, not a promise to complete every feature in three months. For a two-person team, keep one active product slice and one reliability track; defer integrations without a named athlete or organizer benefit.

## Remaining evidence gaps

Agent MySQL version/schema and actual deployed connection configuration remain unverified. Fable's landscape identifies the shared GMTM backend but is a September 1 source snapshot; its MySQL 5.7 statement is superseded by the bundle README's owner-reported 8.4.11 baseline (`/Users/joey/Desktop/gmtm-code-research/gmtm-repo-landscape-2026-09-01.md:9–11,42–51`; `README.md:7,12–17`). Worker runtimes, current guardian behavior, source deletion semantics and verified-scoring provenance still need evidence.

Authenticated GMTM navigation can write even when presented as a GET: fixed core `getVirtual` calls `importEvent` and updates invitations (`work/sparq-platform-reconciliation-2026-09-06/core-virtual-1bf4fc02.js:56–65`). Controlled read-only validation must avoid that path or intercept requests. Full app import also executes table setup today (`backend/profile_api.py:291`; `backend/claims_api.py:182`). No AWS/RDS/IAM/account changes, core deployment, production writes or big-bang migration are part of this recommendation.

Paths beginning `backend/` or `docs/` refer to `work/sparq-agent-review`; fixed core source paths refer to the enclosing task workspace. Prior verification evidence: `.sammy/handoffs/2026-09-06-current-combine-build.md:21–45`. Active conversational-help edits were not treated as completed functionality in this memo.
