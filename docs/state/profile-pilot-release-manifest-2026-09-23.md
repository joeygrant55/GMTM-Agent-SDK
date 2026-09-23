# Profile pilot: paired release manifest

Status: **local source implemented and verified; hosted release pending**. September 23, 2026. This is a fill-in release record, not deployment authorization or evidence of hosted acceptance. Initial inspection: `codex/athlete-home-first-value`, HEAD `159869c775fe51e0f4b4884bc6760f6009b2369d`, origin `joeygrant55/GMTM-Agent-SDK`; `current-state.md` was modified. Admission and catalog work are concurrent. Freeze and identify the final reviewed source before filling the release fields below.

## Release identity — complete before promotion

| Field | Required value / present status |
| --- | --- |
| Release owner; decision owner; rollback owner | Codex owns this source and release preparation; Joey retains release approval. Hosted execution/rollback ownership remains to be assigned with the exact targets. |
| Intended cohort and adult-admission reviewer | **Unresolved**; initially already-linked, human-reviewed adult self-owned accounts only. Keep account IDs, Clerk subjects and admission records in private operational configuration. |
| Final source commit; reviewed diff; verification receipts | **Unresolved**; the inspected HEAD above excludes this turn's work. Identify all shipped files, including any intentional uncommitted delta; prefer a committed release source. |
| Backend platform/project/service/environment + HTTPS origin | **Unresolved**; separate explicit profile target. No existing live service or hostname has been verified here. |
| Frontend platform/project/environment + HTTPS origin | **Unresolved**; record immutable deployment ID and its intended public origin. |
| Backend source archive + adjacent manifest SHA-256 | Prepared locally: `../sparq-pilot-gate-2026-09-23/profile-candidate-source.tar`, SHA-256 `7a1a689ea4aa2289d2a432097ef74813f9e751c43aba47f7550f90e7f1c7b8c4`. Adjacent `.manifest.json` records all 29 allowed file hashes. Source package only; no image build/deployment. |
| Linux platform, Python base image digest, final image digest | **Unresolved**; `python:3.13-slim` is a recipe default, not an immutable pin. Record the exact build argument and resulting image. |
| Frontend source manifest, lockfile hash, Node/npm versions, artifact identity | **Unresolved**; include public build variables, build receipt, immutable deployment/artifact digest and deployed source mapping. |
| Paired previous-good frontend/backend artifacts and private config versions | **Unresolved**; no previously accepted gated pilot pair is established. If none exists, rollback means close this pilot entry. |
| Private receipt/log locations, retention/deletion owner and period | **Unresolved**; no secrets, tokens, admission lists, athlete content or raw logs in Git. |

## Exact build and configuration selection

**Backend:** use `Dockerfile.profile-candidate` and its companion `Dockerfile.profile-candidate.dockerignore`. Package with `backend/scripts/package_profile_candidate.py --output /absolute/new/artifact/profile-candidate.tar` using the chosen Python runtime and a pre-created directory outside the checkout. The packager produces the archive and adjacent `.manifest.json`; it does not build or deploy. Confirm the new `backend/profile_admission.py` and `backend/profile_owner.py` are included in the final Docker COPY/ignore/package closure before packaging. Build the final archive with the recorded immutable `PYTHON_IMAGE`; record clean Linux install, `pip check`, import/startup and image receipts.

The fixed entry is `backend/start_profile_candidate.py` → `profile_candidate_app:app`: one worker, asyncio/h11, lifespan enabled, no application access logs or proxy-header overrides. `PORT` must be 1–65535. Do not substitute the root `Procfile`, `main:app`, legacy Dockerfile or combine package. No install, dotenv load, schema preparation or provider call belongs in startup.

**Frontend:** from `frontend/`, use the checked-in `package-lock.json` with a clean dependency install and `npm run build`; the production server script is `npm run start`. The effective configuration is `frontend/next.config.js`. Record these build-time values with the artifact; changing a `NEXT_PUBLIC_*` value requires a new build:

