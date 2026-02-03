"""
GMTM Agent SDK Backend
======================

FastAPI backend for orchestrating autonomous marketing agents.
Handles triggers (cron, webhooks) and spawns E2B sandboxes.

Deployment: Vercel, Railway, or Render
"""

import os
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import sandbox runner
from sandbox_runner import run_agent_in_sandbox, AgentResult

# Import simplified Search API (bypasses Agent SDK)
from search_api import router as search_router

# Import Agent API
from agent_api import router as agent_router

# Import Profile API
from profile_api import router as profile_router

app = FastAPI(
    title="SPARQ Agent Backend",
    description="AI-powered athlete search and recruiting intelligence.",
    version="1.0.0"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(search_router)
app.include_router(agent_router)
app.include_router(profile_router)

# ============================================
# DATA MODELS
# ============================================

class AgentTrigger(BaseModel):
    """Request model for triggering an agent"""
    agent_name: str
    params: Optional[dict] = {}

class AgentResponse(BaseModel):
    """Response model for agent execution"""
    status: str
    agent_name: str
    started_at: str
    output: Optional[str] = None
    error: Optional[str] = None

# ============================================
# HEALTH & STATUS ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "GMTM Agent SDK Backend",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "checks": {
            "e2b_configured": bool(os.environ.get("E2B_API_KEY")),
            "anthropic_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "notion_configured": bool(os.environ.get("NOTION_TOKEN")),
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================
# AGENT TRIGGER ENDPOINTS
# ============================================

@app.post("/agents/content-pipeline", response_model=AgentResponse)
async def trigger_content_pipeline(background_tasks: BackgroundTasks):
    """
    Trigger the Content Pipeline Agent

    Monitors Notion Content Calendar and generates scheduled content.
    Runs every 4 hours via cron or on-demand.
    """
    result = await run_agent_in_sandbox(
        agent_module="content_pipeline",
        agent_function="run_content_pipeline"
    )

    return AgentResponse(
        status=result.status,
        agent_name="content-pipeline",
        started_at=datetime.utcnow().isoformat(),
        output=result.output,
        error=result.error
    )

@app.post("/agents/event-factory", response_model=AgentResponse)
async def trigger_event_factory(event_id: Optional[str] = None):
    """
    Trigger the Event Content Factory Agent

    Processes SPARQ events into multi-platform content.
    Can target specific event or process all recent events.
    """
    params = {"event_id": event_id} if event_id else {}

    result = await run_agent_in_sandbox(
        agent_module="event_factory",
        agent_function="run_event_factory",
        params=params
    )

    return AgentResponse(
        status=result.status,
        agent_name="event-factory",
        started_at=datetime.utcnow().isoformat(),
        output=result.output,
        error=result.error
    )

@app.post("/agents/lead-qualification", response_model=AgentResponse)
async def trigger_lead_qualification():
    """
    Trigger the Lead Qualification Agent

    Researches and scores B2B prospects.
    Runs daily or on-demand.
    """
    result = await run_agent_in_sandbox(
        agent_module="lead_qualification",
        agent_function="run_lead_qualification"
    )

    return AgentResponse(
        status=result.status,
        agent_name="lead-qualification",
        started_at=datetime.utcnow().isoformat(),
        output=result.output,
        error=result.error
    )

@app.post("/agents/performance-dashboard", response_model=AgentResponse)
async def trigger_performance_dashboard():
    """
    Trigger the Performance Dashboard Agent

    Aggregates metrics from all platforms to Notion.
    Runs hourly or on-demand.
    """
    result = await run_agent_in_sandbox(
        agent_module="performance_dashboard",
        agent_function="run_performance_dashboard"
    )

    return AgentResponse(
        status=result.status,
        agent_name="performance-dashboard",
        started_at=datetime.utcnow().isoformat(),
        output=result.output,
        error=result.error
    )

@app.post("/agents/orchestration-hub", response_model=AgentResponse)
async def trigger_orchestration_hub(goal: str):
    """
    Trigger the Orchestration Hub Agent

    Coordinates multiple agents for complex campaigns.
    Example: "Prepare all content for Volleyball Canada event"
    """
    result = await run_agent_in_sandbox(
        agent_module="orchestration_hub",
        agent_function="run_orchestration_hub",
        params={"goal": goal}
    )

    return AgentResponse(
        status=result.status,
        agent_name="orchestration-hub",
        started_at=datetime.utcnow().isoformat(),
        output=result.output,
        error=result.error
    )

# ============================================
# WEBHOOK ENDPOINTS
# ============================================

@app.post("/webhooks/notion")
async def notion_webhook(payload: dict, background_tasks: BackgroundTasks):
    """
    Handle Notion webhook events

    Triggers agents based on Notion database changes:
    - Content Calendar updates → Content Pipeline
    - UniCalendar event completion → Event Factory
    """
    # TODO: Implement Notion webhook verification and routing
    return {"status": "received", "payload": payload}

@app.post("/webhooks/slack")
async def slack_webhook(payload: dict, background_tasks: BackgroundTasks):
    """
    Handle Slack slash commands and events

    Allows triggering agents from Slack:
    - /gmtm-content - Trigger content pipeline
    - /gmtm-leads - Trigger lead qualification
    """
    # TODO: Implement Slack webhook handling
    return {"status": "received", "payload": payload}

# ============================================
# CRON ENDPOINTS (for Vercel/Railway cron)
# ============================================

@app.get("/cron/content-pipeline")
async def cron_content_pipeline():
    """
    Cron endpoint for Content Pipeline (every 4 hours)

    Configure in vercel.json:
    {
      "crons": [{
        "path": "/cron/content-pipeline",
        "schedule": "0 */4 * * *"
      }]
    }
    """
    result = await run_agent_in_sandbox(
        agent_module="content_pipeline",
        agent_function="run_content_pipeline"
    )
    return {"status": result.status, "output": result.output[:500] if result.output else None}

@app.get("/cron/lead-qualification")
async def cron_lead_qualification():
    """
    Cron endpoint for Lead Qualification (daily at 9am)

    Configure in vercel.json:
    {
      "crons": [{
        "path": "/cron/lead-qualification",
        "schedule": "0 9 * * *"
      }]
    }
    """
    result = await run_agent_in_sandbox(
        agent_module="lead_qualification",
        agent_function="run_lead_qualification"
    )
    return {"status": result.status, "output": result.output[:500] if result.output else None}

@app.get("/cron/performance-dashboard")
async def cron_performance_dashboard():
    """
    Cron endpoint for Performance Dashboard (hourly)

    Configure in vercel.json:
    {
      "crons": [{
        "path": "/cron/performance-dashboard",
        "schedule": "0 * * * *"
      }]
    }
    """
    result = await run_agent_in_sandbox(
        agent_module="performance_dashboard",
        agent_function="run_performance_dashboard"
    )
    return {"status": result.status, "output": result.output[:500] if result.output else None}

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# ============================================
# LOCAL DEVELOPMENT
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
