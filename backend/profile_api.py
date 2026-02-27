"""
Profile & Links API - Athlete dashboard data
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import pymysql
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
load_dotenv()

router = APIRouter(prefix="/api", tags=["Profile"])


def _get_agent_db():
    return pymysql.connect(
        host=os.getenv('AGENT_DB_HOST', 'mysql.railway.internal'),
        port=int(os.getenv('AGENT_DB_PORT', '3306')),
        user=os.getenv('AGENT_DB_USER', 'root'),
        password=os.getenv('AGENT_DB_PASSWORD', ''),
        database=os.getenv('AGENT_DB_NAME', 'railway'),
        cursorclass=pymysql.cursors.DictCursor
    )


def _get_gmtm_db():
    """Read-only connection to GMTM database"""
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database='gmtm',
        port=3306,
        cursorclass=pymysql.cursors.DictCursor
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


def _ensure_tables():
    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS sparq_profiles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    clerk_id VARCHAR(255) NOT NULL UNIQUE,
                    maxpreps_athlete_id VARCHAR(255),
                    maxpreps_data JSON,
                    name VARCHAR(255),
                    position VARCHAR(100),
                    school VARCHAR(255),
                    class_year INT,
                    city VARCHAR(100),
                    state VARCHAR(50),
                    gpa DECIMAL(3,2),
                    major_area VARCHAR(100),
                    hudl_url VARCHAR(500),
                    combine_metrics JSON,
                    recruiting_goals JSON,
                    enrichment_complete TINYINT(1) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS college_targets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    sparq_profile_id INT NOT NULL,
                    college_name VARCHAR(255) NOT NULL,
                    college_city VARCHAR(100),
                    college_state VARCHAR(50),
                    division VARCHAR(20) DEFAULT 'D1',
                    fit_score INT DEFAULT 75,
                    fit_reasons JSON,
                    status ENUM('Researching','Interested','Contacted','Visited','Offered','Committed','Declined') DEFAULT 'Researching',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_profile (sparq_profile_id)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    clerk_id VARCHAR(255) NOT NULL UNIQUE,
                    session_id VARCHAR(255) NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_clerk (clerk_id)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS outreach_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    sparq_profile_id INT NOT NULL,
                    school VARCHAR(200) NOT NULL,
                    coach VARCHAR(200) DEFAULT NULL,
                    method ENUM("Email","Phone","Visit","Camp") NOT NULL DEFAULT "Email",
                    contact_date DATE NOT NULL,
                    status ENUM("Awaiting Response","Responded","Meeting Scheduled","Archived") NOT NULL DEFAULT "Awaiting Response",
                    notes TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_profile (sparq_profile_id)
                )
            """)
            try:
                c.execute("ALTER TABLE sparq_profiles ADD COLUMN enrichment_complete TINYINT(1) DEFAULT 0")
            except Exception:
                pass  # Column already exists
            # Ensure agent_conversations has clerk_id column (may be missing on old tables)
            try:
                c.execute("ALTER TABLE agent_conversations ADD COLUMN clerk_id VARCHAR(255) DEFAULT NULL")
            except Exception:
                pass  # Column already exists
            try:
                c.execute("ALTER TABLE agent_conversations ADD UNIQUE INDEX idx_clerk_conv (clerk_id)")
            except Exception:
                pass  # Index already exists
            # Ensure agent_messages exists with correct structure
            c.execute("""
                CREATE TABLE IF NOT EXISTS agent_messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    conversation_id INT NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_conv (conversation_id)
                )
            """)
        db.commit()
    except Exception as e:
        print(f"Table creation warning: {e}")
    finally:
        if db:
            db.close()


_ensure_tables()


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


class ProfileConnect(BaseModel):
    user_id: int
    clerk_id: str


class OnboardingPayload(BaseModel):
    clerk_id: Optional[str] = None
    maxprepsData: Optional[dict] = None
    combineMetrics: Optional[dict] = None
    gpa: Optional[float] = None
    majorArea: Optional[str] = None
    recruitingGoals: Optional[dict] = None
    hudlUrl: Optional[str] = None


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

