"""
Agent API — Raw Anthropic SDK with native web_search tool.

The claude-agent-sdk Python package requires the `claude` CLI binary
installed as a subprocess, which is not available in Railway. This version
uses the raw anthropic Python SDK directly with Anthropic's built-in
web_search tool (no Brave API key needed) and direct DB access via Python.
"""

import json
import os
from typing import Optional

import anthropic
import httpx
import pymysql
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env"))
load_dotenv()

router = APIRouter()

SYSTEM_PROMPT = """You are SPARQ's recruiting AI assistant. You help high school athletes navigate the college recruiting process with data-driven, personalized advice.

You have access to:
- web_search: search the web for current recruiting news, coaching staff, program info, camp schedules
- query_database: read-only access to the GMTM database (75K athletes, scholarship offers, college programs)

GMTM DATABASE (READ-ONLY — SELECT queries only):
Key tables:
- users: id, first_name, last_name, sport, position, graduation_year, city, state, height, weight
- user_metrics: user_id, metric_type, metric_value (40_yard, vertical, bench_press, shuttle)
- scholarship_offers: id, user_id, organization_id, created_at
- organizations: id, name, city, state, division, conference
- organization_metrics: org_id, metric_type, metric_value

CRITICAL: GMTM database is READ-ONLY. Only SELECT statements are allowed. Never attempt INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or TRUNCATE.

When answering questions:
1. Use web_search for current info (coaches, news, camps, depth charts, recent offers)
2. Use query_database for historical patterns (offer rates, position comparisons, school stats)
3. Be specific, data-driven, and actionable — you are a recruiting expert
4. The athlete's profile is provided as context before each message
"""

def _run_web_search(query_str: str) -> dict:
    """Execute a web search using Brave Search API."""
    brave_key = os.environ.get("BRAVE_API_KEY", "")
    if not brave_key:
        return {"error": "Search unavailable", "results": []}
    try:
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": brave_key},
            params={"q": query_str, "count": 5, "text_decorations": False},
            timeout=10,
        )
        data = resp.json()
        results = []
        for r in data.get("web", {}).get("results", [])[:5]:
            results.append({
                "title": r.get("title"),
                "url": r.get("url"),
                "description": r.get("description", ""),
            })
        return {"results": results, "query": query_str}
    except Exception as e:
        return {"error": str(e), "results": []}


TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for current information about college programs, coaching staff, recruiting news, camp schedules, and player profiles.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "query_database",
        "description": (
            "Execute a READ-ONLY SQL SELECT query against the GMTM athlete database. "
            "Returns rows as JSON. Only SELECT statements are permitted."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A SELECT SQL query to run against the GMTM database. Must start with SELECT.",
                }
            },
            "required": ["sql"],
        },
    },
]

FORBIDDEN_SQL = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE", "GRANT", "REVOKE"]


