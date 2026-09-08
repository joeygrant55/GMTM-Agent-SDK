# Synthetic family rehearsal and combine ownership fix

September 7, 2026. Joey reports no family test account and believes family accounts have not been tested since the development team left. The [rehearsal contract](../../docs/state/family-rehearsal-contract-2026-09-07.md) is complete for offline mechanics, the local SPARQ fix and an unapplied GMTM patch. No real family account was needed or created. Actual family login and delegated guardian access remain unverified/unimplemented.

## Product outcome

The repeatable synthetic family contains a parent, independently authenticated child and sibling, and a separate same-name duplicate profile. The actual SPARQ handlers preserve the parent's existing link, refuse a child's claim into that parent link, keep event choice separate from athlete choice, and read only the linked athlete's submissions. Unlinked progress remains unknown. Fake child authentication supplies a test identity; it does not prove that real child sign-in or parental authority reaches SPARQ.

Two failing regression cases exposed a local SPARQ defect: connection recovery rejected case-colliding or conflicting ownership, but the combine reader returned progress. `combine_api._linked_athlete` now checks the exact returned Clerk subject and a strict positive integer athlete ID, then verifies exactly one matching reverse owner. Both queries are parameterized and bounded to two rows. Missing/ambiguous/malformed/conflicting ownership fails before GMTM access. Combine help uses the same reader and also refuses before a provider client starts. A missing forward link still permits public requirements with personal status unavailable.

The legacy source rehearsal also reproduced a separate child-removal authorization gap: an unrelated authenticated synthetic parent could detach another family's child. Parent-to-child switching itself checked the recorded relationship and rejected unrelated/sibling switching. The returned child session did not carry an explicit parent actor/delegation claim, confirming why it cannot serve as SPARQ's guardian bridge by itself.

## Verification

All evidence is local in [`work/sparq-family-rehearsal-2026-09-07/`](../../../sparq-family-rehearsal-2026-09-07/).

- [SPARQ baseline](../../../sparq-family-rehearsal-2026-09-07/sparq/baseline-receipt.json): seven cases passed and the two ownership cases failed before the fix; original source/test hashes and output are preserved. An earlier collection-only import-path error is retained separately.
- [Family regression](../../../sparq-family-rehearsal-2026-09-07/sparq/verification.json): **22 passed**, including malformed/missing/changed/repeated reverse records, case-sensitive ownership, strict IDs, actual claim/connect/recovery/combine/help handlers, no model initialization on rejection, and source-lease cleanup. Independent review reran all 22 successfully.
- [Full backend](../../../sparq-family-rehearsal-2026-09-07/backend-verification.json): **423 passed**, with all 42 tested source/fixture files unchanged during the run. The first full run had 422 passes and one stale fake-driver failure; its receipt is retained. Updating that existing read-only runner fixture to return Clerk identity fixed it. The operator runner itself was not changed.
- [Legacy results](../../../sparq-family-rehearsal-2026-09-07/legacy/results.json): **31 passing harness assertions**, including one assertion preserving the original removal authorization failure. This is not 31 passing product acceptance stories. Exact pinned list/switch/removal functions run in a restricted VM with in-memory SQL/session/Redis interfaces; no application module import, environment loading or network occurred.
- [Independent review](../../../sparq-family-rehearsal-2026-09-07/review.md) covers the SPARQ fix, regression and legacy candidate. [Final preservation](../../../sparq-family-rehearsal-2026-09-07/verification.json) verifies tested hashes, unchanged frontend/historical receipts and `git diff --check`.

No browser, live Clerk, MySQL, Redis, participant, model or production endpoint was exercised. Frontend files are unchanged, so component/TypeScript tests were not rerun. Previous live self-account evidence is historical for its recorded source: this ownership fix adds a reverse lookup and has not had current-source live acceptance. The old frozen harnesses remain stopped and must not be repointed or have their hashes/budgets reset.

## GMTM patch for its owning lane

The final candidate is [removeChildAccount.draft.patch](../../../sparq-family-rehearsal-2026-09-07/legacy/removeChildAccount.draft.patch), with [extracted candidate function](../../../sparq-family-rehearsal-2026-09-07/legacy/removeChildAccount.draft.js). It is **unapplied**. It validates scalar positive IDs, checks ownership inside a transaction with `FOR UPDATE`, restricts the update by both child and parent IDs, checks affected rows, and handles terminal transaction operations without reusing a released connection. Synthetic cases cover unrelated parents, an owned-ID prefix followed by SQL junk, simulated relationship changes, missing rows, claim reset and transaction failures.

The first guard-only proposal was insufficient: it retained raw ID interpolation and checked ownership outside the transaction. Its files are explicitly named `guard-superseded` and preserved as review history. Use only the final `draft.patch` as the candidate. A read-only patch-application check passed against the inspected local resolver; no shared GMTM file changed.

Source provenance: the reference artifact is labeled `1bf4fc02`; the inspected local core checkout is `f2fe121d16073de34d4e2a3a1bc94514388d236c`, and its resolver bytes match the pin. The local route/session-hook inspection found no per-child ownership gate before this handler. That is source evidence, not a current production vulnerability probe. See [legacy reproduction and limits](../../../sparq-family-rehearsal-2026-09-07/legacy/README.md).

Before applying/shipping, the GMTM owner must reconcile with current source and verify against isolated MySQL/Redis and the actual transaction wrapper. Row locks, affected-row behavior, concurrent changes, existing switched-session revocation and real HTTP authentication remain integration gates. The current wrapper releases on commit failure; the candidate returns failure without claiming rollback or a known database outcome. Broader transaction-helper changes are outside this patch.

Local unsent handoff for Fable: “Please review the final `legacy/removeChildAccount.draft.patch` and preserved failure in this rehearsal. Reconcile it with your current GMTM API checkout, then test ownership, invalid IDs, affected-row handling and transaction failure in an isolated environment. Do not deploy or touch production data as part of that review. The SPARQ combine ownership fix remains in Codex's checkout.” No message was sent to another agent session or external person.

## Next work and limits

We can continue engineering with synthetic records. The immediate core priority is the reviewed child-removal patch and its database/transaction integration evidence. Parent-managed SPARQ access still needs a server-verified actor/athlete relationship and separate state; this rehearsal deliberately does not add a family dropdown or weaken the one-athlete guard. Canonical-profile disambiguation remains necessary because a same-name child profile can legitimately have zero submissions while another profile holds the work.

The [junior matrix](../../docs/state/junior-account-acceptance-2026-09-07.md) retains real participant/organizer acceptance as open. A real family walkthrough can follow once the mechanics and appropriate account setup are ready; it is not a prerequisite for these local fixes.

## Checkout and uncommitted changes

Checkout `work/sparq-agent-review`, branch `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`, origin `https://github.com/joeygrant55/GMTM-Agent-SDK.git`. No move, commit, push, deployment, production write, cloud configuration change or outgoing message occurred.

This continuation changes/adds:

- `backend/combine_api.py`
- `backend/tests/test_family_handoff.py`
- `backend/tests/test_combine_requirements.py`, `backend/tests/test_combine_readonly_runner.py` (fake query-response updates)
- `backend/tests/README.md`
- `docs/state/family-rehearsal-contract-2026-09-07.md`, `docs/state/junior-account-acceptance-2026-09-07.md`, `docs/state/current-state.md`
- this dated handoff and sibling rehearsal artifacts.

See [full git status](../../../sparq-family-rehearsal-2026-09-07/git-status.txt) for prior uncommitted batches. GMTM shared checkout/source, frontend files, previous live receipts and exhausted model allowances were preserved.
