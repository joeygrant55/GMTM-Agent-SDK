# Current-combine implementation contract

Started and completed locally September 6, 2026 in the existing Codex implementation lane. [Verification and remaining gates](../../.sammy/handoffs/2026-09-06-current-combine-build.md). This is the next authorized local build slice, following the [verified USA Football configuration](usaf-combine-contract-2026-09-06.md).

## User clarification

Joey identifies the GMTM deadline display and adult dash labels as known platform bugs that should not block this work. He suspects a UTC/Eastern issue; the exact cause is not diagnosed here. Show USA Football's published September 21, 2026 date with its source, preserve the configured timestamp separately, and omit an exact countdown. No GMTM source configuration is changed.

The highlight activity is playing footage in addition to the structured combine exercises. Present it separately from the drills and background form's optional highlight field. Activity progress does not determine whole-program completion or selection eligibility.

## Completion contract for this slice

1. Add an authenticated, read-only current-combine endpoint for public USA Football events 1317 and 1318 under organization 249002. Resolve personal progress only for the caller's uniquely linked athlete. Fail closed on ambiguous ownership and unavailable/malformed source data. No schema writes, model calls, email, or generic recruiting bootstrap occur in this request.
2. Select a supported event explicitly through the URL or from one distinct owner-matching redeemed invitation context. Preserve invalid URL context through home entry so it results in a choice rather than silent substitution. Otherwise show a choice. Public requirements remain available without a linked athlete or numeric results. Do not infer division from an athlete's current age or select the first event arbitrarily.
3. Derive activity submission and required-field presence from current task definitions and the latest visible submission per task. Preserve both shuttle directions, video-only squat, separate highlights and nonnumeric background fields. Report unknown evidence honestly; field presence is not semantic validation or eligibility. Do not return private answer values.
4. Render current-combine progress independently of recruiting profile and inbox loading. Continue to the existing GMTM event; refresh on return/manual request without optimistic completion. Account/event changes cancel or ignore stale responses. A failed refresh retains the last successful snapshot with a visible warning.
5. Make the phone workspace usable with collapsed navigation/chat and accessible controls while preserving desktop panels. Use organizer instructions as grounded help and keep Athlete ID validation explicitly unknown.
6. Verify the actual changed code with isolated backend tests, actual-component browser journeys, phone/desktop layout evidence, TypeScript and independent review. Record limits: synthetic fixtures and HTTP mocks do not establish live GMTM/Clerk/MySQL acceptance.

## Work ownership and boundaries

- Backend agent: new `combine_api.py`, `combine_requirements.py`, adapter/endpoint tests.
- Frontend agent: current-combine component/types, inbox integration, claim event handoff, phone shell and journey harness.
- Root: router registration, home entry, integration review and checks, state/contract/handoff.
- Independent reviewer: correctness and source-contract review after implementation.

No production writes, deployment, messages, payment changes, AWS work or core GMTM changes. Existing uncommitted work and other SDK checkouts remain separate. No automatic infrastructure or organization-task resumption.

## Remaining work beyond this slice

This slice does not implement a durable cross-device event preference, external Athlete ID verification, a verified guardian/child workflow, a new uploader, semantic exercise validation, coach sharing controls, reliable outreach or monetization. The larger journey milestone remains open until its remaining acceptance gates are met. A local pass is not a launch decision.
