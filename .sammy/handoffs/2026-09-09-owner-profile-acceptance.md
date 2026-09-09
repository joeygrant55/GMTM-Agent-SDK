# Owner-profile acceptance: real persistence passed, previews unresolved

Date: 2026-09-09, final reconciliation 18:31 UTC. Owner: existing Codex SPARQ lane.
Checkout: `work/sparq-agent-review`; branch `codex/athlete-home-first-value`.
Starting HEAD: `2e1fa430f9f6f27dece47e09858ef937841d574e`.
Remote: `https://github.com/joeygrant55/GMTM-Agent-SDK.git`.

## Final outcome (supersedes the sign-in checkpoint below)

Joey completed sign-in while Codex was writing the initial checkpoint. Actual Clerk JWT verification and exact owner-2 link passed. Evidence/materials and an empty version-0 workspace loaded. Codex used exactly three saves: a goal about turning the existing GMTM profile/footage into a useful coach introduction; the already eligible Shuttle film reference; and an explicitly edited private summary. No preexisting authored content was overwritten.

After a full browser reload, Home showed the same goal and featured Shuttle reference and offered **Continue my draft**. Opening it returned the exact edited draft (including punctuation/newlines), with **Saved. You can come back to this draft.** confirmed. The draft remains private in Joey's Agent workspace. Codex did not copy/send it externally.

**Persistence passed; media presentation did not.** Shuttle and the other eligible footage card displayed **Preview unavailable**. A displayed film record is not evidence of playable video. Source review narrows the poster issue to either a null normalized thumbnail or an image load failure; the component removes its img after onError. Do not infer URLs from film IDs, fabricate thumbnails or claim a CORS cause without observing the image response. `FilmPreview` uses `crossOrigin="anonymous"`; if a valid image URL exists, its response/CORS policy is a concrete diagnostic to inspect. Actual athletic relevance/voice/usefulness still needs Joey's feedback.

Final ledger: 9 personal requests, 61 SELECT reservations, 24 connections opened and closed, 3 PATCH attempts, 3 commit attempts/acknowledgements, no denials/errors, zero provider calls/GMTM writes. The initial private workspace receipt is retained outside Git. Browser confirmation is recorded in `browser-acceptance.json` without the authored draft text.

The parent was explicitly stopped through its own STOP file. Exit 0; both owned process groups dead, ports 52872 and 52873 had no listeners, final source hashes unchanged. `supervisor.json` and `cleanup-verification.json` record this. The visible old page is no longer backed by running services. No cleanup should remove Joey's saved workspace.

Implementation checkpoint commit: `3741fcb4511ffa72b8eefcc08e17030cde1a5e78`; later documentation reconciliation has its own commit. Durable safe receipts: sibling `work/sparq-owner-profile-acceptance-2026-09-09/`. Private before-state stays only under the private temporary run directory. No push or deployment.

**Next:** repair the observed film-preview issue using actual null/URL/request evidence. Preserve the saved work. This run's three-save limit is exhausted; no silent restart/reset for additional writes. The continued full-media/value acceptance is separate from the verified real persistence flow.

## User request and completion contract

Joey asked whether Codex could perform the agreed acceptance with his own profile. Codex owns technical verification; Joey judges usefulness and voice. Use only the current uniquely linked GMTM user 2. Preserve prior saved work and unchanged fields. Check real media, a saved goal, an editable summary/introduction, explicit draft save and exact reload. No other athlete, linking operation, outreach, provider/debrief call, GMTM mutation, infrastructure operation or deployment is included.

## Implemented