def _get_agent_db():
    return pymysql.connect(
        host=os.environ.get("AGENT_DB_HOST", "localhost"),
        user=os.environ.get("AGENT_DB_USER", "root"),
        password=os.environ.get("AGENT_DB_PASSWORD", ""),
        database=os.environ.get("AGENT_DB_NAME", "railway"),
        port=int(os.environ.get("AGENT_DB_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor,
    )


def _get_gmtm_db():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database="gmtm",
        port=3306,
        cursorclass=pymysql.cursors.DictCursor,
    )


def _run_read_only_query(sql: str) -> dict:
    """Execute a read-only SQL query against the GMTM DB."""
    sql_upper = sql.strip().upper()

    # Triple-check: block any write operations
    for keyword in FORBIDDEN_SQL:
        if sql_upper.startswith(keyword) or f" {keyword} " in sql_upper:
            return {"error": f"GMTM database is READ-ONLY. {keyword} operations are not permitted."}

    if not sql_upper.startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed."}

    try:
        db = _get_gmtm_db()
        with db.cursor() as c:
            c.execute(sql)
            rows = c.fetchmany(50)  # limit to 50 rows max
        db.close()
        return {"rows": rows, "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}


def _load_athlete_profile(athlete_id: str) -> Optional[dict]:
    """Load profile from sparq_profiles (new users) or GMTM users (legacy)."""
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute("SELECT * FROM sparq_profiles WHERE clerk_id = %s", (athlete_id,))
            profile = c.fetchone()
        db.close()
        if profile:
            return {
                "source": "sparq_profile",
                "name": profile.get("name"),
                "position": profile.get("position"),
                "school": profile.get("school"),
                "class_year": profile.get("class_year"),
                "state": profile.get("state"),
                "gpa": str(profile.get("gpa")) if profile.get("gpa") else None,
                "recruiting_goals": profile.get("recruiting_goals"),
                "combine_metrics": profile.get("combine_metrics"),
            }
    except Exception:
        pass

    if athlete_id and athlete_id.isdigit():
        try:
            db = _get_gmtm_db()
            with db.cursor() as c:
                c.execute(
                    "SELECT first_name, last_name, position, graduation_year, city, state FROM users WHERE id = %s",
                    (int(athlete_id),),
                )
                user = c.fetchone()
            db.close()
            if user:
                return {"source": "gmtm", **user}
        except Exception:
            pass

    return None


def _load_conversation(athlete_id: str) -> list:
    """Load persisted conversation history for session continuity."""
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute(
                """SELECT role, content FROM agent_messages am
                   JOIN agent_conversations ac ON am.conversation_id = ac.id
                   WHERE ac.clerk_id = %s
                   ORDER BY am.id DESC LIMIT 20""",
                (athlete_id,),
            )
            rows = c.fetchall()
        db.close()
        # Return in chronological order
        messages = []
        for row in reversed(rows):
            content = row["content"]
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except Exception:
                    pass
            messages.append({"role": row["role"], "content": content})
        return messages
    except Exception:
        return []


def _save_message(athlete_id: str, role: str, content):
    """Persist a message to the conversation history."""
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            # Get or create conversation
            c.execute(
                "INSERT IGNORE INTO agent_conversations (clerk_id, created_at, updated_at) VALUES (%s, NOW(), NOW())",
                (athlete_id,),
            )
            db.commit()
            c.execute("SELECT id FROM agent_conversations WHERE clerk_id = %s", (athlete_id,))
            conv = c.fetchone()
            if conv:
                content_str = json.dumps(content) if not isinstance(content, str) else content
                c.execute(
                    "INSERT INTO agent_messages (conversation_id, role, content, created_at) VALUES (%s, %s, %s, NOW())",
                    (conv["id"], role, content_str),
                )
        db.commit()
        db.close()
    except Exception as e:
        print(f"Warning: could not save message: {e}")


@router.get("/api/agent/stream")
async def stream_agent(athlete_id: str, message: str, session_id: Optional[str] = None):
    """
    Streaming workspace AI chat.
    Uses Anthropic API directly with native web_search + custom query_database tool.
    Maintains conversation history across sessions.
    """

    async def generate():
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        # Load athlete profile for context injection
        profile = _load_athlete_profile(athlete_id)
        profile_context = (
            f"\n\nAthlete profile for this conversation:\n{json.dumps(profile, default=str)}\n"
            if profile else ""
        )

        # Load conversation history
        history = _load_conversation(athlete_id)

        # Build messages array with history + new message
        user_content = message
        if profile_context and not history:
            # Inject profile context on first message
            user_content = f"{profile_context}\n\nUser question: {message}"

        messages = history + [{"role": "user", "content": user_content}]

        # Save user message
        _save_message(athlete_id, "user", user_content)

        # Agentic loop — keep going until no more tool calls
        full_response_text = ""
        tool_results_to_add = []

        while True:
            # Add any pending tool results to messages
            if tool_results_to_add:
                messages.append({"role": "user", "content": tool_results_to_add})
                tool_results_to_add = []

            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            ) as stream:
                assistant_content = []
                current_text = ""

                for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_start":
                            block = event.content_block
                            if hasattr(block, "type"):
                                if block.type == "text":
                                    pass  # handled in delta
                                elif block.type == "tool_use":
                                    tool_name = block.name
                                    label = (
                                        "🔍 Searching the web..."
                                        if tool_name == "web_search"
                                        else "🗄️ Querying athlete database..."
                                        if tool_name == "query_database"
                                        else f"⚙️ {tool_name}..."
                                    )
                                    yield f"data: {json.dumps({'type': 'tool', 'label': label})}\n\n"

                        elif event.type == "content_block_delta":
                            delta = event.delta
                            if hasattr(delta, "type"):
                                if delta.type == "text_delta":
                                    current_text += delta.text
                                    full_response_text += delta.text
                                    yield f"data: {json.dumps({'type': 'text', 'text': delta.text})}\n\n"

                # Get final message with full content blocks
                final_message = stream.get_final_message()
                assistant_content = final_message.content

                # Add assistant turn to messages
                messages.append({"role": "assistant", "content": assistant_content})

                # Check stop reason
                if final_message.stop_reason == "end_turn":
                    # Done — save and exit loop
                    _save_message(athlete_id, "assistant", current_text)
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return

                elif final_message.stop_reason == "tool_use":
                    # Process tool calls
                    for block in assistant_content:
                        if hasattr(block, "type") and block.type == "tool_use":
                            tool_result = None

                            if block.name == "query_database":
                                sql = block.input.get("sql", "")
                                result = _run_read_only_query(sql)
                                tool_result = json.dumps(result, default=str)

                            elif block.name == "web_search":
                                result = _run_web_search(block.input.get("query", ""))
                                tool_result = json.dumps(result)

                            if tool_result is not None:
                                tool_results_to_add.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": tool_result,
                                })

                    # Continue the loop to process tool results
                    continue

                else:
                    # Unexpected stop reason — finish
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# Legacy POST endpoint for backward compat
@router.post("/api/agent/chat")
async def chat_agent(request: dict):
    """Non-streaming chat endpoint."""
    athlete_id = str(request.get("athlete_id", ""))
    message = request.get("message", "")

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    profile = _load_athlete_profile(athlete_id)
    profile_context = f"\n\nAthlete profile:\n{json.dumps(profile, default=str)}\n" if profile else ""
    history = _load_conversation(athlete_id)

    user_content = f"{profile_context}\n\nUser question: {message}" if profile_context and not history else message
    messages = history + [{"role": "user", "content": user_content}]

    full_text = ""
    tool_results_to_add = []

    while True:
        if tool_results_to_add:
            messages.append({"role": "user", "content": tool_results_to_add})
            tool_results_to_add = []

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        for block in response.content:
            if hasattr(block, "text"):
                full_text += block.text

        if response.stop_reason == "end_turn":
            break
        elif response.stop_reason == "tool_use":
            for block in response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    if block.name == "query_database":
                        result = _run_read_only_query(block.input.get("sql", ""))
                        tool_results_to_add.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        })
                    elif block.name == "web_search":
                        result = _run_web_search(block.input.get("query", ""))
                        tool_results_to_add.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
            if not tool_results_to_add:
                break
        else:
            break

    _save_message(athlete_id, "user", user_content)
    _save_message(athlete_id, "assistant", full_text)
    return {"response": full_text}
