"""
Profile & Links API - Athlete dashboard data
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import threading
import pymysql

from combine_results import get_combine_results
from auth import require_identity, assert_owner


router = APIRouter(prefix="/api", tags=["Profile"])


# ── Ownership resolvers ─────────────────────────────────────────────────────
# Map an internal resource id back to the clerk_id that owns it, so endpoints
# keyed by integer id can enforce that the caller owns the row before acting.

def _owner_for_gmtm_user(user_id: int) -> Optional[str]:
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT clerk_id FROM athlete_profiles WHERE user_id = %s", (user_id,))
            row = c.fetchone()
            return row["clerk_id"] if row else None
    finally:
        db.close()


def _owner_for_profile_id(profile_id: int) -> Optional[str]:
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT clerk_id FROM sparq_profiles WHERE id = %s", (profile_id,))
            row = c.fetchone()
            return row["clerk_id"] if row else None
    finally:
        db.close()


def _owner_for_college_target(target_id: int) -> Optional[str]:
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                """SELECT sp.clerk_id FROM college_targets ct
                   JOIN sparq_profiles sp ON sp.id = ct.sparq_profile_id
                   WHERE ct.id = %s""",
                (target_id,),
            )
            row = c.fetchone()
            return row["clerk_id"] if row else None
    finally:
        db.close()


def _owner_for_outreach_entry(entry_id: int) -> Optional[str]:
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                """SELECT sp.clerk_id FROM outreach_log ol
                   JOIN sparq_profiles sp ON sp.id = ol.sparq_profile_id
                   WHERE ol.id = %s""",
                (entry_id,),
            )
            row = c.fetchone()
            return row["clerk_id"] if row else None
    finally:
        db.close()


def _owner_for_link(link_id: int) -> Optional[str]:
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT user_id FROM athlete_links WHERE id = %s", (link_id,))
            row = c.fetchone()
    finally:
        db.close()
    if not row:
        return None
    return _owner_for_gmtm_user(row["user_id"])


# Match the combine connectors: bound socket connection and individual I/O
# operations. These are not DNS, server execution, or whole-request deadlines.
def _get_agent_db():
    return pymysql.connect(
        host=os.getenv('AGENT_DB_HOST', 'mysql.railway.internal'),
        port=int(os.getenv('AGENT_DB_PORT', '3306')),
        user=os.getenv('AGENT_DB_USER', 'root'),
        password=os.getenv('AGENT_DB_PASSWORD', ''),
        database=os.getenv('AGENT_DB_NAME', 'railway'),
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5, read_timeout=10, write_timeout=10,
    )


def _get_gmtm_db():
    """Read-only connection to GMTM database"""
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database='gmtm',
        port=3306,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5, read_timeout=10, write_timeout=10,
    )


def _generate_fit_preview(college: dict, profile: dict) -> list[str]:
    """Generate instant fit reasons from existing DB data (no AI needed)."""
    reasons: list[str] = []
    position = str(profile.get("position") or "athlete").strip()

    div = str(college.get("division") or "").strip()
    if div:
        reasons.append(f"{div} program actively recruiting {position}s")

    college_city = str(college.get("college_city") or "").strip()
    college_state = str(college.get("college_state") or "").strip()
    target_geo = str(profile.get("target_geography") or "Anywhere").strip()
    athlete_state = str(profile.get("state") or "").strip()

    if target_geo == "Anywhere":
        reasons.append("Matches your open geography preference")
    elif target_geo == "In-state" and college_state and athlete_state and college_state == athlete_state:
        reasons.append(f"In-state program — {college_state}")
    elif college_city or college_state:
        reasons.append(f"Located in {', '.join([v for v in [college_city, college_state] if v])}")

    grad_year = profile.get("grad_year") or profile.get("class_year")
    if grad_year:
        reasons.append(f"Recruiting the Class of {grad_year}")

    return reasons[:3]


# ── Models ──────────────────────────────

class LinkCreate(BaseModel):
    user_id: int
    platform: str
    url: str
    label: Optional[str] = None


class LinkUpdate(BaseModel):
    platform: Optional[str] = None
    url: Optional[str] = None
    label: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str


class OutreachCreate(BaseModel):
    school: str
    coach: Optional[str] = None
    method: str = "Email"
    contact_date: str
    status: str = "Awaiting Response"
    notes: Optional[str] = None


class OutreachStatusUpdate(BaseModel):
    status: str


# ── Dashboard endpoint ──────────────────


def _run_matching_thread(pid, profile, pos, st, sport):
    """Standalone thread target for AI college matching + enrichment."""
    import asyncio as _aio, traceback as _tb
    from enrichment_worker import ai_match_programs_sync, enrich_college_targets, _get_agent_db as _edb
    try:
        print(f"[Matching] Thread started: profile {pid} | {sport} {pos} from {st}")
        programs = ai_match_programs_sync(profile)
        if not programs:
            print(f"[Matching] No programs returned for profile {pid}")
            return
        db2 = _edb()
        try:
            with db2.cursor() as c2:
                c2.execute("DELETE FROM college_targets WHERE sparq_profile_id = %s", (pid,))
                for prog in programs:
                    fit_score = max(65, min(95, int(prog.get("fit_score") or 75)))
                    fit_summary = prog.get("fit_summary") or ""
                    source_url = prog.get("source_url") or ""
                    research_seed = {"matching_source_url": source_url} if source_url else {}
                    c2.execute("""
                        INSERT INTO college_targets
                            (sparq_profile_id, college_name, college_city, college_state,
                             division, fit_score, fit_reasons, research_data)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (pid, prog.get("name","Unknown"), prog.get("city",""),
                          prog.get("state",""), prog.get("division") or "D1",
                          fit_score, json.dumps([fit_summary] if fit_summary else []),
                          json.dumps(research_seed) if research_seed else None))
            db2.commit()
            print(f"[Matching] Stored {len(programs)} verified colleges for profile {pid}")
        finally:
            db2.close()
        _aio.run(enrich_college_targets(
            sparq_profile_id=pid, athlete_position=pos,
            athlete_state=st, athlete_sport=sport,
        ))
    except Exception as e:
        print(f"[Matching] Thread error: {e}")
        _tb.print_exc()

