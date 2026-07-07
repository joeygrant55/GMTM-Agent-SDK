"""
Verified Data Spine — testing events, device-captured metrics, athlete outcomes.
================================================================================

This is the data asset behind the club-first strategy (see PRODUCT_STRATEGY.md):
SPARQ testing days capture verified metrics; selection results (national-team trial
invites, college commits, offers) become labeled outcomes. Together they form the
training set for outcome-calibrated assessments no general-purpose AI can replicate.

Tables (created idempotently on import):
- testing_events    — a SPARQ testing day (club, location, date, sport)
- verified_metrics  — one measurement, with full provenance (event, device, timestamp)
- athlete_outcomes  — labeled outcomes (trial_invite, national_team_selection,
                      scholarship_offer, college_commit, ...) linked to a profile

Auth model:
- Ingestion (capture devices / event staff software) authenticates with
  `X-Ingest-Key` == INGEST_API_KEY env var — devices don't have Clerk sessions.
  Fail-closed: unset key ⇒ ingestion disabled.
- Athlete reads require a Clerk token and are scoped to the caller's own profile.

Athlete linking at capture time is best-effort: rows carry sparq_profile_id when the
athlete is known (pre-registered), otherwise athlete_name/external_ref for later
reconciliation via the admin flow.
"""

import hmac
import json
import os
import traceback
from typing import Optional

import pymysql
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from auth import require_clerk_id

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
load_dotenv()

router = APIRouter(prefix="/api", tags=["VerifiedData"])

# Suggested metric_type values — not enforced, but keeps device payloads consistent.
KNOWN_METRIC_TYPES = [
    "sparq_score", "forty_yard", "shuttle_5_10_5", "vertical_jump", "broad_jump",
    "three_cone", "height", "weight", "wingspan", "flying_20",
]

