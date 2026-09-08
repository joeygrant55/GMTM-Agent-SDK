# SPARQ product build — 2026-09-04

## Latest direction
Joey confirms Marines net $12k is expected in October and steers back to building exceptional products to revive GMTM/SPARQ. Do not continue cash questionnaires or revive the superseded service/deal-chasing plan. Athlete Agent + organization recruitment workflow + shared SPARQ performance evidence is the proposed flagship. It must help athletes without universal coach/NGB adoption.

## Implementation and completion contract
Local repo `/Users/joey/Documents/Codex/2026-09-04/higgsfield-plugin-app-6a3293e129088191abf0875820e839da-openai-curated/work/sparq-agent-review`, origin joeygrant55/GMTM-Agent-SDK, base main 6c7e649ce5154f211401ed2e4af03d9691366194. Created local branch codex/athlete-home-first-value. No local AGENTS.md/CLAUDE.md/current-state existed. Required bounded contract: home reads real evidence; makes no demo seed writes; gives source-backed event link or profile/film step; handles errors/account changes honestly; verifies scoped UI behavior. This contract passed. It does not complete the whole agentic recruiting platform.

Uncommitted application files:
- frontend/app/home/components/InboxFeed.tsx
- frontend/app/home/components/AthleteStartingPoint.tsx (new)
- frontend/app/home/components/ArtifactCard.tsx
- frontend/app/home/components/WorkspaceSidebar.tsx
- frontend/app/home/profile/page.tsx

Home reuses canonical combine card. It loads profile and inbox independently using Promise.allSettled and per-account cancellation/gating. Empty state makes no automatic seed-demo call. Results link to actual /virtuals/{event_id}; no false task completion inference. Missing results show an honest message; missing film links to existing profile film section. Outreach routes to full draft review instead of inbox send; other mutations require confirmed API state before removing cards.

## Evidence and verification
- Full frontend TypeScript check passed: ./node_modules/.bin/tsc --noEmit --incremental false.
- git diff --check passed.
- Local browser harness passed 14 assertions with real component code, mocked Clerk and synthetic localhost API. Includes 390px home-content width, result/event link, empty state/no writes, film-loaded next step, independent failures, failed mutations, outreach review without sends, account switch/sign-out, no runtime errors.
- Browser assets/scripts and receipt: `/Users/joey/Documents/Codex/2026-09-04/higgsfield-plugin-app-6a3293e129088191abf0875820e839da-openai-curated/work/athlete-home-preview/`.
- No full Next build or real Clerk/GMTM end-to-end run; app-wide mobile shell untested.
- No production calls, customer sends, push, merge or deployment. Fable homepage and AWS lane untouched.
- npm ci --ignore-scripts installed ignored frontend/node_modules; package lock unchanged.

## Corrected findings / next integration
Correction: full results already existed on /home/profile at main6c7e649; prior claim that full card was legacy-only was inaccurate. Corrected outputs/sparq-agent-evaluation-2026-09-04.md. Bootstrap summary is lossy, but profile separately fetches full results.

Core source mapping: `/Users/joey/Documents/Codex/2026-09-04/higgsfield-plugin-app-6a3293e129088191abf0875820e839da-openai-curated/work/gmtm-event-completion-seam.md`; pinned source snapshots in work/gmtm-core-seams. Public event route /virtuals/{event_id} is verified in source. Existing org entry is /front-office/router/events/{event_id}. Reuse existing task submission/staff review interfaces; do not build a duplicate evaluator portal. Clerk identities need a trusted adapter to GMTM session/data context. Required fields are question-level; prefills can come from other events; existing aggregates disagree on completion. Next implementation: identity-scoped task/submission/review adapter, reconcile source records after action, then persistent shortlist/action plan. No metric-count or link-click completion claims.

Remaining launch concerns: backend demo endpoint and already-seeded rows still exist; earlier ownership/source-quality findings remain; real task completion/outcome loop and recurring agent work not implemented. Do not describe this first-use patch as the whole product or production ready.