- `backend/verification/profile_acceptance.py`: outer ASGI boundary around the current profile candidate, actual candidate JWT verification, fixed Host/Origin and route/method allowlist, strict forward/reverse owner+generation checks, every relevant imported DB alias guarded, exact SQL parameters and returned-row ownership checks. GMTM connectors start read-only transactions. Agent writes can reach only the current owner's workspace under existing locks/version checks.
- Fresh exclusive private ledger: 3 PATCH attempts, 40 personal requests, 500 SELECTs, 160 connections. A successful workspace GET records private before-state before saving. Uncertain or failed saves close further writes; GET can reconcile. No automatic write replay or compensating overwrite.
- `backend/scripts/run_profile_acceptance.py`: default offline snapshot preparation; explicit single-use launch retrieves existing Railway configuration and the exact existing Vercel project's two Clerk keys into memory. Source snapshots contain no env files. Fixed profile backend closure plus frontend source are hashed; unreviewed additions and secret files are rejected. Next and backend get separate minimal environments, without model credentials. Parent supervises both owned groups for at most 900 seconds and writes cleanup plus post-run source verification.
- `backend/tests/test_profile_acceptance.py` and `backend/tests/test_run_profile_acceptance.py`: actual app/signature code with injected signing key and in-memory SQL; default/no-network, cloud binding, source injection, single-use launch and cleanup failures are covered.

## Verification

Command: `PYTHONDONTWRITEBYTECODE=1 /Users/joey/GMTM-Agent-SDK/backend/.venv/bin/python -m pytest -q -p no:cacheprovider backend/tests/test_profile_acceptance.py backend/tests/test_run_profile_acceptance.py` from repo root.

Observed: **42 passed**, one existing Starlette/AnyIO deprecation warning, exit 0, 3.13 seconds. Independent review found no remaining launch blocker. Treat `source_unchanged: true` as a separate acceptance requirement; supervisor exit 0 only establishes its lifecycle result.

Frozen run directory (outside Git, private): `/private/tmp/sparq-profile-real-2026-09-09-01/`.
176 source files; extracted import/startup check matched 24 actual source imports, health returned `profile_candidate`, zero offline database connections. The first ad hoc import collector failed after health because it treated `__main__.__file__ = <stdin>` as a real source file. The collector was corrected to skip that non-file; both offline ledgers remain. This was a verifier failure, not a backend startup failure.

## Historical live checkpoint and acceptance sequence

Explicit launch used the frozen source and existing configuration; no cloud configuration was changed. Frontend `http://localhost:52872`, backend `http://127.0.0.1:52873`. Parent exec session 14605. `ready.json` records expiry, approximately **18:34:27 UTC**. `processes.json` identifies only the two owned process groups. Do not revive older preview ports or ledgers.

The in-app tab is on `/sign-in/factor-one`, email `joey@gmtm.com`. Joey was asked to enter the email code. Gmail connector retrieved the correct current SPARQ notification, but there was no secure shared in-memory transfer into the separate CUA runtime. The unused node-runtime value was cleared. A temporary Chrome Gmail tab was closed; it did not yield the target Gmail session. No password or code was printed or written to an artifact.

As of 18:25 UTC, `acceptance-ledger.json` showed **zero personal requests, zero connections, zero SELECTs, zero PATCH attempts**, no denials/errors. Actual Clerk acceptance, media, saved state and persistence have not been verified. The schema migration completed in the prior handoff; do not repeat it.

Once Joey completes sign-in while this finite session is alive:

1. Check the same ledger and existing workspace before touching controls. Stop on ownership mismatch or source-unavailable state; do not weaken guards. Any private before-state is outside Git at `private-workspace-before.json`.
2. Preserve existing goal/draft if present. For an empty workspace, use at most Save goal, optional Feature this footage, and Save draft. Only pick real eligible media. Preparation itself is local, deterministic, editable and does not invoke AI. Do not invent athletic achievements or recipients.
3. Compare exact draft text, goal and featured reference after browser reload. Record real media availability separately from actual playback and from drafting quality. Do not count an HTTP 200 with `source_unavailable` as success.
4. Stop by creating the exact run directory's `STOP` file, or let the finite parent expire. Inspect `supervisor.json`, owned process groups and both ports, then record final ledger counts and source hashes. Do not report cleanup merely from the intended deadline.

If the session has already expired, inspect and reconcile its ledger/cleanup first; do not reuse this single-use launch or silently reset save allowances. A fresh authenticated session still requires the same owner, source and finite limits.

## Git and release

This batch adds four implementation/test files plus this handoff/current-state update. Local commit identities are recorded in the sibling receipt directory. No push, application deployment, new database schema change or production GMTM modification is part of this batch. The final outcome at the top supersedes the historical sign-in checkpoint.
