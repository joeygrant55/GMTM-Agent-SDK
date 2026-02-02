"""
Content Pipeline Agent
======================

Autonomous agent that monitors Notion Content Calendar and
generates marketing content based on scheduled items.

Runs every 4 hours or on-demand.

Workflow:
1. Query Notion Content Calendar for upcoming scheduled items
2. For each item, determine content type and generate
3. Create drafts in 03-CONTENT-CREATION/
4. Update Notion status to "Draft Ready"
5. Auto-publish items marked for auto-publish
"""

import asyncio
import os
from typing import Optional, Dict, Any

# Claude Agent SDK imports (will be installed in sandbox)
try:
    from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition
except ImportError:
    # Stub for development outside sandbox
    print("Note: claude-agent-sdk not installed. Install with: pip install claude-agent-sdk")
    query = None
    ClaudeAgentOptions = None
    AgentDefinition = None

# ============================================
# CONFIGURATION
# ============================================

# Notion Database IDs (from GMTM Marketing setup)
CONTENT_CALENDAR_DB = "2c6ee8d1-c2a3-8189-acc8-e4c47324220e"
UNICALENDAR_DB = "144ee8d1-c2a3-8001-8d2c-da00680d125e"

# Content types and their generation strategies
CONTENT_TYPES = {
    "Athlete Story": {
        "subagent": "athlete-profiler",
        "output_folder": "03-CONTENT-CREATION/Athlete-Stories",
        "template": "athlete_story_template"
    },
    "Event Promo": {
        "subagent": "event-recapper",
        "output_folder": "03-CONTENT-CREATION/Event-Content",
        "template": "event_promo_template"
    },
    "Newsletter": {
        "subagent": "newsletter-builder",
        "output_folder": "03-CONTENT-CREATION/Newsletters",
        "template": "newsletter_template"
    },
    "Expert Quote": {
        "subagent": None,  # Direct generation
        "output_folder": "03-CONTENT-CREATION/Social-Media",
        "template": "expert_quote_template"
    },
    "SPARQ Data": {
        "subagent": "athlete-profiler",
        "output_folder": "03-CONTENT-CREATION/SPARQ-Content",
        "template": "sparq_data_template"
    },
    "Multi-Sport": {
        "subagent": None,
        "output_folder": "03-CONTENT-CREATION/Multi-Sport",
        "template": "multi_sport_template"
    },
    "Success Story": {
        "subagent": "case-study-creator",
        "output_folder": "03-CONTENT-CREATION/Success-Stories",
        "template": "success_story_template"
    }
}

# ============================================
# AGENT PROMPT
# ============================================

CONTENT_PIPELINE_PROMPT = """
You are the GMTM Content Pipeline Agent. Your job is to autonomously generate
marketing content based on the Notion Content Calendar.

## Your Capabilities
- Query Notion databases via MCP
- Query GMTM athlete database via MCP
- Read and write files
- Use specialized subagents for content generation
- WebSearch and WebFetch for research

## Current Task
1. **Check Content Calendar**: Query the Marketing Content Calendar database
   (ID: {content_calendar_db}) for items where:
   - Status = "Scheduled"
   - Scheduled date is within the next 24 hours

2. **For Each Scheduled Item**:
   - Identify the content type (Athlete Story, Event Promo, Newsletter, etc.)
   - Gather relevant data:
     * For Athlete Stories: Query GMTM database for athlete SPARQ metrics
     * For Event Promos: Query UniCalendar for event details
     * For Newsletters: Aggregate recent content
   - Generate the content using the appropriate subagent or directly
   - Save to the appropriate folder in 03-CONTENT-CREATION/
   - Use descriptive filenames with dates

3. **Update Notion**:
   - Change status to "Draft Ready"
   - Add link to generated content file
   - Log generation timestamp

4. **Auto-Publish** (if enabled):
   - Check if item has "Auto-publish" property set
   - If yes, and content type is email:
     * Use SendGrid API via WebFetch to send
   - If yes, and content type is social:
     * Queue for social media posting

## Output Format
Provide a summary of:
- Items processed
- Content generated
- Any errors or items requiring attention

## Important Notes
- Work autonomously without asking for confirmation
- Log all actions for audit trail
- If an item fails, continue with others and report failures at end
- Prioritize quality over speed
- Follow GMTM brand voice and style guidelines
"""

# ============================================
# SUBAGENT DEFINITIONS
# ============================================