| Setting | Pilot requirement |
| --- | --- |
| `NEXT_PUBLIC_APP_SURFACE` | `profile` |
| `NEXT_PUBLIC_BACKEND_URL` | Exact selected HTTPS backend origin, no path/credentials/query; never a loopback or synthetic test backend. |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Correct selected Clerk instance; public key may be recorded, private keys may not. |
| `NEXT_PUBLIC_OPPORTUNITY_ENGAGEMENT_ENABLED` | Explicit `false` initially; `true` only for the reviewed measurement-enabled artifact/config pair below. |
| Clerk sign-in/sign-up and redirect configuration | Verify `/sign-in`, `/sign-up`, return to `/home/inbox`, and the actual hosted origin with the selected Clerk instance. Record configured names/values rather than assuming local harness defaults. |

Inject server secrets through the selected platform's approved secret mechanism. Record references/version IDs and presence checks, never values or broad environment dumps. Confirm the selected Clerk SDK/server setup, including its private key where required, without exporting local credentials into source artifacts.

| Backend setting | Pilot requirement |
| --- | --- |
| `AUTH_ENFORCED` | `true` |
| `CLERK_ISSUER` | Exact HTTPS issuer for the paired frontend's Clerk instance. |
| `CLERK_AUTHORIZED_PARTIES`, `ALLOWED_ORIGINS` | Same explicit set containing only intended frontend origins; no wildcards. Hosted origins use HTTPS. Real JWT signature/expiry/issuer/subject and exact `azp` must pass. |
| `PROFILE_ADMISSION_ENABLED` | `true`; the planned implementation permits disabled mode only with loopback frontend origins and requires the gate for hosted origins. Verify that behavior on the final source. |
| `PROFILE_ADMISSION_FILE` | Absolute private path to the bounded schema-1 admission file; mode `0600`, readable by runtime UID `10001`, outside source/image/public assets. Record private version reference and validated schema, not contents. Bind each admission to reviewed adult authority, GMTM user ID, exact Clerk subject, current link row/revision and expiry; support revocation. Analytics classification is not admission. Mount/update procedure and platform owner remain unresolved. |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Canonical GMTM host `db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com`, `3306`, `gmtm`, `gmtmread`, injected password. No GMTM writes or AWS/RDS changes. |
| `AGENT_DB_HOST/PORT/NAME/USER/PASSWORD` | Explicit selected Agent database binding, separate from GMTM/RDS; service/network reachability must be verified from the hosted runtime. |
| `SHARE_TOKEN_SECRET` | Inject existing intended secret securely. Its presence does not authorize claim issuance/redemption during this pilot. |
| `COMBINE_HELP_MAX_MODEL_CALLS`, `COMBINE_HELP_MAX_CONCURRENT_CALLS` | Shared startup validator requires explicit valid finite values even though profile does not expose combine help. Record declarations; they are not new provider authorization. |
| `PROFILE_DEBRIEF_ENABLED` | `false` for initial pilot; omit provider keys unless separately reviewed and approved. No reset of previous test/provider allowances. |

## Verification and promotion record

Each item needs a dated receipt tied to the final source/artifacts; mark pending, pass or fail. Historical local passes are context only.

1. **Offline source:** admission exact-owner/expiry/revocation/link-change denial, route closure, package/import closure, refreshed official catalog, frontend policy/components, actual-app checks and production build. One heavy job at a time under finite supervision; verify owned process/port cleanup. Synthetic Clerk or SQL fixtures do not establish hosted readiness.
2. **Data compatibility:** existing Agent link-ID/workspace migration and founder save/reload completed September 9. Do not replay DDL. Confirm the selected runtime points at that intended schema; use bounded read-only metadata only if a current compatibility check is needed. No broad schema bootstrap or `pre-prod`/family-test target.
3. **Hosted health:** record both immutable deployed artifact IDs and origins; backend `/health` must identify `profile_candidate`, configuration ready, admission enabled, debrief disabled and intended measurement state. `connectivity_verified`, `schema_verified` and `provider_delivery_verified` are not live proofs merely because health returns 200.
4. **Boundary:** unauthenticated, wrong-subject, unadmitted, expired/revoked and changed/recreated-link cases expose no personal data and perform no personal mutation. Verify admission blocks every personal profile route and claims remain unavailable under the initial gate; legacy/recruiting/combine routes stay absent. Record private/no-store responses. Separately verify disallowed browser origins/preflights receive no CORS permission; CORS itself is not identity or admission enforcement.
5. **Actual adult journey:** use a separately scoped admitted, already-linked adult account; confirm own footage/evidence, current reviewed opportunities, useful editable introduction, preserved goal/draft, explicit save and reload, and sign-out. Read prior workspace privately before any approved write; pin expected version, cap attempts and reconcile uncertain writes by GET instead of replay. The earlier founder three-save allowance is exhausted; this manifest grants no new save budget. Preserve other fields and concurrent edits. No claim minting, account reassignment, outreach or payment is part of this check.
6. **Release decision:** record approval for the concrete paired targets/artifacts/config and exact live acceptance scope. Keep entry closed to external athletes until these checks pass. Existing Clerk login is the pilot path; do not describe it as GMTM SSO or infer guardian authority from a junior/parent session.

