# Focused athlete design

## Request and ownership

Joey said the page had too much text and asked for a simpler, interactive, beautiful design. Codex continued its existing `sparq-agent-review` checkout on `codex/athlete-home-first-value`, starting clean at `286366c4ee8104f01d4790d1164747343481c2ae`. Fable infrastructure/security and Audit organization lanes were untouched. Read the [completion contract](../../docs/state/profile-focus-design-contract-2026-09-08.md).

## Delivered

- The first screen now has compact identity, View profile, one question, three editable intent starters and Ask SPARQ. Current 390x844 synthetic capture contains 53 visible words; the full Ask control fits its first viewport.
- A native modal sheet holds the existing measurements, submissions, footage, selection controls and source context. Done/Escape restores focus. Opening it does not reload data or call AI. The sheet fills the phone viewport and sits at the desktop's right edge.
- Successful answers collapse the form and emphasize the takeaway and one action. Unknowns stay visible. Observations/action reasoning open under Why this answer; citation buttons open and focus their source disclosure. Adult USA Football scope remains explicit.
- Local actions and Write an introduction open a dedicated composer. Preparing text collapses the inputs behind Edit details; Copy becomes primary. Changing an action's output kind opens its new details without replacing the existing draft. Back to SPARQ/Return to your draft preserve answer, edits and selections.
- Request cancellation, account-key reset, strict parsing, stale-answer guards, draft eligibility and exact clipboard behavior remain. No dependency, backend contract, provider prompt, model or infrastructure change.

## Verification

All heavy runs were finite and serial. Every owned browser/service process group and port closed.

- 198 component checks pass: account/source isolation, timeouts, strict validation, clipboard failures, explicit rebuild, modal focus, intent prefills, no automatic requests, collapsed answer and preserved editing state.
- 86 actual Next/ASGI journey checks plus five safety assertions pass. Auth, SQL and provider output are synthetic. One explicit synthetic debrief per full-app run, zero real provider attempts, all synthetic connections closed.
- Final actual Next production compile/typecheck/start passes using real Clerk packages and synthetic configuration. The initial production pass preceded a one-line composer refinement; the final run verifies that exact refinement.
- Final source bytes match all retained component, actual-app frontend/backend and production receipts. `git diff --check` passes. Backend source and the API policy were unchanged; their broad suites were not rerun for this design slice.
- Independent source review found no blocking state/privacy regression. Root and a second reviewer inspected initial, answered, editor and sheet states on desktop and phone. No visible overlap/horizontal overflow. The first editor screenshots retained Playwright's end-of-text scroll; final captures explicitly show the beginning, with no product code change.

Evidence lives outside Git, under the sibling `work/` directory:

- `sparq-focus-design-2026-09-08/verification.json` — aggregate result, source counts and supervisor receipts.
- `sparq-focus-design-2026-09-08/component-01.json` — component behavior.
- `sparq-focus-app-2026-09-08-02/` — final app screenshots, source hashes, app/backend receipts.
- `sparq-focus-production-2026-09-08-02/` — final production compile/start receipts.
- The local checkpoint hash is recorded in `sparq-focus-design-2026-09-08/commit-receipt.json` after commit.

## Limits and next action

This verifies a much more focused interface and its mechanics. Synthetic answers do not prove compelling advice, long-answer usefulness, real-account acceptance or willingness to pay. No real athlete database read, model call, external message, push or deployment occurred. The separately prepared eight-call synthetic model-quality allowance still awaits Joey's answer; this design request did not grant it. Persistent drafts/goals, durable multi-worker quotas and release packaging remain open.

Next: Joey can review the new initial and answered screens, then evaluate real advice usefulness under the separately authorized model/identity gates. Keep post-combine profile value central; do not reintroduce a duplicate submission checklist or a persistent test server.