OUTCOME_TYPES = [
    "trial_invite", "national_team_selection", "scholarship_offer",
    "college_commit", "college_roster", "all_conference", "camp_invite",
]


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
                CREATE TABLE IF NOT EXISTS testing_events (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    club_name VARCHAR(255) DEFAULT NULL,
                    sport VARCHAR(80) DEFAULT 'Flag Football',
                    location VARCHAR(255) DEFAULT NULL,
                    event_date DATE DEFAULT NULL,
                    notes TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_date (event_date),
                    INDEX idx_club (club_name)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS verified_metrics (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    sparq_profile_id INT DEFAULT NULL,
                    event_id INT DEFAULT NULL,
                    athlete_name VARCHAR(255) DEFAULT NULL,
                    external_ref VARCHAR(255) DEFAULT NULL,
                    metric_type VARCHAR(60) NOT NULL,
                    metric_value DECIMAL(10,3) NOT NULL,
                    unit VARCHAR(20) DEFAULT NULL,
                    device_id VARCHAR(120) DEFAULT NULL,
                    captured_at TIMESTAMP NULL DEFAULT NULL,
                    source VARCHAR(40) NOT NULL DEFAULT 'sparq_device',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_profile_type (sparq_profile_id, metric_type),
                    INDEX idx_event (event_id),
                    INDEX idx_unlinked (sparq_profile_id, athlete_name(64))
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS athlete_outcomes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    sparq_profile_id INT DEFAULT NULL,
                    gmtm_user_id INT DEFAULT NULL,
                    athlete_name VARCHAR(255) DEFAULT NULL,
                    outcome_type VARCHAR(40) NOT NULL,
                    organization VARCHAR(255) DEFAULT NULL,
                    level VARCHAR(80) DEFAULT NULL,
                    outcome_date DATE DEFAULT NULL,
                    source VARCHAR(255) DEFAULT NULL,
                    details JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_profile (sparq_profile_id),
                    INDEX idx_type (outcome_type),
                    INDEX idx_gmtm (gmtm_user_id)
                )
            """)
        db.commit()
    except Exception as e:
        print(f"⚠️ verified-data table creation warning: {e}")
        traceback.print_exc()
    finally:
        if db:
            db.close()


_ensure_tables()


def _require_ingest_key(x_ingest_key: Optional[str]) -> None:
    expected = os.environ.get("INGEST_API_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Ingestion not configured (INGEST_API_KEY unset).")
    if not x_ingest_key or not hmac.compare_digest(x_ingest_key.strip(), expected):
        raise HTTPException(status_code=401, detail="Invalid ingest key.")


def _resolve_profile_id(c, clerk_id: Optional[str], sparq_profile_id: Optional[int]) -> Optional[int]:
    if sparq_profile_id:
        return sparq_profile_id
    if clerk_id:
        c.execute("SELECT id FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
        row = c.fetchone()
        return row["id"] if row else None
    return None


# ── Ingestion (device / event-staff key) ────────────────────────────────────

class EventCreate(BaseModel):
    name: str
    club_name: Optional[str] = None
    sport: str = "Flag Football"
    location: Optional[str] = None
    event_date: Optional[str] = None  # YYYY-MM-DD
    notes: Optional[str] = None


@router.post("/ingest/events")
def create_event(body: EventCreate, x_ingest_key: Optional[str] = Header(default=None)):
    _require_ingest_key(x_ingest_key)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "INSERT INTO testing_events (name, club_name, sport, location, event_date, notes) VALUES (%s,%s,%s,%s,%s,%s)",
                (body.name, body.club_name, body.sport, body.location, body.event_date, body.notes),
            )
        db.commit()
        return {"ok": True, "event_id": db.insert_id() or None}
    finally:
        db.close()


class MetricIn(BaseModel):
    metric_type: str
    metric_value: float
    unit: Optional[str] = None
    sparq_profile_id: Optional[int] = None
    clerk_id: Optional[str] = None
    athlete_name: Optional[str] = None
    external_ref: Optional[str] = None
    device_id: Optional[str] = None
    captured_at: Optional[str] = None  # ISO timestamp


class MetricsBulkIn(BaseModel):
    event_id: Optional[int] = None
    source: str = "sparq_device"
    metrics: list[MetricIn]


@router.post("/ingest/metrics")
def ingest_metrics(body: MetricsBulkIn, x_ingest_key: Optional[str] = Header(default=None)):
    """Bulk metric ingestion from capture devices / event software."""
    _require_ingest_key(x_ingest_key)
    if not body.metrics:
        raise HTTPException(status_code=400, detail="metrics list is empty")
    db = _get_agent_db()
    inserted, unlinked = 0, 0
    try:
        with db.cursor() as c:
            for m in body.metrics:
                profile_id = _resolve_profile_id(c, m.clerk_id, m.sparq_profile_id)
                if profile_id is None:
                    unlinked += 1
                    if not (m.athlete_name or m.external_ref):
                        # Nothing to reconcile against later — reject rather than lose data silently.
                        raise HTTPException(
                            status_code=400,
                            detail="each metric needs sparq_profile_id, clerk_id, athlete_name, or external_ref",
                        )
                c.execute("""
                    INSERT INTO verified_metrics
                        (sparq_profile_id, event_id, athlete_name, external_ref,
                         metric_type, metric_value, unit, device_id, captured_at, source)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    profile_id, body.event_id, m.athlete_name, m.external_ref,
                    m.metric_type, m.metric_value, m.unit, m.device_id,
                    m.captured_at, body.source,
                ))
                inserted += 1
        db.commit()
        return {"ok": True, "inserted": inserted, "unlinked": unlinked}
    finally:
        db.close()


class OutcomeIn(BaseModel):
    outcome_type: str
    organization: Optional[str] = None
    level: Optional[str] = None
    outcome_date: Optional[str] = None  # YYYY-MM-DD
    sparq_profile_id: Optional[int] = None
    clerk_id: Optional[str] = None
    gmtm_user_id: Optional[int] = None
    athlete_name: Optional[str] = None
    source: Optional[str] = None
    details: Optional[dict] = None


class OutcomesBulkIn(BaseModel):
    outcomes: list[OutcomeIn]