@router.get("/dashboard/{user_id}")
async def get_dashboard(user_id: int, caller_id: str = Depends(require_identity)):
    """Full dashboard data: profile + metrics + links + recent chats"""
    assert_owner(_owner_for_gmtm_user(user_id), caller_id)
    gmtm = _get_gmtm_db()
    agent_db = _get_agent_db()
    
    try:
        with gmtm.cursor() as c:
            # Get athlete profile from GMTM (READ ONLY)
            c.execute("""
                SELECT u.user_id, u.first_name, u.last_name, u.email,
                       l.city, l.province as state
                FROM users u
                LEFT JOIN locations l ON u.location_id = l.location_id
                WHERE u.user_id = %s
            """, (user_id,))
            profile = c.fetchone()
            
            if not profile:
                raise HTTPException(status_code=404, detail="Athlete not found")
            
            # Get position
            c.execute("""
                SELECT p.name as position
                FROM career c
                JOIN user_positions up ON up.career_id = c.career_id
                JOIN positions p ON up.position_id = p.position_id
                WHERE c.user_id = %s AND up.is_primary = 1
                LIMIT 1
            """, (user_id,))
            pos = c.fetchone()
            profile['position'] = pos['position'] if pos else 'N/A'
            
            # Get key metrics
            c.execute("""
                SELECT title, value, unit, verified
                FROM metrics
                WHERE user_id = %s AND is_current = 1
                AND title IN ('Height', 'Weight', '40 Yard Dash', 'Vertical Jump', 
                             'Bench Press', 'Squat', '5-10-5 shuttle', 'Broad Jump',
                             'Rivals.com Stars', '247Sports.com Stars')
                ORDER BY title
            """, (user_id,))
            metrics = c.fetchall()
            
            # Get scholarship offers
            c.execute("""
                SELECT COUNT(*) as offer_count
                FROM scholarship_offers
                WHERE user_id = %s
            """, (user_id,))
            offers = c.fetchone()
        
        with agent_db.cursor() as c:
            # Get links
            c.execute("""
                SELECT id, platform, url, label, created_at
                FROM athlete_links
                WHERE user_id = %s
                ORDER BY platform
            """, (user_id,))
            links = c.fetchall()
            for link in links:
                link['created_at'] = str(link['created_at'])
            
            # Get recent conversations. Conversations are keyed by clerk_id (not the
            # GMTM user_id) and have no title column, so scope by the owner's clerk_id
            # and synthesize a title.
            c.execute("""
                SELECT ac.id, ac.updated_at,
                       (SELECT COUNT(*) FROM agent_messages WHERE conversation_id = ac.id) as message_count
                FROM agent_conversations ac
                WHERE ac.clerk_id = %s
                ORDER BY ac.updated_at DESC
                LIMIT 5
            """, (caller_id,))
            recent_chats = c.fetchall()
            for chat in recent_chats:
                chat['updated_at'] = str(chat['updated_at'])
                chat['title'] = 'Recruiting conversation'
        
        # Calculate profile completeness
        total_fields = 8  # metrics we care about + links
        filled = len([m for m in metrics if m['value']]) + min(len(links), 3)
        completeness = min(100, int((filled / total_fields) * 100))
        
        # Suggested links to add
        existing_platforms = {l['platform'] for l in links}
        all_platforms = ['hudl', 'twitter', 'instagram', 'maxpreps', '247sports', 'rivals', 'youtube', 'personal_website']
        missing_platforms = [p for p in all_platforms if p not in existing_platforms]
        
        try:
            combine_results = get_combine_results(user_id, _get_gmtm_db)
        except Exception:
            combine_results = []

        return {
            "profile": profile,
            "metrics": metrics,
            "combine_results": combine_results,
            "offer_count": offers['offer_count'],
            "links": links,
            "recent_chats": recent_chats,
            "completeness": completeness,
            "suggested_links": missing_platforms[:4],  # Top 4 suggestions
        }
    
    finally:
        gmtm.close()
        agent_db.close()


