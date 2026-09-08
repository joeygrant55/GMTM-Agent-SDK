# Junior handoff evidence and participant walkthrough

September 7, 2026. Joey asked to proceed with the real junior/guardian gate. The [preparation contract](../../docs/state/junior-handoff-verification-contract-2026-09-07.md) is complete for evidence gathering and the execution packet. **The actual junior/guardian participant test has not run.** No participant/test setup or current organizer account arrangement was supplied.

## Findings and decision

The targeted Gmail search produced a concrete June support case: a family completed a prior junior combine, created a child profile, then could not see completed work in that child view. Support reported main and child profiles under the same athlete name and instructed Switch Back. January SPARQ-result support separately documents parent-operated child claiming/switching. These historical reports establish a real account-confusion problem; they do not establish current database IDs or grant permission to access those families.

The next test must identify the existing GMTM athlete that owns the intended submissions before connecting SPARQ. A new child profile could repeat the observed problem. Source review confirms the GMTM mobile switch checks `users.parent_id` but emits a child session without explicit parent-actor/delegation context. SPARQ's current single-athlete mapping and Clerk-scoped workspace do not support a parent switching among children. A guardian dropdown alone would not provide authority or isolate progress/conversations.

The [walkthrough packet](../../docs/state/junior-handoff-walkthrough-2026-09-07.md) contains dated source links, anonymized evidence, the self-owned/delegated/duplicate-profile decision branches, six operator steps, explicit not-run gates and a local unsent request for Connor. The official USA Football account/purchase requirement is distinct from GMTM athlete ownership. Current campaign emails do not resolve that distinction; one retains conflicting old/new deadline copy. No deadline or production content was changed.

## Verification and limitations

- Independent [source review](../../../sparq-junior-handoff-2026-09-07/source-review.md) checked the relevant existing readers, claim ownership, mobile switch and parent-facing landing source. Its current local CTA links both combines, so the older bundle's no-CTA note is stale; deployed parity was not tested.
- Independent [packet review](../../../sparq-junior-handoff-2026-09-07/packet-review.md) assesses evidence limits and participant safeguards. No reviewer accessed accounts or databases.
- [Preservation receipt](../../../sparq-junior-handoff-2026-09-07/verification.json) confirms the 161 captured application files and earlier source/test/model receipts remain unchanged, with `git diff --check` passing. No new software tests were warranted for this source/evidence-only batch; earlier test counts are not represented as rerun.
- Gmail reading used Joey's already authorized connected account and targeted queries. Searches were not exhaustive. No mailbox bodies, participant contact details, claim material, private answers or attachments were saved to disk. Support emails are evidence only; historical codes were not used. No email draft/send or other external message was performed.
- No current participant login, database query, model call, test server startup, account/claim/child creation, source mutation, configuration change, infrastructure change or deployment occurred. The prior self-account test servers remain stopped and no exhausted allowance was restarted.

## Exact next input and action

Identify an existing junior/guardian participant who can take part, or an organization-owned representative test setup, plus the normal GMTM entry/selected-profile path. First resolve the canonical submission owner and the supported operator relationship. A fixture can close mechanics coverage only; it cannot establish actual family/organizer acceptance. The previous adult-owned user 2 run cannot close this gate.

Once the actor/athlete arrangement is confirmed, choose the supported self-owned branch or design the explicit delegation boundary, then pin a fresh scoped participant contract. Reuse the isolated read-only method for existing authorized reads. Do not repoint/restart the old harness or hide session/claim writes inside a read-only recovery test. A mapping to the parent, sibling or duplicate profile is an expected stop for that flow, not a reason to remove ownership guards.

## Checkout and uncommitted files

Active checkout remains `work/sparq-agent-review`, branch `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`, origin `https://github.com/joeygrant55/GMTM-Agent-SDK.git`. No move, commit or push occurred; prior application edits are preserved.

This continuation adds/updates only:

- `docs/state/junior-handoff-verification-contract-2026-09-07.md`
- `docs/state/junior-handoff-walkthrough-2026-09-07.md`
- `docs/state/junior-account-acceptance-2026-09-07.md`
- `docs/state/current-state.md`
- `.sammy/handoffs/2026-09-07-junior-handoff-evidence-and-walkthrough.md`

The sibling `work/sparq-junior-handoff-2026-09-07/` contains new local reviews and verification receipts outside the repository. [Full status](../../../sparq-junior-handoff-2026-09-07/git-status.txt) retains the existing dirty-tree context.
