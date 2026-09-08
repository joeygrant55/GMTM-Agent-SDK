# Sidebar combine event context — September 7, 2026

Codex's delegated frontend lane fixed one navigation regression in the existing owned checkout on `codex/athlete-home-first-value` at `6c7e649`. Existing dirty work was preserved; no branch switch, commit, push or deployment occurred.

## Completion contract and result

When an athlete explicitly selects adult combine 1318 in the current URL, clicking the sidebar's **My next move** must retain that event instead of falling back to a previously claimed junior event. `WorkspaceSidebar.tsx` now reads the same supported event context as the combine card and appends it only to the inbox navigation link. The other links, API calls, routes and authentication remain unchanged. This does not persist an event across unrelated routes that omit the query parameter.

## Verification

- Added a real rendered shell/menu-click regression to `frontend/tests/check-combine-journey.cjs`: explicit adult URL, synthetic saved junior claim, click My next move, verify adult heading/division/URL remain.
- The saved original sidebar failed exactly that new assertion in an isolated browser run; no application source was reverted for the baseline.
- The corrected existing journey harness passed **89 checks**. Clerk, Next navigation, source data and requests remain synthetic/intercepted. The owned browsers exited and closed through the harness cleanup.
- Full current-source TypeScript snapshot passed with no source changes during the check. JavaScript syntax and targeted whitespace checks passed.
- Initial current-checkout dependencies stalled loading Tailwind; the attempts were stopped. The prior known dependency tree loaded successfully. Chromium initially failed the filesystem sandbox's MachPortRendezvous permission check; the ordinary approval path then approved both fully intercepted browser runs. No dependencies were installed or browser sandbox flags altered.

Receipts and exact patch: [baseline failure](../../../sparq-gmtm-resume-2026-09-07/sidebar-event-baseline-receipt.json), [89-check pass](../../../sparq-gmtm-resume-2026-09-07/sidebar-event-fixed-receipt.json), [TypeScript](../../../sparq-gmtm-resume-2026-09-07/sidebar-event-typecheck.json), [isolated patch](../../../sparq-gmtm-resume-2026-09-07/sidebar-event-fix.patch).

## Scope and limits

Application/test files touched by this lane: `frontend/app/home/components/WorkspaceSidebar.tsx` and `frontend/tests/check-combine-journey.cjs`. This handoff is the only repo documentation added by this lane. Root owns the combined current-state update and integration review. Prior versions are saved under the sibling `sparq-sidebar-event-fix-2026-09-07/before/` directory; no existing receipt was overwritten.

No real accounts, GMTM submission, database, models, Next server, live network request or release was exercised. Full Next startup, actual GMTM navigation and submission-return acceptance remain open. This is a local uncommitted fix awaiting root review, not a release candidate or public launch.