@router.get("/dashboard/{user_id}")
async def get_dashboard(user_id: int):
    """Full dashboard data: profile + metrics + links + recent chats"""
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
            
            # Get recent conversations
            c.execute("""
                SELECT ac.id, ac.title, ac.updated_at,
                       (SELECT COUNT(*) FROM agent_messages WHERE conversation_id = ac.id) as message_count
                FROM agent_conversations ac
                WHERE ac.user_id = %s
                ORDER BY ac.updated_at DESC
                LIMIT 5
            """, (user_id,))
            recent_chats = c.fetchall()
            for chat in recent_chats:
                chat['updated_at'] = str(chat['updated_at'])
        
        # Calculate profile completeness
        total_fields = 8  # metrics we care about + links
        filled = len([m for m in metrics if m['value']]) + min(len(links), 3)
        completeness = min(100, int((filled / total_fields) * 100))
        
        # Suggested links to add
        existing_platforms = {l['platform'] for l in links}
        all_platforms = ['hudl', 'twitter', 'instagram', 'maxpreps', '247sports', 'rivals', 'youtube', 'personal_website']
        missing_platforms = [p for p in all_platforms if p not in existing_platforms]
        
        return {
            "profile": profile,
            "metrics": metrics,
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
async def get_links(user_id: int):
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id, platform, url, label FROM athlete_links WHERE user_id = %s ORDER BY platform", (user_id,))
            return {"links": c.fetchall()}
    finally:
        db.close()


@router.post("/links")
async def add_link(request: LinkCreate):
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
async def delete_link(link_id: int):
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("DELETE FROM athlete_links WHERE id = %s", (link_id,))
            db.commit()
            return {"deleted": True}
    finally:
        db.close()


# ── Connect Clerk to athlete ────────────

@router.post("/profile/connect")
async def connect_profile(request: ProfileConnect):
    """Link a Clerk user ID to an athlete ID"""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "INSERT INTO athlete_profiles (user_id, clerk_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE clerk_id = %s",
                (request.user_id, request.clerk_id, request.clerk_id)
            )
            db.commit()
            return {"connected": True, "user_id": request.user_id, "clerk_id": request.clerk_id}
    finally:
        db.close()


@router.get("/athlete/search")
async def search_athletes(name: str):
    """Search athletes by name (READ ONLY from GMTM)"""
    if len(name.strip()) < 2:
        return {"athletes": []}
    gmtm = _get_gmtm_db()
    try:
        with gmtm.cursor() as c:
            parts = name.strip().split()
            if len(parts) >= 2:
                c.execute("""
                    SELECT u.user_id, u.first_name, u.last_name,
                           l.city, l.province as state
                    FROM users u
                    LEFT JOIN locations l ON u.location_id = l.location_id
                    WHERE u.first_name LIKE %s AND u.last_name LIKE %s
                    LIMIT 20
                """, (f"{parts[0]}%", f"{parts[-1]}%"))
            else:
                c.execute("""
                    SELECT u.user_id, u.first_name, u.last_name,
                           l.city, l.province as state
                    FROM users u
                    LEFT JOIN locations l ON u.location_id = l.location_id
                    WHERE u.first_name LIKE %s OR u.last_name LIKE %s
                    LIMIT 20
                """, (f"{name.strip()}%", f"{name.strip()}%"))
            athletes = c.fetchall()
            
            # Get positions
            for a in athletes:
                c.execute("""
                    SELECT p.name as position
                    FROM career c
                    JOIN user_positions up ON up.career_id = c.career_id
                    JOIN positions p ON up.position_id = p.position_id
                    WHERE c.user_id = %s AND up.is_primary = 1
                    LIMIT 1
                """, (a['user_id'],))
                pos = c.fetchone()
                a['position'] = pos['position'] if pos else None
            
            return {"athletes": athletes}
    finally:
        gmtm.close()


