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

## Home speed: deployed (Joey "go ahead and deploy")
- c2cd2df on Vercel sparq-junior-mabc155os: Ready on sparq.gmtm.com. Railway unchanged.
- Live (Joey's account): all 4 reads now start together. All data at 2.6 s and 1.8 s on 2 warm loads (before 2.8 s, 2.9 s).
  Each read is slower when they run together, so the gain is smaller than the 1.9 s estimate. Small sample.

## Wave 1 step report
- backend/scripts/wave1_report.py: read-only (READ ONLY transaction, SELECT only, ROLLBACK). Counts per step and A1..An rows,
  no names, emails or ids. Days are US Eastern and include step times, not only sign-ins (a 24 h session writes one entry).
- Run (ids file stays in the scratchpad, never in the repo): see the script docstring. `--demo` is the self-check.
- Proof: Joey's account shows every step, Saved 2 / Drafts 3 / Sent 1, which matches his live page (Warner saved, Daytona emailed).
  The 19 invitees: all "Not signed in" on 2026-10-16 (invites not sent).
- Fable review: safe to commit; fixed: day count (step times + Eastern days), "Furthest step" label, refusal label, shared-subject
  warning, error output without host/user, empty or bad ids file.
- Suggested first 5 invites (Joey sends): A1, A3, A5, A7, A8 (most recent on GMTM, ages 13 to 17).
