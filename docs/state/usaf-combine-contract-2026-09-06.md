# USA Football Combine 2 — verified public event contract

Observed September 6, 2026. Joey supplied the [official USA Football page](https://usafootball.com/national-team/digital-combine). Its links resolve to [junior event 1317](https://gmtm.com/virtuals/1317/2027-u-s-flag-national-team-junior-digital-combine-2) and [adult event 1318](https://gmtm.com/virtuals/1318/2027-u-s-flag-national-team-adult-digital-combine-2). These IDs are now independently confirmed current public destinations; earlier references were only SDK fixtures.

## Program policy and GMTM configuration are separate sources

USA Football publishes an August 10–September 21, 2026 window. Division is based on age on December 31, 2027: junior at most 17, adult at least 18. All seven exercises and a valid Athlete ID are required. Combine entry is free; the listed ID prices are $35 youth and $39.50 adult. Its parent/guardian account-purchase note concerns USA Football, not proof of GMTM delegation. [Source](https://usafootball.com/national-team/digital-combine)

Root made unauthenticated GET requests to both public GMTM event landing pages and extracted only event/task definitions from their HTML data. Session and athlete-submission data were excluded. Both served the Next build identifier `b0293a2cc918da59afb53cc75c0cfdd71769c4a3`, matching the local web checkout's HEAD. This narrows the previous freshness gap, but is not proof that every served asset or private workflow matches that checkout.

Both definitions identify USA Football organization **249002**, have nine ordered visible activities, are published/public/non-invite-only, and have no GMTM product ID. Their configured start is `2026-08-11T03:59:59.000Z`; their end is **`2026-09-22T23:59:00.000Z`**. The close date differs from USA Football's published September 21 deadline. Joey subsequently identified this as a known GMTM issue and said it must not block implementation. The Agent will show the published September 21 date with its source, retain the raw configured timestamp, and omit a precise countdown. The suspected UTC/Eastern cause has not been verified.

## Task map

These are activity IDs and required fields inside each form. A field's `required` flag does not establish whether the whole activity is mandatory for the program.

| Order | Activity | Junior task | Adult task | Required form evidence |
| --- | --- | --- | --- | --- |
| 0 | Athlete background | 4896 | 4911 | 11 required fields junior; 10 adult; membership ID, contact/profile information and sport background included |
| 1 | Highlight reel | 4900 | 4915 | One video of the athlete playing, alongside structured exercises |
| 2 | Overhead squat | 4906 | 4920 | Video only |
| 3 | Push-ups | 4901 | 4916 | Video plus repetition count |
| 4 | Sit-ups | 4902 | 4917 | Video plus repetition count |
| 5 | Broad jump | 4904 | 4918 | Video plus distance in inches |
| 6 | 5-10-5 shuttle | 4893 | 4908 | Video plus separate right-start and left-start times |
| 7 | 20-yard dash | 4892 | 4907 | Video plus time; adult question/metric labels conflict |
| 8 | 60-yard shuttle | 4894 | 4909 | Video plus time |

Task IDs and form definitions are from the two GMTM public configurations linked above. The background form has 16 fields in each event. Junior requires the most recent team; adult leaves that field optional. The optional highlight field inside background is distinct from the standalone highlight activity. Never collapse them solely because their titles are similar.

## Discrepancies that affect implementation

1. **Deadline:** published September 21 versus configured September 22. Joey confirms a known platform issue, suspects UTC/Eastern configuration, and directs that it not block this build. Use the sourced date-only display described above; no timezone repair is claimed.
2. **Highlight activity:** Joey clarifies that athletes submit footage of themselves playing in addition to the structured submissions. Keep this standalone activity distinct from the optional highlight field inside background. Report per-activity progress; do not announce seven-of-seven or nine-of-nine as whole-program eligibility or completion.
3. **Adult dash labels:** task 4907 is a 20-yard dash with 20-yard instructions, but its metric question says `40 Yard Dash Time` and references a `20 Yard Shuttle` metric template, ID 2623828. Junior task 4892 references a 20-yard dash template, ID 2700905. Joey confirms this is a known platform bug he can fix and that it should not block the Agent build. Preserve exact event/task/question identity, record the mismatch and avoid generating 40-yard instructions or silently editing stored data.
4. **Adult ID price:** the adult background instructions still mention $35, while USA Football's current page lists $39.50 for an adult ID. Use the official purchase destination and resolve the stale copy; the Agent must not introduce a separate combine fee.

The two shuttle direction questions share a metric template ID. A metric ID alone cannot prove both answers are present. Some other template metadata is stale or irrelevant to the question's declared type; use the type and canonical question identity, not arbitrary nested metric properties. Template values/approval flags are configuration, not athlete results or verification evidence.

## Changes to the SPARQ integration contract

- **Public requirements are available before registration/results.** These events have no GMTM product ID. Do not require a paid-product or invitation row merely to display/select public event instructions. Authenticated personal progress must still be scoped to the uniquely linked athlete; public access grants no permission to another athlete's answers.
- **Separate eligibility and progress.** Track public event context, account/link state, any registration evidence, Athlete ID validity, required-form evidence, review and outcome independently. Entering a membership number is not verification that it is valid.
- **Requirements are not numeric results.** The squat is video-only, the shuttle needs two direction values, and background contains nonnumeric fields. Existing numeric results cannot supply the completion denominator or validate these forms.
- **Preserve source conflicts.** The UI can show each activity and confirmed submission state with a sourced date-only deadline. Unknown eligibility or review status cannot become a successful milestone automatically.
- **Use actual dated definitions in fixtures.** Retain event/task/question IDs, required flags, type, units and the known adult label mismatch. Strip metric-template row metadata from normalized fixtures; keep source definitions separate. Synthetic zero-submission cases must not be described as observed athletes.

## Evidence and next steps

Public source projections are saved at the task's `work/sparq-usaf-events-2026-09-06/event-1317-public-config.json` and `event-1318-public-config.json`. A normalized fixture is at `backend/tests/fixtures/usaf_2027_combine2_public.json`. No real athlete/session data or production writes were used.

The [current implementation contract](current-combine-build-contract-2026-09-06.md) now builds the owner-scoped current-event context and per-activity checklist against these actual configurations, with Joey's clarifications above. Current form validation and saved payload keys have been traced in source; external Athlete ID verification and the junior account actor still require live acceptance. The known source bugs and target inventory do not block local implementation.

This is live public configuration evidence, not an authenticated submission test, valid-membership verification, deployed SPARQ change or authorization to edit the source events.