# ── Links CRUD ──────────────────────────

@router.get("/links/{user_id}")
async def get_links(user_id: int, caller_id: str = Depends(require_identity)):
    assert_owner(_owner_for_gmtm_user(user_id), caller_id)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id, platform, url, label FROM athlete_links WHERE user_id = %s ORDER BY platform", (user_id,))
            return {"links": c.fetchall()}
    finally:
        db.close()


@router.post("/links")
async def add_link(request: LinkCreate, caller_id: str = Depends(require_identity)):
    assert_owner(_owner_for_gmtm_user(request.user_id), caller_id)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "INSERT INTO athlete_links (user_id, platform, url, label) VALUES (%s, %s, %s, %s)",
                (request.user_id, request.platform, request.url, request.label)
            )
            db.commit()
            return {"id": c.lastrowid, "platform": request.platform, "url": request.url}
    finally:
        db.close()


@router.delete("/links/{link_id}")
async def delete_link(link_id: int, caller_id: str = Depends(require_identity)):
    assert_owner(_owner_for_link(link_id), caller_id)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("DELETE FROM athlete_links WHERE id = %s", (link_id,))
            db.commit()
            return {"deleted": True}
    finally:
        db.close()



@router.get("/profile/by-owner/{clerk_id}")
async def get_profile_by_owner(clerk_id: str, caller_id: str = Depends(require_identity)):
    """Read this caller's existing unique link/workspace, without creating either."""
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    conflict = "The existing account connection needs review before it can be recovered."

    def owned_id(row, key):
        # Owner identifiers are case-sensitive even if an older SQL collation
        # is not. Do not coerce malformed identity values into an apparent link.
        value = row.get(key) if isinstance(row, dict) else None
        if (type(value) is not int or value <= 0
                or row.get("clerk_id") != caller_id):
            raise HTTPException(status_code=409, detail=conflict)
        return value

    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute("SELECT user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2", (caller_id,))
            links = c.fetchall()
            if len(links) > 1:
                raise HTTPException(status_code=409, detail=conflict)
            user_id = owned_id(links[0], "user_id") if links else None
            if user_id is not None:
                c.execute("SELECT user_id, clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 2", (user_id,))
                owners = c.fetchall()
                if len(owners) != 1 or owned_id(owners[0], "user_id") != user_id:
                    raise HTTPException(status_code=409, detail=conflict)

            c.execute("SELECT id, clerk_id FROM sparq_profiles WHERE clerk_id = %s LIMIT 2", (caller_id,))
            workspaces = c.fetchall()
            if len(workspaces) > 1:
                raise HTTPException(status_code=409, detail=conflict)
            if workspaces:
                owned_id(workspaces[0], "id")
            return {"found": user_id is not None, "user_id": user_id, "has_sparq_profile": bool(workspaces)}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="The existing account connection could not be checked. Please try again.") from None
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                raise HTTPException(status_code=503, detail="The existing account connection could not be checked. Please try again.") from None



