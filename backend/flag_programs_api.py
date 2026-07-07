"""
Women's College Flag Football Programs — the bounded matching universe.
=======================================================================

Flag football is SPARQ's focus market. The entire women's college flag landscape is
~100-116 programs, which means college matching for flag athletes can draw from a
curated table instead of open-ended LLM web search — eliminating hallucinated programs.

- Table `flag_programs` is created idempotently on import (same pattern as the rest of
  the backend) and seeded from data/womens_college_flag_programs.json on startup, so a
  Railway deploy applies both schema and seed with no manual DB access.
- GET  /api/flag-programs           → public list (also useful for marketing pages)
- POST /api/flag-programs/bulk      → admin upsert (X-Admin-Key = ADMIN_API_KEY) for
  ongoing curation as new programs are announced (they are, monthly).
"""

import hmac
import json
import os
from typing import Optional

import pymysql
from dotenv import load_dotenv
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
load_dotenv()

router = APIRouter(prefix="/api", tags=["FlagPrograms"])

SEED_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "womens_college_flag_programs.json",
)


def _get_agent_db():
    return pymysql.connect(
        host=os.getenv('AGENT_DB_HOST', 'mysql.railway.internal'),
        port=int(os.getenv('AGENT_DB_PORT', '3306')),
        user=os.getenv('AGENT_DB_USER', 'root'),
        password=os.getenv('AGENT_DB_PASSWORD', ''),
        database=os.getenv('AGENT_DB_NAME', 'railway'),
        cursorclass=pymysql.cursors.DictCursor
    )


def _ensure_table_and_seed():
    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS flag_programs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    city VARCHAR(100) DEFAULT NULL,
                    state VARCHAR(10) DEFAULT NULL,
                    org VARCHAR(20) NOT NULL,             -- NAIA / NCAA D1 / NCAA D2 / NCAA D3 / NJCAA / CCCAA
                    conference VARCHAR(120) DEFAULT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'varsity',  -- varsity / announced / club
                    first_varsity_season VARCHAR(20) DEFAULT NULL,
                    coach_name VARCHAR(160) DEFAULT NULL,
                    coach_email VARCHAR(255) DEFAULT NULL,
                    roster_size INT DEFAULT NULL,
                    scholarship_info VARCHAR(255) DEFAULT NULL,
                    source_url VARCHAR(500) DEFAULT NULL,
                    notes TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_org_status (org, status),
                    INDEX idx_state (state)
                )
            """)
        db.commit()

        # Seed from the JSON file — INSERT IGNORE so the seed only creates missing rows.
        # Once a row exists, /api/flag-programs/bulk owns all updates; a redeploy must
        # never clobber hand-curated edits (status changes, conference fixes, coach info).
        if os.path.exists(SEED_PATH):
            with open(SEED_PATH) as f:
                seed = json.load(f)
            programs = seed.get("programs", [])
            with db.cursor() as c:
                for p in programs:
                    c.execute("""
                        INSERT IGNORE INTO flag_programs
                            (name, state, org, conference, status, first_varsity_season, source_url)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        p.get("name"), p.get("state"), p.get("org", "NAIA"),
                        p.get("conference"), p.get("status", "varsity"),
                        p.get("first_varsity_season"), p.get("source_url"),
                    ))
            db.commit()
            print(f"[FlagPrograms] Seed ensured ({len(programs)} programs in seed file; existing rows untouched)")
    except Exception as e:
        print(f"⚠️ flag_programs table/seed warning: {e}")
    finally:
        if db:
            db.close()


_ensure_table_and_seed()


def load_flag_programs(org: Optional[str] = None, status: Optional[str] = None) -> list[dict]:
    """Shared loader used by the matching pipeline (enrichment_worker) and the API."""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            q = "SELECT * FROM flag_programs WHERE 1=1"
            params: list = []
            if org:
                q += " AND org = %s"; params.append(org)
            if status:
                q += " AND status = %s"; params.append(status)
            q += " ORDER BY org, state, name"
            c.execute(q, params)
            return c.fetchall()
    finally:
        db.close()


@router.get("/flag-programs")
def list_flag_programs(org: Optional[str] = None, status: Optional[str] = None, state: Optional[str] = None):
    """Public directory of women's college flag football programs."""
    rows = load_flag_programs(org=org, status=status)
    if state:
        rows = [r for r in rows if (r.get("state") or "").upper() == state.upper()]
    for r in rows:
        r["created_at"] = str(r.get("created_at") or "")
        r["updated_at"] = str(r.get("updated_at") or "")
    return {"programs": rows, "total": len(rows)}


class ProgramUpsert(BaseModel):
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    org: str = "NAIA"
    conference: Optional[str] = None
    status: str = "varsity"
    first_varsity_season: Optional[str] = None
    coach_name: Optional[str] = None
    coach_email: Optional[str] = None
    roster_size: Optional[int] = None
    scholarship_info: Optional[str] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None


class BulkUpsert(BaseModel):
    programs: list[ProgramUpsert]


def _require_admin_key(x_admin_key: Optional[str]) -> None:
    expected = os.environ.get("ADMIN_API_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Admin API not configured (ADMIN_API_KEY unset).")
    if not x_admin_key or not hmac.compare_digest(x_admin_key.strip(), expected):
        raise HTTPException(status_code=401, detail="Invalid admin key.")


@router.post("/flag-programs/bulk")
def bulk_upsert_programs(body: BulkUpsert, x_admin_key: Optional[str] = Header(default=None)):
    """Admin curation endpoint — upsert programs by name (completes/updates the seed)."""
    _require_admin_key(x_admin_key)
    db = _get_agent_db()
    upserted = 0
    try:
        with db.cursor() as c:
            for p in body.programs:
                c.execute("""
                    INSERT INTO flag_programs
                        (name, city, state, org, conference, status, first_varsity_season,
                         coach_name, coach_email, roster_size, scholarship_info, source_url, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        city = COALESCE(VALUES(city), city),
                        state = COALESCE(VALUES(state), state),
                        org = VALUES(org),
                        conference = COALESCE(VALUES(conference), conference),
                        status = VALUES(status),
                        first_varsity_season = COALESCE(VALUES(first_varsity_season), first_varsity_season),
                        coach_name = COALESCE(VALUES(coach_name), coach_name),
                        coach_email = COALESCE(VALUES(coach_email), coach_email),
                        roster_size = COALESCE(VALUES(roster_size), roster_size),
                        scholarship_info = COALESCE(VALUES(scholarship_info), scholarship_info),
                        source_url = COALESCE(VALUES(source_url), source_url),
                        notes = COALESCE(VALUES(notes), notes)
                """, (
                    p.name, p.city, p.state, p.org, p.conference, p.status,
                    p.first_varsity_season, p.coach_name, p.coach_email,
                    p.roster_size, p.scholarship_info, p.source_url, p.notes,
                ))
                upserted += 1
        db.commit()
        return {"ok": True, "upserted": upserted}
    finally:
        db.close()
