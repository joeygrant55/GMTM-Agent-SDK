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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
import os
import json
import pymysql
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
load_dotenv()

router = APIRouter(prefix="/api", tags=["Artifacts"])


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
def get_inbox(clerk_id: str):
    """Triage queue — artifacts in ready_for_review for this athlete, newest first."""
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
def get_badges(clerk_id: str):
    """Sidebar badge counts: inbox unread, draft outreach, active agents."""
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
def get_artifact(artifact_id: int):
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
def approve_artifact(artifact_id: int, body: Optional[dict] = None):
    """Approve. Outreach drafts become 'sent', everything else becomes 'approved'."""
    performed_by = (body or {}).get("performed_by")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT type, state FROM artifacts WHERE id = %s", (artifact_id,))
            row = c.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="artifact not found")
            if row["state"] in ("sent", "approved", "archived", "rejected"):
                raise HTTPException(status_code=409, detail=f"artifact already {row['state']}")

            new_state = "sent" if row["type"] == "outreach_draft" else "approved"
            c.execute("UPDATE artifacts SET state = %s WHERE id = %s", (new_state, artifact_id))
            _record_action(c, artifact_id, "approve", performed_by, {"new_state": new_state})
        db.commit()
        return {"ok": True, "state": new_state}
    finally:
        db.close()


@router.post("/artifacts/{artifact_id}/discard")
def discard_artifact(artifact_id: int, body: Optional[dict] = None):
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
def edit_artifact(artifact_id: int, body: EditPayload):
    """Inline edit — overwrite payload, keep state, log the action."""
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
def iterate_artifact(artifact_id: int, body: IteratePayload):
    """Create a revision: new artifact row with parent_artifact_id set, same type, ready_for_review."""
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


# ---------- demo seeding (Phase 1 visible value before Coordinator is wired) ----------

@router.post("/artifacts/seed-demo/{clerk_id}")
def seed_demo_artifacts(clerk_id: str):
    """Seed the inbox with 3 demo artifacts so the V2 UX is demoable before Managed Agents lands."""
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
