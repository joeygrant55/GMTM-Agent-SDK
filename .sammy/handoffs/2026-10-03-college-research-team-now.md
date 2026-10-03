# 2026-10-03 College research: Team now + flag camps (live)

Spec: docs/specs/college-research-agent-2026-10-02.md (v3.1 + "As built"). Roadmap: docs/specs/computer-use-roadmap-2026-10-02.md.

## Shipped
- c69a32b, bf51f57: research module (plain fetch, code-counted rosters, flag camps, validators). c76859c: tables,
  weekly job (backend/scripts/college_research_job.py), GET /api/workspace/college-research/{clerk_id}, cards on a
  saved college's page. Each build: Fable review + fix-checks until "Safe to commit (and deploy)".
- DDL applied 2026-10-03 (create_sparq_college_research, create_sparq_research_runs). Railway 134decfc SUCCESS, Vercel prod.
- First --apply run 20261003T121158-025c8f61: done, 187 programs, $1.2114. DB readback: 187 rows, 61 rosters
  (58 code, 3 model), 149 camps-checked, 6 with a camp (Dallas College clinic Oct 17, 6 campuses).
- Live (GMTM Chrome 5b2e86c6): Daytona State card "The 2025-26 roster lists 20 players: 8 freshmen, 12 sophomores.",
  source link https + noopener, checked Oct 3, 2026; unsaved Warner shows no cards and makes no research request;
  0 console errors, 54 requests all 200/304.

## Total spend: about $3.54 (probes/runs $2.33 + first apply $1.21). Anthropic key from Railway; never printed.

## Open
- Phase 3: weekly schedule needs its own job service (profile image lacks requests/bs4 and backend/scripts). Until
  then the data is from Oct 3; cards show "May be out of date" after 14 days.
- Not built: Home step "See camps at your colleges" (1 real camp today).
- Roadmap next (Joey liked): film import (computer use, needs parent-notice update + site terms), coach contact
  refresh, daily GMTM walkthrough tests, club/federation event leads.
