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
