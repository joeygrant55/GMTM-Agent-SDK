# 2026-10-16 Home page: start its reads together

## Result
- Measured live on sparq.gmtm.com/home (Joey's account, 3 loads, warm HTML 42 ms):
  session 160 ms -> parent-notice ~330 ms -> evidence ~1.0 s -> materials / saved-colleges / card lead ~1.1 s each.
  All Home data arrived at about 2.9 s. The last 3 reads waited about 1 s for evidence.
- d1d4946 (pushed, NOT deployed): prefetchAPI (frontend/app/_lib/api.ts) starts materials, saved-colleges and
  (Home view) card lead in ProfileSession.refresh, after the parent-notice gate. The first plain GET of the same URL
  within 10 s takes the response once. Expected: all data at about 1.9 s. Not measured live yet.
- Parent-notice gate stays first on purpose (no personal read before it).

## Evidence
- tsc, check-profile-safety (new check; a mutant of its new assert fails), check-sparq-session, check-gmtm-entry,
  check-candidate-policy pass. next build passes.
- Fable review: 1 medium issue (a synchronous throw left Home on "Loading" forever) fixed with try/catch; test gaps fixed.
  Accepted low risks: up to 10 s cross-tab staleness while evidence is slow; extra denied reads when evidence answers 401/403/409;
  a ~1 s window where a second-tab sign-in as another user could show the first user's saved list beside the new evidence.

## Open
- Joey: OK to deploy d1d4946 (Vercel only). Then measure live again.
- Each backend read is ~0.3-1 s alone: every query opens a new MySQL connection (combine_api._get_agent_db/_get_gmtm_db).
  Connection reuse is a separate, wider change.
