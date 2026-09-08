# SPARQ: make the athlete's existing profile useful

Decision source: Joey's September 8 founder walkthrough and explicit correction. Codex owns this product lane in `codex/athlete-home-first-value`; source audit began at clean `15b3fd9`. This is a revised direction and bounded next-slice specification, not an implemented or deployed experience.

## The problem to solve

GMTM already captures digital-combine tasks and submissions, predominantly through its mobile app. Joey reports that this flow has worked for three years. A second checklist on desktop asks athletes to manage the same work twice. The local demo compounded that problem with blocked external navigation and canned help. Codex has inspected source and synthetic journeys, but has not completed a real combine as a participant.

SPARQ should help athletes understand and use the profile they are building: what their performance evidence shows, what happens in the program next, and which concrete action could create an opportunity. A completed combine is a useful entry point, not a prerequisite for every useful profile action. The desktop workspace should also remain usable on a phone; athletes should not need to change devices to receive value.

## First experience to build

One private **profile debrief** that answers an actual question and helps prepare a relevant action. Establish the athlete's goal and intended use first. A factual profile summary or coach introduction is useful when there is a real recipient/use; contacting a coach is not a universal next step in a national-team selection process. Lead with evidence and a useful output. Supporting process guidance is available in context; the old per-activity checklist is not the home screen. Uploads continue in GMTM.

1. **Understand my profile.** Show attributable results, units, dates, event and available footage; explain supported observations and gaps. Missing numeric measurements are not fabricated from a video upload. Distinguish unavailable evidence from a source error. Do not turn a submission's approval flag into a verified athletic measurement.
2. **Understand what happens next.** Present sourced guidance for the athlete's actual program/division and distinguish it from their individual status. The current [USA Football FAQ](https://usafootball.com/national-team/digital-combine) explains that results may be evaluated and lead to consideration for later opportunities; it does not establish an individual review, invitation or notification deadline. Display the source and checked date. Do not apply historical 2026 selection procedures to a 2027 combine.
3. **Use my profile.** Prepare a factual summary or introduction from selected evidence for the athlete's stated goal and intended use. Preview the exact text and any verified canonical profile link before copy. If no relevant opportunity or recipient is known, say so; this slice is evidence interpretation and action preparation, not yet opportunity discovery. The first slice does not send messages or invent coaches/programs. If public-profile visibility is unverified, provide the reviewed text without claiming a shareable public destination.

Example question: "What does this profile tell a coach, and help me introduce myself?" The answer should reference this athlete's evidence and produce usable text. Another generic congratulations or checklist fails the test. Process education alone is helpful but insufficient reason to adopt SPARQ; the profile must yield an action or output worth using.

## Success indicators and selection data

Start with observable facts: dated performance history, comparable improvement where protocols match, available film and athlete-visible feedback. Calibrated cohort comparisons require a defined and validated reference population. Selection likelihood needs actual outcome labels and validation; high drill percentiles alone cannot establish it.

The read-only source audit found performance history, feedback, review markers, private recruiting lists, profile views and flexible CRM fields. It did **not** establish an authoritative national-team selection ledger. Views, internal grades, reviewed markers, invitations and final selection are separate events. Private coach notes or lists do not become athlete-visible merely because a service account can read them.

The smallest useful organization input is its actual process/stage definitions and a dated mapping of historical athlete IDs to confirmed outcomes, identifying what athletes may see. First locate whether USA Football records these in GMTM custom fields or elsewhere. This could support outcome-linked examples and success analysis later; it is not required to build the initial evidence-based debrief. Charles's reported success figures remain user-reported until reconciled against records and denominators.

## Reuse and constraints from current source

