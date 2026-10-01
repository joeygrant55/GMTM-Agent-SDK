# SPARQ Agent

Athlete workspace connecting GMTM combine evidence with recruiting assistance. The current build is working toward combine completion, continued progress and athlete-controlled sharing; see [current state](docs/state/current-state.md) and the [build plan](docs/state/sparq-build-plan-2026-09-06.md) for implemented scope and remaining gates.

**Live:** https://sparq-agent.vercel.app
**Backend:** https://focused-essence-production-9809.up.railway.app

## Stack

- **Frontend:** Next.js 14 (app router) on Vercel — `frontend/`
- **Backend:** FastAPI + Uvicorn on Railway — `backend/`
- **Auth:** GMTM sign-in only. `/enter` sends the athlete to GMTM; the backend exchanges the one-use code for a 24 h SPARQ session token (HttpOnly cookie bound to the GMTM session). No other sign-in exists. Settings: `.env.example` AUTH section.
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

Choose isolated Agent/GMTM database and GMTM sign-in (`SPARQ_*`) settings before exercising requests; importing the app does not validate connectivity or prepare schema. Existing legacy request handlers can write Agent data, run matching or send outreach. `/health` reports process/configuration state, not database readiness. A separate focused entry point is `candidate_app:app`; its contract and required settings are documented in the [candidate runbook](docs/state/combine-candidate-runbook-2026-09-08.md). Neither command authorizes production requests.

Schema preparation is a separate explicit operator step. See [Agent schema preparation](docs/state/agent-schema-preparation-2026-09-07.md) for dry-run/apply commands, the required existing conversation baseline and failure behavior. Nothing applies DDL during import or FastAPI startup.

### Frontend

```bash
cd frontend
npm install
# .env.local:
#   NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
#   NEXT_PUBLIC_GMTM_WEB_URL=https://gmtm.com
#   SPARQ_ENTRY_SECRET=...   SPARQ_SESSION_SECRET=...   (server-only, same as backend)
npm run dev
# → http://localhost:3001
```

An explicit `NEXT_PUBLIC_BACKEND_URL` origin is required; missing or invalid configuration fails startup/build. For the focused combine candidate also set `NEXT_PUBLIC_APP_SURFACE=combine`. The private profile workspace uses `NEXT_PUBLIC_APP_SURFACE=profile` with `profile_candidate_app:app`; see its [runbook and acceptance limits](docs/state/profile-workspace-runbook-2026-09-08.md). The default `legacy` surface retains the broader app. The effective Next 14 configuration is `frontend/next.config.js`; the ignored duplicate TypeScript config has been removed.

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
