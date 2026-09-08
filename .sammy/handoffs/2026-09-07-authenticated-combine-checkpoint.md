# Authenticated combine checkpoint

September 7, 2026. Continuation of the [local browser acceptance contract](../../docs/state/live-combine-browser-contract-2026-09-07.md), same Codex-owned checkout, branch `codex/athlete-home-first-value`, HEAD `6c7e649`. This supersedes the pending-sign-in state in the earlier preparation handoff.

## Completed

- Joey explicitly authorized existing-account sign-in as `joey@gmtm.com` and reading verification codes from that connected Gmail. The fresh SPARQ verification message was checked for recipient/sender/context and redeemed in the existing local sign-in UI. No new account or identity mapping was created. No verification code, auth token or cookie was written to artifacts or emitted in output.
- The restricted backend verified the real Clerk token and unique mapping to GMTM athlete 2. The actual source reader returned adult event 1318 with nine activities, zero submissions and zero required-information-present activities.
- A manual refresh completed another authenticated guarded read: source successes advanced from one to two, with zero source failures. The displayed check time advanced from 9:27:34 AM to 9:37:39 AM Eastern and retained event 1318.
- Highlight Reel and 20-Yard Dash opened task-specific help with the correct title, organizer-instructions disclosure and recording starter. The first offscreen automation clicks reported success without activating the button; scrolling the actual activity button into view resolved this. Independent source review found no demonstrated application defect. No fix was applied.
- Desktop and 390 × 844 browser layouts were visually inspected. Mobile help occupies its own panel, closes back to the checklist and has no horizontal page overflow. This is browser viewport verification, not a physical-device test.
- Both inspected continuation links remain `https://gmtm.com/virtuals/1318`. No authenticated GMTM route was navigated. No browser exceptions were observed.

## Remaining gate

Automatic approval review rejected the first attempted Send command, stating that the authenticated private combine context would be sent to an external AI provider without specific payload/destination authorization. The command did not execute; the question field stayed empty, and the server recorded zero help requests, zero model text events and zero completed model answers. Do not retry or use an indirect provider path until the authorization issue is resolved.

The concrete proposed test asks: “What do I need to submit here, and does submitting it mean I have qualified for the team?” while focused on Highlight Reel. The configured destination is Anthropic Claude Sonnet 4.6. `build_combine_context` includes public event/activity requirements and URLs, selected activity, saved submission/evidence statuses, missing-field labels, counts, source fetch time and whether personal progress is available. It excludes the email, Clerk/athlete identifiers, contact details and submitted answer values. The question and bounded session history are also sent. At most five explicit help attempts remain under the existing harness cap; all five are unused.

After Joey approves this exact transfer, continue in the already authenticated browser, verify a grounded streamed answer plus `done`, then test the known adult dash caption mismatch and safe failure within that cap. No production changes or rollout are authorized by this local acceptance.

## Runtime, receipts and changes

Local frontend `http://localhost:3218/home/inbox?event_id=1318`, backend `http://127.0.0.1:8118`; exec sessions 93390 / 99001 remained running at this checkpoint. Browser CLI session `sparq-live-0907` remains signed in and focused on Highlight Reel help at desktop width. Verify liveness on resume. Guard details and startup paths remain in the [initial handoff](2026-09-07-local-combine-browser-acceptance.md).

Artifacts remain outside the application repo in `../sparq-live-browser-2026-09-07/`: `authenticated-checkpoint.json`, ongoing `live-server-receipt.json`, `authenticated-desktop.png`, `authenticated-desktop-activity.png`, `authenticated-mobile-help.png`, `authenticated-mobile-checklist.png` and `authenticated-mobile-refreshed.png`. Screenshots show the authorized test account and should stay local. The earlier `acceptance-checkpoint.json` is retained as historical evidence. No auth state export was created.

This continuation changes only `docs/state/current-state.md` and adds this handoff inside the repo; previous application changes remain uncommitted. No new application edit, commit, push, deployment, production data change, account reassignment or infrastructure/configuration change occurred. Existing nineteen harness tests and earlier component suites remain prior evidence; they were not rerun because no implementation changed. Current source preservation and whitespace checks are recorded in the new receipt.
