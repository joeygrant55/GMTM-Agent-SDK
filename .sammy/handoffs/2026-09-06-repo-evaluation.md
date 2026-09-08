# SPARQ repository evaluation — September 6, 2026

Owner: Codex, Evaluate Sparq agent project, task 01a06f58-7203-7f82-a090-3545f126936b. Joey explicitly resumed product work and asked for a comprehensive repository evaluation. Completion contract: inspect current source/local/open work, audit product/backend/operations against the current-combine and continuing-profile direction, run isolated checks, preserve implementation and infrastructure, and deliver an evidence-backed report.

## Version and scope

Owned checkout: /Users/joey/Documents/Codex/2026-09-04/higgsfield-plugin-app-6a3293e129088191abf0875820e839da-openai-curated/work/sparq-agent-review. Branch codex/athlete-home-first-value; HEAD 6c7e649ce5154f211401ed2e4af03d9691366194. Fresh GitHub comparison confirms identical main. Existing four modified frontend files (ArtifactCard, InboxFeed, WorkspaceSidebar, home/profile/page) and new AthleteStartingPoint were preserved. Other SDK checkouts and the unapplied work/sparq-linking-draft were not changed.

Three bounded source reviews covered backend/data/security, frontend/product, and operations/commercial readiness. Inventories include 51 backend route registrations, 24 frontend page routes and five Next API route files. This is a source/isolated test audit, not a full production security or live acceptance audit. No new source implementation was made.

GitHub open PR #2, Ship-readiness: auth + ownership, flag football pivot, verified-data spine, legal pages, is at 10e4dd0d983f57492b6caf4bfff8bc94dc9d0bc6, seven ahead/thirteen behind main. Actual unmerged code includes verified measurement/outcome ingestion and storage, a flag-program directory and legal pages. Some PR auth claims describe work already shared with main; selectively reconcile actual diffs. A successful Railway backend deployment status on main is reported by GitHub, but live behavior/frontend revision were not verified.

## Findings and next contract

The repo contains a real recruiting-assistant/workspace foundation: GMTM-linked profiles and results, claims, model chat/search, college research, persisted artifacts, editable drafts and real email sending. It does not yet implement authoritative current-event requirements/completion, recurring development tasks, athlete-controlled sharing, organization cohort operations, durable autonomous jobs, usage budgets or subscription entitlements.

Priority blockers: legacy name/ID linking can overwrite ownership; explicit conversation writes lack ownership checks; model SQL lacks user/column scope and a robust allowlist; public athlete detail omits visibility policy; claim ownership acquisition races; caller URLs reach a server-side fetch; failed draft save can proceed to send and backend sends are not idempotent; demo drafts can send. Public report route is shadowed, public athlete rendering assumes owner data, some HTML rendering is unsafe, artifact iteration lacks a bearer token, and full workspace rails lack phone adaptation. Static national-percentile and success/progress claims exceed their evidence.

Most important product seam: redeem returns event_id but the frontend drops it; zero-result home cannot derive the current combine from result rows. Persist authorized athlete/event/registration, read canonical requirement/submission state, deep-link to existing GMTM submission, refresh truthfully and preserve a useful profile/next action afterward. Do not treat numeric results, link opens, submitted, reviewed or selected as equivalent. Do not duplicate core GMTM organizational capabilities without inspecting them first.

Recommended next implementation starts with the exposed identity/data boundaries, then proves that zero-result journey. The prior linking patch is a narrow unapplied candidate; this audit does not apply it or resolve its separate approval. Broader organization/setup work remains in the other task. No deployment or external outreach is authorized by this evaluation.

## Fresh verification

- Current frontend snapshot TypeScript passed using existing hydrated canonical dependencies; no full Next build.
- Seventeen backend Python files compiled in memory, without import-time service startup.
- Existing backend suite: 41 passed using fake DB/driver, disabled dotenv and blocked outbound DNS/TCP.
- Current handler against six ownership safety tests: four failed, two passed. Foreign/unclaimed/unknown athlete IDs were accepted; same-owner confirmation still wrote.
- Actual source helper/route diagnostics reproduced quoted-table allowlist bypass, personal-column query without owner predicate reaching a fake cursor, explicit conversation write without owner lookup, and report route returning 401 anonymous/422 authenticated rather than reaching the intended public handler.
- Fourteen real home-component browser assertions passed with mocked Clerk/local API data and existing fixture CSS; outbound browser requests blocked. Initial sandbox localhost-listener denial was resolved by an approved isolated rerun. Browser/server closed. This does not validate full mobile shell, Next middleware, live Clerk/MySQL or production.
- All 173 source/document/asset hashes matched the initial manifest before required audit documentation edits. Final preservation receipt distinguishes the intentional current-state change and new handoff from unchanged implementation.

No actual DB connection, paid model request, email send, AWS/RDS/IAM/parameter/account change, production data mutation, branch switch, commit, push or deployment. MySQL 8.4.11/db2-dev and sql_mode remain user-reported; no actual pre-prod configuration was found to replace. Public URL fetch attempts were tool-blocked, not evidence of an outage. Database grants/schema, transaction races, live auth/provider behavior, concurrency/load and full live athlete acceptance remain unverified.

## Deliverables and uncommitted work

User artifacts under the active task root:

- outputs/sparq-repo-evaluation-2026-09-06.md — product assessment, version matrix, gaps and build sequence.
- outputs/sparq-repo-technical-appendix-2026-09-06.md — detailed route/source inventories and reviews.
- outputs/sparq-repo-verification-2026-09-06.json — fresh check, branch and preservation receipts.

Reproducible local audit scripts/fixtures/logs are in work/repo-audit-2026-09-06. They remain outside the product source and were not committed as application tests. Snapshot contains no live .env files; browser data is synthetic.

This audit changes only docs/state/current-state.md and adds this handoff inside the owned checkout. Both remain uncommitted along with existing instructions/handoffs and the five previously uncommitted frontend files. No change was made to the separate draft, other checkouts or Control Tower. Required evaluation work is complete; subsequent implementation should use this dated contract and preserve concurrent lanes.
