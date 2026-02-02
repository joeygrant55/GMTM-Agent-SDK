"""
Scout AI Agent
==============

Conversational talent discovery agent for coaches and scouts.
Uses Claude Agent SDK with GMTM MCP to query the database.

Features:
- Natural language athlete search via Claude
- Uses GMTM MCP to execute SQL queries
- Filter by metrics, location, graduation year, sport, position
- Returns structured athlete results
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# Claude Agent SDK imports
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock, ToolResultBlock

from .query_builder import QueryBuilder, SearchFilters, MetricFilter, POSITION_MAPPINGS, STATE_MAPPINGS, SPORT_MAPPINGS

# ============================================
# CONFIGURATION
# ============================================

# Path to the MCP configuration file
MCP_CONFIG_PATH = Path("/Users/joey/Desktop/GMTM Marketing/.mcp.json")

# ============================================
# SYSTEM PROMPT FOR SCOUT AGENT
# ============================================

SCOUT_AGENT_PROMPT = """
You are SPARQ Scout AI, an intelligent talent discovery assistant for finding athletes with VERIFIED performance data from SPARQ combines and events.

## Your Task
Help coaches find athletes with SPARQ-verified metrics from official combines and events. ONLY return athletes who have participated in SPARQ events with verified, measurable performance data.

## Available Tools
- `mcp__gmtmmcp__run_sql` - Execute SQL queries against the GMTM database
- `mcp__gmtmmcp__get_table_schema` - Get schema for specific tables

## Database Schema (Key Tables)

**users** - Athlete profiles
- user_id (INT), first_name, last_name, graduation_year, location_id, avatar_uri
- type = 1 for athletes, visibility = 2 for public profiles

**locations** - Geographic data
- location_id, city, province (state abbreviation), country

**metrics** - Athletic measurements (IMPORTANT: has SPARQ event data!)
- user_id, title (metric name), value, is_current, verified
- score (INT) - SPARQ score for ranking
- percentile (INT) - percentile ranking
- in_person_event_id - links to SPARQ events
- Common titles: "40 Yard Dash", "Vertical Jump", "5-10-5 shuttle", "Broad Jump", "Kneeling Power Ball Toss (6 lb ball)"

**in_person_events** - SPARQ Combines and Events
- in_person_event_id, name, subject_type
- Contains events like "SPARQ Combine", "All Sports Combine", "Slide to Glory"

**career** - Team affiliations
- user_id, career_id, is_current, sport_id

**user_positions** - Player positions
- career_id, position_id

**positions** - Position lookup
- position_id, name

## PRIORITY: Query SPARQ-Verified Athletes

**ALWAYS prioritize athletes with verified metrics from SPARQ events:**

```sql
SELECT DISTINCT
    u.user_id,
    u.first_name,
    u.last_name,
    u.graduation_year,
    l.city,
    l.province,
    p.name as position_name,
    m.title as metric_name,
    m.value,
    m.score as sparq_score,
    m.percentile,
    ipe.name as event_name
FROM metrics m
JOIN users u ON m.user_id = u.user_id
JOIN in_person_events ipe ON m.in_person_event_id = ipe.in_person_event_id
LEFT JOIN locations l ON u.location_id = l.location_id
LEFT JOIN career c ON u.user_id = c.user_id AND c.is_current = 1
LEFT JOIN user_positions up ON c.career_id = up.career_id
LEFT JOIN positions p ON up.position_id = p.position_id
WHERE u.type = 1 AND u.visibility = 2
    AND m.is_current = 1
    AND m.verified = 1
    [AND additional filters]
ORDER BY m.score DESC
LIMIT 10
```

## SPARQ Leaderboard Query (Top Performers)

For "leaderboard", "top performers", "best scores":

```sql
SELECT
    u.user_id, u.first_name, u.last_name, u.graduation_year,
    l.city, l.province,
    m.title, m.value, m.score, m.percentile,
    ipe.name as event_name
FROM metrics m
JOIN users u ON m.user_id = u.user_id
JOIN in_person_events ipe ON m.in_person_event_id = ipe.in_person_event_id
LEFT JOIN locations l ON u.location_id = l.location_id
WHERE u.type = 1 AND u.visibility = 2
    AND m.is_current = 1
    AND m.score > 0
ORDER BY m.score DESC
LIMIT 10
```

## Translation Rules

**Metrics (lower is better for times):**
- "sub-4.5 40" → m.title = '40 Yard Dash' AND CAST(m.value AS DECIMAL(4,2)) < 4.5
- "over 36 inch vertical" → m.title = 'Vertical Jump' AND CAST(m.value AS DECIMAL(4,1)) > 36

**States:**
- "Texas" → l.province = 'TX'
- "Florida" → l.province = 'FL'

