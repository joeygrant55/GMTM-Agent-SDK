"""
Agent API — Raw Anthropic SDK with Anthropic's native web_search tool.

Note: The claude-agent-sdk Python package requires the `claude` CLI binary
as a subprocess (not available on Railway). This uses the raw anthropic
Python SDK directly.

web_search is handled via Anthropic's built-in web_search_20250305 tool —
no Brave API key, no external calls. Anthropic executes the search server-side
and returns results automatically within the same API response stream.

get_current_athlete returns the profile already loaded for the authenticated caller.
The model cannot choose an athlete identity or execute SQL.
"""

import json
import os
from typing import Optional

import anthropic
import pymysql
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from auth import optional_identity, require_identity, demo_secret_ok, rate_limit, assert_owner
from combine_results import get_combine_results, format_for_prompt
from athlete_context import CURRENT_ATHLETE_TOOL, current_athlete_tool_result

# Hard cap on agentic tool-loop iterations — bounds worst-case Claude spend per request.
MAX_AGENT_ITERATIONS = 8


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

2. **get_current_athlete** — Returns only the current athlete's server-loaded profile,
   results, and existing aggregate comparisons. It takes no arguments. Use it for
   structured detail beyond the CURRENT ATHLETE PROFILE below. It cannot look up
   other athletes, execute database queries, or supply new comparisons.
   Missing data means unavailable; do not invent results, completion, or coach interest.
   The public demo has no private athlete data. Use web_search for public recruiting information.

