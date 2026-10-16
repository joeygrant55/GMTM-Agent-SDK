# 2026-10-16 Campus photos and less text on the colleges pages

## Result
- 2026-10-15 colleges redesign deployed (Joey "Deploy"): Railway sparq-junior a785a4f9 SUCCESS, Vercel sparq-junior-iim51m36v Ready on sparq.gmtm.com (53d345c). Live test in GMTM chrome: My list built (11 picks), Explore 186 programs, Warner school page Scorecard box.
- Live bug found and fixed: the Saved tile counted saved+emailed schools. 50b0ac8 (pushed, NOT deployed).
- Joey picked option A: Wikimedia Commons campus photos with a credit line, no logos. Built, NOT deployed:
  - 117 of 187 schools have a photo (frontend/public/college-photos/<id>.webp, 720 px, max 104 KB, 8 MB total).
    Source: Wikidata P18 by UNITID (P1771), 7 Wikipedia lead photos, 16 hand-picked from Commons categories.
    Every photo was looked at by a person (contact sheets); 18 dropped (logos, signs, postcards, a group photo, weak, wrong campus).
  - backend/scripts/build_college_photos.py rebuilds them; it stops if the set changes (run with --accept after a look).
  - Photos on picked cards, the map card, the school page; small photo or initials badge on board and map rows; credit line with author, license and Commons link.
  - "Why it fits" clamps to 3 lines with Read more (measured overflow).
  - Saved/emailed board rows show "N on the <season> roster · Camp: <date>" from the existing college-research data.
  - Served from the site itself; the profile asset rule allows only ids in frontend/lib/college-photo-ids.json. CSP unchanged.

## Evidence
- tsc, check-profile-safety (2 new checks), check-sparq-session, check-gmtm-entry, check-candidate-policy (new photo path checks) pass.
- check-production-build (profile) passes: listed photo 200 image/webp, unlisted 404. Its redirect checks were stale since 27642bc (signed-out goes to /enter first) and are updated.
- Backend 1971 passed. next build passes.
- Local test page (real components, real fixtures) in GMTM chrome, desktop and 390 px frames.
- Fable reviews: first found 8 issues, all fixed; second review of the fixes in this commit.

## Open
- Joey: OK to deploy (Vercel only; backend unchanged). Includes 50b0ac8.
- 70 schools have no free photo (Warner, Keiser among them). Options: ask schools, or more Commons search.
- Research (roster, camps) exists only for saved schools that the research job checked.
