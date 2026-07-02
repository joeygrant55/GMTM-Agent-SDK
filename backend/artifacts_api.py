"""
Artifacts API — V2 cowork canvas
================================

Endpoints powering the Inbox + Artifact Viewer flow:
- GET  /api/workspace/inbox/{clerk_id}    → triage queue (artifacts in ready_for_review)
- GET  /api/artifacts/{artifact_id}       → single artifact with payload + history
- POST /api/artifacts/{artifact_id}/approve → state -> approved (or sent for outreach)
- POST /api/artifacts/{artifact_id}/edit    → store inline edits, keep state
- POST /api/artifacts/{artifact_id}/iterate → create revision child via parent_artifact_id
- POST /api/artifacts/{artifact_id}/discard → state -> rejected
- POST /api/artifacts/seed-demo/{clerk_id}  → seeds 3 mock artifacts for the demo loop

Tables (artifacts, artifact_actions) created idempotently on import.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Any
import os
import json
import re
import pymysql
import anthropic
from datetime import datetime, timezone, date
from dotenv import load_dotenv

from email_sender import send_outreach_email, is_valid_email
from auth import require_clerk_id, assert_owner

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
load_dotenv()

router = APIRouter(prefix="/api", tags=["Artifacts"])


def _clerk_for_artifact(artifact_id: int) -> Optional[str]:
    """Return the clerk_id that owns an artifact, or None if it doesn't exist."""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT clerk_id FROM artifacts WHERE id = %s", (artifact_id,))
            row = c.fetchone()
            return row["clerk_id"] if row else None
    finally:
        db.close()


def _get_agent_db():
    return pymysql.connect(
        host=os.getenv('AGENT_DB_HOST', 'mysql.railway.internal'),
        port=int(os.getenv('AGENT_DB_PORT', '3306')),
        user=os.getenv('AGENT_DB_USER', 'root'),
        password=os.getenv('AGENT_DB_PASSWORD', ''),
        database=os.getenv('AGENT_DB_NAME', 'railway'),
        cursorclass=pymysql.cursors.DictCursor
    )


