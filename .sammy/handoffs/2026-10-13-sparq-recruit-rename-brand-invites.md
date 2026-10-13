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
