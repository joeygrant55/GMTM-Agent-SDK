# Opportunity catalog refreshed — September 30, 2026

Owner: Codex product execution subtask under the root SPARQ lane. Checkout `work/sparq-agent-review`, branch `codex/athlete-home-first-value`, starting application HEAD `d709e43944db6fa33bfd1c1404b2883be80826b6`, origin `joeygrant55/GMTM-Agent-SDK`. Local AGENTS, current state, operating contract and registry were read; CLAUDE.md is absent. Root retains `docs/state/current-state.md` and its existing September 25/30 handoffs. Those uncommitted files were preserved.

## Completion contract and result

Apply fresh official evidence to the existing five-record collection, correct passed-deposit and uncertain-age semantics, keep ended assessment windows withdrawn, and verify bounded freshness/filtering through the actual shortlist implementation. This local task is complete; no hosted release or real athlete acceptance is implied.

- `backend/opportunity_catalog.py`: renewed checked time `2026-09-30T21:09:58Z`; ordinary source receipts expire `2026-10-07T21:09:58Z` (seven days, before Tampa's balance deadline). Four continuing options remain at the review time: High Performance inquiry, Orlando/Tampa team events and organizer inquiry. Response still limits matching options to three.
- Orlando withdraws at `2026-10-02T00:00:00Z`, the existing conservative internal cutoff, rather than lasting seven more days. Both its summary and cost text say the deposit-balance deadline passed and require confirmation that new fully paid entry is still accepted. Status remains `check_details`; there is no availability/registration guarantee.
- Tampa's requirements now flag the published U23 cutoff naming January 1, 2026 for a 2027 event and ask the athlete to confirm division/roster rules. No birthday, division eligibility or corrected cutoff is inferred.
- The historical USA Football Combine 2 remains withdrawn after September 21; its unreviewed GMTM entry receipt retains its old checked/expiry times. A renewed public schedule does not reopen that window.
- Updated the focused catalog regression coverage and the existing actual-catalog filter test's clock. No frontend, route, authentication, account mapping, database schema or measurement configuration changed.

## Official evidence and review limits

These five pages were re-opened and relevant sections read starting at `2026-09-30T21:09:58Z` (5:09 PM EDT), after the preparatory 1:21 PM EDT research. Web-reader crawl recency is explicit below; this is review of retrieved official content, not a live checkout/registration test. Earlier field-level research lives outside Git in sibling `../gmtm-autonomous-revenue-2026-09-30/opportunity-refresh-research.md`.

| Official source | Fresh observation and application |
| --- | --- |
| [USA Football digital combines](https://www.usafootball.com/national-team/digital-combine) — reader crawl last week | Combine 2 still ends September 21; Combine 3 dates remain unannounced. Keep the current assessment withdrawn. No GMTM event page or later registration window was established. |
| [USA Football national team](https://usafootball.com/national-team) — reader crawl today | `teamusa@usafootball.com` remains the High Performance event inquiry address. Retain the sourced draft recipient; dates, costs, response time and selection outcome remain unknown. |
| [Battle Orlando](https://iflag.org/tournaments/2026-battle-orlando/) — reader crawl two days ago | October 10–11 in Winter Haven; open-invite team entry and $375 listed divisions remain published. Deposit balance was due September 25; hard cutoff is October 2, both labelled 7 PM EST. Correct passed-deposit text and withdraw conservatively at the start of October 2 UTC. Current capacity, checkout totals and acceptance of new paid entry are unknown. |
| [Tampa National Championships](https://iflag.org/tournaments/2027-tampa-national-championships/) — reader crawl yesterday | January 14–17 at Tournament Sportsplex of Tampa Bay; existing team prices and October 9 balance requirement remain supported. U23 FAQ says January 1, 2026 while older-age cutoffs reference the 2027 event. Ask for confirmation rather than infer eligibility. Renew for seven days, before the imminent balance requirement. Capacity, individual team placement and checkout totals remain unverified. |
| [iFlag contact](https://iflag.org/contact/) — reader crawl last week | `contact@iflag.org` remains the public inquiry address. Retain inquiry/contact references. No free-agent placement, response commitment, partnership or referral terms were established. |

Tournament competition and organizer championship advancement remain separate from USA Football/Olympic qualification. Publisher EST wording is preserved, not silently converted into a claimed official UTC cutoff. Our source expiry and conservative withdrawal are internal freshness policies.

## Verification

**168 passed, two dependency deprecation warnings**, running only `backend/tests/test_opportunity_catalog_refresh.py` and `backend/tests/test_athlete_opportunities.py`. Python 3.13.7, isolated cached-package runner. Tests cover the real refreshed collection through `reviewed_shortlist`, before-review denial, exact expiry/cutoff withdrawal, unchanged ended-combine exclusion, truthful deposit/age text, separate team versus individual/contact routes, source validation, owner-bound read handling and synthetic HTTP error boundaries.

Pytest reported 76.93 seconds; external supervisor elapsed 89.487 seconds, exit 0, no timeout. Process reaped and owned process group absent. No listeners/services were started. SHA-256 of the changed catalog/tests plus shortlist implementation and offline guards matched before/after. Tests install fail-closed DNS/TCP/database/model guards and synthetic service interfaces; optional missing SDK imports use the existing fail-closed suite shims. These checks do not establish real Clerk, provider, MySQL, hosted-build or athlete-use acceptance.

Private local receipts, outside Git, in sibling `../gmtm-autonomous-revenue-2026-09-30/`:

- `catalog-refresh-test.log`
- `catalog-refresh-test-receipt.json`
- `catalog-refresh-runner-setup.json`: initial sandbox cache-access failure, no network or test run.
- `catalog-refresh-runner-setup-approved.json`: offline environment created; first dependency resolution lacked cached PyJWT. PyJWT is not needed by the synthetic-auth focused tests. Installing the remaining required cached packages succeeded.
- `catalog-refresh-test-venv/`: isolated local runner only; no application dependencies or shared environment changed.

`git diff --check` passed. Changed files are the catalog, its focused regression tests, the existing actual-catalog filter test and this handoff. This subtask does not stage, commit or push; root owns review/integration and the final uncommitted list.

## Next release step

Root reviews these facts/diff, integrates the source checkpoint and re-packages the explicit profile candidate: the September 23 source archive contains the expired catalog and must not be used as proof of this refresh. Resolve the exact paired hosted targets, runtime/admission configuration and rollback, then obtain the scoped release decision and verify an admitted adult's actual journey. Re-review/remove Orlando at its imminent cutoff; remaining source receipts need review before October 7. Further local feature expansion is not a prerequisite to that test.

No deployment, push, production/account/DB/auth change, secret retrieval, provider call, payment, registration or external outreach occurred.
