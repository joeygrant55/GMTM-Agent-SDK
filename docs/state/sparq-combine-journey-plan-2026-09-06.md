# SPARQ current-combine journey — implementation plan

September 6, 2026. Milestone 2 of the [build plan](sparq-build-plan-2026-09-06.md). Status: the [bounded current-combine build contract](current-combine-build-contract-2026-09-06.md) is locally implemented and verified; see its [handoff](../../.sammy/handoffs/2026-09-06-current-combine-build.md). The first identity/data batch is locally implemented and isolated-tested; its live acceptance gates remain open. This document retains the larger milestone contract; local card/adapter progress does not close full live acceptance.

## Product promise and completion contract

An athlete can enter optional SPARQ help before recording any results, see the correct combine and its actual outstanding requirements, get useful help, continue submission in existing GMTM, and return to refreshed progress. The athlete should not need to understand the underlying account, database or agent architecture.

The visible loop is:

**Existing GMTM combine → optional SPARQ invitation → current combine and next requirement → submit in GMTM → return and refresh → next requirement or profile review.**

The milestone is done when that complete loop works on phone and desktop with authorized identities and source-backed requirements. Clicking a link, recording a metric or asking the Agent for help never marks a requirement complete. Submission, requirements satisfied, review and selection have separate evidence and labels.

## Scope decisions

Joey clarified on September 6 that USA Football currently runs both adult and junior digital combines. Plan one reusable implementation with separately verified event configurations and acceptance fixtures for both. The supplied official page and live public GMTM data now confirm junior 1317, adult 1318, organization 249002 and their nine-activity configurations. See the [public event contract](usaf-combine-contract-2026-09-06.md) for policy, task IDs, evidence and unresolved source conflicts. Fable's existing map identifies the relevant repositories; a fresh deep audit of every repository is not a prerequisite.

Fable's supplied folder has now been [reviewed and reconciled](gmtm-platform-reconciliation-2026-09-06.md). Core source at the reported deployed revision confirms candidate events from invitations/product access before submissions and two different parent/child relationship paths. Reuse those source relationships selectively; verify the active event and junior-account contracts rather than duplicating registration or assuming all account-switching mechanisms grant the same rights.

- Use the existing `/home/inbox` starting-point area; keep performance evidence below the combine card. Do not build a parallel combine uploader, registration or payment flow.
- A minimal current-combine view must work independently of generic recruiting-profile enrichment and college matching. Preserve sport from established event/athlete context; do not infer it from numeric results or silently default a zero-result flag athlete to tackle football.
- Use deterministic code to derive progress. The Agent explains organizer instructions and the next step from the same authorized snapshot; it cannot change official progress or invent completion rules.
- Include the phone layout needed for this journey now: readable central content, collapsed navigation and an explicit help control. Full redesign of other workspace surfaces remains later work.
- When requirements are satisfied, retain the evidence and offer private profile review. Persisted development plans, safe public sharing, coach outreach and paid entitlements remain subsequent milestones with their own acceptance gates.
- Verify the junior account/guardian model before fixing the actor-to-athlete contract. The current one-Clerk/one-athlete workspace cannot be assumed to support a guardian managing several athletes. Follow actual program eligibility, consent and visibility rules; do not invent age cutoffs or authorize a second athlete through the existing claim path. If guardian delegation is needed, define it explicitly and verify it before junior acceptance.
- Both current targets are public and have no GMTM product ID. Viewing/selecting public requirements does not require an invitation or paid-product record; reading personal submissions remains owner-scoped. Track program eligibility and external Athlete ID validity separately from task progress. Joey identifies the deadline and adult dash labels as known, nonblocking platform bugs and confirms highlights are separate playing footage. Show a sourced date-only deadline and activity progress without inventing whole-program completion.

## Build sequence

| Slice | Deliverable | Acceptance gate |
| --- | --- | --- |
| 1. Establish the GMTM contract | A versioned fixture and source map for eligibility, event access, activity visibility, required fields, submission rules and continuation | We can explain the expected status for zero submissions, partial payloads and a satisfied requirement set without guessing |
| 2. Preserve athlete and event context | An authenticated current-combine endpoint and event selection independent of results/profile enrichment | A zero-result athlete reaches the right combine; unauthorized IDs cannot expose another athlete/event; multiple events stay separate |
| 3. Calculate truthful progress | A read-only GMTM adapter and deterministic reducer with ordered activities, outstanding requirements, evidence and freshness | Supported fixtures calculate correctly; unknown rules and upstream failures cannot become false completion |
| 4. Deliver the athlete loop | Current-combine card, contextual help, verified GMTM continuation, return refresh and usable phone shell | An athlete can follow the full loop without forced recruiting onboarding, stale account state or a hidden primary action |
| 5. Verify a small cohort | Full-flow acceptance evidence plus a minimal cohort readout | Reconcile Agent status with GMTM for controlled participants before wider distribution; preserve the earlier identity release gates |

