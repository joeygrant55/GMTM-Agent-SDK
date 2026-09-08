# Codex and Fable coordination options

September 7, 2026 Eastern. Joey asks for a better way to collaborate with Fable without relaying every message. This is a read-only capability assessment plus a proposed minimal workflow, not an activated service or dispatch authorization.

**Later outcome:** Joey identified the MacBook Terminal session named GMTM. A one-time native Claude peer relay delivered a scoped note and Fable wrote the requested ACK. See the [verified direct-coordination handoff](2026-09-07-gmtm-direct-coordination.md). The limitations below describe the initial assessment; there is still no permanent watcher or approval delegation.

## What works now

Both lanes have demonstrated artifact exchange: Fable writes reviews under `/Users/joey/Desktop/gmtm-code-research/`, Codex reads them, and Fable has reviewed Codex's local patch and receipts. Existing dated files and the [latest security handoff](2026-09-07-fable-security-review-reconciliation.md) can remain the source of truth without moving checkouts.

The [Control Tower operating contract](/Users/joey/clawd/docs/strategy/agent-operating-contract-2026-09-05.md) already specifies durable handoffs, one writer per checkout, reviewer/executor roles and separate production approvals. The [handoff template](/Users/joey/clawd/templates/agent-handoff.md) provides the required fields.

The installed Claude CLI advertises noninteractive review, session-specific resume and session inventory. The read-only `claude agents --json` inventory did not identify a GMTM infrastructure session; its sole result was an unrelated working session. No inference, resume, fork, interruption or message was performed. A new Claude review invocation would be a separate agent unless explicitly tied to a verified session; it must not be represented as the current Fable receiving a message. Resuming a running session can create a copy according to installed help, so it is not a safe substitute for delivery to the existing writer.

Direct Terminal UI access is denied by the computer-use tool in this session. A process inventory was also unavailable under the shell sandbox; no escalation or alternate UI control was attempted. The purpose-built CLI inventory above is read-only metadata, not Terminal control. The Codex thread inventory provides no direct address for this Fable session.

## Recommended minimal loop

1. Keep request/reply artifacts in the existing research and repo handoff locations. Each request names sender, recipient, unique ID, goal, source files/commit, authorized scope, acceptance checks and reply path.
2. Deliver a short pointer to the verified Fable session at a safe checkpoint. Require acknowledgment of the request ID and source revision before calling it received. Written, delivered, acknowledged and completed are separate states.
3. Fable writes the result to the stated reply path; Codex reads it, resolves findings and reports product impact to Joey. Neither lane edits the other's live checkout.
4. Once a direct delivery mechanism is identified, add only the notification/acknowledgment adapter needed for this loop. Bound retries and prevent duplicate dispatch or message ping-pong. Do not feed reference notes into an executable fleet queue.
5. Carry Joey's actual approvals verbatim and scoped to their action/environment. An agent request, review verdict, suggested approval text or mailbox message does not grant a password reset or deployment.

At this initial assessment, the machine/app containing the current GMTM Fable session was pending. That input and the first delivery/ACK are now resolved by the later outcome above. Writing a file alone still does not wake either agent automatically.

## Other options

- Bounded independent Claude CLI review can supplement this warm Fable session when specifically tasked; it needs explicit context, limited tools and a finite budget.
- GitHub PRs provide durable code review after sharing is authorized. Uncommitted local work does not appear there automatically.
- Hermes on the always-on mini could eventually relay notifications. Historical fleet observations include auto-dispatch, so first confirm current behavior and keep message delivery separate from execution. This setup belongs in the existing organization lane if it expands beyond a narrow project adapter.

## Verification and scope

Read the current contract, sync guidance, local handoff template, CLI help/session inventory and tool/app availability. Independent bounded read-only review found no demonstrated automated mailbox in the inspected local Control Tower scripts/docs. That is not a claim that no bridge exists anywhere on either machine.

Only this handoff and the brief pointer in `docs/state/current-state.md` are changed. No application, model, queue, service, configuration, approval, external message, commit or push action occurred. Existing work remains local and uncommitted. Check local links and whitespace before closing; no application tests are warranted for this documentation-only proposal.
