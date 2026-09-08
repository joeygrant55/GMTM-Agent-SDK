"""Authenticated, read-only current-combine context, independent of bootstrap.

Only reviewed public USA Football events are supported. Public definitions do
not establish enrollment; personal observations always use the server link.
There is no schema setup, connection, model work, or background work at import.
"""

from datetime import datetime, timezone
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Response
import pymysql

from auth import require_clerk_id
from combine_requirements import (
    MAX_TASKS, SourceDefinitionError, parse_activities, project_activity,
    source_int, source_text, source_timestamp,
)


router = APIRouter(prefix="/api/combine", tags=["Combine"])
SUPPORTED_EVENTS = {1317: "junior", 1318: "adult"}
ORGANIZATION_ID = 249002
DEADLINE_SOURCE_URL = "https://usafootball.com/national-team/digital-combine"


def _get_agent_db():
    return pymysql.connect(
        host=os.getenv("AGENT_DB_HOST", "mysql.railway.internal"),
        port=int(os.getenv("AGENT_DB_PORT", "3306")),
        user=os.getenv("AGENT_DB_USER", "root"),
        password=os.getenv("AGENT_DB_PASSWORD", ""),
        database=os.getenv("AGENT_DB_NAME", "railway"),
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5, read_timeout=10, write_timeout=10,
    )


def _get_gmtm_db():
    host, user = os.getenv("DB_HOST"), os.getenv("DB_USER")
    if not host or not user or "pre-prod" in host.casefold():
        raise SourceDefinitionError("GMTM source is not configured")
    return pymysql.connect(
        host=host, user=user, password=os.getenv("DB_PASSWORD"),
        database="gmtm", port=3306, cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5, read_timeout=10, write_timeout=10,
    )


def _linked_athlete(db, clerk_id):
    conflict = "The athlete link needs review before personal combine status can be shown."

    def owned_id(row):
        # Legacy SQL collations may match another case-sensitive Clerk subject.
        # Require the exact owner and an actual integer ID, as recovery does.
        athlete_id = row.get("user_id") if isinstance(row, dict) else None
        if (type(athlete_id) is not int or athlete_id <= 0
                or row.get("clerk_id") != clerk_id):
            raise HTTPException(status_code=409, detail=conflict)
        return athlete_id

    with db.cursor() as cursor:
        cursor.execute(
            "SELECT user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2",
            (clerk_id,),
        )
        rows = cursor.fetchall()
        if len(rows) > 1:
            raise HTTPException(status_code=409, detail=conflict)
        if not rows:
            return None
        athlete_id = owned_id(rows[0])
        cursor.execute(
            "SELECT user_id, clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 2",
            (athlete_id,),
        )
        owners = cursor.fetchall()
        if len(owners) != 1 or owned_id(owners[0]) != athlete_id:
            raise HTTPException(status_code=409, detail=conflict)
        return athlete_id


def _claim_event(db, clerk_id, athlete_id):
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT event_id FROM claim_tokens
            WHERE clerk_id = %s AND user_id = %s AND claimed_at IS NOT NULL
              AND event_id IN (%s, %s)
            LIMIT 3
        """, (clerk_id, athlete_id, *SUPPORTED_EVENTS))
        rows = cursor.fetchall()
    # Malformed/unexpected rows must not turn into an apparently unique choice.
    try:
        events = {source_int(row.get("event_id"), minimum=1) for row in rows}
    except SourceDefinitionError:
        return None
    if len(events) == 1 and events.issubset(SUPPORTED_EVENTS):
        return next(iter(events))
    return None


def _public_events(db):
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT event_id, name, organization_id, published, `public`, visibility,
                   invite_only, product_id, end_date
            FROM events
            WHERE event_id IN (%s, %s) AND organization_id = %s
              AND published = 1 AND `public` = 1 AND visibility = 2
              AND invite_only = 0 AND product_id IS NULL
            ORDER BY event_id LIMIT 3
        """, (*SUPPORTED_EVENTS, ORGANIZATION_ID))
        rows = cursor.fetchall()
    if len(rows) > len(SUPPORTED_EVENTS):
        raise SourceDefinitionError("Conflicting event definitions")
    events = {}
    for row in rows:
        event_id = source_int(row.get("event_id"), minimum=1)
        if event_id not in SUPPORTED_EVENTS or event_id in events:
            raise SourceDefinitionError("Conflicting event identity")
        if (source_int(row.get("organization_id")) != ORGANIZATION_ID
                or source_int(row.get("published")) != 1
                or source_int(row.get("public")) != 1
                or source_int(row.get("visibility"), minimum=-1) != 2
                or source_int(row.get("invite_only")) != 0
                or row.get("product_id") is not None):
            # Defense in depth: a source no longer satisfying the public gate
            # is unavailable, even if a driver/adapter returned it anyway.
            continue
        events[event_id] = {
            "event_id": event_id, "name": source_text(row.get("name"), limit=500),
            "division": SUPPORTED_EVENTS[event_id],
            "continuation_url": f"https://gmtm.com/virtuals/{event_id}",
            "deadline_display": "September 21, 2026",
            "deadline_source_url": DEADLINE_SOURCE_URL,
            "configured_end": source_timestamp(row.get("end_date")),
        }
    return events


