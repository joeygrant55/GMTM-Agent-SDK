# Engineering lead contract — September 7, 2026

Joey's current instruction: “begin taking the lead on all of our builds and everything we are doing really. Use fable as needed and make sure you help spec and review everything fable is doing. Use it to gain additional context and information on the entire code base, but ultimately you know the overall direction of where we are going”.

The shared MacBook role decision is recorded in [Control Tower](/Users/joey/clawd/docs/strategy/codex-engineering-lead-2026-09-07.md). This document supplies the initial product execution contract. Fable's [readback](../../../sparq-engineering-lead-2026-09-07/fable-engineering-readback.md) acknowledges the arrangement; other project/session adoption is still separate.

## Ownership

Codex leads engineering priorities, product/technical specifications, architecture tradeoffs, scoped task delegation, implementation integration, review and release-readiness recommendations. Fable provides codebase/infrastructure context, challenge and independent review, and continues explicitly assigned implementation work. Sammy/Hermes retains cross-machine reconciliation and durable coordination support.

Existing writers retain their active checkouts and authorized work until a deliberate handoff. Leadership does not mean concurrent edits in Fable's checkout. Material new work or scope changes should have a brief Codex-reviewed specification; completed work returns a diff, source revision, verification and remaining risks for review. Routine reversible fixes get proportionate review rather than another planning ceremony. Current urgent, separately approved work should continue while the handoff is assembled.

Joey retains business direction and existing explicit approval boundaries: production deployment/data, AWS/RDS/IAM changes, DNS, billing/payment settings, App Store submission, external customer messages and destructive cleanup. Existing specific approvals remain scoped and valid; coordination messages and this contract do not create new ones. Codex does not operate the protected GMTM AWS/API deployment lane by taking engineering leadership.

## Product direction

GMTM/SPARQ remains the immediate priority: help the correct athlete finish the existing USA Football digital combine, return to truthful progress, and build a useful continuing profile. Keep GMTM authoritative for athlete/event/submission/measurement evidence and SPARQ responsible for Agent-owned goals, conversation and plans. Athlete identity, guardian authority and source freshness must be explicit. Organization expansion should reduce onboarding/support work and produce a paid, measurable outcome.

Other active builds enter the engineering overview with their existing owners and project-specific goals. Registry entries and old handoffs are discovery pointers, not proof of current readiness or permission to replace an executor. Machine/folder reorganization and unattended fleet dispatch remain separate from this leadership assignment.

## First execution sequence

| Package | Owner / reviewer | Completion evidence |
| --- | --- | --- |
| Urgent GMTM ownership fix | Fable executes current approved core/test work; Codex reviews | Exact committed diff matches the intended fix; real isolated DB test receipts and cleanup; explicit coverage limits; PR ready for review. Deployment remains a later authorized decision. |
| Adult-combine release candidate | Codex builds; Fable reviews integration | One supported entry/recovery/checklist/help/GMTM-return path; reviewed source/config manifest; isolated full-startup proof; reachable surfaces work or fail truthfully. |
| Complete athlete acceptance | Codex owns; Fable supplies source contracts/fixtures | Exact athlete/event ownership, zero/partial/submitted states, saved-submission return-refresh, expired auth/source failure and phone behavior on the recorded candidate. Synthetic mechanics and real participant acceptance stay distinct. |
| Cohort measurement and commercial test | Codex implements; Joey/Charles define distribution/offer; Fable reviews operation | Baseline and clear event definitions; minimal authorized organizer reporting; support/usage/error/rollback controls; explicit release decision and deployed critical-path verification. |

Adult-only is the proposed first pilot scope, not an approved public rollout or a change to the existing junior GMTM program. Guardian delegation, broad outreach, full organization dashboards and payment plumbing wait for a supported need; faults on any unavoidable pilot path must still be addressed.

## Working loop and evidence

For each material build, use a concise contract: user/customer outcome, evidence/current source, scope, exact writer/checkout, dependencies, acceptance criteria and approval boundary. Review the spec before a new substantial implementation, preserve the writer's work, review the actual diff, then verify the candidate. Treat local tests, real integration, reviewed PR and deployed acceptance as different states. A count of tests or tasks is not a customer outcome.

Use the verified native GMTM message route for bounded technical coordination and durable response files. A request ID needs a receipt and recipient readback; no agent can approve on Joey's behalf. Seek facts from Fable before duplicating his codebase research, then verify the contracts and modules actually needed by the next product slice. Do not wait for a whole-platform audit to finish a bounded product improvement.

This initial adoption is complete when the role decision is recorded, GMTM/Fable acknowledges the working arrangement and supplies a current source/work inventory, and the near-term priorities and unresolved owners are visible. It does not claim every project or session has adopted the change. No scheduler, automatic approval, broad configuration sync or new company-wide queue is part of it.
