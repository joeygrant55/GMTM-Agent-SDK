# Private athlete profile workspace

This is the first implementation of the September 8 profile-value direction. It replaces the combine checklist in the explicitly selected `profile` surface with existing athlete facts and an editable, copyable output. The legacy and `combine` surfaces retain their separate behavior.

## Career home update — September 9

The [first-output contract](profile-first-output-contract-2026-09-09.md) removes the repeated preparation form from Home. With a saved goal, **Create my summary** or **Prepare introduction** immediately opens the first editable draft, using that intent, selected current evidence and an eligible saved featured reference. A blank recipient produces a summary. Pending materials settle before first preparation; a completed source outage may still produce text from available profile facts and intent. Existing drafts always resume unchanged. Edit details/Rebuild, Copy and Save draft remain explicit; this action does not call a model, send, copy or persist text.

The [career-home contract](athlete-career-home-design-2026-09-09.md) now governs the entry screen and saved behavior. The athlete sees their current source footage, chosen goal and one adaptive action. Home, Portfolio, Opportunities and Progress are focused views in the same route. Portfolio opens the existing details sheet; Opportunities explicitly remains unreviewed; Progress records saved work only.

`GET/PATCH /api/athlete/workspace` adds private Agent persistence. Save goal, feature selection and Save draft are explicit. Save conflicts offer the current saved version without silently replacing local text. Reload restores the goal, feature reference and draft; ordinary source outages preserve authored work. Account/link changes clear old content, and matching server-derived owner scopes are required before showing saved work beside source evidence or an answer.

The application still needs an explicitly prepared `athlete_workspaces` table in its intended Agent database. Review `backend/prepare_athlete_workspace.py --help`; default invocation only prints a plan. Apply requires the existing exact expected host/database guards and the current task's authority for that target. Never point this command at GMTM. Offline fixtures verify transactions with synthetic storage; they do not prove current live Agent schema availability. An unavailable workspace table produces a visible saved-work error instead of startup DDL.

### Separate profile source package

`backend/scripts/package_profile_candidate.py --output /absolute/new/artifact/profile-candidate.tar` creates an exclusive source archive and adjacent manifest in an already-created directory outside this checkout. It reads a fixed allowlist; it never installs, builds or deploys. The profile recipe is `Dockerfile.profile-candidate` with its exact companion ignore file. Its fixed `backend/start_profile_candidate.py` launches only `profile_candidate_app:app`, with one worker, no access logs, no proxy headers and no inherited Uvicorn override settings. The existing combine packager/launcher and production manifests keep their defaults.

The archive contains the profile runtime plus shared imports, including the separate Agent workspace route. It excludes schema preparation commands, tests, environment files and the legacy main entry. Shared combine modules are import dependencies, not exposed profile routes. The frontend must separately be built with `NEXT_PUBLIC_APP_SURFACE=profile` and the explicit intended backend origin. No frontend build or source archive containing synthetic test configuration is a deployable release.

Before release, still verify a clean Linux dependency installation and immutable image, identify the exact paired frontend/backend targets, prepare the Agent workspace table under scoped authority, complete the real-account journey and review rollback. Packaging/import tests establish code closure and route boundaries; they do not establish live authentication, database availability or athlete usefulness.

The historical behavior below describes earlier checkpoints. In particular, references to page-local drafts and clearing them on refresh are superseded by this update. The debrief's disabled default, finite provider allowance, canonical GMTM read-only boundary, and separate release/live-acceptance limits remain.

## Configuration and data flow