def _activities(db, event_id):
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT task_id, event_id, title, type, list_order, description, payload, visibility
            FROM event_tasks
            WHERE event_id = %s AND visibility = 2
            ORDER BY list_order, task_id LIMIT %s
        """, (event_id, MAX_TASKS + 1))
        return parse_activities(cursor.fetchall(), event_id)


def _submissions(db, athlete_id, event_id, activities):
    task_ids = tuple(activity.task_id for activity in activities)
    placeholders = ", ".join(["%s"] * len(task_ids))
    with db.cursor() as cursor:
        # Select one latest visible attempt per task before applying the bound.
        # A malformed newest payload remains unknown; an older answer cannot
        # silently make the current attempt appear complete.
        cursor.execute(f"""
            SELECT s.task_submission_id, s.user_id, s.task_id, s.payload,
                   s.created_on, s.visibility, t.event_id
            FROM event_task_submissions s
            JOIN event_tasks t ON t.task_id = s.task_id
            WHERE s.user_id = %s AND t.event_id = %s AND t.visibility = 2
              AND s.visibility > 0 AND s.task_id IN ({placeholders})
              AND NOT EXISTS (
                  SELECT 1 FROM event_task_submissions newer
                  WHERE newer.user_id = s.user_id AND newer.task_id = s.task_id
                    AND newer.visibility > 0
                    AND (newer.created_on > s.created_on
                         OR (newer.created_on = s.created_on
                             AND newer.task_submission_id > s.task_submission_id))
              )
            ORDER BY s.task_id LIMIT %s
        """, (athlete_id, event_id, *task_ids, MAX_TASKS + 1))
        rows = cursor.fetchall()
    if len(rows) > len(task_ids):
        raise SourceDefinitionError("Conflicting submission observations")
    submissions = {}
    for row in rows:
        task_id = source_int(row.get("task_id"), minimum=1)
        if (task_id not in task_ids or task_id in submissions
                or source_int(row.get("user_id"), minimum=1) != athlete_id
                or source_int(row.get("event_id"), minimum=1) != event_id
                or source_int(row.get("visibility"), minimum=1) < 1
                or row.get("created_on") is None):
            raise SourceDefinitionError("Invalid submission scope")
        source_int(row.get("task_submission_id"), minimum=1)
        submissions[task_id] = row
    return submissions


def load_current_combine(clerk_id: str, event_id: int | None = None):
    """Load the same authoritative read-only snapshot for HTTP and scoped help.

    Callers must obtain clerk_id from authentication, never from request data.
    This function performs no bootstrap, schema setup, model call, or write.
    """
    if event_id is not None and event_id not in SUPPORTED_EVENTS:
        raise HTTPException(status_code=404, detail="This combine is not available.")
    agent_db = gmtm_db = None
    try:
        agent_db = _get_agent_db()
        athlete_id = _linked_athlete(agent_db, clerk_id)
        selected_id = event_id
        if selected_id is None and athlete_id is not None:
            selected_id = _claim_event(agent_db, clerk_id, athlete_id)
        gmtm_db = _get_gmtm_db()
        events = _public_events(gmtm_db)
        if event_id is not None and event_id not in events:
            raise HTTPException(status_code=404, detail="This combine is not available.")
        selected = events.get(selected_id)
        activities = []
        if selected is not None:
            definitions = _activities(gmtm_db, selected["event_id"])
            submissions = (_submissions(gmtm_db, athlete_id, selected["event_id"], definitions)
                           if athlete_id is not None else {})
            activities = [project_activity(activity, submissions.get(activity.task_id),
                                            personal_available=athlete_id is not None)
                          for activity in definitions]
        observed = athlete_id is not None and selected is not None
        return {
            "schema_version": 1, "clerk_id": clerk_id, "athlete_id": athlete_id,
            "state": "link_required" if athlete_id is None else "ready" if selected else "choose_event",
            "athlete_id_status": "unknown",
            "events": [{key: event[key] for key in ("event_id", "name", "division", "continuation_url")}
                       for _, event in sorted(events.items())],
            "selected_event": selected, "activities": activities,
            "counts": {
                "activities": len(activities),
                "submitted": sum(item["submission_state"] == "submitted" for item in activities) if observed else None,
                "fields_present": sum(item["evidence_state"] == "fields_present" for item in activities) if observed else None,
            },
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception:
        # Never turn connection/schema/definition failures into zero submissions,
        # and never return driver errors or private answer contents to the caller.
        raise HTTPException(status_code=503, detail="Combine information is temporarily unavailable. Please try again.") from None
    finally:
        for connection in (gmtm_db, agent_db):
            if connection is not None:
                connection.close()


@router.get("/current")
def current_combine(
    response: Response,
    event_id: int | None = Query(default=None),
    clerk_id: str = Depends(require_clerk_id),
):
    response.headers["Cache-Control"] = "private, no-store"
    return load_current_combine(clerk_id, event_id)
