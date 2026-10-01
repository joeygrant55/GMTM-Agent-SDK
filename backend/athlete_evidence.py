"""Private, read-only facts for the linked athlete; no startup or provider work.

The first adapter deliberately exposes a narrow subset of GMTM: owner identity,
an explicit primary career, and current, public-marked numeric measurements.
Public flags permit this adapter's inclusion; they do not establish permission
to publish a new profile, independently verified performance, or selection.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import math
import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from auth import require_identity
from combine_api import _get_agent_db, _get_gmtm_db
from profile_owner import linked_profile_athlete as _linked_athlete
from source_scope import owner_scope


router = APIRouter(prefix="/api/athlete", tags=["Athlete evidence"])
MAX_SOURCE_MEASUREMENTS = 100
MAX_EVIDENCE = 20
PRIVATE_HEADERS = {"Cache-Control": "private, no-store", "Vary": "Authorization"}
SCOPE_LIMIT = (
    "This view includes supported current measurements marked public in GMTM, "
    "excluding unapproved suggestions and measurements from restricted digital events. "
    "Other profile evidence may exist outside this view."
)
TRUST_LIMIT = (
    "These are recorded profile values. Capture method and independent "
    "verification are unconfirmed; they do not establish eligibility, review, "
    "invitations or selection."
)

# Explicit title/unit compatibility, not the legacy results adapter's inferred
# units or event-dependent '20 Yard Shuttle' -> dash interpretation. No unit
# conversion, percentile, physical plausibility or cross-protocol comparison.
_UNITS = {
    "length": {"in": "inches", "inch": "inches", "inches": "inches",
               "cm": "cm", "centimeter": "cm", "centimeters": "cm"},
    "mass": {"lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
             "kg": "kg", "kilogram": "kg", "kilograms": "kg"},
    "time": {"s": "seconds", "sec": "seconds", "second": "seconds", "seconds": "seconds"},
    "count": {"rep": "repetitions", "reps": "repetitions", "repetition": "repetitions",
              "repetitions": "repetitions", "count": "repetitions"},
}
_MEASUREMENTS = {
    "height": ("Height", "length"), "weight": ("Weight", "mass"),
    "20 yard dash": ("20-Yard Dash", "time"),
    "20-yard dash": ("20-Yard Dash", "time"),
    "40 yard dash": ("40-Yard Dash", "time"),
    "40-yard dash": ("40-Yard Dash", "time"),
    "5-10-5 shuttle": ("5-10-5 Shuttle", "time"),
    "60 yard shuttle": ("60-Yard Shuttle", "time"),
    "60-yard shuttle": ("60-Yard Shuttle", "time"),
    "broad jump": ("Standing Broad Jump", "length"),
    "standing broad jump": ("Standing Broad Jump", "length"),
    "vertical jump": ("Vertical Jump", "length"),
    "push ups": ("Push-Ups", "count"), "push-ups": ("Push-Ups", "count"),
    "sit ups": ("Sit-Ups", "count"), "sit-ups": ("Sit-Ups", "count"),
}


class EvidenceSourceError(ValueError):
    """An invalid or inconsistent source cannot become personal evidence."""


def _text(value, limit=160):
    if not isinstance(value, str) or len(value) > limit:
        return None
    value = value.strip()
    if not value or any(unicodedata.category(char).startswith("C") for char in value):
        return None
    return value


def _owned(row, athlete_id):
    if (not isinstance(row, dict) or type(row.get("user_id")) is not int
            or row["user_id"] != athlete_id):
        raise EvidenceSourceError("Source ownership is inconsistent")


def _flag(value, expected):
    return type(value) is int and value == expected


def _recorded_at(value):
    if isinstance(value, datetime):
        # MySQL's naive datetime has no documented timezone. Preserve that
        # absence instead of silently labeling it UTC.
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and len(value) <= 40:
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                return date.fromisoformat(value).isoformat()
            if not re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", value):
                return None
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        except ValueError:
            pass
    return None


def _identity(db, athlete_id):
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT u.user_id, u.first_name, u.last_name, u.graduation_year,
                   l.city, l.province AS state
            FROM users u LEFT JOIN locations l ON l.location_id = u.location_id
            WHERE u.user_id = %s LIMIT 2
        """, (athlete_id,))
        rows = cursor.fetchall()
        if len(rows) != 1:
            raise EvidenceSourceError("Linked identity is unavailable")
        row = rows[0]
        _owned(row, athlete_id)
        name = " ".join(filter(None, (_text(row.get("first_name"), 100),
                                     _text(row.get("last_name"), 100)))) or None
        year = row.get("graduation_year")
        athlete = {
            "name": name, "sport": None, "position": None, "school": None,
            "city": _text(row.get("city")), "state": _text(row.get("state")),
            "graduation_year": year if type(year) is int and 1900 <= year <= 2200 else None,
        }
        cursor.execute("""
            SELECT c.user_id, c.career_id, c.is_primary, c.visibility,
                   c.approved, c.suggested_by, p.name AS position,
                   o.name AS school, s.name AS sport
            FROM career c
            LEFT JOIN user_positions up ON up.career_id = c.career_id AND up.is_primary = 1
            LEFT JOIN positions p ON p.position_id = up.position_id
            LEFT JOIN organizations o ON o.organization_id = c.organization_id
            LEFT JOIN sports s ON s.sport_id = c.sport_id
            WHERE c.user_id = %s AND c.is_primary = 1 AND c.visibility >= 0
              AND (c.approved = 1 OR c.suggested_by IS NULL)
            ORDER BY c.career_id DESC LIMIT 2
        """, (athlete_id,))
        careers = cursor.fetchall()
    for career in careers:
        _owned(career, athlete_id)
    # Multiple primary rows or primary positions are ambiguous. Do not choose
    # a career or call a fallback historic organization the athlete's school.
    if len(careers) == 1:
        career = careers[0]
        if (_flag(career.get("is_primary"), 1)
                and type(career.get("visibility")) is int and career["visibility"] >= 0
                and (_flag(career.get("approved"), 1) or career.get("suggested_by") is None)):
            athlete.update({field: _text(career.get(field)) for field in ("sport", "position", "school")})
    return athlete