When helping an athlete:
- Be specific, confident, and actionable — you are a recruiting expert, not a general chatbot
- Name coaches, give Twitter handles, cite specific programs and needs
- Always tell the athlete the exact next step they should take
- The athlete's full profile, MaxPreps stats, and recruiting goals are injected into CURRENT ATHLETE PROFILE above — NEVER ask for info you already have
- Address the athlete by name, cite their actual stats in your recommendations
"""

# Native web_search tool — Anthropic executes it server-side, no client handling needed
# Current-athlete tool — no database access or caller-selected identity during tool execution.
TOOLS = [
    {
        "type": "web_search_20250305",
        "name": "web_search",
    },
    CURRENT_ATHLETE_TOOL,
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
    """Load profile from sparq_profiles (new users) or GMTM users (legacy)."""
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute("SELECT * FROM sparq_profiles WHERE clerk_id = %s", (athlete_id,))
            profile = c.fetchone()
        db.close()
        if profile:
            # Parse maxpreps_data JSON for real stats
            maxpreps_raw = profile.get("maxpreps_data")
            maxpreps = {}
            if maxpreps_raw:
                try:
                    maxpreps = json.loads(maxpreps_raw) if isinstance(maxpreps_raw, str) else maxpreps_raw
                except Exception:
                    pass

            stats_preview = maxpreps.get("statsPreview") or []  # [[label, value], ...]
            last_season = maxpreps.get("lastSeason")
            sport = maxpreps.get("sport") or profile.get("position")
            profile_url = maxpreps.get("profileUrl")

            linked_results = []
            try:
                db2 = _get_agent_db()
                with db2.cursor() as c:
                    c.execute("SELECT user_id FROM athlete_profiles WHERE clerk_id = %s", (athlete_id,))
                    link = c.fetchone()
                db2.close()
                if link:
                    linked_results = get_combine_results(int(link["user_id"]), _get_gmtm_db)
            except Exception:
                linked_results = []
            return {
                "source": "sparq_profile",
                "combine_results": linked_results,
                "name": profile.get("name"),
                "position": profile.get("position"),
                "sport": sport,
                "school": profile.get("school"),
                "class_year": profile.get("class_year"),
                "state": profile.get("state"),
                "gpa": str(profile.get("gpa")) if profile.get("gpa") else None,
                "recruiting_goals": profile.get("recruiting_goals"),
                "combine_metrics": profile.get("combine_metrics"),
                "maxpreps_stats": {s[0]: s[1] for s in stats_preview} if stats_preview else None,
                "maxpreps_season": last_season,
                "maxpreps_url": profile_url,
            }
    except Exception:
        pass
    # Legacy GMTM athlete: resolve only through the authenticated owner mapping.
    gmtm_user_id: Optional[int] = None
    if athlete_id:
        try:
            db = _get_agent_db()
            with db.cursor() as c:
                c.execute("SELECT user_id FROM athlete_profiles WHERE clerk_id = %s", (athlete_id,))
                row = c.fetchone()
            db.close()
            if row:
                gmtm_user_id = int(row["user_id"])
        except Exception:
            pass
    if gmtm_user_id:
        try:
            db = _get_gmtm_db()
            with db.cursor() as c:
                c.execute(
                    """SELECT u.user_id, u.first_name, u.last_name, u.graduation_year, l.city, l.province AS state
                       FROM users u LEFT JOIN locations l ON l.location_id = u.location_id
                       WHERE u.user_id = %s""",
                    (gmtm_user_id,),
                )
                user = c.fetchone()
                pos = None
                if user:
                    c.execute(
                        """SELECT p.name AS position FROM career c
                           JOIN user_positions up ON up.career_id = c.career_id
                           JOIN positions p ON up.position_id = p.position_id
                           WHERE c.user_id = %s AND up.is_primary = 1 LIMIT 1""",
                        (gmtm_user_id,),
                    )
                    pr = c.fetchone()
                    pos = pr["position"] if pr else None
            db.close()
            if user:
                results = []
                try:
                    results = get_combine_results(gmtm_user_id, _get_gmtm_db)
                except Exception:
                    results = []
                return {
                    "source": "gmtm",
                    "gmtm_user_id": gmtm_user_id,
                    "name": f"{user.get('first_name') or ''} {user.get('last_name') or ''}".strip() or None,
                    "position": pos,
                    "sport": None,
                    "school": None,
                    "class_year": user.get("graduation_year"),
                    "state": user.get("state"),
                    "gpa": None,
                    "recruiting_goals": None,
                    "combine_metrics": None,
                    "maxpreps_stats": None,
                    "maxpreps_season": None,
                    "maxpreps_url": None,
                    "combine_results": results,
                }
        except Exception:
            pass
    return None


def _conversation_id(value) -> Optional[int]:
    """Accept the existing numeric/string request shape, never a falsey or malformed ID."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise HTTPException(status_code=400, detail="Invalid conversation ID.")
    if isinstance(value, str) and not value.isdigit():
        raise HTTPException(status_code=400, detail="Invalid conversation ID.")
    try:
        result = int(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid conversation ID.") from exc
    if result <= 0:
        raise HTTPException(status_code=400, detail="Invalid conversation ID.")
    return result


def _default_conversation_id(c, athlete_id: str) -> Optional[int]:
    # Keep the existing oldest-thread convention for both reads and writes. Do not
    # mix newer What-If forks into the default history or require a schema migration.
    c.execute("SELECT id FROM agent_conversations WHERE clerk_id = %s ORDER BY id ASC LIMIT 1", (athlete_id,))
    row = c.fetchone()
    return int(row["id"]) if row else None


def _require_conversation_owner(athlete_id: str, conversation_id: int) -> None:
    """Preflight explicit IDs before any profile, model, or tool work."""
    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute("SELECT clerk_id FROM agent_conversations WHERE id = %s", (conversation_id,))
            row = c.fetchone()
            assert_owner(row.get("clerk_id") if row else None, athlete_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Conversation storage is unavailable.") from exc
    finally:
        if db:
            db.close()


def _load_conversation(athlete_id: str, conversation_id: Optional[int] = None) -> list:
    """Load the last 20 messages from one owned thread, never all of an athlete's forks."""
    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            conv_id = conversation_id if conversation_id is not None else _default_conversation_id(c, athlete_id)
            if conv_id is None:
                return []
            c.execute(
                """SELECT role, content FROM agent_messages am
                   JOIN agent_conversations ac ON am.conversation_id = ac.id
                   WHERE ac.id = %s AND ac.clerk_id = %s
                   ORDER BY am.id DESC LIMIT 20""",
                (conv_id, athlete_id),
            )
            rows = c.fetchall()
        messages = []
        for row in reversed(rows):
            content = row["content"]
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except (ValueError, TypeError):
                    pass
            messages.append({"role": row["role"], "content": content})
        return messages
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Conversation history is unavailable.") from exc
    finally:
        if db:
            db.close()


def _save_message(athlete_id: str, role: str, content, conversation_id: Optional[int] = None) -> int:
    """Persist only into a currently owned conversation; reject ownership changes atomically."""
    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            conv_id = conversation_id
            if conv_id is None:
                conv_id = _default_conversation_id(c, athlete_id)
                if conv_id is None:
                    c.execute(
                        "INSERT IGNORE INTO agent_conversations (clerk_id, created_at, updated_at) VALUES (%s, NOW(), NOW())",
                        (athlete_id,),
                    )
                    conv_id = _default_conversation_id(c, athlete_id)
            if conv_id is None:
                raise HTTPException(status_code=503, detail="Could not create a conversation.")
            content_str = json.dumps(content) if not isinstance(content, str) else content
            c.execute(
                """INSERT INTO agent_messages (conversation_id, role, content, created_at)
                   SELECT ac.id, %s, %s, NOW() FROM agent_conversations ac
                   WHERE ac.id = %s AND ac.clerk_id = %s""",
                (role, content_str, conv_id, athlete_id),
            )
            if c.rowcount != 1:
                raise HTTPException(status_code=403, detail="This conversation is no longer available to your account.")
        db.commit()
        return int(conv_id)
    except HTTPException:
        if db:
            db.rollback()
        raise
    except Exception as exc:
        if db:
            db.rollback()
        raise HTTPException(status_code=503, detail="Your message could not be saved. Please try again.") from exc
    finally:
        if db:
            db.close()


@router.get("/api/agent/stream")
async def stream_agent(
    request: Request,
    athlete_id: str,
    message: str,
    session_id: Optional[str] = None,
    fork_scenario: Optional[str] = None,
    conversation_id: Optional[int] = None,
    caller_id: Optional[str] = Depends(optional_identity),
    x_demo_secret: Optional[str] = Header(default=None),
):
    """
    Streaming workspace AI chat.
    - web_search: Anthropic native tool (web_search_20250305) — server-side, no client handling
    - get_current_athlete: returns the authenticated request's already-loaded profile

    Auth: either a valid SPARQ session whose subject matches athlete_id (the athlete
    chatting about their own profile), or the demo path — a request carrying the
    DEMO_PROXY_SECRET (injected by the Next.js /api/demo-chat proxy) which is
    rate-limited by client IP and never loads any real athlete's profile or history.
    """
    is_demo = False
    if caller_id:
        # Authenticated user — may only run the agent as themselves.
        if athlete_id != caller_id:
            raise HTTPException(status_code=403, detail="Not authorized for this athlete.")
    else:
        # No token → public demo path. Require the shared proxy secret + rate limit.
        if not demo_secret_ok(x_demo_secret):
            raise HTTPException(status_code=401, detail="Authentication required.")
        client_ip = (request.client.host if request.client else "unknown")
        if not rate_limit(f"demo:{client_ip}", max_calls=20, window_seconds=3600):
            raise HTTPException(status_code=429, detail="Demo limit reached. Sign in with GMTM to keep going.")
        is_demo = True

    conversation_id = _conversation_id(conversation_id)
    if is_demo:
        if conversation_id is not None:
            raise HTTPException(status_code=400, detail="Demo chat cannot use a saved conversation.")
        profile, history = None, []
    else:
        if conversation_id is not None:
            _require_conversation_owner(caller_id, conversation_id)
        history = _load_conversation(caller_id, conversation_id)
        # Persist before returning an SSE response so storage/ownership failures
        # have an ordinary HTTP error and never start paid model work.
        conversation_id = _save_message(caller_id, "user", message, conversation_id)
        profile = _load_athlete_profile(caller_id)

    async def generate():
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        if conversation_id is not None:
            yield f"data: {json.dumps({'type': 'session', 'session_id': str(conversation_id)})}\n\n"

        # Build athlete-aware system prompt — always injected, every message
        if profile:
            stats = profile.get("maxpreps_stats") or {}
            stats_str = ""
            if stats:
                season = profile.get("maxpreps_season", "")
                stats_str = f"\n  MaxPreps stats ({season} season): " + ", ".join(f"{k}: {v}" for k, v in stats.items())
            combine = profile.get("combine_metrics")
            combine_str = ""
            if combine and isinstance(combine, dict):
                try:
                    cm = json.loads(combine) if isinstance(combine, str) else combine
                    parts = [f"{k.replace('_', ' ')}: {v}" for k, v in cm.items() if v]
                    if parts:
                        combine_str = "\n  Combine metrics: " + ", ".join(parts)
                except Exception:
                    pass
            results_str = format_for_prompt(profile.get("combine_results") or [])
            goals = profile.get("recruiting_goals")
            goals_str = ""
            if goals:
                try:
                    g = json.loads(goals) if isinstance(goals, str) else goals
                    goals_str = f"\n  Recruiting goals: {json.dumps(g)}"
                except Exception:
                    pass

            athlete_context = f"""

CURRENT ATHLETE PROFILE (use this — do not ask for info you already have):
  Name: {profile.get("name") or "Unknown"}
  Sport/Position: {profile.get("sport") or profile.get("position") or "Unknown"}
  School: {profile.get("school") or "Unknown"}
  Class year: {profile.get("class_year") or "Unknown"}
  State: {profile.get("state") or "Unknown"}
  GPA: {profile.get("gpa") or "not provided"}{stats_str}{combine_str}{results_str}{goals_str}
"""
        else:
            athlete_context = ""

        system_with_profile = SYSTEM_PROMPT + athlete_context
        if fork_scenario:
            system_with_profile += f"\n\nHYPOTHETICAL SCENARIO (the athlete is exploring this what-if — adjust all advice accordingly): {fork_scenario}"

        messages = history + [{"role": "user", "content": message}]

        # Agentic loop — continues until end_turn
        # web_search is native: Anthropic executes it server-side within the stream,
        # result blocks come back automatically, stop_reason stays "end_turn"
        # Current-athlete data is a fixed request snapshot, not a new database query.
        pending_tool_results = []

        iterations = 0
        while iterations < MAX_AGENT_ITERATIONS:
            iterations += 1
            if pending_tool_results:
                messages.append({"role": "user", "content": pending_tool_results})
                pending_tool_results = []

            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=system_with_profile,
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
                            elif tool_name == CURRENT_ATHLETE_TOOL["name"]:
                                yield f"data: {json.dumps({'type': 'tool', 'label': 'Reviewing your athlete profile...'})}\n\n"

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
                    if not is_demo:
                        _save_message(athlete_id, "assistant", current_text, conversation_id=conversation_id)
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return

                elif final_message.stop_reason == "tool_use":
                    # Only our typed current-athlete tool requires local handling.
                    # web_search_20250305 is server-side — skip it here
                    for block in assistant_content:
                        if not (hasattr(block, "type") and block.type == "tool_use"):
                            continue
                        result = current_athlete_tool_result(block.name, block.input, profile, is_demo=is_demo)
                        pending_tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                            "is_error": "error" in result,
                        })
                        # web_search_20250305: server-side, no tool_result needed from us

                    if not pending_tool_results:
                        # No custom tools to handle — done
                        if not is_demo:
                            _save_message(athlete_id, "assistant", current_text, conversation_id=conversation_id)
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        return
                    # Loop continues with the scoped tool result.
                else:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return

        # Iteration cap reached — persist what we have and close out cleanly.
        if not is_demo and current_text:
            _save_message(athlete_id, "assistant", current_text, conversation_id=conversation_id)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    async def generate_with_errors():
        try:
            async for event in generate():
                yield event
        except HTTPException as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc.detail)})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'type': 'error', 'error': 'The response could not be completed. Please try again.'})}\n\n"

    return StreamingResponse(
        generate_with_errors(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/agent/chat")
async def chat_agent(request: dict, caller_id: str = Depends(require_identity)):
    """Non-streaming legacy endpoint."""
    athlete_id = str(request.get("athlete_id", ""))
    if athlete_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized for this athlete.")
    message = request.get("message", "")
    conversation_id = _conversation_id(request.get("conversation_id"))
    if conversation_id is not None:
        _require_conversation_owner(caller_id, conversation_id)
    history = _load_conversation(caller_id, conversation_id)
    conversation_id = _save_message(caller_id, "user", message, conversation_id)

    profile = _load_athlete_profile(caller_id)
    profile_context = f"\n\nAthlete profile:\n{json.dumps(profile, default=str)}\n" if profile else ""
    messages = history + [{"role": "user", "content": message}]
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    full_text = ""
    pending_tool_results = []

    iterations = 0
    while iterations < MAX_AGENT_ITERATIONS:
        iterations += 1
        if pending_tool_results:
            messages.append({"role": "user", "content": pending_tool_results})
            pending_tool_results = []

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT + profile_context,
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
                    result = current_athlete_tool_result(block.name, block.input, profile)
                    pending_tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                        "is_error": "error" in result,
                    })
            if not pending_tool_results:
                break
        else:
            break

    _save_message(caller_id, "assistant", full_text, conversation_id)
    return {
        "session_id": str(conversation_id),
        "response": full_text,
        "tools_used": [],
        "steps": [],
    }


