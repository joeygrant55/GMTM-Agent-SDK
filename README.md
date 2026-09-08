# SPARQ Agent

Athlete workspace connecting GMTM combine evidence with recruiting assistance. The current build is working toward combine completion, continued progress and athlete-controlled sharing; see [current state](docs/state/current-state.md) and the [build plan](docs/state/sparq-build-plan-2026-09-06.md) for implemented scope and remaining gates.

**Live:** https://sparq-agent.vercel.app
**Backend:** https://focused-essence-production-9809.up.railway.app

## Stack

- **Frontend:** Next.js 14 (app router) on Vercel — `frontend/`
- **Backend:** FastAPI + Uvicorn on Railway — `backend/`
- **Auth:** Clerk (`@clerk/nextjs`)
- **LLM:** Claude Sonnet 4.6 via Anthropic SDK with `web_search_20250305` + a no-argument `get_current_athlete` tool bound to the authenticated request's profile. Model-selected SQL and athlete IDs are not accepted.
- **Databases:**
  - Railway MySQL — `sparq_profiles`, `college_targets`, `agent_conversations`, `agent_messages`, `outreach_log` (read/write)
  - GMTM MySQL — 75K athlete profiles, 131K metrics, 7,832 scholarship offers (read-only)

## Run locally

### Backend

```bash
cd backend
pip install -r requirements.txt
# Inject configuration explicitly from an isolated environment, or select
# an isolated env file yourself. No application module auto-loads .env.
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --env-file /absolute/path/to/isolated-backend.env
# → http://localhost:8000  (docs at /docs)
```

Choose isolated Agent/GMTM database and Clerk settings before exercising requests; importing the app does not validate connectivity or prepare schema. Existing legacy request handlers can write Agent data, run matching or send outreach. `/health` reports process/configuration state, not database readiness. The supported combine candidate is still being isolated; this command is not authorization to run it with production credentials.

Schema preparation is a separate explicit operator step. See [Agent schema preparation](docs/state/agent-schema-preparation-2026-09-07.md) for dry-run/apply commands, the required existing conversation baseline and failure behavior. Nothing applies DDL during import or FastAPI startup.

### Frontend

```bash
cd frontend
npm install
# .env.local:
#   NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
#   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
npm run dev
# → http://localhost:3001
```

If you omit `NEXT_PUBLIC_BACKEND_URL`, the frontend falls back to the live Railway backend.

## Product docs

- [`docs/state/current-state.md`](./docs/state/current-state.md) — current implementation, verification and next action
- [`docs/state/sparq-build-plan-2026-09-06.md`](./docs/state/sparq-build-plan-2026-09-06.md) — active milestone plan and acceptance gates
- [`PRODUCT_STRATEGY.md`](./PRODUCT_STRATEGY.md) — pricing, moat, revenue projections
- [`SPARQ_10X_SPEC.md`](./SPARQ_10X_SPEC.md) — live demo + welcome reveal + instant fit preview specs
- [`SPARQ_E2E_FIXES.md`](./SPARQ_E2E_FIXES.md) — historical bug-fix log
- [`AGENT_CAPABILITIES.md`](./AGENT_CAPABILITIES.md) — vision doc (17 agents imagined; 1 shipped — this is aspirational)
- [`VIDEO_PIPELINE_RESEARCH.md`](./VIDEO_PIPELINE_RESEARCH.md) — Remotion evaluation (not wired up)

## Deploy

```bash
# Frontend
cd frontend && npx vercel --prod --yes

# Backend — auto-deploys on push to main via Railway GitHub integration
```