def _metric_rows(db, athlete_id):
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT m.metric_id, m.user_id, m.title, m.value, m.unit,
                   m.created_on, m.is_current, m.visibility, m.user_approved,
                   m.suggested_by, m.event_id,
                   e.event_id AS public_event_id, e.name AS event_name,
                   e.published AS event_published, e.`public` AS event_public,
                   e.visibility AS event_visibility, e.invite_only AS event_invite_only,
                   e.product_id AS event_product_id, e.networks_only AS event_networks_only
            FROM metrics m
            LEFT JOIN events e ON e.event_id = m.event_id
              AND e.published = 1 AND e.`public` = 1 AND e.visibility = 2
              AND e.invite_only = 0 AND e.product_id IS NULL AND e.networks_only = 0
            WHERE m.user_id = %s AND m.is_current = 1 AND m.visibility = 2
              AND (m.user_approved = 1 OR (m.user_approved = 0 AND m.suggested_by IS NULL))
              AND (m.event_id IS NULL OR e.event_id IS NOT NULL)
            ORDER BY m.created_on DESC, m.metric_id DESC LIMIT %s
        """, (athlete_id, MAX_SOURCE_MEASUREMENTS + 1))
        rows = cursor.fetchall()
    if not isinstance(rows, (tuple, list)) or len(rows) > MAX_SOURCE_MEASUREMENTS + 1:
        raise EvidenceSourceError("Measurement bound was not respected")
    # Check ownership even for malformed, unsupported or overflow rows before
    # producing any response. Never rely on a fixture/driver honoring WHERE.
    for row in rows:
        _owned(row, athlete_id)
    return rows


def _measurement(row):
    required = {"metric_id", "title", "value", "unit", "created_on", "is_current", "visibility",
                "user_approved", "suggested_by", "event_id"}
    if not required.issubset(row):
        return None
    if (not _flag(row.get("is_current"), 1) or not _flag(row.get("visibility"), 2)
            or not (_flag(row.get("user_approved"), 1)
                    or (_flag(row.get("user_approved"), 0) and row.get("suggested_by") is None))):
        return None
    metric_id = row.get("metric_id")
    if type(metric_id) is not int or metric_id <= 0:
        return None
    title, unit = _text(row.get("title"), 75), _text(row.get("unit"), 25)
    spec = _MEASUREMENTS.get(title.casefold()) if title else None
    if not spec or not unit or unit.casefold() not in _UNITS[spec[1]]:
        return None
    raw = row.get("value")
    if (isinstance(raw, bool) or not isinstance(raw, (str, int, float, Decimal))
            or len(str(raw)) > 25):
        return None
    try:
        numeric = Decimal(str(raw).strip())
        value = float(numeric)
    except (ValueError, InvalidOperation, OverflowError):
        return None
    if (not math.isfinite(value) or not 0 <= value <= 1_000_000
            or (spec[1] != "count" and value == 0)
            or (spec[1] == "count" and numeric != numeric.to_integral_value())):
        return None
    # In-person event membership, source strings, score and verified flags are
    # intentionally not read. A public-marked metric remains usable as a
    # recorded fact, never as proof of event access or verified capture.
    item = {"id": f"metric-{metric_id}", "label": spec[0], "value": value,
            "unit": _UNITS[spec[1]][unit.casefold()],
            "recorded_at": _recorded_at(row.get("created_on")),
            "source_label": "GMTM profile measurement", "verification": "unconfirmed"}
    event_id = row.get("event_id")
    if event_id is not None:
        event_fields = {"public_event_id", "event_name", "event_published", "event_public",
                        "event_visibility", "event_invite_only", "event_product_id", "event_networks_only"}
        if (not event_fields.issubset(row) or type(event_id) is not int or event_id <= 0
                or type(row.get("public_event_id")) is not int or row["public_event_id"] != event_id
                or not _flag(row.get("event_published"), 1) or not _flag(row.get("event_public"), 1)
                or not _flag(row.get("event_visibility"), 2) or not _flag(row.get("event_invite_only"), 0)
                or not _flag(row.get("event_networks_only"), 0)
                or row.get("event_product_id") is not None):
            return None
        name = _text(row.get("event_name"), 300)
        if name:
            item["event_name"] = name
    return item


def _response(state, *, athlete=None, evidence=None, observations=None, limitations=None, status=200, scope=None):
    return JSONResponse({
        "state": state, "athlete": athlete, "evidence": evidence or [],
        "observations": observations or [], "limitations": limitations or [],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        **({"owner_scope": scope} if scope is not None else {}),
    }, status_code=status, headers=PRIVATE_HEADERS)


@router.get("/evidence")
def current_athlete_evidence(request: Request, caller_id: str = Depends(require_identity)):
    """Derive ownership on the server; user/event selectors are not supported."""
    if request.query_params:
        return JSONResponse({"detail": "This endpoint does not accept query parameters."},
                            status_code=400, headers=PRIVATE_HEADERS)
    scope = None
    try:
        agent = _get_agent_db()
        try:
            athlete_id = _linked_athlete(agent, caller_id)
        finally:
            agent.close()
        if athlete_id is None:
            return _response("unlinked", limitations=["Connect your GMTM athlete profile to view its recorded evidence."])
        scope = owner_scope(caller_id, athlete_id)
        source = _get_gmtm_db()
        try:
            athlete = _identity(source, athlete_id)
            rows = _metric_rows(source, athlete_id)
        finally:
            source.close()
    except HTTPException as error:
        return JSONResponse({"detail": error.detail}, status_code=error.status_code, headers=PRIVATE_HEADERS)
    except Exception:
        # Do not emit database errors, identifiers or partially read identity.
        return _response("source_unavailable", scope=scope, limitations=[
            "Profile evidence could not be loaded. This does not mean your profile has no evidence. Try again later."
        ])

    evidence, seen, omitted = [], set(), False
    for row in rows[:MAX_SOURCE_MEASUREMENTS]:
        item = _measurement(row)
        if item is None:
            omitted = True
            continue
        if item["id"] in seen:
            return _response("source_unavailable", scope=scope, limitations=["Conflicting measurement records could not be loaded."])
        seen.add(item["id"])
        evidence.append(item)
    limited = len(rows) > MAX_SOURCE_MEASUREMENTS or len(evidence) > MAX_EVIDENCE
    evidence = evidence[:MAX_EVIDENCE]
    limitations = [SCOPE_LIMIT, TRUST_LIMIT,
                   "This private view does not create a public profile link or establish permission to publish one."]
    if omitted:
        limitations.append("Some returned measurements were omitted because their type, value, unit or visibility could not be used safely.")
    if limited:
        limitations.append(f"This view is limited to {MAX_EVIDENCE} measurements from the {MAX_SOURCE_MEASUREMENTS} most recent eligible source rows.")
    if not all(athlete.get(field) for field in ("name", "sport", "position", "school")):
        limitations.append("Some identity or primary-career fields are missing or ambiguous; no fallback career or sport was inferred.")
    if any(item["recorded_at"] is None for item in evidence):
        limitations.append("Some measurements have no usable recorded date. Dates without an offset have no confirmed timezone.")
    elif evidence:
        limitations.append("Recorded dates without an offset have no confirmed timezone.")
    observations = []
    if evidence:
        labels = list(dict.fromkeys(item["label"] for item in evidence))
        observations.append({
            "title": "Recorded evidence available",
            "detail": f"{len(evidence)} shareable recorded measurement{'s' if len(evidence) != 1 else ''} in this view: {', '.join(labels)}.",
            "evidence_ids": [item["id"] for item in evidence],
        })
    else:
        limitations.append("No supported shareable recorded measurements were returned in this view. Other profile evidence may still exist.")
    return _response("ready", scope=scope, athlete=athlete, evidence=evidence, observations=observations, limitations=limitations)
