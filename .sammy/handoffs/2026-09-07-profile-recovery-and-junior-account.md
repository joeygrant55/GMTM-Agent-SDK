# Profile recovery and junior-account checkpoint

September 7, 2026. Joey asked to proceed with the proposed recovery hardening and junior source investigation. The [completion contract](../../docs/state/profile-recovery-contract-2026-09-07.md) is complete for local implementation and source review. Real junior acceptance remains open.

## Result

- GET `/api/profile/by-clerk/{clerk_id}` checks this authenticated caller's existing connection using at most three parameterized `LIMIT 2` reads. It rejects duplicate forward/reverse/workspace rows, invalid IDs and mismatched case-sensitive Clerk subjects. A foreign caller is rejected before opening the database. Existing response fields and workspace-only/no-profile cases remain compatible.
- The GET no longer creates a workspace or invokes bootstrap/model work. A unique athlete without a workspace returns `found: true, has_sparq_profile: false`; it does not claim setup completed. Ambiguity returns 409 and database/lifecycle failure returns a generic 503 rather than false “not found.” This guarantee applies to this handler, not full application startup or every legacy endpoint.
- The three current frontend consumers use the shared strict response parser. Connection recovery retains the selected junior/adult destination and offers retry; malformed or failed checks do not expose manual connection actions or redirect as if recovery succeeded. Quick Scan and outreach also show explicit failure/retry rather than incorrectly asserting no athlete/onboarding.
- Account-keyed Quick Scan and outreach sessions remove old rendered state when identity changes. Outreach uses the existing caller-authorized workspace-profile response, verifies its returned Clerk owner, and ignores the old unowned onboarding browser cache. This also fixes the case where account B inherited account A's draft after a failed or successful lookup. Pending reads and copy-after-clipboard continuations stop on account changes.

## Verification

Receipts and tested source snapshots are local-only at [`work/sparq-profile-recovery-2026-09-07/`](../../../sparq-profile-recovery-2026-09-07/):

- [Backend receipt](../../../sparq-profile-recovery-2026-09-07/backend-verification.json): 401 full tests passed, including 40 new recovery cases and six existing legacy-connect checks. Tests use fake databases and FastAPI with precollection dotenv/network/provider guards. No live account or database was accessed.
- [Account receipt](../../../sparq-profile-recovery-2026-09-07/account-receipt.json): 172 actual-component checks passed. Coverage includes HTTP/network/JSON/schema failures in all three consumers, selected-combine retry, late account responses, old draft removal, stale unowned cache rejection, wrong-owner workspace rejection, successful retries, and no outreach POST after an account switch during clipboard wait.
- [Journey receipt](../../../sparq-profile-recovery-2026-09-07/journey-receipt.json): 88 checks passed. [Help receipt](../../../sparq-profile-recovery-2026-09-07/help-receipt.json): 59 checks passed. Chromium renders actual components with all network intercepted and synthetic fixtures; generated phone/desktop screenshots are beside the receipts. This does not establish full Next middleware, physical-device usability or real Clerk/GMTM acceptance.
- [TypeScript receipt](../../../sparq-profile-recovery-2026-09-07/typecheck-receipt.json): 93 current source/configuration files, no errors and no source changes during checking. Existing dependencies were used without installation, environment loading or starting Next.
- [Consolidated verification](../../../sparq-profile-recovery-2026-09-07/verification.json): current source hashes match all receipts, `git diff --check` passes, and all 23 earlier model comparison/refinement JSON artifacts remain unchanged. No model calls or allowance resets occurred.
- Independent backend review and two frontend source reviews found no new blocking issue. Early browser attempts failed at Chromium's sandboxed MachPort startup before tests; approved outside-sandbox synthetic runs passed. An initial outreach harness stub rendered `next/dynamic` as null; the harness was corrected to render the actual component before the passing suite.

## Junior source findings and next gate

The [junior account acceptance matrix](../../docs/state/junior-account-acceptance-2026-09-07.md) contains exact source references and provenance limits. Reviewed web combines use the ordinary GMTM session to attribute submissions, with no reviewed web family-switch caller. The mobile `users.parent_id` switch is wired; the separate `user_parents` context has unresolved legacy wiring. These facts do not establish USA Football's current guardian process. SPARQ does not import a GMTM child session; a selected event or claim token does not prove guardian authority.

The smallest missing evidence is who signs in to GMTM, whose athlete profile receives junior submissions, and which current client/switch flow the organizer expects. A question is pending with Joey; no external message has been sent and no policy has been assumed. His existing user 2 can support a separately scoped junior/adult event-isolation check, but cannot prove a real junior/guardian journey. The earlier live harness covered user 2/adult 1318 and predates these changes; it was not reloaded or expanded here.

Before broader release: verify this current source with the real approved self-account flow, resolve actual junior actor/athlete handling, and complete the previously identified pilot gates. Do not implement parent delegation by bypassing the one-athlete guard, swapping links, or merging the two family tables. Keep the existing GMTM combine as the submission destination.

## Known remaining scope

Copying a coach draft still logs “Awaiting Response” in the existing product even though copying does not send an email; that delivery/logging contract needs separate work. Quick Scan's existing waitlist handler can report success after failure. The downstream workspace-profile route still uses legacy first-row reads and optional combine enrichment; this batch validates its consumer's owner response but does not harden every legacy route or all onboarding storage. These pre-existing gaps remain outside the recovery completion claim.

## Checkout and uncommitted changes

Owned checkout: `work/sparq-agent-review`; branch `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`, origin `https://github.com/joeygrant55/GMTM-Agent-SDK.git`. Previous work remains in place; no relocation, commit, push or deployment occurred.

This continuation changed or added only:

- `backend/profile_api.py`, `backend/tests/test_profile_recovery.py`
- `frontend/app/_lib/profileConnection.ts`, `frontend/app/connect/ConnectClient.tsx`, `frontend/app/quick-scan/QuickScanClient.tsx`, `frontend/app/home/outreach/draft/page.tsx`
- `frontend/tests/check-account-boundaries.cjs`, `frontend/tests/README.md`
- `docs/state/profile-recovery-contract-2026-09-07.md`, `docs/state/junior-account-acceptance-2026-09-07.md`, `docs/state/current-state.md`, this handoff

The sibling verification artifacts are also new local files outside the repository. The full dirty tree includes prior authorized batches; see the [status snapshot](../../../sparq-profile-recovery-2026-09-07/git-status.txt). No production configuration/data, infrastructure, claim/account creation, model setting, payment setting or external message was changed.
