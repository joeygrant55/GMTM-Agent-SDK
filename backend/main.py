"""
SPARQ Agent Backend
===================

FastAPI backend serving the SPARQ Agent recruiting advisor:
- Claude Sonnet 4.6 streaming agent (agent_api)
- Athlete profile + college matching + outreach (profile_api)
- Shareable reports (reports_api)
- Optional legacy athlete search (search_api)

Deployment: Railway (https://focused-essence-production-9809.up.railway.app)
"""

import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Core routers — must work
from agent_api import router as agent_router
from profile_api import router as profile_router
from reports_api import router as reports_router
from artifacts_api import router as artifacts_router

# Optional router (best-effort)
search_router = None
try:
    from search_api import router as search_router
except Exception as e:
    print(f"⚠️ search_api unavailable: {e}")

app = FastAPI(
    title="SPARQ Agent Backend",
    description="AI-powered athlete search and recruiting intelligence.",
    version="1.0.0",
)

# CORS — restrict to known frontends. Set ALLOWED_ORIGINS (comma-separated) in the
# environment; falls back to the production Vercel app + localhost for dev.
_default_origins = "https://sparq-agent.vercel.app,http://localhost:3000,http://localhost:3001"
_allowed_origins = [
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile_router)
app.include_router(agent_router)
app.include_router(reports_router)
app.include_router(artifacts_router)
if search_router:
    app.include_router(search_router)


@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "SPARQ Agent Backend",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
async def health():
    from auth import auth_status
    return {
        "status": "healthy",
        "checks": {
            "anthropic_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "agent_db_configured": bool(os.environ.get("AGENT_DB_HOST")),
            "gmtm_db_configured": bool(os.environ.get("DB_HOST")),
            "auth": auth_status(),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Log the real error server-side; return a generic message so we don't leak
    # stack details, DB errors, or internal paths to clients.
    import traceback
    print(f"❌ Unhandled error on {request.method} {request.url.path}: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": "Internal server error.",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