- Frontend: `NEXT_PUBLIC_APP_SURFACE=profile`, an explicit `NEXT_PUBLIC_BACKEND_URL`, and the existing Clerk settings.
- Backend: `profile_candidate_app:app`. Its factory selects the profile route manifest explicitly; a request or environment variable cannot widen that manifest.
- The candidate configuration validation, identity/claim settings, origin allowlist and finite database connection settings still apply. The shared configuration validator also requires the documented combine-help configuration shape, even though this entry exposes no combine-help route.
- Existing Clerk-to-GMTM linkage is authoritative. The new evidence GET takes no athlete ID or query parameters and verifies both directions of the stored link before reading GMTM.
- GMTM supplies canonical identity, unambiguous approved/unsuggested primary-career context and bounded current public numeric measurements. Restricted, invite-only, paid and network-only digital-event evidence is excluded. Missing units, unknown verification and ambiguous source context are never filled in by inference.

The backend exposes `GET /api/athlete/evidence`, `GET /api/athlete/materials`, `POST /api/athlete/debrief`, the existing by-Clerk connection GET, claim preview GET, claim redemption POST and health. Athlete endpoints accept no query parameters and independently confirm ownership. Claim redemption can write existing Agent records; GMTM remains read-only. This profile entry imports no legacy startup/schema hook and adds no tables. Health reports configuration readiness, not database or model success.

## Question-based debrief

The [debrief contract](profile-debrief-contract-2026-09-08.md) adds one explicit question with a focus: the adult USA Football pathway, profile understanding, or outreach preparation. The server resolves the owner again, reads the current evidence, closes the connections, and makes one bounded model call. It supplies supported numbers, generic eligible footage records and coverage limits; server-derived identity, contact details, private material, media titles/descriptions and media URLs stay out of the provider context. The athlete's question is included verbatim and may itself contain personal information.

The answer remains buffered until strict paragraph, citation and action validation completes. A successful answer replaces the expanded question form with the actual question, a takeaway, visible unknowns and one action. Supporting observations and action reasoning open under Why this answer; citations open their source details. Edit question restores the form. Intent starters fill an editable question and never submit automatically. Local actions open a dedicated composer without replacing an existing draft or selecting new facts. Changing the question/focus marks an earlier answer as belonging to that earlier question. Profile/account refresh and materials retry clear the debrief; all state is page-local.

This feature is disabled by default. Enable only in a separately approved isolated run with `PROFILE_DEBRIEF_ENABLED=true`, an allowlisted `PROFILE_DEBRIEF_MODEL` (default `claude-sonnet-4-6`), and explicit positive `PROFILE_DEBRIEF_MAX_MODEL_CALLS` and `PROFILE_DEBRIEF_MAX_CONCURRENT_CALLS`. These limits use a separate process ledger; they do not reuse the earlier combine allowance. They are not durable across restarts or multiple workers. Deployment still needs durable quota and retention decisions.

Official facts in `backend/profile_pathways.py` were reviewed September 8 and expire October 8, 2026 at 22:51 UTC. The national-team track refuses expired sources; other tracks remain usable. A reviewer must recheck the facts before updating the dates. No upcoming adult camp or 2027 Trials date is confirmed. The available external actions open the published support or development-resource page; neither sends a message nor claims a recruiting connection.

Synthetic provider responses verify the flow, not AI quality. The separate [quality evaluation](profile-debrief-quality-evaluation-2026-09-08.md) covers invented benchmarks, unsupported film judgments and selection claims. Valid citation IDs prove reference membership, not that a claim follows from that reference.

## Athlete behavior

The page loads only the signed-in athlete's evidence and now leads with their eligible footage, its stored thumbnail when available, and up to two recorded/submitted results. Previous and Next browse the returned public clips in source order; this is not a ranking. Use this in an introduction selects that clip's canonical GMTM page reference and opens preparation without generating or replacing text. Missing/broken previews retain the title and useful action. See the [media design contract](profile-media-design-contract-2026-09-08.md), which supersedes the question-only initial screen.

Ask about my profile opens the focused question surface. Back to your content restores the overview; the answer and draft stay page-local and intact. View profile opens a native modal sheet with identity, measurements and materials. The first three records in each collection appear there; the athlete can expand the complete bounded lists and select eligible records. Done or Escape returns to the initiating control. Opening or closing the sheet changes no sources, selections, drafts or model requests.

