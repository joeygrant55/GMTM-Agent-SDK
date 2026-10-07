# 2026-10-06 Roadmap: daily site checks live, event leads list, film import ruled out

## Daily site checks (idea 6, signed-out part): live
- 7b7d984. Railway service `sparq-site-check` (768acb27-f5a0-44b0-9d2e-e6b9bb567c93), same image as the weekly job
  (Dockerfile.research-job, entry run_job.py, SPARQ_JOB=site_check), AGENT_DB_* references only, no model key.
- Cron `0 12 * * *` (daily 12:00 UTC), restart NEVER, next run 2026-10-07. First run on Railway: 11/11 ok, 11 rows
  in sparq_site_checks. Joey chose "Fable checks daily": read sparq_site_checks at the start of each session
  (e.g. SELECT check_name, ok, detail FROM sparq_site_checks WHERE checked_at > NOW() - INTERVAL 2 DAY AND ok = 0).
- Weekly research service redeployed with the new entry (SPARQ_JOB unset = research); schedule unchanged
  (Mondays 10:00 UTC, next 2026-10-12); no extra run started (run table unchanged).
- Signed-in flow checks need a dedicated GMTM test account from Joey (Claude cannot create accounts).

## Event leads (idea 7, girls' flag): list, not a crawler
- docs/research/girls-flag-event-leads-2026-10-06.md (574faf2): ~40 upcoming girls' events but few organizers
  (NFL FLAG/RCX, iFLAG + 3 sanctioned organizers, USA Football = existing customer, state HS associations, NAIA/NJCAA).
  A weekly agent is not justified; the list is worked by hand. NFL terms forbid commercial harvesting.

## Film import (idea 4): ruled out as designed
- Hudl Terms §3.2.8 (no bots), §2.3 (no account sharing); YouTube ToS (no automated access/downloads); Google
  blocks automated sign-in. Pasting a link stays allowed (GMTM already takes YouTube links). A Hudl partner
  agreement would be the legal route (Joey's business call). Hudl help pages (own-highlight download/share) unread.

## 2026-10-07 update
- Scheduled run 20261007T120500 ran on time: 11/11 ok.
- f76aeaf adds 5 refusal checks (SPARQ handoff 401, redeem 403, authorize-without-state 400, SPARQ home -> gmtm.com,
  SPARQ proxy 401); 15/15 pass live. Deployed to sparq-site-check (and the weekly job, same image); schedules
  unchanged (daily 12:00 UTC, next 2026-10-08; weekly Mon 10:00 UTC, next 2026-10-12). First 15-check scheduled run:
  2026-10-08 — confirm 15 rows.
- No test account: Claude cannot create accounts; GMTM sign-in is an emailed code (no password), so a real signed-in
  check would need inbox access. Joey told this on 2026-10-07; recommended skipping it.
- Correction: Joey says athletes can already paste Hudl links and GMTM shows them natively (I had said YouTube only).
  Open question (unmeasured): SPARQ "My card" plays only GMTM-hosted files inline; Hudl clips likely show the
  "Watch on GMTM" link.
