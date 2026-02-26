"""
Agent API - Claude Agent SDK version
Replaces the hand-rolled orchestrator with the official SDK.
"""

import json
import os
from typing import Optional

import pymysql
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, query
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env"))
load_dotenv()

router = APIRouter()

SYSTEM_PROMPT = """You are SPARQ's recruiting AI assistant. You help high school athletes navigate the college recruiting process with data-driven, personalized advice.

You have access to:
- WebSearch: search the web for current recruiting news, coaching staff, program info, camp schedules
- WebFetch: fetch and read specific web pages for detailed information
- mcp__gmtm-db__query: read-only access to the GMTM database (75K athletes, scholarship offers, college programs)

GMTM DATABASE (READ-ONLY - SELECT queries only):
Key tables:
- users: id, first_name, last_name, sport, position, graduation_year, city, state, height, weight
- user_metrics: user_id, metric_type, metric_value (40_yard, vertical, bench_press, shuttle)
- scholarship_offers: id, user_id, organization_id, created_at
- organizations: id, name, city, state, division, conference
- organization_metrics: org_id, metric_type, metric_value

CRITICAL: GMTM database is READ-ONLY. Only SELECT statements are allowed. Never attempt INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or TRUNCATE.

When answering questions:
1. Use WebSearch/WebFetch for current info (coaches, news, camps, depth charts)
2. Use the DB for historical patterns (offer rates, position comparisons, school recruiting history)
3. Be specific, data-driven, and actionable - you are a recruiting expert
4. The athlete's profile is injected as context automatically before each message
"""


WRITE_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "REPLACE",
    "GRANT",
    "REVOKE",
]


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


def _load_athlete_profile(athlete_id: str) -> Optional[dict]:
    """Load profile from sparq_profiles or gmtm users table."""
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

    if athlete_id.isdigit():
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


def _save_session_id(athlete_id: str, session_id: str):
    """Persist session_id so workspace chat can resume."""
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute(
                """
                INSERT INTO agent_sessions (clerk_id, session_id, updated_at)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE session_id = VALUES(session_id), updated_at = NOW()
                """,
                (athlete_id, session_id),
            )
        db.commit()
        db.close()
    except Exception as e:
        print(f"Warning: could not save session_id: {e}")


def _load_session_id(athlete_id: str) -> Optional[str]:
    """Load existing session_id for this athlete."""
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute(
                "SELECT session_id FROM agent_sessions WHERE clerk_id = %s ORDER BY updated_at DESC LIMIT 1",
                (athlete_id,),
            )
            row = c.fetchone()
        db.close()
        return row["session_id"] if row else None
    except Exception:
        return None