@router.get("/workspace/colleges/{clerk_id}")
async def get_college_targets(clerk_id: str, caller_id: str = Depends(require_identity)):
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT id, position, class_year, state, recruiting_goals FROM sparq_profiles WHERE clerk_id = %s",
                (clerk_id,),
            )
            profile = c.fetchone()
            if not profile:
                return {"colleges": [], "total": 0}
            recruiting_goals = profile.get("recruiting_goals")
            if isinstance(recruiting_goals, str):
                try:
                    recruiting_goals = json.loads(recruiting_goals)
                except Exception:
                    recruiting_goals = {}
            if not isinstance(recruiting_goals, dict):
                recruiting_goals = {}
            profile_data = {
                "position": profile.get("position"),
                "class_year": profile.get("class_year"),
                "grad_year": profile.get("class_year"),
                "state": profile.get("state"),
                "target_geography": recruiting_goals.get("geography", "Anywhere"),
            }
            c.execute("""
                SELECT id, college_name, college_city, college_state,
                       division, fit_score, fit_reasons, status
                FROM college_targets
                WHERE sparq_profile_id = %s
                ORDER BY fit_score DESC
            """, (profile["id"],))
            colleges = c.fetchall()
            for col in colleges:
                if isinstance(col.get("fit_reasons"), str):
                    try:
                        col["fit_reasons"] = json.loads(col["fit_reasons"])
                    except Exception:
                        col["fit_reasons"] = []
                if not isinstance(col.get("fit_reasons"), list) or len(col.get("fit_reasons") or []) == 0:
                    col["fit_reasons"] = _generate_fit_preview(col, profile_data)
            return {"colleges": colleges, "total": len(colleges)}
    finally:
        db.close()


@router.get("/workspace/enrichment-status/{clerk_id}")
async def get_enrichment_status(clerk_id: str, caller_id: str = Depends(require_identity)):
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id, enrichment_complete FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            profile = c.fetchone()
            if not profile:
                return {"complete": False, "colleges_researched": 0, "total": 0}

            c.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE
                        WHEN fit_reasons IS NOT NULL
                         AND JSON_LENGTH(fit_reasons) > 0
                        THEN 1 ELSE 0 END) AS colleges_researched
                FROM college_targets
                WHERE sparq_profile_id = %s
                """,
                (profile["id"],),
            )
            counts = c.fetchone() or {}
            total = int(counts.get("total") or 0)
            researched = int(counts.get("colleges_researched") or 0)
            complete = bool(profile.get("enrichment_complete")) or (total > 0 and researched >= total)
            return {"complete": complete, "colleges_researched": researched, "total": total}
    finally:
        db.close()


@router.put("/workspace/colleges/{college_target_id}/status")
async def update_college_status(college_target_id: int, body: StatusUpdate, caller_id: str = Depends(require_identity)):
    valid = {"Researching", "Interested", "Contacted", "Visited", "Offered", "Committed", "Declined"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail="Invalid status")
    assert_owner(_owner_for_college_target(college_target_id), caller_id)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "UPDATE college_targets SET status = %s WHERE id = %s",
                (body.status, college_target_id)
            )
        db.commit()
        return {"updated": True, "id": college_target_id, "status": body.status}
    finally:
        db.close()


@router.get("/workspace/outreach/{clerk_id}")
async def get_outreach_entries(clerk_id: str, caller_id: str = Depends(require_identity)):
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            profile = c.fetchone()
            if not profile:
                return {"entries": [], "total": 0}

            c.execute("""
                SELECT id, school, coach, method, contact_date, status, notes, created_at, updated_at
                FROM outreach_log
                WHERE sparq_profile_id = %s
                ORDER BY contact_date DESC, id DESC
            """, (profile["id"],))
            entries = c.fetchall()
            return {"entries": entries, "total": len(entries)}
    finally:
        db.close()


@router.post("/workspace/outreach/{clerk_id}")
async def create_outreach_entry(clerk_id: str, body: OutreachCreate, caller_id: str = Depends(require_identity)):
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    valid_methods = {"Email", "Phone", "Visit", "Camp"}
    valid_statuses = {"Awaiting Response", "Responded", "Meeting Scheduled", "Archived"}
    if body.method not in valid_methods:
        raise HTTPException(status_code=400, detail="Invalid method")
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            profile = c.fetchone()
            if not profile:
                raise HTTPException(status_code=404, detail="SPARQ profile not found")

            c.execute("""
                INSERT INTO outreach_log
                    (sparq_profile_id, school, coach, method, contact_date, status, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                profile["id"],
                body.school.strip(),
                body.coach.strip() if body.coach else None,
                body.method,
                body.contact_date,
                body.status,
                body.notes.strip() if body.notes else None,
            ))
            entry_id = c.lastrowid

            c.execute("""
                SELECT id, school, coach, method, contact_date, status, notes, created_at, updated_at
                FROM outreach_log
                WHERE id = %s
            """, (entry_id,))
            entry = c.fetchone()
        db.commit()
        return {"entry": entry, "id": entry_id}
    finally:
        db.close()