Slices 1 and 2 start first. Frontend work can proceed against the agreed fixtures while the adapter is implemented. Final integration follows the same contract. Sequence reflects dependencies, not promised calendar dates.

## 1. Establish the source contract

The core API source was verified at Joey's reported deployed revision `1bf4fc0297d5eea56bed6bda54715f2f9c01593f`. See the [source map](combine-adapter-source-map-2026-09-06.md). Source verification is not proof that live schema or behavior matches it.

Before calculating official progress, resolve:

1. **Entry and access before submission.** Identify the authoritative athlete/event registration or eligibility record, including public/open, invited and paid-event behavior. Existing participant queries based on submissions cannot identify everyone who has not submitted yet. A signed SPARQ invitation establishes its issued athlete/event context; its current admin mint operation does not itself validate GMTM registration. Verify the issuance cohort and recheck event access separately. Do not label an invitee “registered” without evidence.
2. **Applicable requirements.** Establish task inclusion, ordering, required versus optional questions, accepted payload shapes and deleted/hidden behavior. Required questions within a task and whether the task is mandatory are different rules. Current aggregate notification counts are insufficient to settle either.
3. **Submission validity.** Establish which saved attempt counts, handling of duplicates/edits/deletions, partial form answers and media processing. Preserve attempts as evidence; never combine fragments from incompatible attempts into an invented valid submission. An unsupported payload can be labeled submitted while satisfaction remains unknown.
4. **Continuation and sessions.** Verify the current web route and behavior for signed-in and signed-out athletes. SPARQ's Clerk session does not establish a GMTM session. Retain intended event/task through the supported GMTM sign-in path where available; otherwise provide a clear event-level recovery. Do not invent single sign-on or a callback.

Additional source leads were inspected in `gmtmsports/gmtm.com` at `b0293a2cc918da59afb53cc75c0cfdd71769c4a3`. Public GMTM event GETs subsequently served this build identifier; private session/submission behavior remains unverified:

- `components/organisms/Task/index.js:173–305` and `420–476` use question-level `required` and type-specific form validation.
- `pages/virtuals/[virtual_id]/tasks/[task_id].js` provides a candidate task redirect; the slugged task page checks session, visibility/invites and product access.
- The slugged task page also invokes a payment-intent API for some products during page rendering. Source inspection is safe; do not treat an automated live visit as necessarily read-only.

Use these as discovery pointers, then verify the relevant current source and target combine. Until a task route is accepted, use the established `https://gmtm.com/virtuals/{event_id}` continuation.

## 2. Proposed athlete/event API contract

Proposed route names are implementation choices, not existing endpoints:

- `GET /api/combine/current`: resolve the caller's unique linked GMTM athlete, authorized candidate events and active selection; return the current snapshot or an explicit resolution state.
- `PUT /api/combine/current`: accept an event ID and expected preference version; save the selection only after checking it belongs to the caller's authorized candidate set. This is Agent-owned preference storage, not a GMTM registration write. Reject stale conflicting changes rather than overwriting a newer selection.

Resolve athlete identity on the server. A query parameter is only a selection hint. Redeemed `claim_tokens` already retain athlete, event and claiming Clerk identity; reuse that evidence rather than storing bearer tokens or duplicating an invitation system. The claim's event should be selected on successful entry only after the access contract is satisfied. Do not choose the first numeric-result row. If several candidates exist and no current preference is valid, ask the athlete to choose.

Recheck authorization for every read and selection. Distinguish no link, ambiguous link, no authorized event, selection needed and upstream unavailable. A registration lookup failure must not silently become “no active combine” or send the athlete to unrelated onboarding.

Persist only the minimum preference needed across devices: linked athlete, active event, provenance, selection time and version; choose the existing Agent store after inspecting its schema. Claim retries must not overwrite a later explicit event choice. Any needed migration must be explicit, versioned and tested in isolation, not opportunistic request-time DDL. No changes to core GMTM schema or production data are part of implementation.

## 3. Proposed snapshot and progress rules

| Field group | Meaning |
| --- | --- |
| Identity/context | Authenticated athlete ID, selected event ID/name, authorization basis and event availability |
| Source/freshness | Source revision or contract version, successful read time and snapshot identity; never a timestamp that implies an unsuccessful refresh succeeded |
| Activities | Canonical task ID, source order, title/instructions, applicability, required/optional/unknown rules and verified continuation URL |
| Evidence | Relevant saved submission IDs/times and type-specific evidence presence; avoid exposing unnecessary personal answers |
| Progress | Independent submission, requirement-satisfaction, review and outcome states; unknown is a supported value |
| Next action | First actionable outstanding requirement in organizer order, or grounded recovery, event selection, waiting or profile review |

Use bounded parameterized reads scoped to the authenticated athlete and authorized event. Join only applicable tasks and eligible submissions. Count distinct task IDs rather than attempts. Return a consistent snapshot or a visible unavailable state; do not combine an old denominator with newly read submissions and call it authoritative completion.