@router.get("/api/agent/stream")
async def stream_agent(athlete_id: str, message: str, session_id: Optional[str] = None):
    """
    Streaming workspace AI chat endpoint.
    Uses Claude Agent SDK with WebSearch, WebFetch, and read-only GMTM DB via MCP.
    Maintains persistent sessions so the AI remembers previous conversations.
    """

    async def generate():
        captured_session_id = None

        async def inject_athlete_context(input_data, tool_use_id, context):
            _ = (tool_use_id, context)
            profile = _load_athlete_profile(athlete_id)
            if profile:
                return {
                    "hookSpecificOutput": {
                        "hookEventName": input_data["hook_event_name"],
                        "additionalContext": f"Current athlete profile: {json.dumps(profile, default=str)}",
                    }
                }
            return {}

        async def enforce_gmtm_read_only(input_data, tool_use_id, context):
            _ = (tool_use_id, context)
            if not input_data.get("tool_name", "").startswith("mcp__gmtm-db__"):
                return {}
            sql = str(input_data.get("tool_input", {}).get("query", "")).strip().upper()
            for keyword in WRITE_KEYWORDS:
                if sql.startswith(keyword) or f" {keyword} " in sql or f"\n{keyword} " in sql:
                    print(f"BLOCKED write attempt on GMTM DB: {keyword}")
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": input_data["hook_event_name"],
                            "permissionDecision": "deny",
                            "permissionDecisionReason": (
                                "GMTM database is strictly read-only. "
                                f"{keyword} operations are not permitted. Use SELECT only."
                            ),
                        }
                    }
            return {}

        async def save_session_on_stop(input_data, tool_use_id, context):
            _ = (input_data, tool_use_id, context)
            nonlocal captured_session_id
            if captured_session_id:
                _save_session_id(athlete_id, captured_session_id)
            return {}

        resume_session = session_id or _load_session_id(athlete_id)

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            allowed_tools=["WebSearch", "WebFetch", "mcp__gmtm-db__query"],
            permission_mode="bypassPermissions",
            resume=resume_session,
            mcp_servers={
                "gmtm-db": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-mysql",
                        f"mysql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:3306/gmtm",
                    ],
                    "env": {
                        "MYSQL_READ_ONLY": "true",
                    },
                }
            },
            hooks={
                "UserPromptSubmit": [HookMatcher(hooks=[inject_athlete_context])],
                "PreToolUse": [HookMatcher(matcher="^mcp__gmtm-db__", hooks=[enforce_gmtm_read_only])],
                "Stop": [HookMatcher(hooks=[save_session_on_stop])],
            },
        )

        async for sdk_message in query(prompt=message, options=options):
            if hasattr(sdk_message, "subtype") and sdk_message.subtype == "init":
                session_data = {}
                if hasattr(sdk_message, "session_id"):
                    session_data = {"session_id": sdk_message.session_id}
                elif hasattr(sdk_message, "data"):
                    session_data = sdk_message.data or {}
                sid = session_data.get("session_id")
                if sid:
                    captured_session_id = sid
                    yield f"data: {json.dumps({'type': 'session', 'session_id': sid})}\n\n"

            if hasattr(sdk_message, "content") and sdk_message.content:
                for block in sdk_message.content:
                    if hasattr(block, "text") and block.text:
                        yield f"data: {json.dumps({'type': 'text', 'text': block.text})}\n\n"
                    elif hasattr(block, "name"):
                        tool_name = str(getattr(block, "name", ""))
                        tool_label = (
                            "Querying athlete database..."
                            if tool_name.startswith("mcp__gmtm-db__")
                            else "Searching the web..."
                            if tool_name == "WebSearch"
                            else "Reading page..."
                            if tool_name == "WebFetch"
                            else f"{tool_name or 'Working'}..."
                        )
                        yield f"data: {json.dumps({'type': 'tool', 'label': tool_label})}\n\n"

            if hasattr(sdk_message, "result"):
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/agent/chat")
async def chat_agent(request: dict):
    """Legacy non-streaming endpoint. Wraps the SDK synchronously."""
    athlete_id = str(request.get("athlete_id", ""))
    message = request.get("message", "")
    session_id = request.get("session_id")

    full_response = []
    captured_session = None

    resume_session = session_id or _load_session_id(athlete_id)

    async def inject_context(input_data, tool_use_id, context):
        _ = (tool_use_id, context)
        profile = _load_athlete_profile(athlete_id)
        if profile:
            return {
                "hookSpecificOutput": {
                    "hookEventName": input_data["hook_event_name"],
                    "additionalContext": f"Athlete profile: {json.dumps(profile, default=str)}",
                }
            }
        return {}

    async def block_writes(input_data, tool_use_id, context):
        _ = (tool_use_id, context)
        if not input_data.get("tool_name", "").startswith("mcp__gmtm-db__"):
            return {}
        sql = str(input_data.get("tool_input", {}).get("query", "")).strip().upper()
        for keyword in WRITE_KEYWORDS:
            if keyword in sql:
                return {
                    "hookSpecificOutput": {
                        "hookEventName": input_data["hook_event_name"],
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"READ-ONLY: {keyword} not allowed.",
                    }
                }
        return {}

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["WebSearch", "WebFetch", "mcp__gmtm-db__query"],
        permission_mode="bypassPermissions",
        resume=resume_session,
        mcp_servers={
            "gmtm-db": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-mysql",
                    f"mysql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:3306/gmtm",
                ],
                "env": {"MYSQL_READ_ONLY": "true"},
            }
        },
        hooks={
            "UserPromptSubmit": [HookMatcher(hooks=[inject_context])],
            "PreToolUse": [HookMatcher(matcher="^mcp__gmtm-db__", hooks=[block_writes])],
        },
    )

    async for msg in query(prompt=message, options=options):
        if hasattr(msg, "subtype") and msg.subtype == "init":
            sid = getattr(msg, "session_id", None) or (msg.data.get("session_id") if hasattr(msg, "data") and msg.data else None)
            if sid:
                captured_session = sid
                _save_session_id(athlete_id, sid)
        if hasattr(msg, "content") and msg.content:
            for block in msg.content:
                if hasattr(block, "text") and block.text:
                    full_response.append(block.text)

    return {"response": "".join(full_response), "session_id": captured_session}