@router.put("/workspace/outreach/{entry_id}/status")
async def update_outreach_status(entry_id: int, body: OutreachStatusUpdate, caller_id: str = Depends(require_identity)):
    valid_statuses = {"Awaiting Response", "Responded", "Meeting Scheduled", "Archived"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    assert_owner(_owner_for_outreach_entry(entry_id), caller_id)

    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("UPDATE outreach_log SET status = %s WHERE id = %s", (body.status, entry_id))
        db.commit()
        return {"updated": True}
    finally:
        db.close()


@router.delete("/workspace/outreach/{entry_id}")
async def delete_outreach_entry(entry_id: int, caller_id: str = Depends(require_identity)):
    assert_owner(_owner_for_outreach_entry(entry_id), caller_id)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("DELETE FROM outreach_log WHERE id = %s", (entry_id,))
        db.commit()
        return {"deleted": True}
    finally:
        db.close()


@router.get("/workspace/stats/{clerk_id}")
async def get_workspace_stats(clerk_id: str, caller_id: str = Depends(require_identity)):
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    base_breakdown = {
        "Researching": 0,
        "Interested": 0,
        "Contacted": 0,
        "Offered": 0,
    }
    try:
        with db.cursor() as c:
            c.execute("SELECT id FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            profile = c.fetchone()
            if not profile:
                return {
                    "colleges_tracked": 0,
                    "outreach_sent": 0,
                    "responses": 0,
                    "college_breakdown": base_breakdown,
                }

            profile_id = profile["id"]
            c.execute("SELECT COUNT(*) AS total FROM college_targets WHERE sparq_profile_id = %s", (profile_id,))
            colleges_tracked = c.fetchone()["total"]

            c.execute("""
                SELECT status, COUNT(*) AS count
                FROM college_targets
                WHERE sparq_profile_id = %s
                  AND status IN ('Researching', 'Interested', 'Contacted', 'Offered')
                GROUP BY status
            """, (profile_id,))
            breakdown_rows = c.fetchall()
            college_breakdown = dict(base_breakdown)
            for row in breakdown_rows:
                college_breakdown[row["status"]] = row["count"]

            c.execute("""
                SELECT
                    COUNT(*) AS outreach_sent,
                    SUM(CASE WHEN status IN ('Responded', 'Meeting Scheduled') THEN 1 ELSE 0 END) AS responses
                FROM outreach_log
                WHERE sparq_profile_id = %s
            """, (profile_id,))
            outreach_row = c.fetchone() or {}

            return {
                "colleges_tracked": colleges_tracked or 0,
                "outreach_sent": outreach_row.get("outreach_sent") or 0,
                "responses": outreach_row.get("responses") or 0,
                "college_breakdown": college_breakdown,
            }
    finally:
        db.close()


@router.get("/workspace/timeline/{clerk_id}")
async def get_workspace_timeline(clerk_id: str, caller_id: str = Depends(require_identity)):
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id, created_at FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            profile = c.fetchone()
            if not profile:
                return []

            profile_id = profile["id"]
            events = []

            # Onboarding event
            events.append({
                "type": "onboarding",
                "date": str(profile["created_at"]),
                "title": "Started your SPARQ journey",
                "detail": None,
            })

            # Colleges added
            c.execute(
                "SELECT college_name, division, created_at FROM college_targets WHERE sparq_profile_id = %s ORDER BY created_at DESC",
                (profile_id,),
            )
            for row in c.fetchall():
                events.append({
                    "type": "college_added",
                    "date": str(row["created_at"]),
                    "title": f"Added {row['college_name']}",
                    "detail": row.get("division") or None,
                })

            # Outreach entries
            c.execute(
                "SELECT school, method, status, created_at FROM outreach_log WHERE sparq_profile_id = %s ORDER BY created_at DESC",
                (profile_id,),
            )
            for row in c.fetchall():
                events.append({
                    "type": "outreach_sent",
                    "date": str(row["created_at"]),
                    "title": f"Reached out to {row['school']}",
                    "detail": f"{row['method']} — {row['status']}",
                })

        # Sort all events newest first
        events.sort(key=lambda e: e["date"], reverse=True)
        return events
    finally:
        db.close()



@router.post("/workspace/trigger-matching/{clerk_id}")
async def trigger_matching(clerk_id: str, caller_id: str = Depends(require_identity)):
    """Manually re-trigger AI college matching for an existing profile."""
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT * FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            profile = c.fetchone()
    finally:
        db.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.get("clerk_id") != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")

    profile_id = profile["id"]
    position = profile.get("position") or "Athlete"
    state = profile.get("state") or "US"

    missing_sport = "College matching needs a sport in your recruiting profile. Your combine progress remains available."
    mp_raw = profile.get("maxpreps_data")
    try:
        maxpreps = json.loads(mp_raw) if isinstance(mp_raw, str) else mp_raw
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail=missing_sport) from None
    if not isinstance(maxpreps, dict):
        raise HTTPException(status_code=422, detail=missing_sport)

    def sport_text(value):
        if not isinstance(value, str) or any(ord(char) < 32 for char in value):
            return None
        label = value.strip()
        placeholders = {"all sports", "athlete", "unknown", "n/a", "na", "none", "null",
                        "not specified", "unspecified", "tbd", "other", "select sport"}
        return label if 0 < len(label) <= 100 and label.casefold() not in placeholders else None

    # Preserve the existing first-sport selection, including its gendered label.
    # A position or default sport cannot stand in for missing source sport data.
    sports = maxpreps.get("sports")
    if sports is not None and (not isinstance(sports, list) or any(not sport_text(value) for value in sports)):
        raise HTTPException(status_code=422, detail=missing_sport)
    sport_label = sport_text(sports[0]) if sports else sport_text(maxpreps.get("sport"))
    if not sport_label:
        raise HTTPException(status_code=422, detail=missing_sport)

    stats_preview = maxpreps.get("statsPreview") or []
    maxpreps_stats = {s[0]: s[1] for s in stats_preview} if stats_preview else {}

    goals = profile.get("recruiting_goals")
    if isinstance(goals, str):
        try:
            goals = json.loads(goals)
        except Exception:
            goals = {}

    athlete_profile = {
        "sport": sport_label,
        "position": position,
        "state": state,
        "class_year": maxpreps.get("classYear"),
        "maxpreps_stats": maxpreps_stats,
        "recruiting_goals": goals or {},
    }

    t = threading.Thread(
        target=_run_matching_thread,
        args=(profile_id, athlete_profile, position, state, sport_label),
        daemon=True, name=f"matching-trigger-{profile_id}"
    )
    t.start()
    print(f"[Matching] Trigger thread launched: {t.name}")
    return {"status": "matching started", "profile_id": profile_id, "sport": sport_label, "position": position}


@router.get("/workspace/profile/{clerk_id}")
async def get_profile(clerk_id: str, caller_id: str = Depends(require_identity)):
    """Return full sparq_profiles row for the workspace profile editor."""
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT * FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            row = c.fetchone()
    finally:
        db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Parse JSON columns
    for col in ("maxpreps_data", "combine_metrics", "recruiting_goals"):
        val = row.get(col)
        if isinstance(val, str):
            try:
                row[col] = json.loads(val)
            except Exception:
                row[col] = {}
        elif val is None:
            row[col] = {}

    # Combine results with ranks, for GMTM-linked athletes (claim link / legacy connect).
    row["combine_results"] = []
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute("SELECT user_id FROM athlete_profiles WHERE clerk_id = %s", (clerk_id,))
            link = c.fetchone()
        db.close()
        if link:
            row["combine_results"] = get_combine_results(int(link["user_id"]), _get_gmtm_db)
    except Exception:
        pass

    return row


class ProfileUpdatePayload(BaseModel):
    gpa: float | None = None
    majorArea: str | None = None
    hudlUrl: str | None = None
    combineMetrics: dict | None = None
    recruitingGoals: dict | None = None


@router.patch("/workspace/profile/{clerk_id}")
async def update_profile(clerk_id: str, payload: ProfileUpdatePayload, caller_id: str = Depends(require_identity)):
    """Update editable fields on an existing sparq_profile."""
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            row = c.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Profile not found")

            updates = []
            values = []

            if payload.gpa is not None:
                updates.append("gpa = %s"); values.append(payload.gpa)
            if payload.majorArea is not None:
                updates.append("major_area = %s"); values.append(payload.majorArea)
            if payload.hudlUrl is not None:
                updates.append("hudl_url = %s"); values.append(payload.hudlUrl or None)
            if payload.combineMetrics is not None:
                updates.append("combine_metrics = %s"); values.append(json.dumps(payload.combineMetrics))
            if payload.recruitingGoals is not None:
                updates.append("recruiting_goals = %s"); values.append(json.dumps(payload.recruitingGoals))

            if updates:
                values.append(clerk_id)
                c.execute(f"UPDATE sparq_profiles SET {', '.join(updates)} WHERE clerk_id = %s", values)
                db.commit()
    finally:
        db.close()

    return {"success": True}


@router.get("/workspace/colleges/{clerk_id}/{college_id}")
async def get_college_detail(clerk_id: str, college_id: int, caller_id: str = Depends(require_identity)):
    """Return full college target detail including research_data."""
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            profile = c.fetchone()
            if not profile:
                raise HTTPException(status_code=404, detail="Profile not found")

            c.execute("""
                SELECT ct.*, sp.maxpreps_data, sp.position, sp.state, sp.gpa, sp.major_area,
                       sp.recruiting_goals, sp.combine_metrics
                FROM college_targets ct
                JOIN sparq_profiles sp ON sp.id = ct.sparq_profile_id
                WHERE ct.id = %s AND ct.sparq_profile_id = %s
            """, (college_id, profile["id"]))
            row = c.fetchone()
    finally:
        db.close()

    if not row:
        raise HTTPException(status_code=404, detail="College not found")

    for col in ("fit_reasons", "research_data"):
        val = row.get(col)
        if isinstance(val, str):
            try:
                row[col] = json.loads(val)
            except Exception:
                row[col] = None

    for col in ("maxpreps_data", "recruiting_goals", "combine_metrics"):
        val = row.get(col)
        if isinstance(val, str):
            try:
                row[col] = json.loads(val)
            except Exception:
                row[col] = {}

    return row


DEEP_RESEARCH_SYSTEM = """You are an expert college athletic recruiting researcher.
Given an athlete profile and a college program, produce a deep research report.
Return ONLY a valid JSON object in this exact format:

{
  "coaching_staff": {
    "head_coach": {"name": "string or null", "years_at_school": "string", "bio": "1-2 sentences", "recruiting_style": "1-2 sentences on their recruiting philosophy and what they look for"},
    "position_coach": {"name": "string or null", "role": "string", "background": "1 sentence"},
    "contact_email": "email or null",
    "staff_note": "1 sentence on staff stability or recent changes"
  },
  "roster_fit": {
    "players_at_position": "estimated count or range",
    "graduating_seniors": "estimated count",
    "depth_chart_opportunity": "immediate starter / compete for playing time / developmental",
    "typical_commit_profile": "describe the type of athlete they typically recruit at this position",
    "roster_note": "1-2 sentences on roster dynamics relevant to this athlete"
  },
  "academic_fit": {
    "major_available": true or false,
    "major_name": "closest matching major name",
    "academic_profile": "GPA range of admitted athletes or general academic reputation",
    "campus_size": "small / medium / large",
    "academic_support": "1 sentence on athletic academic support programs",
    "academic_note": "1 sentence on how academic fit looks for this athlete"
  },
  "recruiting_path": {
    "next_step": "most important immediate action for this athlete",
    "camp_opportunity": "any known camps or showcases hosted or attended by this program",
    "contact_window": "when/how to reach out per NCAA rules",
    "timeline": "realistic timeline if this athlete were to pursue this school",
    "outreach_tip": "1 specific sentence on what to highlight when contacting this program"
  },
  "overall_assessment": "3-4 sentences synthesizing why this program is or isn't a strong fit for this specific athlete, referencing their stats and goals"
}

Return ONLY the JSON. No markdown, no code blocks, no explanation."""


@router.post("/workspace/colleges/{clerk_id}/{college_id}/research")
async def run_deep_research(clerk_id: str, college_id: int, background_tasks: BackgroundTasks, caller_id: str = Depends(require_identity)):
    """Trigger deep per-college research for an athlete."""
    if clerk_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT * FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            profile = c.fetchone()
            if not profile:
                raise HTTPException(status_code=404, detail="Profile not found")

            c.execute("SELECT * FROM college_targets WHERE id = %s AND sparq_profile_id = %s",
                      (college_id, profile["id"]))
            college = c.fetchone()
            if not college:
                raise HTTPException(status_code=404, detail="College not found")

            # Mark as researching
            c.execute("UPDATE college_targets SET deep_research_status = 'researching' WHERE id = %s",
                      (college_id,))
            db.commit()
    finally:
        db.close()

    # Parse profile data
    mp_raw = profile.get("maxpreps_data") or {}
    if isinstance(mp_raw, str):
        try: mp_raw = json.loads(mp_raw)
        except: mp_raw = {}

    sports_list = mp_raw.get("sports") or []
    sport = sports_list[0] if sports_list else (mp_raw.get("sport") or profile.get("position") or "Basketball")

    goals_raw = profile.get("recruiting_goals") or {}
    if isinstance(goals_raw, str):
        try: goals_raw = json.loads(goals_raw)
        except: goals_raw = {}

    stats_preview = mp_raw.get("statsPreview") or []
    stats_str = ", ".join(f"{s[0]}: {s[1]}" for s in stats_preview) if stats_preview else "not provided"

    athlete_summary = (
        # No name or city: a model prompt / web search must not identify a minor.
        f"Sport: {sport}\n"
        f"Position: {profile.get('position') or mp_raw.get('position') or 'Unknown'}\n"
        f"Class of: {profile.get('class_year') or 'not provided'}\n"
        f"State: {profile.get('state') or 'not provided'}\n"
        f"Stats: {stats_str}\n"
        f"GPA: {profile.get('gpa') or 'not provided'}\n"
        f"Major interest: {profile.get('major_area') or 'Undecided'}\n"
        f"Target division: {goals_raw.get('targetLevel', 'Open')}\n"
        f"Geography preference: {goals_raw.get('geography', 'Anywhere')}\n"
    )

    college_name = college["college_name"]
    division = college.get("division", "D1")
    city = college.get("college_city", "")
    state = college.get("college_state", "")

    def _do_research(cid, name, div, ct, st, athlete_info, spt):
        import anthropic as _anth, re as _re
        client = _anth.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        db2 = _get_agent_db()
        try:
            prompt = (
                f"Research {name} ({div}, {ct}, {st}) for this athlete:\n\n{athlete_info}\n"
                f"Focus on the {spt} program specifically. "
                f"If sport includes 'Girls' or 'Women', research ONLY the women's program. "
                f"Provide deep, specific information useful for a recruiting decision."
            )
            print(f"[DeepResearch] Starting for college_target {cid}: {name}")
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                system=DEEP_RESEARCH_SYSTEM,
                tools=[{"type": "web_search_20260209", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}],
            )
            full_text = "".join(b.text for b in response.content if hasattr(b, "text"))
            print(f"[DeepResearch] Got {len(full_text)} chars for {name}")

            research_data = None
            for pattern in [r'\{[\s\S]*\}']:
                m = _re.search(pattern, full_text)
                if m:
                    try:
                        research_data = json.loads(m.group())
                        break
                    except Exception:
                        pass

            status = "complete" if research_data else "error"
            with db2.cursor() as c2:
                c2.execute("""
                    UPDATE college_targets
                    SET research_data = %s, deep_research_status = %s
                    WHERE id = %s
                """, (json.dumps(research_data) if research_data else None, status, cid))
            db2.commit()
            print(f"[DeepResearch] Stored for {name} — status: {status}")
        except Exception as e:
            import traceback
            print(f"[DeepResearch] Error for {name}: {e}")
            traceback.print_exc()
            with db2.cursor() as c2:
                c2.execute("UPDATE college_targets SET deep_research_status = 'error' WHERE id = %s", (cid,))
            db2.commit()
        finally:
            db2.close()

    t = threading.Thread(
        target=_do_research,
        args=(college_id, college_name, division, city, state, athlete_summary, sport),
        daemon=True,
        name=f"deep-research-{college_id}"
    )
    t.start()
    print(f"[DeepResearch] Thread launched for college {college_id} ({college_name})")

    return {"status": "researching", "college_id": college_id, "college_name": college_name}
