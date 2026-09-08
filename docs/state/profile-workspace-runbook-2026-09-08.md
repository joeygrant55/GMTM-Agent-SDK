# Private athlete profile workspace

This is the first implementation of the September 8 profile-value direction. It replaces the combine checklist in the explicitly selected `profile` surface with existing athlete facts and an editable, copyable output. The legacy and `combine` surfaces retain their separate behavior.

## Configuration and data flow

- Frontend: `NEXT_PUBLIC_APP_SURFACE=profile`, an explicit `NEXT_PUBLIC_BACKEND_URL`, and the existing Clerk settings.
- Backend: `profile_candidate_app:app`. Its factory selects the profile route manifest explicitly; a request or environment variable cannot widen that manifest.
- The candidate configuration validation, identity/claim settings, origin allowlist and finite database connection settings still apply. The shared configuration validator currently also requires the documented combine-help configuration shape, even though this entry exposes no help route or provider action.
- Existing Clerk-to-GMTM linkage is authoritative. The new evidence GET takes no athlete ID or query parameters and verifies both directions of the stored link before reading GMTM.
- GMTM supplies canonical identity, unambiguous approved/unsuggested primary-career context and bounded current public numeric measurements. Restricted, invite-only, paid and network-only digital-event evidence is excluded. Missing units, unknown verification and ambiguous source context are never filled in by inference.

The backend exposes `GET /api/athlete/evidence`, `GET /api/athlete/materials`, the existing by-Clerk connection GET, claim preview GET, claim redemption POST and health. Both athlete reads accept no query parameters and independently confirm ownership. Claim redemption can write existing Agent records; GMTM remains read-only. This profile entry imports no legacy startup/schema hook and adds no tables. Health reports configuration readiness, not database or model success.

## Athlete behavior

The page loads only the signed-in athlete's evidence. Initially it shows up to three results; the athlete can expand the complete bounded list and select any returned result. A goal is required. An introduction also requires the athlete to name an actual recipient.

Preparing text is deterministic and local. It uses the selected facts, source/date and the athlete's words. Editing and copying send no message and call no provider. Collapsing results preserves selections. Changing account, refreshing or leaving discards page-local drafts; stale fetches and clipboard completions cannot restore old-account content. Saving drafts across visits is a future product decision.

An empty measurement response means this adapter returned no supported numeric results. It does not mean the GMTM profile has no film, historical submissions or other evidence. A failed source read has a distinct recovery state and produces no fallback facts.

The [materials extension](athlete-materials-contract-2026-09-08.md) independently loads up to 20 numeric submission results and 10 footage records. It uses original submission snapshots, explicit units and source dates, and generates existing GMTM film-page links without requesting media. Three records appear initially, with expansion. On phones the composer precedes the material collection, reached by a direct page anchor. Only eligible, selected public-source material enters text; restricted owner material stays view-only. A materials failure has its own retry and leaves profile measurements and the existing draft usable. Main refresh/account changes clear both collections and page-local output.

## Verification and remaining acceptance

Use the existing test scripts with explicit `profile` selectors:

```text
SPARQ_BUILD_SURFACE=profile ... node frontend/tests/check-production-build.cjs
SPARQ_CANDIDATE_SURFACE=profile ... node frontend/tests/check-candidate-app.cjs
```

Each requires a new absolute artifact directory outside this checkout. The production check uses real Clerk packages and synthetic configuration. The complete app fixture uses actual Next/ASGI with synthetic Clerk identity and SQL records. Run one heavy job at a time, under a finite external supervisor; inspect the receipt's owned-process and port cleanup before starting another.

The separate [owner-profile read contract](owner-profile-read-contract-2026-09-08.md) covers the designated user-2 projection with exact source/configuration review. It is not a browser/JWT acceptance test. Never place its private output in Git or send it to a provider under an earlier combine-help allowance.

For a separately reviewed materials read, the same finite launcher requires explicit `--scope materials` in preflight and execution. Its fresh source digest includes `athlete_materials.py` and the existing owner/helper sources. The fixed cap is two connections, seven SELECTs and eleven explicit statements including transaction setup. Only user 2 is eligible; there is no athlete argument. Use a new private absolute directory outside every Git checkout; output is `private-athlete-materials.json`, plus count-only read/supervisor receipts. Never reuse an earlier ledger. The default `profile` scope retains its smaller six-SELECT measurement contract. See the [source map](athlete-materials-source-map-2026-09-08.md) for all four exact material paths and interpretation limits.

This workspace is a factual preparation foundation. It does not yet interpret film, establish athletic potential, discover current opportunities, provide organizer-confirmed selection outcomes or send outreach. Those are the next product-value tests. The older combine Docker/source package does not include this new profile entry; profile packaging and real signed-in end-to-end acceptance must precede a paired release recommendation. No deployment is implied by a passing local check.
