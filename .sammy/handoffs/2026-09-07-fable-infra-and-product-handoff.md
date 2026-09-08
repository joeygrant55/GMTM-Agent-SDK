# Fable infrastructure update and Codex return notes

Recorded September 7, 2026. Purpose: preserve Joey's incoming infrastructure update and prepare a reviewable handoff for Fable. Documentation only; no infrastructure action, application edit, deployment or message is authorized by this record.

## Incoming infrastructure report

Source: Fable's report pasted by Joey, timestamped **00:20 UTC**, described as two days after the MySQL upgrade. No calendar date accompanied that timestamp; no date is inferred for the measurement window. Codex did not independently query infrastructure in this continuation.

| Area | Fable reports |
| --- | --- |
| Production `db2-dev` | MySQL 8.4.11; CPU 5% average / 17% peak; free memory minimum 18.6 GB; latency below 1 ms; connections 207 average / 322 peak; alarm OK; free storage 55 GB. No database problems over two days. |
| Other database resources | `development` on 8.4.11; `pre-prod` stopped; rehearsal copy deleted; four snapshots retained as planned. |
| Search | `gmtm-v2` green; both zones active; 8.61 million documents. |
| Availability | API, gmtm.com home and coaches, gmtm.com database route, SPARQ site and SPARQ backend returned HTTP 200. Specific response bodies and deployed commit IDs were not included. |
| Lambda errors | Five errors in one function over the last 24 hours, attributed to Apple push timeouts at 12:45–13:56 UTC; reported self-cleared and unrelated to the database. |
| Alarms | “Insufficient data” attributed to old EC2 CPU alarms on stopped instances. |

Fable's remaining plans: delete `pre-prod` before Saturday's automatic restart; consider shrinking production from Tuesday based on memory use. Those windows and execution remain with Fable. This is a record of the owner's plan, not Codex validation of instance sizing, deletion readiness or change authorization.

Existing boundaries remain: use `db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com` for approved GMTM reads; never select `pre-prod`. No RDS/IAM/parameter-group changes, new production MySQL accounts, password-plugin changes or GMTM API deployment from this lane.

## Return notes for Fable

### 1. Please review the legacy child-removal finding first

Our offline rehearsal of the inspected GMTM resolver reproduced an ownership gap: an unrelated authenticated synthetic parent could detach another family's child through `removeChildAccount`. The source checks authentication and contact/claim prerequisites but does not verify the recorded parent before detaching. The inspected route and session hook had no separate per-child gate. **No real endpoint was probed and current production exposure is not established.**

The final candidate is [removeChildAccount.draft.patch](../../../sparq-family-rehearsal-2026-09-07/legacy/removeChildAccount.draft.patch), with the [reproduction and integration limits](../../../sparq-family-rehearsal-2026-09-07/legacy/README.md), [results](../../../sparq-family-rehearsal-2026-09-07/legacy/results.json) and [source provenance](../../../sparq-family-rehearsal-2026-09-07/legacy/source-provenance.json). It is **unapplied**; the shared GMTM checkout was untouched. Do not use the earlier `guard-superseded` proposal.

The patch validates IDs, reads and verifies ownership inside a transaction with `FOR UPDATE`, scopes updates to both child and parent, checks affected rows and avoids duplicate terminal cleanup after the current helper releases its connection. A commit failure is an indeterminate database outcome, not a proven rollback or permission to retry automatically.

Reference resolver label: `1bf4fc02`. The inspected local core clone was at `f2fe121d16073de34d4e2a3a1bc94514388d236c`, and the resolver bytes matched the pin. Please reconcile with your **current source and deployed revision** before deciding applicability. Read-only `git apply --check` passed against the inspected clone; this does not prove integration.

Requested next review: isolated tests using the actual transaction wrapper, MySQL, Redis and HTTP authentication. Cover owned/unrelated parent cases, invalid IDs, affected rows, concurrency, rollback/commit failures, contact/claim behavior and existing switched-session revocation. Review and test before proposing any production change; no deployment or real participant mutation is part of this handoff.

The legacy runner has **31 passing harness assertions, including one that deliberately preserves the original authorization failure**. It is not a clean set of 31 product acceptance tests.

### 2. Family identity remains a distinct integration gap

Legacy parent-to-child switching checks the relationship in the inspected source, but constructs a child-only session without explicit guardian actor/delegation provenance. SPARQ currently links one Clerk identity to one GMTM athlete. Selecting a child in GMTM does not establish authority to link that child in SPARQ.

We need an explicit server-verified actor/athlete contract and separate state for delegated family access. Matching a name or reassigning a link is not a valid bridge. Joey has no ready family test account. Synthetic engineering can continue; an actual organizer/participant walkthrough and canonical submission-owning profile are still needed for real junior acceptance. Please identify the current session/profile authority source and any existing supported family testing setup.

### 3. Codex's local SPARQ status

The latest local fix makes the combine reader verify exact Clerk identity, a strict athlete ID and a unique reverse owner before GMTM reads or model work. This closes case-collision and conflicting-owner cases that connection recovery already refused. **423 backend tests passed, including 22 family cases**, under recorded unchanged source hashes. These existing results were reviewed for this note; the suite was not rerun for documentation edits.

The [family implementation handoff](2026-09-07-family-rehearsal-and-ownership-fix.md) carries the receipts. Earlier real self-account acceptance used Joey's athlete 2 and predates this additional ownership lookup; it is not live acceptance of today's source. The local current-combine/help/recovery changes remain uncommitted and undeployed. HTTP 200s for the SPARQ site/backend do not establish that these features are live or working end to end.

The remaining pilot gates include current-source authenticated acceptance, a saved GMTM submission reflected after return, supported onboarding and canonical identity, operational/usage controls and an explicit release decision. A small adult pilot was suggested to Joey; it has not been approved or launched. Junior delegation remains a separate unfinished capability.

The previous provider inventory found an invalid OpenAI binding in Railway. A separate mini-held credential supported bounded local synthetic Luna tests without being persisted into Railway. No production provider switch occurred. This is historical configuration evidence; recheck only in an authorized provider configuration task, and never place credentials in a handoff.

### 4. Keep the lanes clear

Fable owns the infrastructure work already underway and can review/reconcile the core API patch in its existing lane. Codex retains the Agent checkout below. Please return current API commit/path, applicability of the removal finding, isolated integration results and the proposed family authority contract. There is no need to wait for a real family before doing source review and isolated mechanics testing.

Agent checkout on the MacBook:

`/Users/joey/Documents/Codex/2026-09-04/higgsfield-plugin-app-6a3293e129088191abf0875820e839da-openai-curated/work/sparq-agent-review`

Branch `codex/athlete-home-first-value`; HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`; origin `https://github.com/joeygrant55/GMTM-Agent-SDK.git`. The patch and receipts live in the sibling `work/sparq-family-rehearsal-2026-09-07/legacy/` directory. These uncommitted local files are not available just by pulling GitHub. No checkout relocation or overwrite is requested.

## This coordination pass

Changed only:

- `docs/state/current-state.md`: added the attributed incoming report and coordination pointer.
- This dated handoff: recorded exact reported metrics, return notes, limits and next actions.

Verification passed: all **170 captured application files are unchanged**, all **six local links** in the new handoff/state section resolve, and the new text plus repository diff pass whitespace checks. Independent read-only review confirmed the legacy finding, source provenance, final candidate status and integration limits against the existing patch/results. No application test suite was rerun for documentation edits.

All prior application edits remain local and uncommitted. No commit, push, cloud query, deployment, service/model test, participant action or external message occurred. Joey can share this note with Fable; Codex has not sent it.
