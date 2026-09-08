# Current-source self-account acceptance

September 7, 2026. Joey requested the proposed acceptance using the same isolated method as prior tests. The [completion contract](../../docs/state/self-account-acceptance-contract-2026-09-07.md) is complete. The tested current source passed for Joey's existing account; no application changes were needed in this continuation.

## Observed product result

- The existing signed-in browser passed actual Clerk signature/issuer/expiry/authorized-party verification. Guarded forward/reverse lookups verified the unique GMTM athlete 2 mapping; the current by-Clerk handler found the existing SPARQ workspace. No account, claim, mapping or workspace was created.
- Junior 1317 → adult 1318 → junior 1317 retained the same athlete and the selected division. Both actual events returned nine activities, zero submissions and zero activities with required information present. These were observed source values, not assumed fixtures.
- Signed-in recovery through `/connect?event_id=1317` and `/connect?event_id=1318` returned to each corresponding inbox and retained its GMTM continuation destination. The browser was already signed in; no fresh email verification or expired-session sign-in was needed.
- At 390×844, adult manual refresh advanced the displayed check time from 3:59:05 PM to 4:00:05 PM, retaining event 1318 and the observed counts. This proves a refreshed read, not a new saved submission.
- Adult public instructions and focused help showed the exact `40 Yard Dash Time` measurement and `20 Yard Dash` video fields, with the known organizer caption mismatch explained. Junior focused Highlight Reel help showed Video / `Upload your Highlight Reel`; the card distinguished playing footage from exercise videos and the background form.
- Desktop and phone observations passed the scoped DOM checks. Phone viewport and document widths were both 390. Both phone help screenshots passed independent visual review. This does not establish physical-device/keyboard behavior; the junior still image does not show the composer.

## Verification and limits

Local-only receipts and screenshots are in [`work/sparq-self-account-2026-09-07/`](../../../sparq-self-account-2026-09-07/):

- [Final verification](../../../sparq-self-account-2026-09-07/final-verification.json): all 161 captured application files remain unchanged, all 123 frontend source and snapshot files match, all 12 frozen backend/harness files and two continuation files match, and all 23 prior model comparison/refinement JSON artifacts remain unchanged. `git diff --check` passed.
- [Final live ledger](../../../sparq-self-account-2026-09-07/self-account-continuation-receipt.json): **9 admitted reads, 9 source successes, 45 reserved SELECT attempts, 0 source failures, 0 provider calls, stopped=true**. The SELECT counter reserves before the driver call; it is not a separate post-execution SQL audit. The same 20-read/140-SELECT caps were never increased or reset after use.
- [Boundary probes](../../../sparq-self-account-2026-09-07/live-boundaries.json): missing/invalid session 401, wrong origin 403, unsupported event 404 and disabled model-help POST 503; all five rejected before any source read. The final ledger has one authentication failure, one route failure and 53 boundary rejections, including deliberate probes and unrelated workspace panels. Zero source failures does not mean the entire application served successfully.
- [Harness verification](../../../sparq-self-account-2026-09-07/live-runtime-offline-verification.json): 39 offline tests passed using the actual live runtime. [Continuation verification](../../../sparq-self-account-2026-09-07/resume-offline-verification.json): 24 offline tests passed. These use synthetic drivers/signatures and are separate from the live browser evidence.
- [Independent harness review](../../../sparq-self-account-2026-09-07/review-herschel.md), [continuation review](../../../sparq-self-account-2026-09-07/review-resume-herschel.md) and [browser/receipt review](../../../sparq-self-account-2026-09-07/review-browser-halley.md) found no scoped blocker.
- Browser JSON records division, public requirements, counts, freshness and dimensions. Representative images: [junior desktop](../../../sparq-self-account-2026-09-07/junior-desktop.png), [adult phone dash help](../../../sparq-self-account-2026-09-07/adult-phone-dash-help.png), [junior phone highlight help](../../../sparq-self-account-2026-09-07/junior-phone-highlight-help.png). Private self-account images remain local; no cookies/tokens/private saved answers were exported.

The isolated backend mounted the actual current combine GET and an AST-extracted exact current by-Clerk handler. It did not import the full profile module or run application startup/schema/bootstrap. Both databases used exact scoped SELECT templates inside guarded read-only transactions with rollback/close. GMTM stayed pinned to db2-dev/gmtmread; Railway used its existing public proxy. Other routes, models and writes were unavailable. No authenticated GMTM submission/event route was visited.

## Runtime repair and cleanup

The first launcher stopped before serving HTTP or opening a database because Hermes Python lacked real PyMySQL. Its stopped receipt records zero activity and remains byte-for-byte unchanged. No dependency was installed. The existing `/Users/joey/GMTM-Agent-SDK/backend/.venv/bin/python` supplied the actual dependencies; the harness tests were rerun there before live use. A separately frozen, reviewed one-time continuation verified the exact zero-use predecessor and preserved its caps in an exclusive linked receipt. It refuses nonzero prior use or an existing continuation; this is not a reusable restart/reset mechanism.

Only the identified previous SPARQ test servers were replaced. Their prior live receipt naturally changed `stopped` on shutdown while retaining its counters; the pre-stop receipt copy is preserved in this artifact directory. At completion, the new backend PID 80889 and frontend parent 68920/child 68940 stopped; `lsof` confirmed no listeners on 8118 or 3218. Only SPARQ tab `t1` was closed in the shared browser session. Other tabs were preserved. No test service remains available at the local inbox URL.

## Remaining pilot gates

This closes current-source self-account identity, division isolation, existing-session recovery, refreshed reads and static contextual-help rendering. It does not establish deployed endpoints, full application behavior, generated answers, a new saved submission, claim concurrency in production, real junior ownership, guardian authority, eligibility, organizer acceptance or selection. The [junior matrix](../../docs/state/junior-account-acceptance-2026-09-07.md) retains the actual actor/athlete arrangement as unknown. The question to Joey remains unanswered; elapsed time is not policy evidence.

Next: resolve that organizer arrangement and consolidate the pilot release gates for onboarding, source freshness, operational errors and bounded model usage. Do not reopen exhausted model allowances or bypass one-athlete ownership to manufacture junior acceptance. Existing GMTM remains the submission destination.

## Checkout and uncommitted files

Checkout `work/sparq-agent-review`, branch `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`, origin `https://github.com/joeygrant55/GMTM-Agent-SDK.git`. No relocation, commit, push or deployment occurred. Prior dirty application work was preserved.

This continuation adds/updates only these repository documents:

- `docs/state/self-account-acceptance-contract-2026-09-07.md`
- `docs/state/junior-account-acceptance-2026-09-07.md`
- `docs/state/current-state.md`
- `.sammy/handoffs/2026-09-07-current-source-self-account-acceptance.md`

The sibling operator/verification artifacts and temporary frontend snapshot are new local files outside this repository. See the [full git status](../../../sparq-self-account-2026-09-07/git-status.txt) for the existing uncommitted batches. No production data, cloud configuration, provider binding, infrastructure, payment setting or external message changed.
