# Opportunity engagement measurement contract

Date: 2026-09-10. Status: implemented locally, default off; verification evidence belongs in the dated handoff. No live audience or traffic is claimed. Starting baseline: `d123943` on `codex/athlete-home-first-value`.

## Purpose and product boundary

Surface relevant opportunities, observe interest, then consider an exploratory organizer conversation. Affiliate terms and referral attribution are deferred. Ranking, reviewed URLs and navigation are unchanged; payment cannot affect relevance. This slice measures SPARQ interactions, not website arrivals, registrations, selection or revenue. It adds no athlete task, paid ranking, affiliate code, model call or automatic outreach.

## Browser capture

Both the profile build flag `NEXT_PUBLIC_OPPORTUNITY_ENGAGEMENT_ENABLED=true` and separately enabled backend are needed for accepted measurement. The public flag alone cannot enable server capture. With the build flag absent, the browser creates no tracker.

| Event | Implemented trigger | Excluded actions |
| --- | --- | --- |
| `card_visible` | At least 50% geometric intersection for one continuous second, with the current Opportunities result active, document visible and no open native dialog. | Mount, API response, hidden/offscreen/expired cards, loading/error states, occlusion by the details or draft-confirmation dialog. |
| `details_opened` | A deliberate details action successfully opens the selected card's drawer. | Automatic rendering or state restoration. |
| `outbound_activated` | Primary `open_source` anchor activation by normal/keyboard click or middle click while the action remains current. | Source citations, context-menu opening, Prepare introduction, copying, internal navigation or disabled/expired actions. |

Each mounted result attempts each kind at most once per card: three kinds across at most three cards, nine attempts total. It does not retry failures. Pending requests abort after four seconds and on tracker teardown; missing UUID/observer support drops measurement without blocking use. Document visibility, view changes, scope changes and native dialogs reset/pause observation. Repeated intentional actions within that mounted result are therefore not an exhaustive click count.

The observer establishes a browser-reported geometric condition, not verified attention. The server cannot independently prove visibility, a real human action or an external destination arrival. Navigation never waits for analytics success. Destination classification is `event_page`, `program_page` or `contact_page`; an inquiry link is not an event-registration click.

## Server activation and isolation

`POST /api/athlete/opportunities/engagement` exists only in the profile candidate. Default-off capture returns 404 before its authentication dependency or database access. Enabled capture requires the existing candidate authentication, then accepts exactly five string fields: `event_id` (canonical UUID4), `opportunity_id`, `kind`, `link_revision` and `reviewed_at`. Query parameters, extra fields, duplicate JSON keys and arbitrary URLs/actor IDs are rejected. Body size is at most 1,024 bytes with a five-second read timeout.

| Server variable | Exact role |
| --- | --- |
| `OPPORTUNITY_ENGAGEMENT_ENABLED` | Exact `true` enables; absent, empty or `false` disables. Other values fail configuration. |
| `OPPORTUNITY_ENGAGEMENT_COHORT` | `internal` (default), `fixture` or `pilot`; assigned by the operator, not inferred from hostname or athlete behavior. |
| `OPPORTUNITY_ENGAGEMENT_PERIOD` | Required named lowercase slug, at most 64 characters. Identify one planned measurement period consistently. |
| `OPPORTUNITY_ENGAGEMENT_SECRET` | Required dedicated 32-byte secret encoded as 64 lowercase hex characters. Server-only; never use a public variable or reuse an auth secret. |
| `OPPORTUNITY_ENGAGEMENT_EXCLUDED_IDS` | Comma-separated positive GMTM IDs, without spaces; at most 1,000 entries. Founder owner 2 is always added. |
| `OPPORTUNITY_ENGAGEMENT_PILOT_IDS` | Same format. Pilot mode requires at least one explicitly admitted ID outside exclusions. |

Use the same secret, period and cohort policy on every worker contributing to one report. Secret/period/cohort changes change account pseudonyms and can invalidate audience deduplication. The named period is a reporting label, not a timed collector shutdown. Define a fixed UTC reporting window separately.

Admit external adults explicitly before assigning pilot IDs; browsing adult results is not age verification. Owner 2 and excluded IDs are always classified internal. Unknown IDs in pilot mode also become internal. Keep staff/test/automation accounts excluded and local/staging/test configurations internal or fixture. These are operator-controlled classifications, not automatic environment detection.

For accepted requests, the collector validates the current reviewed record and source/event date windows, then makes only two Agent ownership SELECTs, forward and reverse, checking the current link revision and closing the connection before emission. No workspace/GMTM read or database write occurs. Process-local rate limits allow at most 60 admitted requests per account and 6,000 total per monotonic minute, with at most 2,048 account entries. They reset on restart and multiply across workers; they are not distributed fraud prevention.