def _ensure_tables():
    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    clerk_id VARCHAR(255) NOT NULL,
                    type VARCHAR(40) NOT NULL,
                    state VARCHAR(40) NOT NULL DEFAULT 'draft',
                    agent_id VARCHAR(64) DEFAULT NULL,
                    parent_artifact_id INT DEFAULT NULL,
                    title VARCHAR(255) DEFAULT NULL,
                    summary TEXT DEFAULT NULL,
                    payload JSON,
                    sources JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_athlete_state_updated (clerk_id, state, updated_at),
                    INDEX idx_athlete_type (clerk_id, type),
                    INDEX idx_state_updated (state, updated_at)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS artifact_actions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    artifact_id INT NOT NULL,
                    kind VARCHAR(40) NOT NULL,
                    performed_by VARCHAR(64) DEFAULT NULL,
                    payload JSON,
                    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_artifact (artifact_id, performed_at)
                )
            """)
        db.commit()
    except Exception as e:
        print(f"⚠️ artifacts table creation warning: {e}")
    finally:
        if db:
            db.close()


_ensure_tables()


# ---------- helpers ----------

def _safe_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _row_to_artifact(row: dict) -> dict:
    return {
        "id": row["id"],
        "clerk_id": row["clerk_id"],
        "type": row["type"],
        "state": row["state"],
        "agent_id": row.get("agent_id"),
        "parent_artifact_id": row.get("parent_artifact_id"),
        "title": row.get("title"),
        "summary": row.get("summary"),
        "payload": _safe_json(row.get("payload")) or {},
        "sources": _safe_json(row.get("sources")) or [],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


def _record_action(c, artifact_id: int, kind: str, performed_by: Optional[str], payload: Optional[dict] = None) -> None:
    c.execute(
        "INSERT INTO artifact_actions (artifact_id, kind, performed_by, payload) VALUES (%s, %s, %s, %s)",
        (artifact_id, kind, performed_by, json.dumps(payload) if payload else None),
    )


# ---------- request models ----------

class EditPayload(BaseModel):
    payload: dict
    performed_by: Optional[str] = None


class IteratePayload(BaseModel):
    instruction: str
    payload: dict
    performed_by: Optional[str] = None


# ---------- endpoints ----------

@router.get("/workspace/inbox/{clerk_id}")
def get_inbox(clerk_id: str, caller_clerk_id: str = Depends(require_clerk_id)):
    """Triage queue — artifacts in ready_for_review for this athlete, newest first."""
    if clerk_id != caller_clerk_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                """
                SELECT id, clerk_id, type, state, agent_id, parent_artifact_id,
                       title, summary, payload, sources, created_at, updated_at
                FROM artifacts
                WHERE clerk_id = %s AND state = 'ready_for_review'
                ORDER BY updated_at DESC, id DESC
                LIMIT 50
                """,
                (clerk_id,),
            )
            rows = c.fetchall()
            return {"artifacts": [_row_to_artifact(r) for r in rows]}
    finally:
        db.close()


@router.get("/workspace/badges/{clerk_id}")
def get_badges(clerk_id: str, caller_clerk_id: str = Depends(require_clerk_id)):
    """Sidebar badge counts: inbox unread, draft outreach, active agents."""
    if clerk_id != caller_clerk_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT COUNT(*) AS n FROM artifacts WHERE clerk_id = %s AND state = 'ready_for_review'",
                (clerk_id,),
            )
            inbox = c.fetchone()["n"]
            c.execute(
                "SELECT COUNT(*) AS n FROM artifacts WHERE clerk_id = %s AND type = 'outreach_draft' AND state = 'ready_for_review'",
                (clerk_id,),
            )
            outreach_drafts = c.fetchone()["n"]
            return {
                "inbox": int(inbox or 0),
                "outreach_drafts": int(outreach_drafts or 0),
                "active_agents": 0,  # TODO Phase 3 — wire from Coordinator
            }
    finally:
        db.close()


@router.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: int, caller_clerk_id: str = Depends(require_clerk_id)):
    assert_owner(_clerk_for_artifact(artifact_id), caller_clerk_id)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                """
                SELECT id, clerk_id, type, state, agent_id, parent_artifact_id,
                       title, summary, payload, sources, created_at, updated_at
                FROM artifacts WHERE id = %s
                """,
                (artifact_id,),
            )
            row = c.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="artifact not found")
            artifact = _row_to_artifact(row)

            c.execute(
                """
                SELECT id, kind, performed_by, payload, performed_at
                FROM artifact_actions WHERE artifact_id = %s
                ORDER BY performed_at DESC, id DESC LIMIT 50
                """,
                (artifact_id,),
            )
            actions = [
                {
                    "id": a["id"],
                    "kind": a["kind"],
                    "performed_by": a.get("performed_by"),
                    "payload": _safe_json(a.get("payload")),
                    "performed_at": a["performed_at"].isoformat() if a.get("performed_at") else None,
                }
                for a in c.fetchall()
            ]
            artifact["actions"] = actions
            return artifact
    finally:
        db.close()


@router.post("/artifacts/{artifact_id}/approve")
def approve_artifact(artifact_id: int, body: Optional[dict] = None, caller_clerk_id: str = Depends(require_clerk_id)):
    """Approve.

    - Non-outreach artifacts → state 'approved'.
    - outreach_draft → attempt actual send via SendGrid:
        * success → 'sent' (real email out)
        * send infra not configured → 'queued' (logged in outreach_log for manual send)
        * invalid to_email or no payload → 'queued' (athlete approved, but can't send)
        * SendGrid/network error → 'send_failed' (transient — athlete can retry)
    The frontend passes athlete_email/athlete_name so coach replies route directly to the athlete
    via SendGrid's reply_to.
    """
    b = body or {}
    performed_by = b.get("performed_by")
    athlete_email = b.get("athlete_email")
    athlete_name = b.get("athlete_name")

    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT type, state, clerk_id, payload FROM artifacts WHERE id = %s",
                (artifact_id,),
            )
            row = c.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="artifact not found")
            assert_owner(row.get("clerk_id"), caller_clerk_id)
            if row["state"] in ("sent", "approved", "archived", "rejected"):
                raise HTTPException(status_code=409, detail=f"artifact already {row['state']}")

            if row["type"] != "outreach_draft":
                c.execute("UPDATE artifacts SET state = 'approved' WHERE id = %s", (artifact_id,))
                _record_action(c, artifact_id, "approve", performed_by, {"new_state": "approved"})
                db.commit()
                return {"ok": True, "state": "approved"}

            # outreach_draft path — try to actually send.
            payload = _safe_json(row.get("payload")) or {}
            to_email = (payload.get("to_email") or "").strip()
            to_name = payload.get("to_name") or None
            subject = payload.get("subject") or ""
            email_body = payload.get("body") or ""
            school = payload.get("school") or "Unknown School"
            coach = to_name

            if not is_valid_email(to_email) or not email_body.strip():
                new_state = "queued"
                action_meta = {
                    "new_state": new_state,
                    "reason": "missing_to_email" if not is_valid_email(to_email) else "empty_body",
                }
            else:
                result = send_outreach_email(
                    to_email=to_email,
                    to_name=to_name,
                    subject=subject,
                    body=email_body,
                    reply_to_email=athlete_email,
                    reply_to_name=athlete_name,
                )
                if result.get("ok"):
                    new_state = "sent"
                    action_meta = {
                        "new_state": new_state,
                        "message_id": result.get("message_id"),
                        "to_email": to_email,
                    }
                elif result.get("reason") == "send_infra_unconfigured":
                    new_state = "queued"
                    action_meta = {"new_state": new_state, "reason": "send_infra_unconfigured"}
                else:
                    new_state = "send_failed"
                    action_meta = {
                        "new_state": new_state,
                        "reason": result.get("reason"),
                        "status_code": result.get("status_code"),
                        "error": result.get("body") or result.get("error"),
                    }

            c.execute("UPDATE artifacts SET state = %s WHERE id = %s", (new_state, artifact_id))
            _record_action(c, artifact_id, "approve", performed_by, action_meta)

            # Mirror sent/queued outreach into outreach_log so the existing /home/outreach view sees it.
            if new_state in ("sent", "queued"):
                c.execute("SELECT id FROM sparq_profiles WHERE clerk_id = %s", (row["clerk_id"],))
                profile_row = c.fetchone()
                if profile_row:
                    log_notes = subject or None
                    if new_state == "queued":
                        log_notes = (log_notes or "") + " (queued — manual send needed)"
                    c.execute(
                        """
                        INSERT INTO outreach_log
                          (sparq_profile_id, school, coach, method, contact_date, status, notes)
                        VALUES (%s, %s, %s, 'Email', %s, 'Awaiting Response', %s)
                        """,
                        (
                            profile_row["id"],
                            school,
                            coach,
                            date.today().isoformat(),
                            log_notes,
                        ),
                    )

        db.commit()
        return {
            "ok": True,
            "state": new_state,
            "detail": action_meta if new_state != "sent" else None,
        }
    finally:
        db.close()


@router.post("/artifacts/{artifact_id}/discard")
def discard_artifact(artifact_id: int, body: Optional[dict] = None, caller_clerk_id: str = Depends(require_clerk_id)):
    assert_owner(_clerk_for_artifact(artifact_id), caller_clerk_id)
    performed_by = (body or {}).get("performed_by")
    reason = (body or {}).get("reason")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("UPDATE artifacts SET state = 'rejected' WHERE id = %s", (artifact_id,))
            _record_action(c, artifact_id, "reject", performed_by, {"reason": reason} if reason else None)
        db.commit()
        return {"ok": True, "state": "rejected"}
    finally:
        db.close()


@router.post("/artifacts/{artifact_id}/edit")
def edit_artifact(artifact_id: int, body: EditPayload, caller_clerk_id: str = Depends(require_clerk_id)):
    """Inline edit — overwrite payload, keep state, log the action."""
    assert_owner(_clerk_for_artifact(artifact_id), caller_clerk_id)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id FROM artifacts WHERE id = %s", (artifact_id,))
            if not c.fetchone():
                raise HTTPException(status_code=404, detail="artifact not found")
            c.execute(
                "UPDATE artifacts SET payload = %s WHERE id = %s",
                (json.dumps(body.payload), artifact_id),
            )
            _record_action(c, artifact_id, "edit", body.performed_by, None)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/artifacts/{artifact_id}/iterate")
def iterate_artifact(artifact_id: int, body: IteratePayload, caller_clerk_id: str = Depends(require_clerk_id)):
    """Create a revision: new artifact row with parent_artifact_id set, same type, ready_for_review."""
    assert_owner(_clerk_for_artifact(artifact_id), caller_clerk_id)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                """
                SELECT clerk_id, type, agent_id, title, summary, sources
                FROM artifacts WHERE id = %s
                """,
                (artifact_id,),
            )
            parent = c.fetchone()
            if not parent:
                raise HTTPException(status_code=404, detail="parent artifact not found")

            c.execute(
                """
                INSERT INTO artifacts
                  (clerk_id, type, state, agent_id, parent_artifact_id, title, summary, payload, sources)
                VALUES (%s, %s, 'ready_for_review', %s, %s, %s, %s, %s, %s)
                """,
                (
                    parent["clerk_id"],
                    parent["type"],
                    parent.get("agent_id"),
                    artifact_id,
                    parent.get("title"),
                    parent.get("summary"),
                    json.dumps(body.payload),
                    parent.get("sources") or json.dumps([]),
                ),
            )
            new_id = c.lastrowid
            _record_action(c, artifact_id, "iterate", body.performed_by, {"instruction": body.instruction, "child_id": new_id})
        db.commit()
        return {"ok": True, "child_id": new_id}
    finally:
        db.close()


# ---------- agent-driven endpoints (the "real" wiring) ----------

ANTHROPIC_MODEL = "claude-sonnet-4-6"

ITERATE_SYSTEM = """You revise an athlete's recruiting artifact in place.

You will be given:
- The current artifact payload as JSON
- A natural-language instruction from the athlete

Respond with ONLY valid JSON in this exact shape — no preamble, no code fences, no commentary:
{
  "updated_payload": { ...the full artifact payload with the athlete's instruction applied... },
  "explanation": "one short sentence describing what you changed and why"
}

Rules:
- Preserve the existing top-level keys of the payload. Only modify what the instruction asks for.
- Keep the athlete's voice — concise, confident, factual. Don't add hype or filler.
- If the instruction is ambiguous, pick the most reasonable interpretation and note it in explanation.
- Never invent facts about coaches, programs, or schedules. Only use what's in the payload or trim/rephrase what's there.
"""

DRAFT_OUTREACH_SYSTEM = """You draft a high-quality cold outreach email from a high-school athlete to a college coach.

You will be given the athlete's full profile and the target college's research data. Use both — every email should reference at least one specific detail about the program (recent recruiting, depth chart, position need) and at least one specific stat the athlete has.

Respond with ONLY valid JSON in this exact shape — no preamble, no code fences, no commentary:
{
  "to_name": "Coach <Last Name>",
  "to_email": "<email or empty string if unknown>",
  "school": "<full school name>",
  "subject": "<short, specific subject line — class year + position + the hook>",
  "body": "<150-220 word email body — opens with a specific personal observation about the program, states 1-2 measurable stats, asks one clear next step (camp, film review, questionnaire). Sign with the athlete's first name only.>",
  "personalization_notes": ["<3-5 short bullets describing the specific things you used from the program and the athlete to personalize this draft>"]
}

Rules:
- Never invent coach names, emails, or facts. If the position coach name isn't provided, address the head coach. If no email is available, return "" for to_email.
- Body must be one block of plain text with \\n\\n between paragraphs.
- Avoid clichés (\"I am writing to express my interest…\"). Open with a real observation.
- Stay under 220 words in the body.
"""


def _strip_code_fences(text: str) -> str:
    if not text:
        return text
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    return text


def _parse_json_response(text: str) -> Optional[dict]:
    text = _strip_code_fences(text)
    try:
        return json.loads(text)
    except Exception:
        # Last-resort recovery — find the outermost JSON object.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
    return None


def _claude_json(system: str, user: str, max_tokens: int = 2048) -> Optional[dict]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text_chunks = [b.text for b in response.content if hasattr(b, "text")]
    return _parse_json_response("".join(text_chunks))


class IterateViaAgentBody(BaseModel):
    instruction: str
    performed_by: Optional[str] = None


@router.post("/artifacts/{artifact_id}/iterate-via-agent")
def iterate_artifact_via_agent(artifact_id: int, body: IterateViaAgentBody, caller_clerk_id: str = Depends(require_clerk_id)):
    """Mode B chat → Claude rewrites the artifact payload per the instruction. Creates a revision."""
    assert_owner(_clerk_for_artifact(artifact_id), caller_clerk_id)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                """
                SELECT id, clerk_id, type, agent_id, title, summary, payload, sources
                FROM artifacts WHERE id = %s
                """,
                (artifact_id,),
            )
            parent = c.fetchone()
            if not parent:
                raise HTTPException(status_code=404, detail="artifact not found")
    finally:
        db.close()

    current_payload = _safe_json(parent.get("payload")) or {}
    user_message = (
        f"Artifact type: {parent['type']}\n\n"
        f"Current payload:\n{json.dumps(current_payload, indent=2)}\n\n"
        f"Athlete instruction: {body.instruction}"
    )

    parsed = _claude_json(ITERATE_SYSTEM, user_message, max_tokens=2048)
    if not parsed or not isinstance(parsed.get("updated_payload"), dict):
        raise HTTPException(status_code=502, detail="agent returned an unparseable response")

    new_payload = parsed["updated_payload"]
    explanation = parsed.get("explanation") or "Updated."

    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                """
                INSERT INTO artifacts
                  (clerk_id, type, state, agent_id, parent_artifact_id, title, summary, payload, sources)
                VALUES (%s, %s, 'ready_for_review', %s, %s, %s, %s, %s, %s)
                """,
                (
                    parent["clerk_id"],
                    parent["type"],
                    parent.get("agent_id"),
                    artifact_id,
                    parent.get("title"),
                    parent.get("summary"),
                    json.dumps(new_payload),
                    parent.get("sources") or json.dumps([]),
                ),
            )
            child_id = c.lastrowid
            _record_action(
                c,
                artifact_id,
                "iterate_via_agent",
                body.performed_by,
                {"instruction": body.instruction, "child_id": child_id, "explanation": explanation},
            )
            # Mark the parent artifact as 'archived' so the inbox shows only the latest revision.
            c.execute("UPDATE artifacts SET state = 'archived' WHERE id = %s", (artifact_id,))
        db.commit()
    finally:
        db.close()

    return {
        "ok": True,
        "child_id": child_id,
        "explanation": explanation,
    }


# ---------- on-demand outreach draft generation ----------

class DraftOutreachBody(BaseModel):
    athlete_id: str
    college_target_id: Optional[int] = None
    college_name: Optional[str] = None
    coach_name: Optional[str] = None
    coach_email: Optional[str] = None
    division: Optional[str] = None
    state: Optional[str] = None


def _load_athlete_profile_for_artifacts(athlete_id: str) -> Optional[dict]:
    """Lightweight athlete profile load — mirrors agent_api._load_athlete_profile but local to avoid cross-router import."""
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute("SELECT * FROM sparq_profiles WHERE clerk_id = %s", (athlete_id,))
            profile = c.fetchone()
        db.close()
        if not profile:
            return None
        maxpreps_raw = profile.get("maxpreps_data")
        maxpreps = {}
        if maxpreps_raw:
            try:
                maxpreps = json.loads(maxpreps_raw) if isinstance(maxpreps_raw, str) else maxpreps_raw
            except Exception:
                pass
        stats_preview = maxpreps.get("statsPreview") or []
        last_season = maxpreps.get("lastSeason")
        sport = maxpreps.get("sport") or profile.get("position")
        return {
            "name": profile.get("name"),
            "position": profile.get("position"),
            "sport": sport,
            "school": profile.get("school"),
            "class_year": profile.get("class_year"),
            "state": profile.get("state"),
            "gpa": str(profile.get("gpa")) if profile.get("gpa") else None,
            "recruiting_goals": _safe_json(profile.get("recruiting_goals")),
            "combine_metrics": _safe_json(profile.get("combine_metrics")),
            "stats": {s[0]: s[1] for s in stats_preview} if stats_preview else None,
            "season": last_season,
        }
    except Exception:
        return None


def _load_college_target(college_target_id: int) -> Optional[dict]:
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                """
                SELECT id, college_name, college_city, college_state, division, fit_score,
                       fit_reasons, research_data
                FROM college_targets WHERE id = %s
                """,
                (college_target_id,),
            )
            row = c.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "college_name": row["college_name"],
                "city": row.get("college_city"),
                "state": row.get("college_state"),
                "division": row.get("division"),
                "fit_score": row.get("fit_score"),
                "fit_reasons": _safe_json(row.get("fit_reasons")),
                "research": _safe_json(row.get("research_data")),
            }
    finally:
        db.close()


@router.post("/artifacts/draft-outreach")
def draft_outreach(body: DraftOutreachBody, caller_clerk_id: str = Depends(require_clerk_id)):
    """Generate a real outreach_draft artifact for the athlete + college via Claude."""
    if body.athlete_id != caller_clerk_id:
        raise HTTPException(status_code=403, detail="Not authorized for this athlete.")
    profile = _load_athlete_profile_for_artifacts(body.athlete_id)
    if not profile:
        raise HTTPException(status_code=404, detail="athlete profile not found")

    college: dict = {}
    if body.college_target_id:
        loaded = _load_college_target(body.college_target_id)
        if loaded:
            college = loaded
    # Fallback to inline fields if no target row.
    if not college.get("college_name"):
        college["college_name"] = body.college_name or "Target College"
    if body.division and not college.get("division"):
        college["division"] = body.division
    if body.state and not college.get("state"):
        college["state"] = body.state

    research = college.get("research") or {}
    coach_email = body.coach_email or research.get("coaching_staff", {}).get("contact_email") or ""
    head_coach = research.get("coaching_staff", {}).get("head_coach", {}).get("name")
    position_coach = research.get("coaching_staff", {}).get("position_coach", {}).get("name")
    coach_name = body.coach_name or position_coach or head_coach or ""

    user_message = (
        "ATHLETE PROFILE\n"
        f"{json.dumps(profile, default=str, indent=2)}\n\n"
        "TARGET PROGRAM\n"
        f"{json.dumps(college, default=str, indent=2)}\n\n"
        "ADDRESSEE\n"
        f"Coach name (if provided, use it; otherwise pick the most appropriate coach from the research): {coach_name or '(none)'}\n"
        f"Coach email (if known): {coach_email or '(none)'}\n"
    )

    parsed = _claude_json(DRAFT_OUTREACH_SYSTEM, user_message, max_tokens=2048)
    if not parsed or not parsed.get("body"):
        raise HTTPException(status_code=502, detail="agent did not return a usable draft")

    title = f"Outreach draft: {parsed.get('to_name') or 'Coach'} @ {college.get('college_name')}"
    summary = (
        parsed.get("subject")
        or f"Personalized to {college.get('college_name')}"
    )
    sources = []
    if research:
        sources.append({"label": f"{college.get('college_name')} research data"})
    if profile.get("season"):
        sources.append({"label": f"Your {profile['season']} stats"})

    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                """
                INSERT INTO artifacts
                  (clerk_id, type, state, agent_id, title, summary, payload, sources)
                VALUES (%s, 'outreach_draft', 'ready_for_review', 'drafter', %s, %s, %s, %s)
                """,
                (
                    body.athlete_id,
                    title,
                    summary,
                    json.dumps(parsed),
                    json.dumps(sources),
                ),
            )
            new_id = c.lastrowid
            _record_action(c, new_id, "generate", body.athlete_id, {"college_target_id": body.college_target_id})
        db.commit()
    finally:
        db.close()

    return {"ok": True, "artifact_id": new_id, "title": title}


# ---------- demo seeding (Phase 1 visible value before Coordinator is wired) ----------

@router.post("/artifacts/seed-demo/{clerk_id}")
def seed_demo_artifacts(clerk_id: str, caller_clerk_id: str = Depends(require_clerk_id)):
    """Seed the inbox with 3 demo artifacts so the V2 UX is demoable before Managed Agents lands."""
    if clerk_id != caller_clerk_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    now = datetime.now(timezone.utc).isoformat()
    demos = [
        {
            "type": "outreach_draft",
            "agent_id": "drafter",
            "title": "Outreach draft: Coach Smith @ Rutgers",
            "summary": "Personalized to their 2026 OL class and your 5.1 forty.",
            "payload": {
                "to_name": "Coach Smith",
                "to_email": "coach.smith@rutgers.edu",
                "school": "Rutgers University",
                "subject": "2027 OL — film + spring update",
                "body": (
                    "Coach Smith,\n\n"
                    "I caught your halftime adjustment at the spring game vs Penn State — "
                    "the way you stunted the interior on third-and-medium is exactly the kind of "
                    "scheme I want to play in.\n\n"
                    "I'm a 2027 OL out of [Your School] (3.9 GPA, 5.1 40, 305lbs). My junior film "
                    "is at the link below. I'd love to know what your '26 class is looking for at "
                    "tackle, and whether you'll be at the June camp circuit.\n\n"
                    "Film: https://hudl.com/profile/[your-link]\n\n"
                    "Thanks for your time, Coach.\n\n"
                    "— Joey Brown"
                ),
                "personalization_notes": [
                    "their 2026 OL class profile",
                    "your 5.1 forty",
                    "spring showcase note",
                ],
            },
            "sources": [
                {"label": "rutgers.edu/recruiting", "url": "https://rutgers.edu/recruiting"},
                {"label": "PennLive 4/22", "url": "https://pennlive.com/"},
            ],
        },
        {
            "type": "research_brief",
            "agent_id": "scout",
            "title": "Penn State just opened a 2027 OL spot",
            "summary": "Coach Trautwein flagged a portal departure yesterday. Your 88% fit puts you in the watch range.",
            "payload": {
                "school": "Penn State",
                "headline": "2027 OL spot opened",
                "body": (
                    "Penn State lost OT [Player] to the portal yesterday. "
                    "Coach Trautwein has been active on Twitter looking for replacement film. "
                    "Your size (6'4 / 305) and 5.1 forty fit their template — "
                    "they recruited two OLs in the 5.0–5.2 range last cycle."
                ),
                "next_actions": [
                    "Send Coach Trautwein your latest film by Friday",
                    "Mention the spring game adjustment Drafter pulled into your Rutgers email — same coaching staff move",
                ],
            },
            "sources": [
                {"label": "pennstate.edu/recruiting", "url": "https://pennstate.edu/recruiting"},
                {"label": "247sports — PSU portal tracker", "url": "https://247sports.com/"},
            ],
        },
        {
            "type": "honest_assessment",
            "agent_id": "analyst",
            "title": "Weekly honest assessment: your D1 path narrows",
            "summary": "12 D1 schools tracked → 2 realistic this cycle. Plan B (D2/D3) options up 40% in fit since April.",
            "payload": {
                "verdict": "Your D1 path is narrowing. Here's what the data says.",
                "percentile_bars": [
                    {"label": "Height", "value": 72, "warn": False},
                    {"label": "40 time", "value": 31, "warn": True, "note": "below D1 median"},
                    {"label": "Bench", "value": 54, "warn": False},
                    {"label": "Camp count", "value": 18, "warn": True, "note": "low exposure"},
                ],
                "reality_check": (
                    "Of the 12 D1 schools you track, 2 are realistic this cycle (Rutgers, Buffalo). "
                    "10 are reaches without a faster 40 by July."
                ),
                "plan_b": (
                    "D2/D3 fit grew from 4 → 11 strong matches since April. "
                    "Three schools (Bloomsburg, Kutztown, Shippensburg) actively recruiting your profile."
                ),
                "one_action": "Get to a Rivals camp before July 1.",
            },
            "sources": [
                {"label": "247sports class trends"},
                {"label": "your activity log"},
                {"label": "38 fit calcs"},
            ],
        },
    ]

    db = _get_agent_db()
    inserted = 0
    try:
        with db.cursor() as c:
            # Don't double-seed — bail if any ready_for_review already exists for this athlete
            c.execute(
                "SELECT COUNT(*) AS n FROM artifacts WHERE clerk_id = %s AND state = 'ready_for_review'",
                (clerk_id,),
            )
            if (c.fetchone() or {}).get("n", 0) > 0:
                return {"ok": True, "inserted": 0, "skipped": True}

            for d in demos:
                c.execute(
                    """
                    INSERT INTO artifacts
                      (clerk_id, type, state, agent_id, title, summary, payload, sources)
                    VALUES (%s, %s, 'ready_for_review', %s, %s, %s, %s, %s)
                    """,
                    (
                        clerk_id,
                        d["type"],
                        d["agent_id"],
                        d["title"],
                        d["summary"],
                        json.dumps(d["payload"]),
                        json.dumps(d["sources"]),
                    ),
                )
                inserted += 1
        db.commit()
        return {"ok": True, "inserted": inserted, "seeded_at": now}
    finally:
        db.close()
