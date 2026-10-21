# Goal v1: SPARQ Recruit pre-wave-2 sprint (2026-10-21)

## Mission
Before Joey invites wave 2 (82 more minors), the email step works on a phone and for staff-page-only schools, the
wave report shows where athletes stop between pages, the 3 remaining pre-wave-2 security and setup items are done, and the 82
invite drafts wait in Joey's Gmail for him to send. Two small gmtm.com / saintlings.app SEO fixes ship with them.

## Completion contract
1. Email step on a phone (390x844): the "I sent it" control is visible without a long scroll after the athlete opens
   the email kit. Evidence: measured position in the harness at 390x844, before and after.
2. Staff-page-only schools: when a program has no coach email, the email step tells the athlete what to do (open the
   staff page, find the coach, paste the address) and the page link works. Evidence: harness render + unit/check test.
3. Two new steps are recorded: "opened a school page" and "opened the email kit". Stored data = subject, step name,
   date. No other personal data. Evidence: backend test + a live row after deploy.
4. wave1_report.py shows both new steps. Evidence: `--demo` passes and the live report prints them.
5. GMTM RDS connections verify the server certificate (AWS global bundle, verify identity) in the deployed image.
   Evidence: test + live `Ssl_cipher` / connect with the bundle, sparq-junior health OK after deploy.
6. REMOVED (Joey 2026-10-21): no change to the GMTM `sessionId` cookie. It controls sign-in on all of gmtm.com.
7. Tester ids are out of `SPARQ_TEST_ALLOWLIST` (Railway sparq-junior and gmtm.com Vercel, where set). Evidence: env
   listing shows the value without the ids (no ids printed).
8. NOT NEEDED (2026-10-21): no legacy or combine app is on Vercel. 'frontend' only redirects to sparq.gmtm.com.
9. 82 wave 2 Gmail drafts exist, one per athlete, none sent. Evidence: draft count; ids file in the scratchpad (0600).
10. gmtm.com/coaches has 1 h1. Evidence: crawler fetch counts h1 tags.
11. saintlings.app/robots.txt returns 200 with a sitemap line. Evidence: curl.
12. A Fable 5.1 adversarial review (read only) ran before every commit and every deploy; holding findings fixed.
13. Handoff `.sammy/handoffs/2026-10-21-pre-wave2.md` written; current-state updated.

## Locked decisions
- Athletes sign in with GMTM only. Claude never sends messages; Joey sends all invites.
- No hash links for in-page scroll (App Router Back bug); use a scroll button.
- Minors' data stays private: no names, emails or ids in output or commits.
- Step logging stores no page content, no school text, no IP or user agent.

## Hard rails
- Joey's "go" on 2026-10-21 approves the work in this spec: code, tests, local builds, commits on the task branches,
  Gmail drafts (drafts are not sends).
- Still need Joey's yes per item: every deploy (Railway sparq-junior, Vercel sparq-junior, gmtm.com merge to master,
  saintlings.app), every env change (items 7, 8), any production data change, any DNS change, any send.
- `gh pr merge` to a production branch: Joey runs it with `!`.

## Budget & stop conditions
- Same problem fails 2 rounds: stop and report. Surprise scope (for example, client code needs the sessionId cookie):
  stop that item, name the blocker, finish the others.

## Workstreams (executor: Fable, MacBook; review: Fable 5.1 subagent, read only)
- A. SPARQ frontend + backend (items 1-5): checkout /Users/joey/sparq-demo/v2, branch feat/junior-pilot.
- B. Removed by Joey (item 6).
- C. Env items (7, 8): prepare exact commands; run after Joey's yes.
- D. Wave 2 drafts (item 9): read-only GMTM query for the 82, drafts via Gmail. Depends on nothing.
- E. gmtm.com h1 (item 10): ~/mercor-scan/repos/gmtm.com, new branch, PR. saintlings.app robots (item 11): site repo.
- Codex spec review: not requested; Joey set Fable 5.1 adversarial review as the gate for this sprint.