@router.get("/profile/by-clerk/{clerk_id}")
async def get_profile_by_clerk(clerk_id: str):
    """Look up athlete ID from Clerk user ID. Also checks sparq_profiles."""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            # Check legacy GMTM athlete link
            c.execute("SELECT user_id FROM athlete_profiles WHERE clerk_id = %s", (clerk_id,))
            row = c.fetchone()
            if row:
                return {"found": True, "user_id": row['user_id'], "has_sparq_profile": False}

            # Check new sparq_profiles (MaxPreps onboarding)
            c.execute("SELECT id FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            sparq_row = c.fetchone()
            if sparq_row:
                return {"found": False, "user_id": None, "has_sparq_profile": True}

            return {"found": False, "user_id": None, "has_sparq_profile": False}
    finally:
        db.close()


@router.post("/profile/create-from-onboarding")
async def create_from_onboarding(payload: OnboardingPayload):
    if not payload.clerk_id:
        raise HTTPException(status_code=400, detail="clerk_id is required")

    db = _get_agent_db()
    try:
        mp = payload.maxprepsData or {}
        position = mp.get("position", "")
        state = mp.get("state", "")
        name = mp.get("name", "")
        school = mp.get("school", "")
        class_year = mp.get("classYear")
        city = mp.get("city", "")
        maxpreps_athlete_id = mp.get("maxprepsAthleteId")

        with db.cursor() as c:
            c.execute("""
                INSERT INTO sparq_profiles
                    (clerk_id, maxpreps_athlete_id, maxpreps_data, name, position, school,
                     class_year, city, state, gpa, major_area, hudl_url, enrichment_complete,
                     combine_metrics, recruiting_goals)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    maxpreps_data=VALUES(maxpreps_data),
                    name=VALUES(name), position=VALUES(position),
                    school=VALUES(school), class_year=VALUES(class_year),
                    city=VALUES(city), state=VALUES(state),
                    gpa=VALUES(gpa), major_area=VALUES(major_area),
                    hudl_url=VALUES(hudl_url),
                    enrichment_complete=0,
                    combine_metrics=VALUES(combine_metrics),
                    recruiting_goals=VALUES(recruiting_goals),
                    updated_at=CURRENT_TIMESTAMP
            """, (
                payload.clerk_id,
                maxpreps_athlete_id,
                json.dumps(mp) if mp else None,
                name,
                position,
                school,
                class_year,
                city,
                state,
                payload.gpa,
                payload.majorArea,
                payload.hudlUrl,
                0,
                json.dumps(payload.combineMetrics) if payload.combineMetrics else None,
                json.dumps(payload.recruitingGoals) if payload.recruitingGoals else None,
            ))
            db.commit()
            c.execute("SELECT id FROM sparq_profiles WHERE clerk_id = %s", (payload.clerk_id,))
            profile_id = c.fetchone()["id"]

        colleges_matched = 0
        try:
            from tools.recruiting_tools import RecruitingTools

            rt = RecruitingTools()
            prefs = {}
            if payload.recruitingGoals:
                geo = payload.recruitingGoals.get("geography", "")
                if geo == "In-state" and state:
                    prefs["region"] = state

            athlete_dict = {
                "sport": "Football (American)",
                "position": position,
                "state": state,
            }
            result = rt.match_programs(athlete_dict, preferences=prefs)

            seen = set()
            programs = []
            for program in (result.get("top_programs", []) + result.get("regional_programs", [])):
                key = program["name"].strip().lower()
                if key not in seen:
                    seen.add(key)
                    programs.append(program)
            programs = programs[:12]

            if programs:
                with db.cursor() as c:
                    c.execute("DELETE FROM college_targets WHERE sparq_profile_id = %s", (profile_id,))

                    for i, program in enumerate(programs):
                        offer_count = program.get("offers_given", 0)
                        fit_score = 70
                        fit_score += max(0, 10 - i)
                        if offer_count >= 50:
                            fit_score += 5
                        elif offer_count >= 20:
                            fit_score += 3
                        else:
                            fit_score += 1
                        if prefs.get("region") and program.get("state") == state:
                            fit_score += 5
                        fit_score = min(fit_score, 95)

                        fit_reasons = []
                        if offer_count > 10:
                            fit_reasons.append(f"Actively recruits your position ({offer_count} offers given)")
                        if program.get("state") == state:
                            fit_reasons.append("In-state program")

                        division = "D1" if offer_count >= 15 else ("D2" if offer_count >= 5 else "D3")

                        c.execute("""
                            INSERT INTO college_targets
                                (sparq_profile_id, college_name, college_city, college_state,
                                 division, fit_score, fit_reasons)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            profile_id,
                            program["name"],
                            program.get("city", ""),
                            program.get("state", ""),
                            division,
                            fit_score,
                            json.dumps(fit_reasons),
                        ))
                        colleges_matched += 1
                    db.commit()
        except Exception as e:
            print(f"College matching error (non-fatal): {e}")

        # Fire-and-forget enrichment (runs in background, doesn't block response)
        try:
            import asyncio
            from enrichment_worker import enrich_college_targets

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    enrich_college_targets(
                        sparq_profile_id=profile_id,
                        athlete_position=position or "Athlete",
                        athlete_state=state or "US",
                    )
                )
        except Exception as e:
            print(f"Warning: enrichment task not started: {e}")

        return {
            "success": True,
            "profile_id": profile_id,
            "colleges_matched": colleges_matched,
        }
    finally:
        db.close()


@router.get("/workspace/colleges/{clerk_id}")
async def get_college_targets(clerk_id: str):
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
async def get_enrichment_status(clerk_id: str):
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
async def update_college_status(college_target_id: int, body: StatusUpdate):
    valid = {"Researching", "Interested", "Contacted", "Visited", "Offered", "Committed", "Declined"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail="Invalid status")
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
async def get_outreach_entries(clerk_id: str):
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
async def create_outreach_entry(clerk_id: str, body: OutreachCreate):
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
async def update_outreach_status(entry_id: int, body: OutreachStatusUpdate):
    valid_statuses = {"Awaiting Response", "Responded", "Meeting Scheduled", "Archived"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("UPDATE outreach_log SET status = %s WHERE id = %s", (body.status, entry_id))
        db.commit()
        return {"updated": True}
    finally:
        db.close()


@router.delete("/workspace/outreach/{entry_id}")
async def delete_outreach_entry(entry_id: int):
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("DELETE FROM outreach_log WHERE id = %s", (entry_id,))
        db.commit()
        return {"deleted": True}
    finally:
        db.close()


@router.get("/workspace/stats/{clerk_id}")
async def get_workspace_stats(clerk_id: str):
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
async def get_workspace_timeline(clerk_id: str):
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
                "SELECT school, method, status, created_at FROM outreach_log WHERE clerk_id = %s ORDER BY created_at DESC",
                (clerk_id,),
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


@router.get("/maxpreps/search")
async def maxpreps_search(q: str, limit: int = 8):
    """Search MaxPreps athletes: dedup, parallel stat fetch, sort by richness."""
    import requests as _requests, json, re, asyncio
    from concurrent.futures import ThreadPoolExecutor

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    def _fetch_url(url):
        return _requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True).text

    def _extract_next_data(html):
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        return json.loads(m.group(1)) if m else None

    # --- Fetch search results page ---
    search_url = f"https://www.maxpreps.com/search/?q={q.replace(' ', '+')}"
    loop = asyncio.get_event_loop()
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            html = await loop.run_in_executor(pool, _fetch_url, search_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MaxPreps fetch failed: {e}")

    data = _extract_next_data(html)
    if not data:
        raise HTTPException(status_code=502, detail="Could not parse MaxPreps search response")

    try:
        careers = data["props"]["pageProps"].get("initialCareerResults") or []
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"JSON parse error: {e}")

    # --- Deduplicate: keep best career per (schoolId + primary_sport) ---
    seen = {}
    for c in careers:
        school_id = c.get("mostRecentSchoolId") or c.get("schoolName", "")
        sports_raw = c.get("sports") or []
        primary_sport = sports_raw[0].replace("Boys ", "").replace("Girls ", "") if sports_raw else "unknown"
        key = f"{school_id}|{primary_sport}"
        if key not in seen:
            seen[key] = c
        # prefer entry with photo
        elif c.get("careerPhotoUrl") and not seen[key].get("careerPhotoUrl"):
            seen[key] = c

    unique_careers = list(seen.values())[:limit]

    # --- Build profile URLs ---
    def career_to_base(c):
        sports_raw = c.get("sports") or []
        sport_label = sports_raw[0].replace("Boys ", "").replace("Girls ", "") if sports_raw else None
        profile_url = f"https://www.maxpreps.com{c.get('careerCanonicalUrl', '')}" if c.get("careerCanonicalUrl") else None
        return {
            "id": c.get("careerId"),
            "maxprepsAthleteId": c.get("careerId"),
            "name": c.get("fullName"),
            "school": c.get("schoolFormattedName"),
            "state": c.get("state"),
            "sports": sports_raw,
            "sport": sport_label,
            "position": sport_label,
            "classYear": c.get("careerGraduatingClass") or None,
            "photoUrl": c.get("careerPhotoUrl"),
            "schoolColor": c.get("schoolColor1"),
            "schoolMascotUrl": c.get("schoolMascotUrl"),
            "profileUrl": profile_url,
            # filled in after parallel fetch:
            "statsPreview": None,
            "lastSeason": None,
        }

    base_results = [career_to_base(c) for c in unique_careers]

    # --- Parallel stats fetch for all results ---
    SPORT_PRIORITY = {
        "Basketball": ["Points Per Game", "Rebounds Per Game", "Assists Per Game"],
        "Football": ["Passing Yards", "Touchdowns", "Tackles", "Rushing Yards"],
        "Soccer": ["Goals", "Assists", "Saves"],
        "Volleyball": ["Kills", "Assists", "Digs"],
        "Baseball": ["Batting Average", "Home Runs", "RBI"],
        "Softball": ["Batting Average", "Home Runs", "RBI"],
        "Lacrosse": ["Goals", "Assists"],
    }

    def _fetch_stats(profile_url):
        if not profile_url:
            return None
        try:
            html = _fetch_url(profile_url)
            d = _extract_next_data(html)
            if not d:
                return None
            pp = d["props"]["pageProps"]
            cards = pp.get("careerHomeCards") or {}
            qs_list = cards.get("quickStats") or []
            if not qs_list:
                return None
            qs = qs_list[0]
            sport = qs.get("sport", "")
            season = qs.get("seasonYear", "")
            position = qs.get("position", "")
            categories = qs.get("categories") or []
            stats = {cat["name"]: cat["seasonValue"] for cat in categories}
            priority = SPORT_PRIORITY.get(sport, list(stats.keys()))
            top = [(k, stats[k]) for k in priority if k in stats][:3]
            if not top:
                top = list(stats.items())[:3]
            return {
                "sport": sport,
                "season": season,
                "position": position,
                "preview": top,  # list of (label, value)
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [loop.run_in_executor(pool, _fetch_stats, r["profileUrl"]) for r in base_results]
        stats_list = await asyncio.gather(*futs, return_exceptions=True)

    for result, stats in zip(base_results, stats_list):
        if isinstance(stats, dict):
            result["statsPreview"] = stats.get("preview")   # [(label, value), ...]
            result["lastSeason"] = stats.get("season")
            result["classYear"] = result["classYear"] or None
            if stats.get("position"):
                result["position"] = stats["position"]
            if stats.get("sport"):
                result["sport"] = stats["sport"]

    # --- Sort: has stats first, then by most recent season ---
    def sort_key(r):
        has_stats = 1 if r.get("statsPreview") else 0
        season = r.get("lastSeason") or ""
        return (has_stats, season)

    base_results.sort(key=sort_key, reverse=True)
    return base_results


@router.get("/maxpreps/athlete-stats")
async def maxpreps_athlete_stats(url: str):
    """Fetch real stats from a MaxPreps athlete profile page."""
    import requests as _requests, json, re
    from concurrent.futures import ThreadPoolExecutor

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    def _fetch():
        resp = _requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        return resp.text

    try:
        loop = __import__('asyncio').get_event_loop()
        with ThreadPoolExecutor() as pool:
            html = await loop.run_in_executor(pool, _fetch)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MaxPreps fetch failed: {e}")

    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not match:
        raise HTTPException(status_code=502, detail="Could not parse MaxPreps response")

    try:
        data = json.loads(match.group(1))
        pp = data["props"]["pageProps"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"JSON parse error: {e}")

    # Pull athlete name and career info
    athlete_name = pp.get("athleteName", "")
    career_context = pp.get("careerContext") or {}

    # Extract quickStats from careerHomeCards
    cards = pp.get("careerHomeCards") or {}
    quick_stats_list = cards.get("quickStats") or []

    seasons = []
    for qs in quick_stats_list:
        sport = qs.get("sport", "")
        season_year = qs.get("seasonYear", "")
        position = qs.get("position", "")
        categories = qs.get("categories") or []
        stats = {c["name"]: c.get("seasonValue") for c in categories}
        seasons.append({
            "sport": sport,
            "season": season_year,
            "position": position,
            "stats": stats,
        })

    # Extract career history for multi-season progression
    career_history = pp.get("careerHistoryData") or {}

    return {
        "athleteName": athlete_name,
        "sport": quick_stats_list[0].get("sport") if quick_stats_list else None,
        "position": quick_stats_list[0].get("position") if quick_stats_list else None,
        "seasons": seasons,
        "careerHistory": career_history,
    }
