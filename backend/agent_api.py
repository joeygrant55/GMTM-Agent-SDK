"""
Agent API — Raw Anthropic SDK with Anthropic's native web_search tool.

Note: The claude-agent-sdk Python package requires the `claude` CLI binary
as a subprocess (not available on Railway). This uses the raw anthropic
Python SDK directly.

web_search is handled via Anthropic's built-in web_search_20250305 tool —
no Brave API key, no external calls. Anthropic executes the search server-side
and returns results automatically within the same API response stream.

query_database is a custom tool we handle ourselves (read-only GMTM MySQL).
"""

import json
import os
from typing import Optional

import anthropic
import pymysql
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env"))
load_dotenv()

router = APIRouter()

SYSTEM_PROMPT = """You are SPARQ's recruiting AI assistant. You help high school athletes navigate the college recruiting process with real, current intelligence.

You have two tools:

1. **web_search** — Use this for EVERYTHING related to colleges and recruiting:
   - Coaching staff (who is the DB coach, who just got hired/fired)
   - Program news, depth charts, recent commits, transfer portal activity
   - Camp and combine schedules
   - Scholarship offer trends, roster needs
   - Anything about a specific school, conference, or program
   web_search gives you live, current data. Always prefer it over any internal database for college-related questions.

2. **query_database** — Use this ONLY to look up the current athlete's own stats/history in GMTM:
   - Their past combine metrics, height, weight, GPA on record
   - How they compare to other athletes at the same position (SELECT from users/user_metrics)
   - Historical offer data for similar athlete profiles
   NEVER use query_database for college program info — that data may be outdated. Use web_search instead.

ATHLETE TABLES (READ-ONLY — SELECT only):
- users: id, first_name, last_name, sport, position, graduation_year, city, state, height, weight
- user_metrics: user_id, metric_type, metric_value (40_yard, vertical, bench_press, shuttle)
- scholarship_offers: id, user_id, organization_id, created_at

CRITICAL: READ-ONLY. Only SELECT allowed. Never INSERT, UPDATE, DELETE, DROP, ALTER, or TRUNCATE.

When helping an athlete:
- Be specific, confident, and actionable — you are a recruiting expert, not a general chatbot
- Name coaches, give Twitter handles, cite specific programs and needs
- Always tell the athlete the exact next step they should take
- The athlete's profile is automatically injected before each message as context
"""

# Native web_search tool — Anthropic executes it server-side, no client handling needed
# query_database — we execute this ourselves (read-only GMTM MySQL)
TOOLS = [
    {
        "type": "web_search_20250305",
        "name": "web_search",
    },
    {
        "name": "query_database",
        "description": (
            "Execute a READ-ONLY SQL SELECT query against the GMTM athlete database. "
            "Use this ONLY to look up athlete stats, metrics, and historical offer data. "
            "Permitted tables: users, user_metrics, scholarship_offers, athlete_profiles, athlete_metrics. "
            "DO NOT use this for college or program information — use web_search for that instead, "
            "as it provides live, current data. Only SELECT statements are permitted."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A SELECT SQL query on athlete tables only. Must start with SELECT.",
                }
            },
            "required": ["sql"],
        },
    },
]

FORBIDDEN_SQL = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE", "GRANT", "REVOKE"]

