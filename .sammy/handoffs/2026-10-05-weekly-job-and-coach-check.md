# 2026-10-05 Weekly research job (Railway cron) + coach contact check

## Weekly job: live
- Railway service `sparq-research-job` (id 60885e5d-19a2-41ca-9928-81eba26ec873, project 27aa6c0a…, env production),
  image Dockerfile.research-job (d8f1d43): 5 backend files + data file + requests/bs4/tzdata; AGENT_DB_* as
  references to the MySQL service, ANTHROPIC_API_KEY referenced from sparq-junior; no GMTM DB settings.
- Cron `0 10 * * 1` (Mondays 10:00 UTC), restartPolicyType NEVER (set via Railway GraphQL; read back;
  nextCronRunAt 2026-10-12T10:00Z). The job always exits 0 so no restart can re-spend; outcome in sparq_research_runs.
- First run 20261005T184715-86487e68: done, 187 programs, $1.1922. Rosters stored: 68 programs (was 61 on Oct 3).

## Coach contact check: built, measured, no changes found
- Spec docs/specs/coach-contact-refresh-2026-10-05.md (v2.1). Code 010cec6 + 424b649: backend/coach_check.py,
  backend/scripts/coach_check.py (local, $0, no model, no DB), backend/scripts/apply_coach_change.py (one reviewed
  change; school-domain emails only; patches the data file and /Users/joey/sparq-demo/research/college-coach-contacts-2026.json).
- Final full run: 129 of 141 readable pages with a stored coach match (91.5%, gate 90%); 0 rows in
  different_person / email_changed / email_added / spelling. 12 misses are not_found (safe; no data change).
- Run it: `python backend/scripts/coach_check.py --review` (prints only rows needing review).
- Not automated: run the coach check by hand (e.g. monthly). Every change: review against the source page,
  apply_coach_change.py, Fable review, commit, Joey sees the list, deploy.

## Spend today: Railway job $1.19. Coach checks $0.
