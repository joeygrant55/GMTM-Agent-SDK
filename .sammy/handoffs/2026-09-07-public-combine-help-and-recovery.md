# Public combine help and event recovery — September 7, 2026

## Outcome

Joey asked Codex to keep going after the model refinement. Under the [current contract](../../docs/state/public-combine-help-acceptance-contract-2026-09-07.md), the local interface now exposes exact public required fields without a model call and preserves an explicitly chosen combine through existing-profile recovery.

The owned checkout remains `work/sparq-agent-review`, branch `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`. All changes remain local and uncommitted. No push, deployment, production configuration/data change, new account or external message occurred.

## Product changes

- A shared “What you’ll submit” section displays required field types and exact organizer captions. It is in each card’s organizer instructions and visible directly in focused help, including for unlinked athletes and during model failures. No new fetch, model request or saved state is needed.
- The adult dash preserves the source caption “40 Yard Dash Time” and explains that it is the known mismatch for the 20-yard activity. Time and video remain separate requirements. Missing legacy definitions and unknown field types stay explicit rather than inventing formats or units.
- The frontend validates supplied public definitions, including count/type/title bounds. Malformed definitions reject the read; missing legacy definitions retain GMTM continuation with uncertainty. Public labels render as text, and unknown types cannot resolve inherited object properties.
- Focused help displays deterministic saved-progress meaning separately from its generated answer. Unlinked athletes receive an explicit public-help offer, with no invented zero progress.
- The card carries a selected event to `/connect`; supported events 1317/1318 survive sign-in and confirmed existing-connection recovery to the correct inbox. Repeated/unsupported event values cannot become a destination, and account/event changes cancel stale requests and redirects. Request bodies and linking policy are unchanged.

## Verification

All 224 actual-component checks passed: 77 account/recovery, 88 combine journey and 59 help checks. These include explicit-send-only behavior, malformed/legacy public fields, unknown progress during provider failure, exact dash/time/video captions, event recovery, stale account/event responses and 360/390/430/1440 widths. Independent React/source review found no blocker. Root inspected phone and desktop screenshots.

Current-source TypeScript passed across 92 files with no source change during the check. No package install, full Next startup, real Clerk flow, database access or model call was used by these frontend checks. They do not prove live auth redirects or guardian ownership.

Receipts and synthetic screenshots are in sibling `work/sparq-public-help-2026-09-07/`: `frontend-verification.json`, account/journey/help receipts, TypeScript receipt, `public-help-phone-390.png` and `public-help-desktop-1440.png`. The isolated TypeScript snapshot lives under `/private/tmp/sparq-public-help-typecheck-2026-09-07/frontend` and uses existing dependencies.

## Uncommitted files in this slice

- `frontend/app/home/components/currentCombine.ts`
- new `frontend/app/home/components/ActivityRequirements.tsx`
- `frontend/app/home/components/CurrentCombineCard.tsx`
- `frontend/app/home/components/CombineHelpPanel.tsx`
- `frontend/app/connect/ConnectClient.tsx`
- `frontend/app/connect/page.tsx`
- `frontend/tests/check-account-boundaries.cjs`
- `frontend/tests/check-combine-journey.cjs`
- `frontend/tests/check-combine-help.cjs`
- The new contract, this handoff and current-state pointer.

Other existing dirty/untracked work was preserved. No application backend change was part of this UI slice. Model-status acceptance is a separate bounded checkpoint under the contract, with separate receipts; frontend passing results must not be counted as model-quality evidence.

## Remaining pilot gates

Actual authenticated evidence still covers Joey’s user 2 in adult event 1318. Source and synthetic tests support junior event 1317, but its actual guardian/account policy is not confirmed. Fable’s mapped GMTM sources contain two family mechanisms (`user_parents` and `users.parent_id`); their existence does not prove which one governs the current junior journey. Preserve one-Clerk/one-athlete ownership until current product-policy evidence supports anything else.

Existing recovery GET `/api/profile/by-clerk/{clerk_id}` also remains a separate hardening target: `backend/profile_api.py` currently selects the first matching legacy row and may bootstrap a missing workspace. These navigation tests do not establish read-only recovery, unique mapping handling or a real recovery-flow acceptance. Do not start that path against production merely to test a redirect. Wider production model configuration, durable multi-worker accounting and release gates remain open.
