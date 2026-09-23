# Adult flag catalog refresh — September 23, 2026

Scope: refresh the existing five records, using official public pages. Reviewed by `2026-09-23T16:17:39Z`. No private athlete data, provider calls, registration, messages or deployment. Existing IDs and response schema are unchanged.

## Current official evidence

| Source | Observation and catalog decision |
| --- | --- |
| [USA Football digital combines](https://www.usafootball.com/national-team/digital-combine) | Calendar still ends Combine 2 on September 21; Combine 3 has no announced date. Keep Combine 2 withdrawn. The adult requirement remains age 18+ on December 31, 2027 with Athlete ID; no later opening or personal qualification inferred. |
| [USA Football national team](https://usafootball.com/national-team) | Have Questions still publishes `teamusa@usafootball.com` for High Performance event questions. Renew this standing inquiry route; dates, fees and a response promise remain unknown. |
| [Battle Orlando](https://iflag.org/tournaments/2026-battle-orlando/) | Details/Fields/Deadlines/Divisions retain the dates, Winter Haven venue, team prices and deadlines recorded in the catalog. The imminent deposit-balance date is September 25, followed by the October 2 hard cutoff. Explicitly preserve open-invite team entry without prior qualification; that does not provide individual placement. |
| [Tampa National Championships](https://iflag.org/tournaments/2027-tampa-national-championships/) | Direct page confirms January 14–17, 2027 at Tournament Sportsplex of Tampa Bay. Retain 5v5 non-contact team pricing; clarify the October 9 balance cutoff and November 27 late fee, both published as 7pm EST. December 4 remains the new-entry deadline without an exact time. Open-invite team entry does not establish USA Football/Olympic qualification. |
| [iFlag contact](https://iflag.org/contact/) | Direct page publishes `contact@iflag.org` for general inquiries. Renew the two event contact references and team-access inquiry. A free-agent route, team placement and response time remain unconfirmed. |

USA Football and Orlando were read through the web reader. Tampa/contact initially timed out there; a bounded direct HTML fallback returned 403. Both official pages then loaded in an ordinary Chrome tab and were read directly, including Tampa's division prices and actual venue. That research tab was closed. Source dates were advanced only after these successful reads, not from search snippets.

The [existing GMTM entry](https://gmtm.com/virtuals/1318/2027-u-s-flag-national-team-adult-digital-combine-2) exposed no current readable event detail. Its source receipt retains September 10/17 checked/expiry dates. The schedule receipt is fresh, but neither that receipt nor a visible registration link reopens an ended window.

## Freshness and truth boundaries

- Four continuing records are available after review: one national-team inquiry, two Florida team events, one organizer inquiry. Queries still return at most three. The fifth, historical combine record is retained but excluded by the existing expiry and closing rules.
- Orlando review expires `2026-09-25T00:00:00Z`, before the imminent deposit date. Other renewed evidence expires `2026-09-30T16:17:39Z`. These are SPARQ review policies, not organizer deadlines. No background monitoring is scheduled.
- Existing conservative final withdrawal timestamps remain October 2 for Orlando and December 4 for Tampa. Publisher “EST” language is preserved; we do not silently choose a daylight-saving interpretation.
- Both events stay `check_details`: capacity, checkout totals, personal age/ranking/roster eligibility and completed registration were not tested. Contact actions only prepare a draft. Competition remains distinct from national-team selection.
- Previous research notes remain historical receipts: [September 10 events](adult-flag-events-2026-09-10.md) and [national-team routes](athlete-opportunities-2026-09-10.md).

## Local verification

Dedicated offline regression tests cover the actual catalog through the production shortlist validator: ended-combine exclusion despite renewed source dates; current national/team/individual filtering; Orlando's shortened review boundary; global expiry; no future-reviewed results; retained unknown inquiry facts and fee/entry distinctions. Execution result will be recorded below. Root owns integration, shared-test updates and the dated handoff; no commit was made by this subtask.

Final integrated verification: all six dedicated refresh regressions passed within the 983-test affected backend run. Raw output: `../sparq-pilot-gate-2026-09-23/focused-03.log` relative to the repo; receipt confirms exit 0, matching input hashes and reaped supervisor process.