## User-facing deliverables
- `/Users/joey/Documents/Codex/2026-09-04/higgsfield-plugin-app-6a3293e129088191abf0875820e839da-openai-curated/outputs/sparq-product-build-2026-09-04.md`
- `/Users/joey/Documents/Codex/2026-09-04/higgsfield-plugin-app-6a3293e129088191abf0875820e839da-openai-curated/outputs/sparq-athlete-home-first-value.patch`
- `/Users/joey/Documents/Codex/2026-09-04/higgsfield-plugin-app-6a3293e129088191abf0875820e839da-openai-curated/outputs/sparq-athlete-home-local-preview.png` (synthetic labeled component preview)
- `/Users/joey/Documents/Codex/2026-09-04/higgsfield-plugin-app-6a3293e129088191abf0875820e839da-openai-curated/outputs/sparq-athlete-home-verification.json`

This handoff is uncommitted in both local application repo and Control Tower. No existing docs/state/current-state.md was found, so none updated. Other preexisting Control Tower changes were left intact.


## Strategic approach follow-up
Joey asks how to approach the problem, alternative solutions, and overlooked issues. Recommendation remains a hypothesis: organization-distributed Athlete Agent on a shared trusted performance record, starting with one complete real pathway. Compare consumer-only recruiting, organization combine/workflow software, organization-distributed hybrid and capture/verification licensing. Existing paid evidence establishes assessment/talent-identification demand more strongly than recurring athlete subscriptions. Test athlete repeat use, organization effort saved, actual review/advancement and activation without founder support separately. No new prices or committed customer expansions inferred.

Important counterarguments: event-driven athlete demand may not retain monthly; club distribution may recreate AD/coach onboarding failure; increasing submissions can overwhelm evaluator capacity; partners may value verified records inside their workflow more than another destination app. Athlete/parent/org incentives and data-permission boundaries need explicit product decisions. Cross-sport pathways are a differentiated idea to investigate using actual NGB criteria, not unsupported sport predictions.

Primary sources rechecked: SportsRecruits Scout already offers profile/context-aware recruiting guidance (https://help.sportsrecruits.com/hc/en-us/articles/37141075836557-Scout-SportsRecruits-AI-Recruiting-Bot); Scorability acquired Ryzer Nov13,2025 (https://scorability.com/in-the-news/scorability-acquires-ryzer-to-create-the-most-powerful-platform-in-college-sports-recruiting-and-events/); FieldLevel has team-funded athlete access (https://support.fieldlevel.com/en/articles/6308122-prime-and-prime-benefits). USA Football official digital combine page confirms all seven exercises plus valid Athlete ID, and current second-combine deadline September21 (https://www.usafootball.com/national-team/digital-combine). These support competition/eligibility context, not proof SPARQ hybrid economics.

No additional application changes made for this strategy follow-up. Prior implementation remains local/uncommitted, with 14 scoped browser assertions and TypeScript passed; no deployment.


## Charles promotion cohort update
Joey says Charles is preparing a joint promotion targeting over 500 digital-combine athletes. In direct clarification, Joey confirms the destination is the EXISTING GMTM combine flow, not a promotion of SPARQ Agent itself. Treat this as a concrete proposed launch cohort/distribution opportunity; 500 is a goal, not confirmed participation or Agent activation. Offer the Agent as optional continuation after submitted results while preserving remaining combine tasks. No upfront Agent payment/account detour in the existing combine flow. Build contract and explicitly denominated metrics saved in outputs/sparq-usa-football-cohort-test-2026-09-04.md. Launch still requires known linking ownership fix, secure checkpoint/claim integration, authoritative task/submission adapter for missing-task promises, instrumentation and real end-to-end checks. No further application source edits or production actions made in this follow-up.


September5 supersession: Joey wants Agent assistance DURING the combine to improve completion, then continued athlete relationship/profile sharing afterward. The earlier post-submission-only entry recommendation is superseded. See 2026-09-05-sparq-completion-and-continuing-profile.md and the revised cohort brief.