Write an introduction, or a local answer action, opens the composer. A goal is required; an introduction also requires the athlete to name an actual recipient. Choose profile details reopens the same sheet. After preparing text, its inputs collapse behind Edit details and copying becomes the primary action. Back to SPARQ and Return to your draft preserve both answer and edited text.

Preparing text is deterministic and local. It uses the selected facts, source/date and the athlete's words. Editing and copying send no message and call no provider. Collapsing results preserves selections. Changing account, refreshing or leaving discards page-local drafts; stale fetches and clipboard completions cannot restore old-account content. Saving drafts across visits is a future product decision.

An empty measurement response means this adapter returned no supported numeric results. It does not mean the GMTM profile has no film, historical submissions or other evidence. A failed source read has a distinct recovery state and produces no fallback facts.

The [materials extension](athlete-materials-contract-2026-09-08.md) independently loads up to 20 numeric submission results and 10 footage records. It uses original submission snapshots, explicit units and source dates. Three records appear initially inside the profile sheet, with expansion. The same sheet fills the phone viewport. Only eligible, selected public-source material enters text; restricted owner material stays view-only. A materials failure has its own retry and leaves profile measurements and the existing draft usable. Main refresh/account changes clear both collections and page-local output.

The visual extension reads stored service/thumbnail fields within the same three bounded owner film queries. Only eligible public footage can receive a thumbnail URL. Exact known GMTM CDN/YouTube HTTPS namespaces and raster filenames are validated on both server and client. The browser requests the admitted image without referrer or cross-origin credentials; the backend never fetches or proxies it. Errors show Preview unavailable without another host, model call or source retry. Existing payloads without thumbnail_url remain compatible. Film contents, titles and thumbnail/page URLs remain excluded from the server-assembled AI context. Current real-CDN availability/CORS and owner thumbnail coverage still need a separate signed-in acceptance run.

## Verification and remaining acceptance

Use the existing test scripts with explicit `profile` selectors:

```text
SPARQ_BUILD_SURFACE=profile ... node frontend/tests/check-production-build.cjs
SPARQ_CANDIDATE_SURFACE=profile ... node frontend/tests/check-candidate-app.cjs
```

Each requires a new absolute artifact directory outside this checkout. The production check uses real Clerk packages and synthetic configuration. The complete app fixture uses actual Next/ASGI with synthetic Clerk identity and SQL records. Its sample sports image is AI-generated test media, served only through exact local browser interception; it is never a product fallback or evidence of a real athlete's footage. Run one heavy job at a time, under a finite external supervisor; inspect the receipt's owned-process and port cleanup before starting another.

The separate [owner-profile read contract](owner-profile-read-contract-2026-09-08.md) covers the designated user-2 projection with exact source/configuration review. It is not a browser/JWT acceptance test. Never place its private output in Git or send it to a provider under an earlier combine-help allowance.

For a separately reviewed materials read, the same finite launcher requires explicit `--scope materials` in preflight and execution. Its fresh source digest includes `athlete_materials.py` and the existing owner/helper sources. The fixed cap is two connections, seven SELECTs and eleven explicit statements including transaction setup. Only user 2 is eligible; there is no athlete argument. Use a new private absolute directory outside every Git checkout; output is `private-athlete-materials.json`, plus count-only read/supervisor receipts. Never reuse an earlier ledger. The default `profile` scope retains its smaller six-SELECT measurement contract. See the [source map](athlete-materials-source-map-2026-09-08.md) for all four exact material paths and interpretation limits.

This workspace is a factual preparation foundation. It does not yet interpret film, establish athletic potential, discover current opportunities, provide organizer-confirmed selection outcomes or send outreach. Those are the next product-value tests. The older combine Docker/source package does not include this new profile entry; profile packaging and real signed-in end-to-end acceptance must precede a paired release recommendation. No deployment is implied by a passing local check.
