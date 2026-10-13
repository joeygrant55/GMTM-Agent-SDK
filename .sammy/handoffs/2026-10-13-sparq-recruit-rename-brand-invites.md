# 2026-10-13 SPARQ Recruit: rename, brand, wave 1 invites

## Result
- Product renamed SPARQ Recruit (5b0d49c, 69008f0). gmtm.com button + authorize page text: PR 402 (626bb53f), live.
- Codex brand pack integrated (206bbc3), deployed to Vercel prod. All 5 brand assets return 200 on sparq.gmtm.com; POST returns 404.
- Wave 1 invites: 19 Gmail drafts in joey@gmtm.com, subject "Your invite to SPARQ Recruit, from GMTM".
  Checked with list_drafts: 19 drafts, sender joey@gmtm.com, recipients match scratchpad wave1_contacts.json 19/19 (0 missing, 0 extra).
  1 athlete skipped (no valid email). One recipient is a .gov address (likely a parent's work email).
- Claude sent nothing. Joey reviews and sends.

## Open items
- Joey: review and send the 19 drafts.
- Fable: after send, track sign-ins from wave 1 in the SPARQ data; then plan wave 2 (29 more female athletes + 53 prefer-not-to-say, all with a reel).
- Alex: revoke the MaxMind key, turn off auto-recharge.
- Fable: delete Railway `focused-essence` after a quiet week; OG share image with a public landing page; 2 old API input-check bugs; monthly coach check; read sparq_site_checks each session.
- Recruiting-literate read of the contact-rules panel.

## Privacy
Contact lists stay in the session scratchpad (0600). No emails in the repo or in chat.

## Update: copy v2 and link fix (same day)
- Joey asked for: no USA Football selection tie, and a beta feedback ask. New copy: "You took part in the USA Football junior flag combine on GMTM", plus "SPARQ Recruit is a GMTM tool. It is not part of USA Football. Using it, or not using it, has no effect on any USA Football team or selection." plus a beta paragraph.
- Found: the Gmail MCP create/update_draft strips <img> and rewrites every link (even plain-text domains) to google.com/url?q=...&ust=<write time + 24 h>. After 24 h those show a Google "Redirect Notice" page. The first 19 drafts had this.
- Fix: rewrote all 19 bodies inside the Gmail web compose (Chrome, paste event). Verified with list_drafts FULL: 19/19 have real https://gmtm.com and https://sparq.gmtm.com links, 1 header image from sparq.gmtm.com, the USA Football line, the beta line, the right name; 0 missing, 0 extra.
- Rule: never use the Gmail MCP for drafts with links that people will click; compose in the Gmail UI or check RAW for google.com/url.

## Update: testers before send
- Connor could not get in: staff accounts (type 9) are not juniors and were not on the allow-list; the gmtm.com button shows only to type 1 athletes.
- Joey set Railway sparq-junior SPARQ_TEST_ALLOWLIST=2,1,3 (Joey 2, Alex 1, Connor 3). Redeploy SUCCESS; is_eligible(1/2/3) = True with live settings.
- Testers enter at sparq.gmtm.com directly. Joey holds the 19 invites until their feedback is in.

## Update: Alex's tester feedback (same day)
Alex: "finding colleges took awhile, some sort of loading indicator"; asked for a Norman/Nielsen usability audit and a security audit.
- Cause measured: one model call wrote all 12 fit reasons, 21.6 s and 22.1 s (2 live runs).
- Fix (Joey: "show them as they come in"): 12 parallel calls, NDJSON stream (list first, then each reason). Measured live: all 12 by 3.1 s / 3.8 s, first at ~2.4 s. Short loading panel, per-card "Writing why it fits you…". Plain JSON stays for clients without Accept: application/x-ndjson.
- Reasons: 13-year-old wording, no em/en dash, drills on every third program only. REASON_SYSTEM is in inputs_key, so every built list reads "not built" once after deploy (saves and sent marks stay).
- A failed model call is not cached (next build retries); unsafe text stays final. Save failure sends {"type":"error"}. Leaving the page aborts the build.
- Usability fixes: "Open in my email" needs a valid To; 409 detail map; source links show the host; "NJCAA (2-year)"; "Show map"; Home copy after the first email; current step shows its count.
- Security fixes: X-Content-Type-Options nosniff + Referrer-Policy on all pages; npm update nanoid/source-map-js/postcss (audit 4 -> 2; the rest needs Next 16).
- Security finding corrected: GMTM RDS link already uses TLS (Ssl_cipher TLS_AES_256_GCM_SHA384 with pymysql 1.2.0, the prod pin). Not verified: server certificate. Tested fix: ssl_ca=AWS global bundle + verify identity connects; needs the PEM in 3 images.
- Checks: backend 1958 passed; tsc OK; check-profile-safety OK; next build (profile surface) OK. Two Fable 5.1 adversarial reviews: no blocking issues; findings fixed.
- Not verified: streaming through Vercel + Railway in a browser (check Network tab after deploy).

## Open items (added)
- Joey: OK to deploy (Railway sparq-junior + Vercel sparq-junior). Then: real browser check of the stream, Connor/Alex retest.
- Fable: RDS cert verification; Next 16 upgrade; forget_athlete script (parent delete request); remove tester ids from SPARQ_TEST_ALLOWLIST after wave 1.
- GMTM: HttpOnly on the sessionId cookie (gmtm.com repos not reviewed).
- Not done from the usability audit: cold visit to sparq.gmtm.com bounces to gmtm.com with no message; map label overlap with the You pin; "I sent it" placement on phone; coach-email steps when only a staff page exists.

## Update: deployed 4e030d1 (Joey: "Deploy!", "I explicitly approve")
- Railway sparq-junior deployment 8aeb84e1 SUCCESS; /health configuration_ready true.
- Vercel sparq-junior production sparq-junior-koxipzpnz Ready; sparq.gmtm.com sends nosniff + strict-origin-when-cross-origin.
- Live browser check (Joey's account, 500 px window): 12 cards at 2.31 s with "Writing why it fits you…", reasons at 4.73-5.33 s, one by one (stream not buffered). Was 22 s+.
- GitHub push of feat/junior-pilot was blocked by the auto-mode classifier; origin is behind 4e030d1. Joey can push.
- Seen live: GET /home/colleges showed "Loading your colleges…" for 3-6 s before the page. Not measured further.

## Update: "See all colleges" (option A; Joey: "a and b both, start with A")
- Joey asked if the 12 use intelligence. Answer: no. rank() is a fixed rule (home state, neighbors, region; levels take turns). AI only writes the reason text. Data: 187 programs, 35 states; no size, cost or academics.
- A: GET /api/workspace/colleges/{id}/all (all 187, closest first, her 12 keep reasons, no model call). Saves and "I sent it" now work for any sourced program (still need a built list). UI: My 12 / See all toggle, search, 24 per page, map shows the same page.
- Review (Fable 5.1): 1 blocking (2 route manifests in tests), 4 UX items; all fixed. Backend 1959 passed; tsc, safety check, next build OK.
- B next: 3-tap preferences (distance, 2-year/4-year, level) + "more like this" from hearts, using only facts we have.
- Deployed fe224c3 (Joey: "yes deploy"): Railway 1404a00e SUCCESS; Vercel sparq-junior-qd4laarb8 Ready. Live check: toggle, See all 187, search "TX", map with one page. Map labels still overlap pins (usability item 9, open).

## Update: option B + map labels (Joey: "then let's do B"; "that's unacceptable" on the map overlap; "just do it!")
- B: 3 taps before Find my colleges (how far: near 300 mi / my part of the country / anywhere; 4-year / 2-year / either; NCAA / NAIA only for 4-year). Server filters before rank(); fewer than 12 shows fewer; 0 matches is shown but never saved. Cache check now uses the saved ids. "More like the ones you saved": 4 same-level programs closest to her saves. Prefs per athlete in localStorage; logged as values only. Builds 10/hour.
- Map: labels z-10 above dots, You z-20, "+N more" z-30; label gap 22% x 11%. Not done: measure real label widths in the browser (review estimate: 2 long labels can still touch at 390 px).
- Permissions (Joey asked): added allow rules for `git push origin feat/junior-pilot` (and the git -C form). The Vercel rule existed; run `vercel deploy --cwd <dir>` without a `cd` prefix so it matches.
- Reviews: 2 Fable 5.1 passes, no blocking issues; fixes applied. Backend 1963 passed; tsc, safety check, next build OK.
- Deployed 99fce92: Railway ba4807d0 SUCCESS; Vercel sparq-junior-50cv04g0m Ready (vercel deploy --cwd ran without a block). Live check on Joey's account: map labels clear; answers "Near me · 4-year · NAIA" -> 8 NAIA programs with reasons; "More like the ones you saved" -> 4 NJCAA near Daytona. Joey's test list is now built from those answers.
- Open: /home/colleges first load took about 9 s ("Loading your colleges…"); not measured. Likely GMTM reads in list_colleges (_identity + _athlete).

## Update: Colleges page load (Joey: "keep going, deploy when done")
- Measured before: GET colleges made about 8 DB connections one after the other. From a laptop via the Railway proxy: 7.3 s (3 runs). Live in the browser: 2.0-2.1 s. Page shown at 3.1 s (warm reload) to 5.0 s (first visit).
- Also measured: after the parent-notice gate, the colleges fetch started 0.73 s after its chunk loaded (lazy `dynamic(ssr:false)` page; React 18 Suspense reveal delay is part of it).
- Fix 1 (dceb257): `_reads()` runs identity, athlete, marks and profile at the same time for colleges, /all and saved-colleges. The identity row is written only when it changes, or on a first visit (save_list is an UPDATE; review found that a first visit with no GMTM gender and no sport would never save her list). ponytail: up to 4 agent-DB connections per request.
- Fix 2 (559508b): the junior pages import their component statically. Combine/legacy builds carry about 31 kB gz more on /home and /home/colleges (accepted).
- Reviews: 2 Fable 5.1 passes. Fixes applied: the first-visit row bug, a profile-read warning log, the college-research test mock, an unused import.
- Checks: backend 1965 passed (new tests fail without the fix); tsc, check-profile-safety (35), next build OK.
- Deployed: Railway 0a663ee2 SUCCESS; Vercel sparq-junior-hhqelmhik Ready.
- Measured after, live (Joey's account): colleges request 1.05 s (5 runs, was 2.0 s). Warm reload: the list shows at 2.2 s (was 3.1 s); gap from notice to fetch 8 ms (was 730 ms). Home, Emails, My card, Colleges, college detail all render.
- Not measured: a female athlete's request (Joey is male + tester, so his GET also reads GMTM identity; hers skips it and should be faster). The tab was in the background during the measurements.
- Next: Home waits for /athlete/evidence (1.0 s) before card, materials and saved-colleges (1.0 s each); Home shows at about 2.8 s.
