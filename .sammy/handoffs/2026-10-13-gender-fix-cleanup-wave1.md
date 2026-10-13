# 2026-10-13 Gender fix, cleanup, MaxMind live, first invite wave drafted

- MaxMind removed from the GMTM API: PR 78 merged as 78bf46c2, deployed staging -> API 1B -> API 2B (gated
  scripts, no npm ci), 30-min watch clean (0 target 5xx, latency ~18 ms unchanged; 2 pre-existing NaN/undefined
  query errors in checkForExistingUser / getScoutingReport, unrelated). Alex: revoke the MaxMind key + auto-recharge.
- GENDER BUG FIXED (3c14a84, deployed sparq-junior 2d335c82): GMTM 0 = female, 1 = male, 2 = prefer not.
  SPARQ had FEMALE = 1. Now everyone not male sees the women's college list; allowlisted testers keep it.
- Weekly job: one bad AI reply no longer stops a run (036ae67); catch-up run done 187/187, $1.26.
- Cleanup: focused-essence stopped (railway down; service + vars kept: delete later to erase its stored keys);
  sparq-agent.vercel.app now 307-redirects every path to https://sparq.gmtm.com/ (Vercel project 'frontend').
- First wave (read-only gmtmread, IDs only in scratchpad/wave1.json, 0600): junior flag 13-17 with a Highlight Reel:
  49 female, 53 prefer-not-to-say. Plan: wave 1 = 20 most recent of the 49, via Joey's GMTM in-platform messaging.
  Invite text drafted (in chat 2026-10-13). Joey sends; nothing sent by Claude.
- Open: Joey to confirm invite wording; Joey deletes the Clerk account; delete focused-essence after a quiet week;
  recruiting-literate read of the contact-rules panel.
