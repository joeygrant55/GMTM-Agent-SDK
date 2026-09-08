# Native Codex-to-Fable coordination verified

September 7, 2026 Eastern. Goal: address Joey's existing MacBook Terminal session named **GMTM**, deliver one bounded coordination note, and verify recipient acknowledgment without resuming a competing executor or changing its permissions.

## Result

**Delivered and acknowledged.** The short-lived Claude relay listed agents and sent exactly one message to the unique local GMTM session. Native `SendMessage` returned success with message ID `4fe9f5c9-bf8c-48ef-8104-5d669992f679`. Fable then wrote the requested [ACK](../../../sparq-fable-relay-2026-09-07/ack-codex-gmtm-20260907-01.md), confirming the handoff was read and providing current status. Delivery and acknowledgment were verified separately.

Evidence under [the relay directory](../../../sparq-fable-relay-2026-09-07/):

- `request-codex-gmtm-20260907-01.txt`: frozen message with request ID, source pointer, exact ACK path and coordination-only scope.
- `relay_once.py`: bounded native CLI relay; no application/terminal/SQL tools.
- `receipt-sandbox.json`: no tool calls, zero cost; existing Claude sign-in unavailable inside the sandbox.
- `receipt-approved-host.json`: approved host execution using the existing sign-in; exactly `ListAgents` then `SendMessage`, three model turns, $0.23485525 reported relay cost under the $0.25 cap. No login flow or credential replacement occurred.
- `manifest.json`: exact target identity, message/script/ACK hashes, delivery ID and acknowledged status.

The target metadata is `/Users/joey/.claude/sessions/52080.json`, session UUID `9bfcf13d-9555-48b2-863f-7e871115eae2`, interactive name GMTM, working directory `/Users/joey`, observed CLI 2.1.261. It was busy when discovered. The launcher is Claude CLI 2.1.263. These process details are temporary; verify the target afresh on another run.

## Supported mechanism and boundaries

Claude's [cross-session messaging documentation](https://code.claude.com/docs/en/cross-session-messaging) describes native `ListAgents`/`SendMessage`, noninteractive peers, delivery between tool calls and per-session inbound controls. We used those native tools, not an invented socket protocol or Terminal UI automation. Direct Terminal UI access remains unavailable; it was not circumvented.

The messenger was a separate limited courier, not a resumed or forked GMTM worker. Safe mode disabled ordinary customizations, the tool allowlist was only `ListAgents,SendMessage`, MCP servers were disabled, manual permission mode and no permission prompts were selected, and turn/cost limits bounded the relay. Managed policy still applies. No target permissions, hooks, credentials, configuration, model selection or approval mode were changed. The relay exited after sending.

The source request explicitly says its quoted proposed approval is not Joey's approval. It requested only artifact reading and an ACK at the next safe checkpoint; it requested no source edit, test, infrastructure change or deployment. Existing separately granted approvals in Fable's conversation remain with that scope. No automatic inbox watcher, recurring job, fleet dispatch or background retry loop was created.

## What Fable reported back

These are Fable's owner-reported observations from the ACK and his updated [review/addendum](/Users/joey/Desktop/gmtm-code-research/review-removeChildAccount-patch-2026-09-07.md); Codex did not verify them in AWS or by rerunning his tests:

- The patch is committed locally on `fix/remove-child-account-ownership`, commit `c5628bea`, in `~/mercor-scan/repos/gmtm-api-v2`; not pushed at the ACK checkpoint.
- The 2020 `development` schema lacks `users.parent_id` and `claim_codes`. It cannot exercise this patch without schema work. He reports separate Joey approval for the infrastructure/test work and says a temporary restore named `family-test` is restoring from the post-upgrade snapshot. Instance deletion after the run remains his planned cleanup, not completed here.
- His 12-group real-module harness includes ordinary-account protection, contact branches, claim rollback, malformed IDs, and the corrected two-connection locking expectation. The actual run and subsequent PR are still pending in the ACK.
- Actual unauthorized helper status is **403**. Our previous 401 shorthand should not be copied into the integration assertions. The ownership denial recommendation is unchanged.
- HTTP session-hook and Redis/session-revocation coverage remain separate from the real-database module test.

The ACK reports existing approval in Fable's chat; Codex did not grant it, independently inspect that approval exchange or acquire infrastructure authority from the message.

## Repeat-use contract

For later technical coordination, verify the current exact GMTM name/session, prepare a fresh request ID and reply file, and use a fresh bounded packet. Preserve this packet and both receipts. Never rerun this successful request, resume the live executor as a workaround, or forward an agent's proposal as Joey's consent. A native hold/refusal or an uncertain send is a stop for that attempt, not a reason to change inbound controls or blindly resend. Checking the ACK during active Codex work is separate from scheduling a future wake-up.

This proved an on-demand exchange. General unattended monitoring/dispatch would be separate setup in the organization lane. The relay's cost cap covers its own inference only, not the receiving Fable turn.

## Verification and uncommitted scope

The relay script compiles. Exactly one native send was observed, its recipient was GMTM, and its message matches the prepared request apart from the final newline. Native success, actual ACK contents and artifact hashes were inspected. Independent review assessed the documented relay approach before execution. Final verification passed: 170 SPARQ application files unchanged, eight local links resolved, whitespace clean, and script/ACK hashes matched. The relay process exited. See `verification.json` in the relay directory; no application tests were rerun for this coordination pass.

Files changed in the SPARQ repo: `docs/state/current-state.md`, the earlier coordination-options note and this new handoff. New sibling artifacts are under `work/sparq-fable-relay-2026-09-07/`. Prior Agent code remains local and uncommitted; no SPARQ commit, push, deployment, provider allowance reset or application edit occurred. Fable's separate core commit/infrastructure progress is reported above rather than claimed as Codex work.
