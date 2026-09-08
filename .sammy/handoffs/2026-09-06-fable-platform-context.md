# Fable platform context and dual combine planning — September 6, 2026

Joey asked whether Fable's existing all-repository mapping would help or whether Codex should deep-audit all GMTM repositories, and clarified that USA Football currently runs both adult and junior digital combines.

## Decision

Use Fable's existing platform map as the broad discovery index, then have Codex verify the narrow authoritative integration paths against the current SPARQ source. Request exact repository/revision pointers, adult/junior event comparison, registration-before-submission access, task/submission rules, account/guardian relationships, reusable services and sanitized fixtures. Do not duplicate an exhaustive audit before making progress on the athlete loop.

The current SDK workspace allows one linked GMTM athlete per Clerk account. Junior naming alone does not imply a guardian model, but if current program operations allow one guardian to manage several athletes, that is a material actor/athlete design dependency. Do not bypass the ownership guard or assume the adult flow covers it.

## Artifacts and scope

- Added task output `outputs/fable-gmtm-platform-handoff-request-2026-09-06.md`, a ready-to-share request; no message was sent to Fable or another application.
- Updated `docs/state/sparq-combine-journey-plan-2026-09-06.md` with the adult/junior scope and verification dependency; refreshed its task-output copy.
- Updated `docs/state/current-state.md` with the new context and next discovery input.
- Added this handoff. All changes are local and uncommitted; no application edits, commits, pushes, deployments or production operations occurred.

Owner remains Codex in `Evaluate Sparq agent project`, checkout `work/sparq-agent-review`, branch `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`, origin `joeygrant55/GMTM-Agent-SDK`. Prior implementation work remains uncommitted in the same lane. No repo-local CLAUDE.md was found. Read-only planning review was requested from the backend reviewer.

## Verification and next action

Verified document consistency, local link resolution and whitespace for this planning-only change; `git diff --check` passed. The task-output plan matches the repository plan with relative links rebased to their actual sources. No application tests are rerun. Await the map path or handoff artifact; the user was asked for its location. A bounded filename search of the local Control Tower docs/handoffs did not identify the new platform map and does not establish that it is unavailable elsewhere.

Exact adult/junior URLs, event IDs, program rules, dates and Charles's promotion coverage remain unknown. Do not reuse historical fixture IDs as confirmed current combines. Once Fable's artifact arrives, compare it with the existing adapter source map and milestone contract, record reuse/gaps, and implement the bounded event-context/requirements slice.
