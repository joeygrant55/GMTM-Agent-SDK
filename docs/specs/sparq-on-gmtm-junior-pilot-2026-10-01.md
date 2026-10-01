# SPARQ on GMTM.com: junior recruiting pilot

Owner: Joey. Lead and executor: Fable (GMTM CTO lane). Written 2026-10-01. Status: DRAFT rev 2, after adversarial review R1. Awaiting Joey's decisions and approvals.

## Mission

A junior flag athlete (13–17) who has a GMTM account clicks **SPARQ** on GMTM.com. They arrive at `sparq.gmtm.com` **already signed in**, see their own combine footage and results, and get **recruiting help**: matched college programs, a plain reason why each fits, and an outreach draft they copy and send themselves. It looks and feels like part of GMTM. It is free. The first testers are the 2026 USA Football **junior** digital-combine athletes aged 13–17.

## Locked decisions (Joey, 2026-10-01)

- Testers: junior flag combine athletes, ages 13–17. **Under 13 is excluded** (COPPA). The adult cohort is not the target.
- Core job: recruiting help (colleges, fit reason, outreach draft).
- Address: `sparq.gmtm.com`, auto sign-in from the GMTM session.
- Free for the test. No payment code.
- Outreach: the athlete or parent **copies and sends** from their own email. SPARQ sends nothing to coaches. A later feature (not in this pilot) may let the athlete connect their own email so SPARQ drafts and sends with them.
- Every build gets an adversarial review by a fresh Fable 5.1 agent before commit.

## Starting point (verified 2026-10-01)

- **Live** `sparq-agent.vercel.app` = GitHub `main` `6c7e649` (Sept 3). Backend on Railway, health 200. Clerk **dev** instance.
- **Base** = Codex branch `codex/athlete-home-first-value` `36cbac6`, snapshot in worktree `/Users/joey/sparq-demo/v2` (branch `codex-snapshot-2026-10-01`). It contains `main` plus Codex's career home, owner checks, admission gate and about 1,000 backend tests. It is not pushed or deployed.
- GMTM.com sets cookie `sessionId` on `.gmtm.com` (SameSite=Lax, **not HttpOnly**, 90 days). The GMTM API validates it against Redis `sessions`.
- Junior cohort, read-only DB, 2026-10-01: events 1305/1314/1317 have 168 distinct submitters.
  - By age (`users.dob`): 11 under 13, 140 aged 13–17, 7 aged 18+, 10 with no DOB.
  - By gender code, ages 13–17 (`users.gender`: 1 = female, 2 = male and also the column default, 0 = unknown): 18 female, 67 male-or-default, 55 unknown.

## Design (rev 2, after adversarial review R1 on 2026-10-01)

Review R1 found 3 blockers and 7 high-severity issues. R1-n names each finding this design answers.

