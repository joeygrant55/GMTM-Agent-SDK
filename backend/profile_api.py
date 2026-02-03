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
                SELECT p.abbreviation as position
                FROM user_positions up
                JOIN positions p ON up.position_id = p.position_id
                WHERE up.user_id = %s AND up.is_primary = 1
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


@router.get("/profile/by-clerk/{clerk_id}")
async def get_profile_by_clerk(clerk_id: str):
    """Look up athlete ID from Clerk user ID"""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT user_id FROM athlete_profiles WHERE clerk_id = %s", (clerk_id,))
            row = c.fetchone()
            if not row:
                return {"found": False, "user_id": None}
            return {"found": True, "user_id": row['user_id']}
    finally:
        db.close()
