# Spec: Coach contact refresh

Status: v2.1 after Fable review (6 blockers, 7 majors, 8 minors) and fix-check (3 majors, 2 minors); all addressed. Joey 2026-10-05: "let's do both";
Fable picked coach contact refresh (roadmap idea 5). Owner: Fable. Repo joeygrant55/GMTM-Agent-SDK, branch
feat/junior-pilot.

## Mission

Keep the head coach name and email that SPARQ pre-fills in a junior athlete's email kit correct. A check reads each
program's public coach page and lists real changes. A person reviews every change before an athlete sees it.

## Design: a local check, no table, no cron step (the reviewer's lazier option)

- `backend/scripts/coach_check.py`: run on the MacBook by Fable. Reads the 187 programs' coach pages with the
  college_research fetch rules (allowlisted hosts, robots.txt, 1 req/s, 2 MB, redirects within the allowlist), parses
  by code, compares with the data file and prints JSON lines. No database, no model call, no deploy. About 4 minutes,
  $0. A model fallback, a table and a weekly cron step are added only if the code path proves too weak (measured).
- `backend/scripts/apply_coach_change.py <program_id> --name --email --checked YYYY-MM-DD [--research PATH]`: patches
  `head_coach_name`, `coach_email` and `contacts_verified_on` in `backend/data/college_womens_flag_2026.json`, and
  `verified_on` plus the same contact fields in the research file. The research file is outside the repo
  (`/Users/joey/sparq-demo/research/college-coach-contacts-2026.json`, 189 rows keyed by `school`); `--research`
  defaults to it like `build_college_data.py`, and the program id (slug of the school name) maps back to `school`.
  The agreement test skips with a clear reason when the research file is not present. `build_college_data.py` (needs hand-downloaded Census files that are not on disk) stays for geography.
- Why review, not automatic updates: the coach email goes into a minor's outreach. A wrong address sends her note
  to the wrong adult. Every change goes through Fable review against the source page, the normal commit review, and
  Joey sees the list of changed coaches before the deploy.

## Page choice (code only)

1. `staff_page_url` when present (159 programs; 24 are whole-department `/staff-directory` pages).
2. Else the program page's own `/sports/<slug>/coaches` link.
3. 28 programs have no coach page and 12 have a page that lists no coach: `not_found` is expected there.

## Head coach rules (measured on the 147 stored titles)

- Title matches `(?i)\bhead\b.*\bcoach\b` (146 of 147) and not `\b(assistant|asst|associate)\b`.
- Sport scoping: on a department directory, only rows whose title or section heading matches `(?i)\bflag\b`, and
  never a section headed men's without women's. On a `/sports/<slug>/coaches` page the page itself is the sport.
- Co-heads: every head-coach row in page order, names joined with "; " (data convention: Post, UW-Stout, Florida
  Memorial). Email from the first row. Interim counts only when no other head coach is listed.
- Emails: `mailto:` links, Cloudflare `data-cfemail` (decoded), and "name [at] school [dot] edu" text. Every email
  goes through the existing rule as `coach_email({**program, "coach_email": found})`. An address that fails it
  (personal or shared domain) is never printed, stored or reported.
- Names and titles are untrusted page text: capped (80 / 120 chars), letters, spaces and `.'-,/&()` only.

## What counts as a change

- Names compare after casefold, accent strip, suffix removal (`II`, `Jr.`), class-year removal (`'95`) and whitespace
  collapse. Last names are split on hyphens and spaces into token sets. `spelling` only when the last-name token sets
  overlap AND the first-name token matches; anything else is `different_person` (so "John Smith" -> "Jane Smith" is
  reviewed, and "Clark-Robinson" vs "Clark Robinson" is spelling). Co-heads compare as a set of normalised names; a
  change of order is `match`. Emails compare casefolded. Titles are not compared (wording churn); only the role (head / co-head /
  interim).
- Both the stored and the found email pass through `coach_email()`; a stored address that fails it (e.g. Southern
  Union's shared alabama.edu) counts as no stored email. An address that appears in the program's `contact_notes`
  (e.g. Nebraska's Director of Operations) is bucket `noted`, never a change.
- Output buckets: `different_person` (normalised last name differs), `email_changed`, `email_added`,
  `spelling` (same last name, different form), `email_not_on_page` (data has one, page shows none: never a change),
  `noted`, `match`, `not_found`, `unreadable` (fetch, robots, off-allowlist or redirect errors).
- Only `different_person`, `email_changed` and `email_added` need review before a data update.

## Phases

0. Probe: Daytona State (Presto coaches page), Keiser (SIDEARM coaches page), Nebraska (SIDEARM department directory,
   ops email on the coach row), Post University (co-heads). Then all 187. Gate: the data file was hand-verified on
   2026-10-02, so code-parsed rows should match it; a match rate below 90 percent of code-parsed rows means an
   extractor bug: stop and fix before trusting any change.
1. Code with tests: title rule, directory scoping, co-heads, interim, the three email forms, the email rule (personal
   address never output), name normalisation and buckets, unreadable vs not_found, apply script + file-agreement test.
2. First full check; review each change against its page; first reviewed data update (one real program end to end,
   with its checked date changed); Joey sees the change list before deploy.

## Completion contract

- [ ] 0: the 4 named programs compared with their real pages; 187 counts per bucket; match rate measured.
- [ ] Tests for every rule above; no personal address in any output (test).
- [ ] Apply script proven on one real program; data and research files agree (test).
- [ ] No coach change reaches athletes without review, a committed data update and Joey seeing the list.
- [ ] Fable "safe" on each phase; handoff written.

## Hard rails

- Approved: this spec and phase 0 ($0, local, read-only fetches of public pages).
- Never: emails to coaches, athletes or parents; automatic data changes; personal or shared-domain addresses.

## Stop conditions

- 2 failed rounds on the same problem; surprise scope; match rate below 90 percent on code-parsed rows.