**Positions (Football):**
- "running back" / "RB" → position_id IN (243, 297, 317, 324)
- "quarterback" / "QB" → position_id IN (211, 240, 302, 327)
- "wide receiver" / "WR" → position_id IN (256, 311, 317, 321)

**Graduation Year:**
- "class of 2026" → u.graduation_year = 2026

**SPARQ Event filters:**
- "SPARQ combine" → ipe.name LIKE '%SPARQ%'
- "Slide to Glory" → ipe.name LIKE '%Slide to Glory%'
- "All Sports Combine" → ipe.name LIKE '%All Sports Combine%'

## Response Format

After running the SQL query, return results in this EXACT JSON format:

```json
{
  "athletes": [
    {
      "user_id": 12345,
      "first_name": "John",
      "last_name": "Smith",
      "graduation_year": 2026,
      "city": "Houston",
      "state": "TX",
      "position": "Running Back",
      "event_name": "SPARQ Combine - Houston",
      "sparq_score": 1850,
      "metrics": {
        "40 Yard Dash": "4.42",
        "Vertical Jump": "38"
      },
      "profile_url": "https://gmtm.com/profile/12345"
    }
  ],
  "summary": "Found 5 SPARQ-verified athletes matching your criteria."
}
```

## Important
1. ALWAYS prioritize athletes with in_person_event_id (SPARQ verified)
2. ALWAYS execute the SQL query using mcp__gmtmmcp__run_sql
3. Return results as JSON even if no athletes found (return empty athletes array)
4. Include SPARQ score and event name when available
5. Build profile_url as https://gmtm.com/profile/{user_id}
6. Focus on verified=1 metrics from SPARQ events
"""


# ============================================
# SCOUT AGENT CLASS
# ============================================

class ScoutAgent:
    """Scout AI Agent for talent discovery using Claude Agent SDK"""

    def __init__(self):
        self.query_builder = QueryBuilder()

    async def search(
        self,
        natural_query: str,
        user_id: Optional[int] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Process a natural language search query using Claude Agent SDK.

        Args:
            natural_query: The coach's search query in natural language
            user_id: Optional coach user_id for tracking
            max_results: Maximum number of results to return

        Returns:
            Dict with status, athletes, and metadata
        """
        try:
            # Build the prompt for Claude
            prompt = f"""
{SCOUT_AGENT_PROMPT}

## Current Search Request
Coach query: "{natural_query}"
Max results: {max_results}

Please:
1. Parse the query to identify filters (metrics, location, position, graduation year)
2. Build and execute the SQL query using mcp__gmtmmcp__run_sql
3. Return the results as JSON in the format specified above
"""

            # Configure agent options
            options = ClaudeAgentOptions(
                mcp_servers=str(MCP_CONFIG_PATH),
                allowed_tools=[
                    "mcp__gmtmmcp__run_sql",
                    "mcp__gmtmmcp__get_table_schema",
                    "mcp__gmtmmcp__get_full_schema"
                ],
                permission_mode="bypassPermissions",
                max_turns=10,
                model="claude-sonnet-4-20250514",
                cwd=str(MCP_CONFIG_PATH.parent)
            )

            # Run the agent and collect responses
            full_response = ""
            tool_calls = []

            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    # Access content directly on AssistantMessage
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response += block.text
                        elif isinstance(block, ToolUseBlock):
                            tool_calls.append({
                                "tool": block.name if hasattr(block, 'name') else "unknown",
                                "input": block.input if hasattr(block, 'input') else {}
                            })
                elif isinstance(message, ResultMessage):
                    # Handle result messages
                    pass

            # Try to extract JSON from the response
            athletes = []
            summary = ""

            # Look for JSON in the response
            json_match = re.search(r'\{[\s\S]*"athletes"[\s\S]*\}', full_response)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    athletes = data.get("athletes", [])
                    summary = data.get("summary", f"Found {len(athletes)} athlete(s).")
                except json.JSONDecodeError:
                    pass

            # If no JSON found, try to parse tabular results
            if not athletes:
                # Extract summary from response
                summary = full_response[:500] if full_response else "Search completed."

            return {
                "status": "success",
                "response": summary,
                "query": natural_query,
                "athletes": athletes,
                "athletes_found": len(athletes),
                "tool_calls": tool_calls,
                "raw_response": full_response[:2000]  # For debugging
            }

        except Exception as e:
            return {
                "status": "error",
                "response": f"Search error: {str(e)}",
                "query": natural_query,
                "athletes": [],
                "athletes_found": 0
            }


    async def search_streaming(
        self,
        natural_query: str,
        user_id: Optional[int] = None,
        max_results: int = 10
    ):
        """
        Process a natural language search query with streaming events.
        Yields events for real-time UI updates.
        """
        import asyncio

        # Yield initial event
        yield {
            "event": "start",
            "message": "Analyzing your search request...",
            "stage": "parsing"
        }

        try:
            # Build the prompt for Claude
            prompt = f"""
{SCOUT_AGENT_PROMPT}

## Current Search Request
Coach query: "{natural_query}"
Max results: {max_results}

Please:
1. Parse the query to identify filters (metrics, location, position, graduation year)
2. Build and execute the SQL query using mcp__gmtmmcp__run_sql
3. Return the results as JSON in the format specified above
"""

            yield {
                "event": "progress",
                "message": "Connecting to AI agent...",
                "stage": "connecting"
            }

            # Configure agent options
            options = ClaudeAgentOptions(
                mcp_servers=str(MCP_CONFIG_PATH),
                allowed_tools=[
                    "mcp__gmtmmcp__run_sql",
                    "mcp__gmtmmcp__get_table_schema",
                    "mcp__gmtmmcp__get_full_schema"
                ],
                permission_mode="bypassPermissions",
                max_turns=10,
                model="claude-sonnet-4-20250514",
                cwd=str(MCP_CONFIG_PATH.parent)
            )

            # Run the agent and stream events
            full_response = ""
            tool_calls = []
            current_tool = None

            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response += block.text
                            yield {
                                "event": "thinking",
                                "message": block.text[:100] + "..." if len(block.text) > 100 else block.text,
                                "stage": "thinking"
                            }
                        elif isinstance(block, ToolUseBlock):
                            tool_name = block.name if hasattr(block, 'name') else "unknown"
                            tool_input = block.input if hasattr(block, 'input') else {}

                            tool_calls.append({
                                "tool": tool_name,
                                "input": tool_input
                            })

                            # Emit user-friendly tool events
                            if "run_sql" in tool_name:
                                yield {
                                    "event": "tool_start",
                                    "message": "Querying athlete database...",
                                    "stage": "querying",
                                    "tool": tool_name,
                                    "details": str(tool_input.get("query", ""))[:200] if isinstance(tool_input, dict) else ""
                                }
                            elif "schema" in tool_name:
                                yield {
                                    "event": "tool_start",
                                    "message": "Analyzing database structure...",
                                    "stage": "analyzing",
                                    "tool": tool_name
                                }
                            current_tool = tool_name
                elif isinstance(message, ResultMessage):
                    if current_tool:
                        yield {
                            "event": "tool_complete",
                            "message": f"Completed: {current_tool}",
                            "stage": "processing"
                        }
                        current_tool = None

            yield {
                "event": "progress",
                "message": "Processing results...",
                "stage": "processing"
            }

            # Try to extract JSON from the response
            athletes = []
            summary = ""

            json_match = re.search(r'\{[\s\S]*"athletes"[\s\S]*\}', full_response)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    athletes = data.get("athletes", [])
                    summary = data.get("summary", f"Found {len(athletes)} athlete(s).")
                except json.JSONDecodeError:
                    pass

            if not athletes:
                summary = full_response[:500] if full_response else "Search completed."

            # Yield final result
            yield {
                "event": "complete",
                "message": summary,
                "stage": "complete",
                "result": {
                    "status": "success",
                    "response": summary,
                    "query": natural_query,
                    "athletes": athletes,
                    "athletes_found": len(athletes),
                    "tool_calls": tool_calls
                }
            }

        except Exception as e:
            yield {
                "event": "error",
                "message": f"Search error: {str(e)}",
                "stage": "error",
                "result": {
                    "status": "error",
                    "response": f"Search error: {str(e)}",
                    "query": natural_query,
                    "athletes": [],
                    "athletes_found": 0
                }
            }


# ============================================
# MAIN EXECUTION FUNCTION
# ============================================

async def run_scout_search(
    natural_query: str,
    user_id: Optional[int] = None,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Run a Scout AI search using Claude Agent SDK.

    Args:
        natural_query: Natural language search query
        user_id: Optional coach user_id
        max_results: Maximum results to return

    Returns:
        Search results dict
    """
    agent = ScoutAgent()
    return await agent.search(natural_query, user_id, max_results)


async def run_scout_search_streaming(
    natural_query: str,
    user_id: Optional[int] = None,
    max_results: int = 10
):
    """
    Run a Scout AI search with streaming events.
    Yields events for real-time UI updates.
    """
    agent = ScoutAgent()
    async for event in agent.search_streaming(natural_query, user_id, max_results):
        yield event


# ============================================
# LOCAL TESTING
# ============================================

if __name__ == "__main__":
    import asyncio

    async def test():
        result = await run_scout_search(
            "Athletes with vertical jump over 36 inches"
        )
        print(f"Result: {json.dumps(result, indent=2)}")

    asyncio.run(test())