The request's `reviewed_at` must exactly equal the first source's `checked_at`. The emitted catalog hash describes the **server-accepted snapshot**, not proof of the exact rendered copy: content changed without updating that first timestamp can still be accepted. Every source refresh must re-review facts and update the timestamp; never extend expiry without reviewing the source.

## Log schema and delivery limits

An accepted event emits one stdout line beginning exactly `SPARQ_OPPORTUNITY_ENGAGEMENT `, followed by JSON with only:

```text
schema, at, catalog_revision, opportunity_id, kind, event_id,
cohort, account, measurement_period, destination_kind
```

`account` is HMAC-SHA256 of the owner ID scoped to period/cohort under the dedicated secret. The payload contains no raw owner/Clerk ID, email, name, token, goal, media, draft or URL. Pseudonyms remain private account data; organizer reports contain only aggregates. This guarantee concerns this event payload, not unrelated hosting/access logs.

Success returns 204. Invalid events are rejected without emission; database/sink failures return a redacted error, and rate rejection is 429. Stdout is a best-effort sink, not a durable ledger: partial/lost exports or uncertain delivery remain possible. Production log retention, export coverage and access control are unverified. No new database/schema, analytics vendor or live settings were created or inspected for this slice.

## Offline report

Run from the checkout against an already-authorized, private local log export:

```sh
python3 backend/opportunity_engagement_report.py /absolute/private/engagement-export.log \
  --start 2026-09-10T00:00:00Z --end 2026-09-24T00:00:00Z \
  --measurement-period adult-flag-pilot-september-2026
```

These dates/period are illustrative, not an activated pilot. Multiple input files or a single `-` for stdin are accepted. `--cohort pilot` is the default; `internal` or `fixture` must be explicitly selected for QA. The CLI emits aggregate JSON, returns 2 for invalid input and 0 for `ok` or `no_data`; it performs no network/database/provider access.

Only lines starting with the exact prefix at column zero are parsed. Hosting wrappers must be converted into verified original message lines during a separately reviewed export; the reporter does not search inside arbitrary strings. Limits are 100,000 lines, 32 MiB total and 8,192 bytes per line. All prefixed records are strictly validated, including records later excluded by cohort/period/window. Invalid records or conflicting retries fail the whole report, with a fixed error code/line number and no partial audience results.

Retry identity is cohort + period + account pseudonym + occurrence UUID. Other fields must agree; the earliest server acceptance in the supplied export wins, independent of input order, including retries across window boundaries. Missing earlier records can change attribution. Capture itself may emit duplicates; browser retries are disabled.

Report selection uses exact period/cohort and UTC `[start, end)`. Within each opportunity/destination group, **V**, **D** and **O** are distinct accounts with card views, details and outbound activations. Rates are `|V ∩ D| / |V|`, `|V ∩ O| / |V|` and `|D ∩ O| / |D|`, returned with numerator/denominator and null for a zero denominator. These are same-window overlaps, not action order or causation. Missing views remain missing; direct outbound can bypass details.

Action totals deduplicate occurrence retries; unique account counts additionally deduplicate repeat visits across devices/sessions. Total audience is deduplicated across opportunities again. Do not sum per-event audience as unique people. Source refresh does not reset opportunity/cycle identity; another year's event needs a different ID. Multiple accounts are not assumed to be one person. Reports retain catalog hashes and exclusion/coverage counts but no pseudonyms. `capture_completeness=not_established` always remains explicit.

## Exploratory evidence threshold

Proposed judgment, not statistical proof: within one fixed 14-day interval, one current event receives views from **20 external pilot accounts** and official event-page activations from **5 of those accounts**. That can justify a learning conversation, not a distribution price, registration promise or claim of incremental demand. Lower counts still inform product decisions. USA Football's 500-athlete promotion target is not a measured audience or denominator.

Use actual counts: “During [dates], 20 signed-in external pilot accounts viewed your event in SPARQ; 5 activated its official event-page link. We have not measured website arrivals or registrations.” Include export/pilot limitations. Do not imply an organizer relationship or count contact-page clicks as event referrals. This feature sends no outreach.

## Founder and release boundary

The current real-owner acceptance wrapper still blocks this new route. Its launcher omits measurement variables and discards child stdout; it is not a pilot-capture/export mechanism. Read-only founder previews cannot establish external demand. The earlier three-save allowance remains exhausted.

No live activation, configuration read/change, schema change, vendor integration, deployment or outreach is implied by this local implementation. Before pilot activation, separately verify the exact paired build/server settings, admitted cohort, private export/retention process, fixed reporting window and source freshness. Verification counts and release decisions belong in the handoff, not this mechanics contract.
