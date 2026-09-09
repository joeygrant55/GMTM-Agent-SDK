# Footage preview repair and opportunity research direction

Date: September 9, 2026. Codex retains the SPARQ writer lane in this checkout, branch `codex/athlete-home-first-value`. Starting HEAD: `25c7c5f9fe196c0c3969700d81da147c2fcf5d20`; the working tree was clean. Remote: `joeygrant55/GMTM-Agent-SDK`. Fable's infrastructure/security work and other checkouts were untouched.

## Request and completion contract

Joey requested the broken footage previews be fixed and emphasized research into relevant opportunities, people to contact and in-person ways athletes can demonstrate skills. Completion for this repair requires real owner-2 posters loading through the current app, preservation of existing saved work, focused regression coverage, and a concrete next research milestone. This does not authorize deployment, outreach, new saves or provider calls.

## Observed cause and repair

A fresh bounded materials read returned both eligible public film references with null thumbnails. The existing public GMTM pages rendered both posters successfully; their actual stored CDN keys used the literal `users/undefined/uploads/<UUID>.jpg` namespace. This was excluded by SPARQ's backend normalizer and frontend parser. The initial failure was not established as a CORS problem.

Both layers now allow only that exact legacy namespace, UUID-shaped filename and existing raster extensions. Original numeric upload paths, supported services, exact CDN host, URL rejection rules and film owner/public-source checks are retained. No ownership is inferred from the legacy storage directory. No SQL changed and no poster URL is guessed or repaired in GMTM. Anonymous cross-origin images and no-referrer settings remain enabled. This verifies stored image previews, not video playback or athletic ability.

Synthetic normalization/parser fixtures cover the legacy shape, malformed paths, unsupported services and private/foreign-owner records. The complete-app synthetic fixture now feeds a legacy stored key through the actual backend, response parser and image element.

## Verification

One heavy job ran at a time, each under the existing finite external supervisor. All passed with confirmed owned process cleanup:

- Materials normalizer, owner reader and reader launcher: **274 tests**.
- Acceptance guard and launcher, including new read-only mode: **49 tests**.
- Profile component browser harness: **327 checks**, no browser errors.
- Actual Next/ASGI fixture app: **120 checks plus five safety assertions**, no browser errors; Chromium, Next and backend groups dead, all three owned ports closed, frontend/backend source hashes unchanged.
- Independent source review found no actionable issue in the ten changed code/test files. Whitespace checks pass.

The relevant backend suites emit the existing Starlette/AnyIO deprecation warning. No new production build was needed for the narrow parser repair; the actual Next development app and current component bundle were exercised. Earlier production-build receipts remain historical and are not presented as a new build.

## Actual account follow-up

The prior three-save allowance is exhausted. Added an explicit `--read-only` launcher mode and strict factory flag: authenticated source/workspace GETs continue, while PATCH and its preflight are rejected before auth/database access and the independent per-run PATCH cap is zero. Default three-save behavior and global caps are unchanged. This wrapper is a local verification tool, not a deployed route.

Prepared a fresh 176-file snapshot in `/private/tmp/sparq-profile-preview-2026-09-09-01` and launched for at most 600 seconds. Existing Railway/Vercel configuration was retrieved into memory/child environments only. Real Clerk authentication and unique owner-2 linkage passed without another sign-in. Both image elements loaded and decoded:

- Featured Shuttle poster: 1080 × 1920.
- Second public film poster: 720 × 1280.

Both retained `crossOrigin=anonymous` and `referrerPolicy=no-referrer`, loaded again after a full reload and no longer displayed the unavailable fallback. No image/browser error was observed; Clerk's development-key warning remains expected. Existing version-3 goal, featured reference and saved draft were displayed; the unchanged draft's save button was disabled. Nothing was edited or saved.

Final real ledger: six personal GETs, 40 SELECTs, 16 connections opened/closed, **zero PATCH attempts, commits, denials, errors, provider calls and GMTM writes**. An explicit STOP ended the finite parent. Both owned groups are dead, ports 54552/54553 are closed and the source manifest is unchanged. The browser may retain a cached page; no preview service remains running.

The separate pre-fix diagnostic used two opened/closed connections, seven SELECTs and eleven explicit statement reservations; its owned child group is also dead. Its private materials projection and the real workspace before-state remain outside Git. No migration, AWS/RDS/IAM/API-server change, claim/link operation, outreach, push or deployment occurred.

## Durable evidence

Safe receipts and test logs: sibling `../sparq-footage-preview-2026-09-09/`. The complete-app fixture artifacts are in `../sparq-footage-preview-app-2026-09-09-01/`. The safe receipt directory contains test supervisors/results, read-only real browser/ledger/cleanup receipts, source manifest, pre-fix diagnostic receipts and the final local commit receipt. Private account bodies and exact real poster URLs are not committed.

## Next product milestone

[Find my next opportunity](../../docs/state/athlete-opportunity-research-2026-09-09.md) is the new implementation contract: up to three genuinely useful options, grounded in the athlete's confirmed goal and constraints, with current official evidence, known eligibility/fees/dates, a relevant public contact where appropriate and one useful action. Use compact visual cards and expandable details; preserve existing drafts when opening the introduction composer.

Start with a small human-reviewed source set, then add bounded discovery behind the same evidence contract. The legacy research/enrichment routes contain useful concepts but currently accept weak verification, fabricate fit percentages, hard-code a class year and include an outreach loader without the current owner binding. Do not remount them unchanged. The founder's inspiration footage also illustrates why upload ownership does not prove who appears in a video or the athlete's ability.

Research is specified, not implemented or populated with live recommendations. Next acceptance is profile → relevant reviewed options → selected option → useful next action, followed by athlete feedback on actual relevance. The preview repair is a local commit; its hash belongs in the sibling commit receipt, avoiding a self-referential handoff hash.
