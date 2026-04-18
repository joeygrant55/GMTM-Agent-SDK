# SPARQ Agent

AI-powered recruiting advisor for student-athletes. $29/mo alternative to $5,000/year consultants.

**Live:** https://sparq-agent.vercel.app
**Backend:** https://focused-essence-production-9809.up.railway.app

## Stack

- **Frontend:** Next.js 14 (app router) on Vercel — `frontend/`
- **Backend:** FastAPI + Uvicorn on Railway — `backend/`
- **Auth:** Clerk (`@clerk/nextjs`)
- **LLM:** Claude Sonnet 4.6 via Anthropic SDK with `web_search_20250305` + custom `query_database` tool
- **Databases:**
  - Railway MySQL — `sparq_profiles`, `college_targets`, `agent_conversations`, `agent_messages`, `outreach_log` (read/write)
  - GMTM MySQL — 75K athlete profiles, 131K metrics, 7,832 scholarship offers (read-only)

## Run locally

### Backend

```bash
cd backend
pip install -r requirements.txt
# Populate .env with:
#   ANTHROPIC_API_KEY, AGENT_DB_{HOST,PORT,USER,PASSWORD,NAME}, DB_{HOST,USER,PASSWORD}
python -m uvicorn main:app --port 8000 --reload
# → http://localhost:8000  (docs at /docs)
```

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
