# Fable security review: reconciliation and corrected test handoff

September 7, 2026 Eastern. Goal: incorporate the received review, correct the risk description and test expectations, and prepare the next decision for Joey. No application or infrastructure action is included in this documentation pass.

## Evidence and priority

Fable's [review](/Users/joey/Desktop/gmtm-code-research/review-removeChildAccount-patch-2026-09-07.md) is dated September 8, 00:45 UTC. He reports the reviewed handler is deployed on the API/staging servers at master `1bf4fc02`, and read-only production counts show 550 attached child accounts and 179 claimed codes. He confirms the final candidate applies to master, its helpers exist and its transaction-wrapper assumptions match the real module. These are attributed owner findings, not a fresh Codex production probe.

The original handler permits unauthorized email/phone replacement as well as detach. Our earlier shorthand understated the impact. Independent local source review adds that `SELECT ... FROM users WHERE user_id=...` and the contact update have **no child-role or non-null-parent predicate**. The source-level exposure therefore includes ordinary or already-detached accounts; 550 is an observed family-use count, not the maximum affected population. Fable's deployment confirmation makes this the immediate core security priority. No evidence reviewed here establishes whether exploitation occurred.

The final patch enforces recorded-parent ownership before contact replacement, detach or claim reset. It remains unapplied. The earlier synthetic evidence, failures and receipts remain intact; current master reconciliation advances the source-review gate, not real-database acceptance or deployment.

## Candidate and provenance

- [Final patch](../../../sparq-family-rehearsal-2026-09-07/legacy/removeChildAccount.draft.patch): SHA-256 `9d4448150744eb22d7284e0035ab2b28abab5728f4f97d0eb4d336918913f98b`.
- [Candidate function file](../../../sparq-family-rehearsal-2026-09-07/legacy/removeChildAccount.draft.js): SHA-256 `4c1b0c1c34495183fb812ba0a35143edcd3d8bdc8b84ac7821221cd3cfe1b324`.
- Fable's `a48f0153...` prefix refers to the candidate JavaScript text with trailing whitespace removed, as recorded by the rehearsal's `revised_draft_sha256`; it is not the patch file's hash. The actual files match the previously frozen [artifact hashes](../../../sparq-family-rehearsal-2026-09-07/legacy/artifact-hashes.json).
- Received review SHA-256: `c3977eec3bd52c18fee7f2cbbd6ed0045ee8dc1bf674f62d9fce9fe6eb6c5e76`.

Use the final `.draft.patch`, never the `guard-superseded` artifacts. No existing source, patch, review or receipt was rewritten in this pass.

## Corrections to the isolated test plan

Fable reports staging uses `DB_PROD_HOST=db2-dev` even though a dormant variable mentions `pre-prod`. The real database module hard-selects `DB_PROD_HOST`. Consequently the development harness must explicitly bind that variable to the confirmed development instance and assert the actual connection target before inserting fixtures. Merely setting `NODE_ENV=development` or `DB_DEV_HOST` is insufficient. Do not use staging, production or the stopped `pre-prod` for these mutation tests.

Retain Fable's six core test groups with these explicit assertions:

| Group | Required result |
| --- | --- |
| Unrelated caller | Denied for another parent's child **and an ordinary non-child account**, including requests with replacement contact data. Email, phone, parent relation and claim state remain unchanged. |
| Recorded parent, contact branch | Success clears the parent and sets contact data. Exercise email-only and phone-only separately: the current behavior clears the omitted contact field. Confirm that preserved behavior deliberately. |
| Recorded parent, claim branch | Success detaches and resets the claim. Missing/failed claim reset must roll back the preceding user update. |
| Already detached | Retain unauthorized rejection; no contact or claim mutation. The NULL parent relation cannot prove who performed an earlier detach. |
| Invalid or missing target | Malformed IDs reject before opening a transaction; missing target is a distinct not-found case. Preserve unrelated records. |
| Concurrent detach | Use two real connections and different contact values. After A commits, the expected waiter B path is to resume its locked read, observe NULL parent and reject **before issuing an UPDATE**. Exactly one winner's data remains. If A rolls back, B may legitimately proceed. |