| Foundation | Source | Required treatment |
| --- | --- | --- |
| Identity and ownership | `backend/combine_api.py:50`; `backend/profile_api.py:458` | Reuse strict linked-athlete checks. Preserve actor/athlete boundaries; no guardian delegation is implied. |
| GMTM facts | `backend/workspace_bootstrap.py:30` | Reuse field mapping, with fresh owner-scoped reads. Bootstrap snapshots are not a second canonical profile. |
| Results and footage | `backend/combine_results.py:180,195,311`; `frontend/app/athlete/[id]/components/CombineResultsCard.tsx`; `frontend/app/home/components/AthleteStartingPoint.tsx` | Reuse parsing/presentation selectively. Existing all-time comparisons lack cohort filters; same-org uses names; capture labels are inferred from the event's first metric row. Do not expose those labels as verified benchmarks. |
| Grounded context | `backend/athlete_context.py:7,20` | Keep the model confined to supplied, authorized athlete facts. No model-selected athlete ID or arbitrary SQL. |
| Draft presentation | `backend/artifacts_api.py:570,647` | Reuse the concept, not the legacy route unchanged; its college target lookup needs ownership correction. |
| Public sharing | `ShareCard.tsx`; `backend/reports_api.py`; `PublicReportClient.tsx` | Not ready: unused share card, missing visibility grants, deterministic unrevocable tokens and raw-HTML rendering risks. No broad legacy route remount. |

GMTM source pointers below refer to the local `/Users/joey/mercor-scan/repos/gmtm-api-v2` checkout at `f2fe121d`; population and current production parity were not verified in this audit:

- `schemas.md:770`: metrics/source/date/unit/verification fields and linked SPARQ history.
- `resources/feedback/feedback.resolver.js:110`: feedback authorship and visibility.
- `resources/submission/submission.resolver.js:3353`: reviewed records, not selection; writer/org attribution also needs validation.
- `resources/list/list.resolver.js:37` and `resources/athlete/athlete.resolver.js:452`: private lists and customizable CRM fields; actual usage unknown.
- `resources/analytics/analytics.resolver.js:2257`: attention signals, not progression decisions.
- `resources/utils/utils.resolver.js:4340`: metric-scale lookup is not a validated national-team cohort.
- `/athletes/:id/sparq/queries` can write history. Do not invoke it as a harmless profile read.

The focused candidate intentionally excludes legacy profile/results/sharing routes. Add a narrow authorized profile projection and corresponding page when implementing this slice, preserving explicit local origins, startup isolation and GMTM read-only access. Legacy seeded opportunities and arbitrary model-generated fit scores are not evidence for recommendations.

## Completion contract for the next build

- One authorized athlete's existing GMTM evidence powers the debrief without re-entry or a second task list. Clearly labeled fixtures can verify mechanics; a real profile is required to establish usefulness.
- Every numerical or status claim traces to an authorized source. Missing data, errors, unverified measurements and unknown individual review status have distinct treatment.
- For a real intended use, the athlete can select evidence, produce, edit and copy a useful summary/introduction in the actual interface. Verify the exact copied text. A blocked button, canned help or fabricated opportunity cannot pass acceptance.
- Identity isolation, output escaping and leakage checks cover the new data projection/draft. No private scouting records enter it by default.
- Joey reviews the complete output and interaction before external testing. Use an actual athlete's evidence and actual question, and compare the answer/action against simply opening their existing GMTM profile. A proposed first small round uses consenting adult athletes with established profiles, including completed combines, to judge what SPARQ adds and what they will use. This is not outreach authorization.
- Measure whether the evidence is accurate, whether the athlete learns something specific, whether they use the output or choose a relevant next action, and why they would return. A personalized-looking summary or successful Copy click alone does not establish value. Log draft creation/copy as such, not as a sent message, coach reply or selection. Longer-term replies, invitations and outcomes need independent receipts.

Broader opportunity discovery, controlled public sharing, comparable longitudinal improvement and organizer outcome reporting follow demonstrated value. The "Strava toward the Olympics" direction can grow from a trusted performance history connected to real opportunities; a social feed and extra tasks are not the first validation target.

## This planning pass

Complete when the correction, source feasibility, narrower first slice and testing criteria are recorded and the old checklist-first pointers are superseded. No application changes, live athlete/database/model calls, outgoing messages or deployment form part of this pass. Fable retains its existing infrastructure/security assignment. The current local demo is historical diagnostic evidence; no further founder testing of its blocked actions is needed.
