# Conversational combine help and controlled validation

September 6, 2026. Joey approved continuing after the locally verified combine-progress slice and designated **GMTM athlete user 2** as his own test profile. He reports no submission to the current USA Football combine; this is a useful expected zero-submission case, not a live observation. He also requested the longer-term GMTM/SPARQ data architecture recommendation.

## Completion contract

1. Reuse the existing deterministic, owner-scoped current-combine service for both the checklist and conversational help. Each help request reloads source state. Browser-supplied snapshots, caller IDs and model-selected athlete IDs cannot substitute for server-resolved authorization.
2. Add authenticated `POST /api/combine/help` with a supported event, optional current-event task, bounded question and optional bounded user/assistant history. Reject extra fields and validate source ownership/event/task before model work. Return SSE text/tool/done/error events; this help path does not create a generic recruiting profile, save conversation rows or execute source writes.
3. A no-argument model tool returns the bounded, already-loaded request snapshot. No SQL, arbitrary source lookup, web-search or write tools are provided in this help mode. Source instructions and prior messages are content, not permissions. Distinguish submissions, required-field presence, review, membership, eligibility and selection. Preserve the known deadline/highlight/adult-label decisions.
4. Provide activity-specific help within the existing shell. Static organizer instructions and the GMTM continuation remain useful before or during model failure. Explicit Send triggers model work; opening help or loading the workspace does not. Keep in-session history isolated from generic recruiting conversations and reset/cancel on relevant account/event/task changes.
5. Bound request size, input history, model iterations, output, time and per-account concurrency/rate. Report failures explicitly; no successful terminal event after a failed generation. Process-local limits are not advertised as durable cross-instance usage accounting.
6. Run relevant existing regressions, new backend/help tests, current-source TypeScript and actual-component browser checks. Independently review correctness-critical changes. Keep live-model answer quality, real identity and source data acceptance separate from synthetic contract checks.
7. Produce a safe read-only verification runner for user 2, with exact permitted GMTM host validation, existing unique ownership mapping, read-only transactions, SELECT-only query guards, explicit inputs and redacted receipts. Do not import application modules with table setup or create/reassign a profile to make the check pass. Run it live only if an existing authorized configuration is available; otherwise report the concrete missing dependency.

## Shared request and UI contract

`POST /api/combine/help` accepts `{ event_id, task_id?, message, history? }`: event 1317 or 1318, positive task ID or null, trimmed question of 1–2000 characters, at most 12 alternating user/assistant history items of 1–2000 characters each and at most 12000 history characters total. Local welcome text and failed turns are excluded from history.

SSE events use `text` with text, `tool` with name `get_current_combine`, `done`, or `error` with a safe message. No conversation/session ID is returned. Expected HTTP failures include 404 unavailable event/task, 409 ambiguous link, 503 source/configuration failure, 422 invalid input and 429 request limit.

The scoped provider carries the confirmed current event and optional selected activity between the checklist, shell and help panel. It is scoped to the authenticated account and cleared when the combine view changes. The frontend sends only locator IDs and conversation text. A refresh does not invent success, and an old response cannot populate a new account/event/task.

## Ownership and current boundaries

- Backend writer: reusable combine reader; new combine-help API/context and focused tests.
- Frontend writer: provider/help panel, current-card/shell wiring and help-browser harness; minimal compatibility updates to prior harnesses.
- Independent architecture/validation writer: architecture memo and isolated read-only runner/tests.
- Root: router registration, offline async-model guard, integration, state/handoff, verification and user-facing recommendation.

No deployment, AWS/RDS/IAM/parameter-group/account change, core API deployment, payment change, external message, real submission or production write is authorized by this local implementation contract. The source application's authenticated event GET can update invitation state, and full backend imports can initialize tables; neither is treated as a harmless read-only shortcut. Existing user tabs and other implementation checkouts remain separate.

Initial live preflight found no local Agent/GMTM DB environment, no Railway CLI and no linked local deployment configuration. The existing GMTM Chrome tab is on signup with sign-in available, not an authenticated test session. Do not record user 2 as live-validated until the missing access and actual observation are resolved.

## Longer-term data direction

Keep GMTM authoritative for canonical athlete/event/submission/measurement evidence and keep SPARQ authoritative for goals, conversations, plans and approved actions. Centralize source reads now; migrate justified interactions to narrow owning-service APIs later. Avoid competing writable copies or a full platform/database migration while validating the product. The architecture memo will distinguish evidenced Agent MySQL from any unverified Convex usage and propose practical reliability/freshness milestones.

The current help implementation deliberately keeps conversation history in the session; durable event-scoped conversations, jobs, consented sharing and measured outcome reporting remain later capabilities.

## Local completion checkpoint

Implementation and isolated verification are complete: 270 backend tests, 47 account checks, 75 combine-journey checks, 50 help-component checks, TypeScript and actual authenticated route registration passed. Independent backend, frontend and read-only-runner source reviews found no blocker for their stated local scope. Final receipt hashes match current tested source.

The configuration-only runner reported missing database settings, without DNS or database access. User 2 is not live-validated. Live source/auth/model acceptance, real ASGI streaming/disconnect behavior and durable cross-instance cost limits remain distinct gates. See `.sammy/handoffs/2026-09-06-combine-help-and-data-direction.md` for evidence and the next action. All changes are local and uncommitted.