# ── Session Forking ────────────────────────────────────────────────────────────

@router.post("/api/agent/fork")
async def fork_session(request: dict, caller_id: str = Depends(require_identity)):
    """Copy one owned parent atomically. Schema changes belong in a separate migration."""
    athlete_id = str(request.get("athlete_id", ""))
    if athlete_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized for this athlete.")
    scenario = str(request.get("scenario", "")).strip()[:500]
    parent_conv_id = _conversation_id(request.get("parent_conversation_id"))
    if not scenario:
        raise HTTPException(status_code=400, detail="A What-If scenario is required.")

    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            parent_id = parent_conv_id if parent_conv_id is not None else _default_conversation_id(c, athlete_id)
            if parent_id is None:
                raise HTTPException(status_code=404, detail="Start a conversation before creating a What-If fork.")
            # Hold the parent through creation and copying. A foreign or missing
            # explicit ID is an error, never an empty newly-created conversation.
            c.execute("SELECT clerk_id FROM agent_conversations WHERE id = %s FOR UPDATE", (parent_id,))
            parent = c.fetchone()
            assert_owner(parent.get("clerk_id") if parent else None, athlete_id)
            c.execute(
                "INSERT INTO agent_conversations (clerk_id, fork_scenario, parent_id, created_at, updated_at) VALUES (%s, %s, %s, NOW(), NOW())",
                (athlete_id, scenario, parent_id),
            )
            fork_conv_id = c.lastrowid
            c.execute(
                """INSERT INTO agent_messages (conversation_id, role, content, created_at)
                   SELECT %s, am.role, am.content, am.created_at FROM agent_messages am
                   JOIN agent_conversations ac ON am.conversation_id = ac.id
                   WHERE ac.id = %s AND ac.clerk_id = %s ORDER BY am.id ASC""",
                (fork_conv_id, parent_id, athlete_id),
            )
        db.commit()
        return {"session_id": str(fork_conv_id), "fork_scenario": scenario}
    except HTTPException:
        if db:
            db.rollback()
        raise
    except Exception as exc:
        if db:
            db.rollback()
        # Some existing schemas still enforce one conversation per owner. Do not
        # mask that incompatibility as success or alter schema during a request.
        raise HTTPException(status_code=503, detail="What-If forks are unavailable. Your existing conversation is unchanged.") from exc
    finally:
        if db:
            db.close()
