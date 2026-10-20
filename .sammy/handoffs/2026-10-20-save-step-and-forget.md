# 2026-10-20 Save step fix (deployed) and parent delete script

## Save step (a540b8c, deployed: Vercel sparq-junior-5sojrr2ko Ready on sparq.gmtm.com; Railway unchanged)
- Why: wave 1 day 3, 2 of 5 built a list, 0 saved. At 390x844 the first card was at y=945 behind empty Emailed/Saved boxes.
- Labeled Save button on cards; next step "See my colleges" (a scroll button, not a #hash link: a native hash entry
  breaks Back in the App Router, found by the Fable review); phones put empty boxes below the picks (first card y=679);
  320 px long names wrap. Live check: 14 of 14 cards show Save, 0 console errors.
## forget_athlete.py (committed, not deployed: runs from this machine)
- Dry run by default; --delete in one transaction; 22 SPARQ tables; stops on a shared subject; refuses any target that
  is not the *.proxy.rlwy.net / railway database. 9 tests pass. Live dry run on Joey (id 2): 45 rows in 16 tables.
- Run: cd /Users/joey/sparq-demo/deploy-8e3178b && npx -y @railway/cli@latest run --service c6becf80-b58f-4fa0-99c6-45f87f405756 -- /Users/joey/GMTM-Agent-SDK/backend/.venv/bin/python /Users/joey/sparq-demo/v2/backend/scripts/forget_athlete.py <gmtm id> [--delete]
- Not covered: browser storage, Railway logs, SendGrid, Anthropic/OpenAI prompts, GMTM media (GMTM request).
## Also today
- gmtm.com PR #405 merged by Joey (0b48069): / and /coaches server-render (crawler words 10 -> 851 / 1172).
## Next
- Wave 1 reports on scratchpad/wave1_all19.json: 10-21, 10-23, 10-27. Watch "Saved a college".
- Still open: "I sent it" button on phones; coach email step for staff-page-only schools; pre-wave-2 security list.