Display a percentage only after the denominator and required-field rules are established. No applicable tasks or unknown rules must not produce “100% complete.” Where only submission presence is proven, say “Submitted” and offer “Check in GMTM.” Review evidence and verified selection/outcomes are separate optional fields, never inferred from submission approval, chat, clicks or manual outreach status.

The first supported payload types should be the ones the target combine actually uses. Unsupported types fall back visibly while remaining launch blockers if they are required by that combine. Do not silently reduce the target's requirements to fit the implementation.

## 4. Athlete experience and grounded help

The card shows the event name, actual progress, one next requirement, organizer instructions and a clear “Continue in GMTM” action. An expandable checklist lets athletes understand what remains. Performance measurements remain visible as evidence, not the source of active-event selection.

Refresh on entry, foreground return and explicit “Refresh progress,” with request deduplication and a short throttle. Preserve the last successful snapshot and its timestamp when a refresh fails. Cancel or disregard late responses after account/event switches. There is no assumed GMTM push callback and no success animation just because an athlete returned.

Provide “Help with this activity” using the selected task and current snapshot. Offer the organizer's instructions immediately; optional model assistance can clarify those instructions. Treat source text as content, not agent permissions. Missing instructions trigger a clear unknown/help route, and model unavailability does not block the checklist or GMTM continuation. No automatic external messages or reminder campaign is included.

On phones the checklist occupies the available width. Navigation and chat collapse into accessible controls. Verify wrapped labels, focus order, touch targets, back navigation, loading/error announcements and account recovery in the full shell. Preserve existing home evidence and claim security work while replacing the result-derived starting action.

## 5. Acceptance cases and measured pilot

Required automated/isolated cases:

- Separate adult and junior event fixtures with their actual applicable rules; correct division/event retained throughout the loop. Junior account/guardian behavior must match the confirmed source contract, including multi-athlete delegation if the supported program actually requires it.

- Correct linked athlete with an authorized event and zero metric rows; generic workspace bootstrap unavailable or still pending.
- Existing user reentry, missing/ambiguous mapping, unauthorized event injection, several events, explicit event switching, stale selection writes and claim retries preserving a later choice.
- Supported mixed task types; optional questions; required fields absent; valid zero/false values where the source permits them; duplicate and edited attempts; hidden/deleted records; no applicable tasks; unknown payload type.
- Partial submissions; submitted with unresolved validity; all applicable requirements satisfied; review and selection independently unknown or source-confirmed.
- Event not open or closed, changed requirements, inaccessible/deleted event and stale selected preference.
- GMTM round trip with no submission change, a confirmed new submission and a failed refresh; delayed responses after account/event switches.
- Full mobile shell, expired sessions, keyboard/back navigation and grounded-help provider failure. No real model, email, payment or production writes during isolated checks.

Run relevant backend contracts, frontend typecheck, component tests and full-flow browser checks. Retain earlier account-boundary regressions. Live identity, Agent MySQL concurrency/schema and actual GMTM parity are separate acceptance steps; local tests do not close them.

Propose a small controlled pilot (for example 10–20 opted-in athletes) before broader Charles distribution, subject to the actual timeline. Reconcile each participant's requirements with GMTM and record discrepancies. The 500+ promotion goal is potential reach, not promised Agent users or revenue.

Measure unique eligible/invited athletes, optional Agent activation, source-confirmed requirement completion, time from first observed incomplete state to completion, help requests/manual staff interventions and a return visit for profile review. Use explicit cohort windows and account for already-complete athletes and missing observations. Show factual changes; claim completion lift only with a defensible comparison. Collect minimal event metadata, not raw personal answers or claim tokens, for analytics.

The commercial deliverable is credible evidence for a USA Football expansion conversation: completed athlete journeys, remaining friction and staff effort. Pricing/charging and a new organization dashboard are separate decisions; use the smallest scoped readout/export that supplies this evidence.

## Implementation ownership and next action

Keep one writer per file lane in the current Codex task:

- Root: source contract, fixture/API agreement, integration, review, documentation and verification.
- Backend executor: authorized event resolution, read-only adapter, reducer and contract tests.
- Frontend executor: claim/context handoff, current-combine card, grounded-help integration, return refresh and phone shell.
- Independent reviewer: challenge authorization, zero-result assumptions, incomplete/unknown statuses and test evidence before release review.

The bounded implementation batch is complete locally after backend/frontend writers, root integration and independent review. Its handoff records verification and remaining gates. Work remains local; no unattended deployment or external communication is started.

The adult/junior URLs, event/task IDs and public form configurations are now recorded. Next implementation uses those normalized fixtures. Remaining inputs are external Athlete ID verification, current junior delegation behavior, live source parity, and Charles's promotion coverage/date. The known source conflicts have nonblocking presentation rules in the implementation contract. These gate relevant eligibility/completion/rollout claims but do not prevent the owner-scoped context and per-activity checklist work.

No push, deployment, production data change, core API deployment, infrastructure change, billing operation or external message is part of this plan's execution authority. A public rollout remains a separate explicit release decision after the required evidence exists.
