# SPARQ Agent — Status (Snapshot 2026-04-17)

## What's running in prod

- **Frontend:** https://sparq-agent.vercel.app (editorial landing + /demo + /onboarding + /home workspace)
- **Backend:** https://focused-essence-production-9809.up.railway.app
- **Model:** Claude Sonnet 4.6 (`claude-sonnet-4-6`) via Anthropic SDK. Tools: native `web_search_20250305` + custom read-only `query_database`.
- **Auth:** Clerk

## What's working

- Landing page with scripted hero demo, bento features, animated proof bar
- `/demo` — streaming Claude agent with tool-call feed, 3-question free gate
- `/onboarding/search` — real MaxPreps SSR scraping (dedup, parallel stat fetch, school colors)
- `/onboarding/confirm` — real MaxPreps stats, sport-aware
- `/onboarding/welcome` — percentile + season stats + college count reveal
- `/home/*` — dashboard, colleges with Reach/Target/Likely tiering + fit reasons, outreach log, draft coach email, profile editor, timeline
- Workspace AI panel with session forking ("What If" scenarios)
- `/athlete/[id]` — public athlete dashboard with expandable college cards, terminal thinking feed, share cards
- `/report/[token]` — shareable public reports with OG meta
- `/quick-scan` — public athlete Quick Scan with waitlist capture
- Enrichment worker — background Claude call generates `fit_score` + `fit_reasons` on profile creation

## What's known-broken / unbuilt

- **College matching is AI-hallucinated** — Claude picks 20 colleges per athlete from a vibe, not validated against real rosters or recruiting needs. See `backend/profile_api.py:232-269`. Biggest remaining product-integrity risk.
- **Stripe / paywall** — not wired. Premium tier is aspirational.
- **Email sending** — draft page produces text; user manually copies. No send flow.
- **16 of 17 agents from `AGENT_CAPABILITIES.md`** — not built (vision doc).
- **Video pipeline** — `video/` has Remotion installed but is not called by anything.

## Recently removed (2026-04-17 cleanup)

- 5 Python agents importing `claude_agent_sdk` (removed from `requirements.txt`, crashed on Railway)
- 4 unused helper modules
- `backend/sandbox_runner.py`, `backend/scout_router.py`, `tools/recruiting_tools.py`
- All `POST /agents/*`, `/webhooks/*`, `/cron/*` handlers in `backend/main.py` — they called the deleted sandbox runner
- Public `/test` page (info disclosure)
- Stale `localhost:8000` and `sparq-agent-backend.up.railway.app` URL fallbacks

## Historical status docs

Pre-April snapshots are intentionally stale (model choices changed, features shipped). Do not trust them for current state:
- `PRODUCT_STRATEGY.md` — correct on vision/pricing, off by a model generation
- `AGENT_CAPABILITIES.md` — vision doc, not a status doc
- `PHASE1_IMPLEMENTATION.md` — February roadmap, not tracked