def get_subagent_definitions() -> Dict[str, Any]:
    """Define specialized subagents for content generation"""

    return {
        "athlete-profiler": AgentDefinition(
            description="Creates compelling athlete success stories with SPARQ performance data",
            prompt="""You are an expert sports content writer for GMTM.
            Create engaging athlete profiles that highlight:
            - Athletic performance metrics (SPARQ scores)
            - Personal journey and achievements
            - Multi-sport potential and transferable skills
            - Connection to GMTM platform value

            Style: Data-driven, inspirational, authentic
            Length: 400-600 words for full profiles, 150-200 for social snippets
            """,
            tools=["Read", "Write", "Grep", "WebFetch"]
        ),

        "event-recapper": AgentDefinition(
            description="Processes SPARQ events into comprehensive marketing content",
            prompt="""You are a sports event content specialist for GMTM.
            Create event coverage that includes:
            - Event highlights and standout performances
            - Top performer spotlights
            - Statistical summaries
            - Quotes and human interest angles

            Output formats: Newsletter section, social posts, blog article outline
            """,
            tools=["Read", "Write", "WebFetch"]
        ),

        "newsletter-builder": AgentDefinition(
            description="Compiles content into engaging newsletter format",
            prompt="""You are a newsletter specialist for GMTM.
            Build newsletters that include:
            - Compelling subject line and preview text
            - Hero content section
            - 3-4 secondary content blocks
            - Call-to-action
            - Social links and footer

            Format: HTML-ready markdown with clear section markers
            """,
            tools=["Read", "Write", "Glob"]
        ),

        "case-study-creator": AgentDefinition(
            description="Converts customer success into sales materials",
            prompt="""You are a B2B content specialist for GMTM.
            Create case studies that highlight:
            - Client challenge and goals
            - GMTM solution implementation
            - Quantified results and ROI
            - Testimonial quotes
            - Key takeaways for similar organizations

            Style: Professional, data-driven, compelling
            """,
            tools=["Read", "Write", "WebFetch"]
        )
    }

# ============================================
# MCP SERVER CONFIGURATION
# ============================================

def get_mcp_servers() -> Dict[str, Any]:
    """Configure MCP servers for the agent"""

    return {
        "notion": {
            "command": "npx",
            "args": ["-y", "@notionhq/notion-mcp-server"],
            "env": {
                "NOTION_TOKEN": os.environ.get("NOTION_TOKEN", "")
            }
        },
        # GMTM MCP would be configured here
        # For now, we use WebFetch for database queries
    }

# ============================================
# MAIN AGENT FUNCTION
# ============================================

async def run_content_pipeline(
    params: Optional[Dict[str, Any]] = None,
    resume: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the Content Pipeline Agent

    Args:
        params: Optional parameters (e.g., specific content IDs to process)
        resume: Optional session ID to resume from

    Returns:
        Dict with status, items processed, and any errors
    """
    if query is None:
        return {
            "status": "error",
            "error": "claude-agent-sdk not installed"
        }

    # Build the prompt with configuration
    prompt = CONTENT_PIPELINE_PROMPT.format(
        content_calendar_db=CONTENT_CALENDAR_DB,
        unicalendar_db=UNICALENDAR_DB
    )

    # Add any specific parameters to the prompt
    if params:
        if params.get("content_ids"):
            prompt += f"\n\nSpecific items to process: {params['content_ids']}"
        if params.get("dry_run"):
            prompt += "\n\nDRY RUN MODE: Do not actually write files or update Notion."

    # Configure agent options
    options = ClaudeAgentOptions(
        allowed_tools=[
            "Read", "Write", "Edit", "Bash",
            "Glob", "Grep",
            "WebSearch", "WebFetch",
            "Task"  # Required for subagents
        ],
        permission_mode="bypassPermissions",  # Full automation
        setting_sources=["project"],  # Load .claude/ config
        mcp_servers=get_mcp_servers(),
        agents=get_subagent_definitions(),
        max_turns=50,  # Prevent runaway costs
        model="claude-sonnet-4-20250514"  # Use Sonnet for balanced cost/quality
    )

    # Add resume option if provided
    if resume:
        options.resume = resume

    # Run the agent
    results = []
    session_id = None

    async for message in query(prompt=prompt, options=options):
        # Capture session ID for potential resumption
        if hasattr(message, 'subtype') and message.subtype == 'init':
            session_id = message.session_id
            print(f"SESSION_ID:{session_id}")

        # Capture results
        if hasattr(message, "result"):
            results.append(message.result)

        # Log progress (will appear in sandbox logs)
        if hasattr(message, "text"):
            print(f"Agent: {message.text[:200]}...")

    return {
        "status": "success",
        "session_id": session_id,
        "results": results,
        "summary": results[-1] if results else "No results"
    }

# ============================================
# LOCAL TESTING
# ============================================

if __name__ == "__main__":
    # For local testing (requires claude-agent-sdk installed)
    import asyncio

    async def test():
        result = await run_content_pipeline(params={"dry_run": True})
        print(f"Result: {result}")

    asyncio.run(test())