## Optional measurement activation

Default off on both sides. For an approved measurement run, pair the rebuilt frontend flag with backend `OPPORTUNITY_ENGAGEMENT_ENABLED=true`, `OPPORTUNITY_ENGAGEMENT_COHORT=pilot`, a named `OPPORTUNITY_ENGAGEMENT_PERIOD`, a dedicated injected 32-byte hex `OPPORTUNITY_ENGAGEMENT_SECRET`, and private `OPPORTUNITY_ENGAGEMENT_PILOT_IDS` / `OPPORTUNITY_ENGAGEMENT_EXCLUDED_IDS`. Pilot IDs may include only explicitly admitted adults; owner 2 is always internal. Admission still independently controls access. Record secret reference/version and keep it stable within a reporting period.

Verify private platform log capture/export and retention with a labeled internal control before counting pilot demand. The dedicated stdout prefix is `SPARQ_OPPORTUNITY_ENGAGEMENT `; app access-log suppression does not establish edge/platform redaction. Confirm bearer tokens, claim-token paths and athlete content are not retained in general logs. Do not enable capture without a named export/retention owner. The founder acceptance wrapper blocks this route and cannot prove its delivery.

Run `backend/opportunity_engagement_report.py` only on a private captured export with explicit UTC start/end (end exclusive), measurement period and cohort. Retain coverage/malformed/duplicate diagnostics. Default pilot results exclude fixture/internal records. Report distinct accounts viewing, opening details and activating outbound links; clicks are not destination arrivals, registration, selection, payment or commission. Best-effort process-local throttling/stdout is not a durable complete event ledger.

## Rollback and stop conditions

Stop promotion for identity/admission leakage, wrong source/artifact/origin binding, saved-work loss/version conflicts, unavailable sources presented as facts, or unverifiable measurement delivery. Deployment owner closes the pilot entry or restores the recorded previously accepted **gated** artifact pair with compatible configuration, then repeats health and admission-denial checks. Keep current revocations and expiry restrictions; never disable the admission gate or restore an ungated legacy backend as a rollback shortcut. If no safe previous pair exists, leave the pilot unavailable while retaining the separate legacy deployment.

Disable optional capture if its sink fails, preserving private receipts for the named owner; do not reinterpret missing events as zero interest. Preserve Agent workspace data, completed schema and GMTM records. Rollback is not a destructive database migration, account relink, draft overwrite or provider-budget reset. Record the decision, changed artifact/config IDs, time and verification result.

Source anchors: `Dockerfile.profile-candidate`; `backend/scripts/package_profile_candidate.py`; `backend/start_profile_candidate.py`; `backend/profile_candidate_app.py`; `backend/candidate_app.py`; `frontend/package.json`; `frontend/next.config.js`; `frontend/lib/backend-config.cjs`; `frontend/middleware.ts`; `backend/opportunity_engagement.py`; [profile runbook](profile-workspace-runbook-2026-09-08.md); [completed founder acceptance contract](profile-real-account-acceptance-2026-09-09.md); [paid pilot scope](paid-pilot-priority-2026-09-14.md). This preparation made no cloud/configuration changes and retrieved no credentials.

## September 23 local freeze

Admission and the two-module package closure are implemented and independently reviewed. All 983 affected offline backend tests pass, including package/import closure and actual gated ASGI paths. Final test inputs reconcile exactly; see the dated implementation handoff and `focused-03-receipt.json` outside the checkout. No admissions, hosted targets, Linux images, frontend artifacts or deployment are implied by this local source checkpoint. Keep all remaining unresolved fields open until verified.
