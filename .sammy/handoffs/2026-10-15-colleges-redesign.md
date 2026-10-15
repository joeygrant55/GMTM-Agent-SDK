# 2026-10-15 Colleges page redesign (Joey: "build"; options 1 + 2, map option A + desktop)

## Result (commit 6d81bf6, not deployed)
- Design canvas Joey approved: https://claude.ai/artifact/WYZhwYSA2pL1fac23nsRo9
- My list: tiles (picked / saved / emailed), one next step (follow-up after 14 days first, then closest saved school with a domain-checked coach email), Picked / Saved / Emailed (3 columns on lg, stacked on phone with Emailed first). Backend "tracked" returns saved or emailed schools outside her 12.
- Explore: frontend/app/home/components/CollegeMap.tsx. Bundled US outline only (no tiles, no outside host). Drag, pinch, ctrl-wheel, double-click, +/-, state circles under 900 px map width, 300-mile ring, tap a dot for a card. The list follows the map ("Show only what is on the map").
- School page: "The school at a glance" (fact + College Scorecard cost after aid, undergrads, admission, graduation; source link).
- Data: backend/data/college_scorecard_2026.json (Scorecard Oct 15, 2026 release; 183 of 187 matched; builder backend/scripts/build_college_scorecard.py). "fact" per program (187, <= 70 chars, from each row's notes only). Siena Heights "closed": true (closed after 2025-26; final commencement May 9, 2026), never shown, ranked or saved.

## Checks
- Backend 1971 passed; tsc OK; check-profile-safety, check-sparq-session, check-gmtm-entry, check-candidate-policy OK; next build (profile) OK.
- Browser (Joey's joey@gmtm.com Chrome, local test page with real-data fixtures from card()/_listing): desktop and 390 px. Tap circle zooms, tap dot opens card, drag pans and list follows, save from Explore appears in Saved, detail shows Scorecard box.
- Fable 5.1 review: 2 "blocking" items. Email ready vs kit domain check: fixed + test. "Everyone who applies": measured all 37 null admission rates are OPENADMP=1; now stored as open_admission and shown only then. Also fixed: region view clusters, 409 copy in Explore, whole_system flag, Scorecard type checks, sr-only list action, aria-live removed, refit on resize, 44 px dot targets, tile count.

## After deploy
- The program data hash changed (facts + closed): every built list reads "not built" once; she taps Find my colleges again; saves and sent marks stay. No invites are out yet.

## Not done / open
- Deploy: needs Joey's OK (Railway sparq-junior + Vercel sparq-junior).
- Not tested: real touch pinch on a phone; the live site.
- nextStep and map math have no unit tests (frontend has no unit test runner for React files).
- Next (Joey 2026-10-15): less wall of text, school imagery and website info. Existing saved-school research (roster, camps, cost) could move onto cards; images must be copied to cdn.gmtm.com (CSP) and need Joey's call on school photos/logos.