# Only allow queries on athlete-related tables. College/program data is served
# via web_search (live) — not from the GMTM DB (potentially stale).
ALLOWED_GMTM_TABLES = {"users", "user_metrics", "scholarship_offers", "athlete_profiles", "athlete_metrics"}


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
    """Execute a read-only SELECT query against the GMTM DB (athlete tables only)."""
    sql_upper = sql.strip().upper()
    for keyword in FORBIDDEN_SQL:
        if sql_upper.startswith(keyword) or f" {keyword} " in sql_upper:
            return {"error": f"GMTM database is READ-ONLY. {keyword} operations are not permitted."}
    if not sql_upper.startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed."}
    # Table allowlist — only athlete-related tables permitted
    # College/program data should come from web_search (live), not GMTM (may be stale)
    import re
    referenced_tables = set(re.findall(r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)', sql_upper))
    flat_tables = {t for pair in referenced_tables for t in pair if t}
    disallowed = flat_tables - {t.upper() for t in ALLOWED_GMTM_TABLES}
    if disallowed:
        return {
            "error": (
                f"Table(s) not permitted: {', '.join(disallowed).lower()}. "
                "query_database is for athlete stats only. "
                "Use web_search for college/program information."
            )
        }
    try:
        db = _get_gmtm_db()
        with db.cursor() as c:
            c.execute(sql)
            rows = c.fetchmany(50)
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
    """Load last 20 messages for session continuity."""
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
    """Persist message for conversation history."""
    try:
        db = _get_agent_db()
        with db.cursor() as c:
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
    - web_search: Anthropic native tool (web_search_20250305) — server-side, no client handling
    - query_database: custom tool — client executes read-only SQL against GMTM DB
    """

    async def generate():
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        profile = _load_athlete_profile(athlete_id)
        profile_context = (
            f"\n\nAthlete profile for this conversation:\n{json.dumps(profile, default=str)}\n"
            if profile else ""
        )

        history = _load_conversation(athlete_id)
        user_content = f"{profile_context}\n\nUser question: {message}" if (profile_context and not history) else message
        messages = history + [{"role": "user", "content": user_content}]
        _save_message(athlete_id, "user", user_content)

        # Agentic loop — continues until end_turn
        # web_search is native: Anthropic executes it server-side within the stream,
        # result blocks come back automatically, stop_reason stays "end_turn"
        # query_database is custom: we execute it and loop back with tool_results
        pending_tool_results = []

        while True:
            if pending_tool_results:
                messages.append({"role": "user", "content": pending_tool_results})
                pending_tool_results = []

            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            ) as stream:

                current_text = ""
                assistant_content = []

                for event in stream:
                    if not hasattr(event, "type"):
                        continue

                    if event.type == "content_block_start":
                        block = event.content_block
                        block_type = getattr(block, "type", "")
                        if block_type == "tool_use":
                            tool_name = getattr(block, "name", "")
                            if tool_name == "web_search":
                                yield f"data: {json.dumps({'type': 'tool', 'label': '🔍 Searching the web...'})}\n\n"
                            elif tool_name == "query_database":
                                yield f"data: {json.dumps({'type': 'tool', 'label': '🗄️ Querying athlete database...'})}\n\n"

                    elif event.type == "content_block_delta":
                        delta = event.delta
                        delta_type = getattr(delta, "type", "")
                        if delta_type == "text_delta" and delta.text:
                            current_text += delta.text
                            yield f"data: {json.dumps({'type': 'text', 'text': delta.text})}\n\n"

                final_message = stream.get_final_message()
                assistant_content = final_message.content
                messages.append({"role": "assistant", "content": assistant_content})

                if final_message.stop_reason == "end_turn":
                    # Done — web_search (if used) was handled server-side within the stream
                    _save_message(athlete_id, "assistant", current_text)
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return

                elif final_message.stop_reason == "tool_use":
                    # Only query_database requires client-side handling
                    # web_search_20250305 is server-side — skip it here
                    for block in assistant_content:
                        if not (hasattr(block, "type") and block.type == "tool_use"):
                            continue
                        if block.name == "query_database":
                            result = _run_read_only_query(block.input.get("sql", ""))
                            pending_tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result, default=str),
                            })
                        # web_search_20250305: server-side, no tool_result needed from us

                    if not pending_tool_results:
                        # No custom tools to handle — done
                        _save_message(athlete_id, "assistant", current_text)
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        return
                    # Loop continues to send query_database results
                else:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/agent/chat")
async def chat_agent(request: dict):
    """Non-streaming legacy endpoint."""
    athlete_id = str(request.get("athlete_id", ""))
    message = request.get("message", "")

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    profile = _load_athlete_profile(athlete_id)
    profile_context = f"\n\nAthlete profile:\n{json.dumps(profile, default=str)}\n" if profile else ""
    history = _load_conversation(athlete_id)
    user_content = f"{profile_context}\n\nUser question: {message}" if (profile_context and not history) else message
    messages = history + [{"role": "user", "content": user_content}]

    full_text = ""
    pending_tool_results = []

    while True:
        if pending_tool_results:
            messages.append({"role": "user", "content": pending_tool_results})
            pending_tool_results = []

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
                if hasattr(block, "type") and block.type == "tool_use" and block.name == "query_database":
                    result = _run_read_only_query(block.input.get("sql", ""))
                    pending_tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })
            if not pending_tool_results:
                break
        else:
            break

    _save_message(athlete_id, "user", user_content)
    _save_message(athlete_id, "assistant", full_text)
    return {"response": full_text}