`affectedRows=0` is a separate defensive assertion, not the expected losing path for the normal two-connection locking case. Keep the affected-row guard and its synthetic regression coverage.

Also retain bounded error/cleanup checks for begin/query/rollback/commit failure. The current helper releases on a failed commit: report an indeterminate result and do not automatically retry or claim a rollback happened. Test-created rows must be uniquely scoped and cleaned up without touching restored or unrelated data. The proposal uses synthetic people, not copied production participant records.

Using the real `gmtm-rds` module validates driver/pool/transaction behavior. It does not by itself exercise the real HTTP session hook or Redis; the resulting report must distinguish what ran from source review and deferred integration coverage.

## Already-detached product decision

Recommendation: keep the current 401 behavior for this narrow fix. A no-op `ok` could avoid retry UI friction, but it would not prove an authorized former parent. Do not bypass the ownership check or permit contact/claim updates for NULL-parent targets. Proper retry support needs an actor-bound operation record or another explicit ownership-preserving design. Resolve that later without delaying the ownership guard; review how the mobile client presents the denial so it is not confused with a need to retry a mutation blindly.

## Remaining follow-ups

- Existing switched child sessions can survive detach for the reported 90-day TTL. Session revocation needs a follow-up design and verification.
- `users.parent_id` and the reportedly near-empty `user_parents` path represent two authority models. Consolidate deliberately; the narrow patch uses the live model.
- Perform a separate read-only ownership audit of other handlers that accept a target ID and mutate profiles or athlete data. Fable's pattern observation is a lead, not proof that every listed handler is vulnerable.
- Preserve available relevant logs while assessing historical access and contact changes; do not equate a live vulnerability with confirmed exploitation. No log export or participant investigation was performed in this pass.

## SPARQ status correction

Fable's final paragraph repeats an older Railway-login blocker. The [September 6 Railway handoff](2026-09-06-railway-access-and-identity-validation.md) records successful CLI login/link and a successful two-database read-only run, followed by the later self-account acceptance. Current session validity was not rechecked in this documentation pass. The real outstanding gate is fresh live acceptance of the added reverse-owner lookup with a current, bounded harness; prior frozen harnesses and exhausted allowances must not be reset or relabeled as current evidence. The 423 backend tests remain offline evidence, not deployment acceptance.

## Proposed reply for Joey to send to Fable

> Test the patch. I approve resetting the master password on the `development` instance only, testing with synthetic fixtures through the actual database module, cleaning up those fixtures, and opening the PR. Confirm the actual connection target before any writes; staging uses production data. Add rejection/contact-preservation coverage for an ordinary account, since the original handler is not limited to children. Keep rejection for already-detached targets. For the concurrent test, expect the losing request to observe the detached row and reject before updating. Send the test results and PR for review. Production deployment, production account tests, pre-prod deletion and instance resizing are separate approvals.

This is a **proposed approval message**, not approval granted by Codex or received from Joey. The incoming review requests a development RDS credential reset; Joey's standing instructions reserve AWS changes and core deployment for explicit approval in Fable's infrastructure lane. No message was sent and no password reset or test was started.

## Scope and verification

Existing checkout: `work/sparq-agent-review`, branch `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`, origin `https://github.com/joeygrant55/GMTM-Agent-SDK.git`.

Changed only `docs/state/current-state.md` and this new handoff. Prior application work remains local and uncommitted. Verification passed: **170 application files and 10 frozen legacy artifacts unchanged**, **seven local links valid**, candidate hash distinction confirmed, and whitespace checks passed. Independent read-only source review agreed with the ordinary-account scope, idempotency recommendation and concurrency correction. No test suite, live service, model, database mutation, cloud action, commit, push or external message was run.