1. **Sign-in bridge, browser-bound (R1-1, R1-4, R1-7).**
   - SPARQ starts the flow. `GET sparq.gmtm.com/enter` sets `__Host-sparq-tx` (random state, HttpOnly, Lax, 5 min) and redirects to `gmtm.com/sparq/authorize?state=…`.
   - That GMTM.com server route reads `sessionId` and calls the new API route `POST /v2/sparq/handoff`.
   - The API route **reads Redis `sessions` directly**. It ignores `req.session` and `unverified_users`. It requires `user_id > 0` and `type >= 1`, and it is rate-limited to 5 per minute per user.
   - It returns a one-use 60-second code. Redis stores only `sha256(code)`, one use via `SET NX` and `GETDEL`.
   - The route has its own try/catch with fixed 401/429/500 bodies. It never rethrows into the global TrackJS handler and never logs the code. (The API's `x-source` gate is dead, `server/index.js:131`, so it protects nothing.)
   - `/enter/callback` requires the state cookie to match. It redeems the code server to server, then redirects (302) to a clean `/home` with `Referrer-Policy: no-referrer` and `Cache-Control: no-store`.
   - **Session = Clerk sign-in ticket.** The backend finds or creates a Clerk user with `externalId = gmtm:<user_id>` and mints a sign-in token. The frontend completes it. All existing `require_clerk_id` routes and ownership checks keep working, and no new auth dependency is needed.
   - To confirm at build time: a Clerk production instance on `sparq.gmtm.com` (needs Clerk DNS records), the dev-instance user cap, and creating users with no email.
2. **Session lifetime (R1-5).**
   - The SPARQ session lasts at most 24 h.
   - Every `/enter` replaces the current session, so user B signs out user A.
   - The header shows "Not you? Switch".
3. **Who gets in (R1-8, R1-11, R1-12).**
   - Admit only if the user submitted to junior events 1305/1314/1317 **and** dob gives 13–17 today, or the user is on Joey's allow-list. The check runs again on every personal request.
   - The redeem response gives only `user_id` and an eligibility flag, not the dob.
   - On refusal, store only `user_id` and the decision.
   - The parent checkbox is stored as `attested_by_session_kind: unknown`. GMTM cannot tell a parent operating a child's account from the child.
   - The GMTM.com SPARQ button renders **only** for eligible users, decided on the server.
4. **One app (R1-2).** Serve the career-home app (`profile_candidate_app.py`). Add an explicit, reviewed list of recruiting routes to its route list: colleges list, trigger-matching, college detail, outreach GET/POST. Keep its admission boundary. Do not mount `main.py` on `sparq.gmtm.com`.
5. **Colleges (R1-3, R1-9, R1-14).**
   - Matching input comes from GMTM, not MaxPreps: sport (`career.sport_id`), gender and `combine_metrics`.
   - No athlete name goes into any model prompt or web search. Drafts use the first name only.
   - No numeric fit score is shown. Each college shows the program, a source link, and why it fits, built only from the athlete's numbers and facts in the source.
   - A source URL must appear in the tool's search results.
   - Program lists (NCAA, NAIA and NJCAA women's flag football) are verified at build time from the governing bodies' pages, not hard-coded in copy.
   - **Approach (Joey, 2026-10-01): a curated, sourced list of real college women's flag football programs** stored as data with a source URL and a verified date. No live web search in the pilot. The model only explains fit from the athlete's own numbers and the stored program facts.
   - **Girls first (Joey, 2026-10-01).** Recruiting help shows only when GMTM gender = 1 (female). All others see the profile home (footage, results, goal) and an honest note that college flag football is mostly women's today. Gender 2 is also the column default, so the note invites the athlete to check their GMTM profile.
   - **Parent: notice + checkbox (Joey, 2026-10-01).**
6. **Outreach (R1-10).**
   - The SendGrid path is removed for this app: `/artifacts/{id}/approve` does not send, `send_outreach_email` returns "not configured", and `SENDGRID_API_KEY` is absent from the deployed environment.
   - The UI shows **Copy** and **Open in my email** only.
   - Drafts are age-aware: they never ask for calls or visits, and they say the athlete knows coaches may not reply yet.
7. **Protect the GMTM session on a gmtm.com subdomain (R1-6).** `.gmtm.com`'s `sessionId` is readable by script, so any script injection on sparq.gmtm.com could steal a GMTM session. Before `sparq.gmtm.com` goes live:
   - replace the 3 `dangerouslySetInnerHTML` sites with `react-markdown`, with no raw HTML;
   - add a CSP without `unsafe-inline`;
   - the SPARQ middleware ignores `sessionId`.
8. **No public exposure of minors (R1-9).** On this app, disable `/api/athlete/{id}`, the public `/athlete/[id]` page and share reports (`/report/[token]`).
9. **Look and feel.** Codex's dark SPARQ theme with "Back to GMTM". The SPARQ button sits on the athlete dashboard and the combine results page, for eligible users only.
10. **Deploy config (R1-15).** Add `https://sparq.gmtm.com` to `ALLOWED_ORIGINS` and Clerk authorized parties. Turn off `/sign-up` and `/onboarding` on this host.

## Completion contract (rev 2)

- [x] C1 Adversarial review R1 done (2026-10-01). It had 16 findings; Design rev 2 answers each one. A re-review of each built piece is required before its commit.
- [ ] C2 GMTM API handoff route + tests:
  - valid session → code;
  - unverified, missing or expired session → 401;
  - more than 5 per minute → 429;
  - reuse → rejected; 60-second expiry;
  - no throw reaches the global handler; the code never appears in logs.
- [ ] C3 SPARQ `/enter` + callback + Clerk ticket + eligibility, with tests:
  - state mismatch → rejected;
  - eligible 13–17 cohort member → in; under 13, no DOB, not in cohort, or 18+ → out;
  - user B replaces user A;
  - a parametrized test over the app's route table: 401 without a session, 403 when the URL `clerk_id` is not the caller.
- [ ] C4 Colleges + outreach, with tests:
  - no name in prompts;
  - SendGrid can never be called;
  - public athlete and report routes return 404;
  - no raw-HTML renderers left;
  - CSP header present.
- [ ] C5 GMTM.com button (eligible users only) + `/sparq/authorize` server route.
- [ ] C6 `sparq.gmtm.com`: DNS, Vercel domain, Clerk production, HTTPS valid.
- [ ] C7 End-to-end in production on Joey's account **and** on one real junior test account (Joey-created, DOB in range). Screenshots.
- [ ] C8 Invite list prepared: count only, ages 13–17, cohort members. Joey sends.

## Hard rails

- Joey approves: DNS, every production deploy (GMTM API, GMTM.com, SPARQ), pushing the SPARQ branch, the invite message and recipients, and Clerk production setup.
- No messages to athletes, parents or coaches from us. No payments. No production data writes beyond SPARQ's own tables, Clerk users for testers and the handoff-code store.
- Codex's checkout stays untouched. Work happens in `/Users/joey/sparq-demo/v2`.

## Open questions for Joey

Answered 2026-10-01: curated list; girls first; notice + checkbox.

Still open: who is on the test allow-list besides Joey?

## Order

Joey's answers → C2 and C3 in parallel (different repos) → C4 → C5 → C6 → C7 → C8.
