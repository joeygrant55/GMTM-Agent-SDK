# GMTM Agent SDK

Autonomous marketing engine powered by Claude Agent SDK + E2B sandboxes.

## Overview

This system provides 5 autonomous agents that run in secure cloud sandboxes:

| Agent | Purpose | Schedule |
|-------|---------|----------|
| **Content Pipeline** | Monitors Notion calendar, auto-generates content | Every 4 hours |
| **Event Factory** | SPARQ events → parallel content generation | On event completion |
| **Lead Qualification** | B2B prospect research with scoring | Daily at 9am |
| **Performance Dashboard** | Real-time metrics aggregation | Hourly |
| **Orchestration Hub** | Campaign coordination | On-demand |

## Architecture

```
Triggers (cron/webhook) → FastAPI Backend → E2B Sandbox → Agent SDK Runtime
                                                 ↓
                              Your .claude/ config + MCP servers
                                                 ↓
                              Notion API + GMTM MySQL + SendGrid + Social APIs
```

## Quick Start

### 1. Install Dependencies

```bash
cd 06-TOOLS/Agent-SDK/backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example to .env
cp .env.example .env

# Fill in your API keys:
# - E2B_API_KEY (from e2b.dev)
# - ANTHROPIC_API_KEY (from console.anthropic.com)
# - NOTION_TOKEN (from Notion integrations)
# - etc.
```

### 3. Run Locally

```bash
# Start the FastAPI server
cd backend
python main.py

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### 4. Test an Agent

```bash
# Trigger Content Pipeline
curl -X POST http://localhost:8000/agents/content-pipeline

# Trigger Lead Qualification
curl -X POST http://localhost:8000/agents/lead-qualification
```

## Deployment

### Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

Add cron jobs in `vercel.json`:
```json
{
  "crons": [
    {
      "path": "/cron/content-pipeline",
      "schedule": "0 */4 * * *"
    },
    {
      "path": "/cron/lead-qualification",
      "schedule": "0 9 * * *"
    }
  ]
}
```

### Railway

```bash
# Deploy via GitHub or CLI
railway up
```

Configure cron triggers in Railway dashboard.

## File Structure

```
06-TOOLS/Agent-SDK/
├── backend/
│   ├── main.py              # FastAPI endpoints
│   ├── sandbox_runner.py    # E2B sandbox management
│   └── requirements.txt
├── agents/
│   ├── __init__.py
│   ├── content_pipeline.py  # Content Calendar automation
│   ├── event_factory.py     # SPARQ event content (TODO)
│   ├── lead_qualification.py # B2B prospecting (TODO)
│   ├── performance_dashboard.py # Metrics (TODO)
│   └── orchestration_hub.py # Campaign coordination (TODO)
├── config/
│   ├── agent_definitions.py # Subagent configs
│   └── mcp_servers.py       # MCP configurations
├── .env.example
└── README.md
```

## API Endpoints

### Agent Triggers

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agents/content-pipeline` | POST | Generate scheduled content |
| `/agents/event-factory` | POST | Process SPARQ events |
| `/agents/lead-qualification` | POST | Research B2B prospects |
| `/agents/performance-dashboard` | POST | Aggregate metrics |
| `/agents/orchestration-hub` | POST | Execute campaign goal |

### Cron Endpoints

| Endpoint | Schedule | Description |
|----------|----------|-------------|
| `/cron/content-pipeline` | `0 */4 * * *` | Every 4 hours |
| `/cron/lead-qualification` | `0 9 * * *` | Daily at 9am |
| `/cron/performance-dashboard` | `0 * * * *` | Hourly |

### Webhooks

| Endpoint | Source | Description |
|----------|--------|-------------|
| `/webhooks/notion` | Notion | Database change events |
| `/webhooks/slack` | Slack | Slash commands |

## Cost Estimates

| Component | Monthly Cost |
|-----------|-------------|
| E2B Sandbox (ephemeral) | $20-50 |
| E2B Sandbox (24/7 hub) | $36 |
| Anthropic API (Sonnet) | $150-400 |
| Backend hosting | $0-20 |
| **Total** | **$206-506** |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `E2B_API_KEY` | Yes | E2B sandbox API key |
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `NOTION_TOKEN` | Yes | Notion integration token |
| `GMTM_DB_URL` | Yes | GMTM MySQL connection string |
| `SENDGRID_API_KEY` | For email | SendGrid API key |
| `TWITTER_BEARER_TOKEN` | For X | Twitter API bearer token |
| `LINKEDIN_ACCESS_TOKEN` | For LinkedIn | LinkedIn API token |

## Development

### Adding a New Agent

1. Create agent file in `agents/`:
```python
async def run_my_agent(params=None, resume=None):
    async for message in query(
        prompt="Your agent prompt...",
        options=ClaudeAgentOptions(...)
    ):
        if hasattr(message, "result"):
            return message.result
```

2. Add endpoint in `backend/main.py`:
```python
@app.post("/agents/my-agent")
async def trigger_my_agent():
    result = await run_agent_in_sandbox("my_agent", "run_my_agent")
    return AgentResponse(...)
```

3. Update `agents/__init__.py` exports

### Testing Locally (Without E2B)

The sandbox runner falls back to local execution if E2B is not available:

```bash
# Install Agent SDK locally
pip install claude-agent-sdk

# Run agent directly
cd agents
python -c "import asyncio; from content_pipeline import run_content_pipeline; asyncio.run(run_content_pipeline())"
```

## Troubleshooting

### Common Issues

1. **"claude-agent-sdk not installed"**
   - E2B sandbox setup may have failed
   - Check E2B API key is valid
   - Try running locally first

2. **"Notion MCP connection failed"**
   - Verify NOTION_TOKEN is set
   - Check Notion integration has access to databases

3. **"Agent timeout"**
   - Increase timeout in sandbox_runner.py
   - Check agent isn't stuck in loop (reduce max_turns)

### Logs

- Local: stdout
- Vercel: `vercel logs`
- Railway: Dashboard logs

## Support

- Anthropic Docs: https://platform.claude.com/docs/en/agent-sdk
- E2B Docs: https://e2b.dev/docs
- GMTM Internal: Check `.claude/` for subagent definitions
