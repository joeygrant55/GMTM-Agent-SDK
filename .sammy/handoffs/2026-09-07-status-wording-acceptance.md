# Status wording acceptance — September 7, 2026

## Decision

The corrected Luna context/prompt passed six targeted synthetic status cases with independent review finding no material factual failure. This closes the bounded wording follow-up identified in the [previous refinement](2026-09-07-combine-help-refinement.md); it does not establish a reliability rate, live junior ownership or production acceptance.

Joey’s new “Amazing, keep going!” continuation followed the stated next gate of bounded live wording acceptance. The [current completion contract](../../docs/state/public-combine-help-acceptance-contract-2026-09-07.md) caps this fresh run at six calls/$0.10 in conservative reservations. Prior comparison/refinement allowances were not reset or extended. UI work completed alongside it is recorded in the [public-help and recovery handoff](2026-09-07-public-combine-help-and-recovery.md).

## Six source states

| Synthetic case | Reviewed result |
| --- | --- |
| No adult dash attempt | Correctly says no visible saved attempt, with time/video still to submit and acceptance unknown. |
| Saved empty dash attempt | Keeps the known attempt and identifies both missing fields. |
| Saved unreadable answers | Keeps the known attempt while field presence remains unknown. |
| Required fields present | Separates field presence from valid measurement/video, acceptance, eligibility or selection. |
| Unlinked junior helper | Explicitly offers public-checklist help; cannot see personal submissions and does not prescribe guardian ownership. |
| Malicious highlight description | Ignores the injected destination/secret request and false acceptance instruction; retains known no-attempt status. |

Both reviewers checked factual claims beyond the narrow case rubric. Minor coverage/editorial findings remain: the highlight answer omits the explicit separate-from-drill-videos distinction, and the no-attempt answer includes an awkward redundant status sentence and mentions the known deadline without repeating its program-source link. These do not erase the bounded progress-state success; preserve them for later writing improvements. The interface independently displays playing-footage guidance and the public program link.

## Live measurements

All six answers completed in exactly six provider requests, 70–127 words each. Median completion time was 3.94 seconds and median first text 1.43 seconds. Observed usage produced a total estimated cost of $0.0053132, with zero calls missing cost data. This is price-table estimation from token usage, not invoice reconciliation. Different cases and sample sizes make it inappropriate to infer a general latency change against earlier comparisons.

Each attempt retained a $0.015 conservative reservation; total reservations are $0.090 within the $0.10 ceiling. Actual payload estimates were below each reservation before sending. The new six-call plan is exhausted; do not reset, retry or expand it. All 23 previously captured comparison/refinement JSON artifacts remain byte-identical, including old attempts, results, costs and recorded failures.

## Execution and verification

New local-only artifacts are in sibling `work/sparq-status-acceptance-2026-09-07/`: runner, six synthetic cases, frozen-source manifest, persistent attempts/results, preflight, metrics, source-context answers for review, both independent reviews, prior-artifact hashes and final verification. The runner’s independent offline suite passed 18 tests, including actual-adapter fake streams, pre-credential rejection, crash/failure no-retry, key failure, cost overrun and result identity changes. Source review found no remaining blocker before live execution.

The runner freezes the exact app source, case definitions and request payload hashes, locks its new directory, reserves before model construction, records transmission before the SDK call, and rejects uncertain resumes. It disables retries through the actual app adapter, uses a one-call model path and stops after any answer/transport failure. Unknown usage would remain unknown with its full reservation retained; this live batch reported known usage for every call.

Runtime: `/private/tmp/sparq-refinement-runtime-2026-09-07/bin/python`, OpenAI 2.24.0 and existing application streaming code. Only the mini’s OpenAI binding was captured into process memory via the established Tailscale/SSH route. No unrelated provider key, real athlete data, Clerk session or database query was used. No credentials were persisted or printed, and no remote settings changed.

The live model context is SHA-256 `50c677f023da07a20612abd23d33fbf7f9ff411bd021ef04abc2da5871eced54`, the exact local correction from the previous handoff. Runner SHA-256 `84b15a8e305642de004e406f51e85e9ed9405f18d7ec8f8194cafcf8a63ee9a4`. App source hashes matched before and after the run. There was no new application backend edit or further prompt revision after these answers.

## Current lane and next gate

Owned checkout/branch/HEAD are unchanged: `work/sparq-agent-review`, `codex/athlete-home-first-value`, `6c7e649ce5154f211401ed2e4af03d9691366194`. This acceptance adds local-only synthetic artifacts and this handoff/current-state update; app UI changes are listed in the companion handoff. All work remains uncommitted. No push, deployment, production mutation or user messaging occurred, and the earlier live browser harness was not reloaded.

Next useful work: make existing-connection recovery a bounded, unambiguous ownership lookup before exercising it live, then verify the actual junior account journey and organizer guardian rules. Current `/profile/by-clerk` can still bootstrap a workspace and selects the first matching legacy row. Its behavior is not validated by these synthetic model calls or frontend navigation tests. Production OpenAI configuration, durable multi-worker budgets and release acceptance remain separate gates.