@router.post("/ingest/outcomes")
def ingest_outcomes(body: OutcomesBulkIn, x_ingest_key: Optional[str] = Header(default=None)):
    """Bulk outcome ingestion (trial invites, selections, offers, commits)."""
    _require_ingest_key(x_ingest_key)
    if not body.outcomes:
        raise HTTPException(status_code=400, detail="outcomes list is empty")
    for o in body.outcomes:
        if o.outcome_type not in OUTCOME_TYPES:
            raise HTTPException(status_code=400, detail=f"unknown outcome_type '{o.outcome_type}' (expected one of {OUTCOME_TYPES})")
    db = _get_agent_db()
    inserted = 0
    try:
        with db.cursor() as c:
            for o in body.outcomes:
                profile_id = _resolve_profile_id(c, o.clerk_id, o.sparq_profile_id)
                if profile_id is None and not (o.gmtm_user_id or o.athlete_name):
                    raise HTTPException(
                        status_code=400,
                        detail="each outcome needs sparq_profile_id, clerk_id, gmtm_user_id, or athlete_name",
                    )
                c.execute("""
                    INSERT INTO athlete_outcomes
                        (sparq_profile_id, gmtm_user_id, athlete_name, outcome_type,
                         organization, level, outcome_date, source, details)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    profile_id, o.gmtm_user_id, o.athlete_name, o.outcome_type,
                    o.organization, o.level, o.outcome_date, o.source,
                    json.dumps(o.details) if o.details else None,
                ))
                inserted += 1
        db.commit()
        return {"ok": True, "inserted": inserted}
    finally:
        db.close()


# ── Athlete-facing reads (Clerk auth, own data only) ────────────────────────

@router.get("/workspace/verified/{clerk_id}")
def get_verified_data(clerk_id: str, caller_clerk_id: str = Depends(require_clerk_id)):
    """The athlete's verified metrics + outcomes, newest first."""
    if clerk_id != caller_clerk_id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            profile = c.fetchone()
            if not profile:
                # Same shape as the success path — event info rides on each metric row
                # (event_name/event_date/club_name via join), not as a separate list.
                return {"metrics": [], "outcomes": []}
            pid = profile["id"]

            c.execute("""
                SELECT vm.*, te.name AS event_name, te.event_date, te.club_name
                FROM verified_metrics vm
                LEFT JOIN testing_events te ON te.id = vm.event_id
                WHERE vm.sparq_profile_id = %s
                ORDER BY COALESCE(vm.captured_at, vm.created_at) DESC
                LIMIT 200
            """, (pid,))
            metrics = c.fetchall()

            c.execute("""
                SELECT * FROM athlete_outcomes
                WHERE sparq_profile_id = %s
                ORDER BY COALESCE(outcome_date, DATE(created_at)) DESC
                LIMIT 100
            """, (pid,))
            outcomes = c.fetchall()

        for row in metrics + outcomes:
            for k, v in list(row.items()):
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
                elif k == "details" and isinstance(v, str):
                    try:
                        row[k] = json.loads(v)
                    except Exception:
                        pass
                elif k == "metric_value" and v is not None:
                    row[k] = float(v)
        return {"metrics": metrics, "outcomes": outcomes}
    finally:
        db.close()


def latest_verified_metrics_for_profile(profile_id: int) -> dict:
    """Most recent value per metric_type — used to enrich the agent's athlete context."""
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("""
                SELECT vm.metric_type, vm.metric_value, vm.unit,
                       COALESCE(vm.captured_at, vm.created_at) AS at
                FROM verified_metrics vm
                WHERE vm.sparq_profile_id = %s
                ORDER BY at DESC
                LIMIT 100
            """, (profile_id,))
            rows = c.fetchall()
        latest: dict = {}
        for r in rows:
            t = r["metric_type"]
            if t not in latest:
                unit = f" {r['unit']}" if r.get("unit") else ""
                latest[t] = f"{float(r['metric_value']):g}{unit}"
        return latest
    except Exception:
        return {}
    finally:
        try:
            db.close()
        except Exception:
            pass
