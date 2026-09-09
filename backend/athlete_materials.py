"""Bounded owner-only submission results and footage; no media/provider access.

Submission answers are self-reports, not verified tests. Source visibility and
link flags constrain draft inclusion; they never establish selection or
successful playback. Importing this module performs no I/O or schema work.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re
from urllib.parse import urlsplit
from source_scope import owner_scope

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from auth import require_clerk_id
from combine_api import _get_agent_db, _get_gmtm_db, _linked_athlete
from athlete_evidence import PRIVATE_HEADERS, _MEASUREMENTS, _UNITS, _recorded_at, _text


router = APIRouter(prefix="/api/athlete", tags=["Athlete materials"])
MAX_SOURCE_ROWS = 50
MAX_PAYLOAD_BYTES = 65536
MAX_QUESTIONS = 40
MAX_RESULTS = 20
MAX_FILMS = 10
MAX_THUMBNAIL_BYTES = 2048
_RASTER_FILE = r"[A-Za-z0-9_-][A-Za-z0-9_.-]*\.(?i:jpg|jpeg|png|webp)"
_CDN_THUMBNAIL_PATH = re.compile(
    rf"(?:videos/film/thumbnails/|videos/events/([1-9][0-9]{{0,15}})/edited-thumbnails/"
    rf"|users/([1-9][0-9]{{0,15}})/uploads/){_RASTER_FILE}\Z")
_YOUTUBE_THUMBNAIL_PATH = re.compile(rf"vi/[A-Za-z0-9_-]{{11}}/{_RASTER_FILE}\Z")
_TIME_FORMATS = {"ss.00", "time (ss.00)", "mm:ss", "time (mm:ss)",
                 "mm:ss.00", "time (mm:ss.00)", "hh:mm:ss", "time (hh:mm:ss)", "time"}


class MaterialsSourceError(ValueError):
    """An inconsistent source cannot be projected as personal material."""


def _positive(value):
    return type(value) is int and 0 < value <= 9_007_199_254_740_991


def _visibility(value):
    return type(value) is int and value in (0, 1, 2, 3, 4, 5)


def _flag(value, expected):
    return type(value) is int and value == expected


def _approved(row, prefix=""):
    needed = {prefix + "approved", prefix + "suggested_by", prefix + "suggested_by_org_id"}
    if not needed.issubset(row):
        return False
    return (_flag(row[prefix + "approved"], 1)
            or (_flag(row[prefix + "approved"], 0) and row[prefix + "suggested_by"] is None
                and row.get(prefix + "suggested_by_org_id") is None))


def _rows(cursor):
    rows = cursor.fetchall()
    if not isinstance(rows, (list, tuple)) or len(rows) > MAX_SOURCE_ROWS + 1:
        raise MaterialsSourceError("Source row bound was not respected")
    if not all(isinstance(row, dict) for row in rows):
        raise MaterialsSourceError("Source rows are malformed")
    return rows


def _submission_rows(db, athlete_id):
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT s.task_submission_id, s.user_id, s.task_id, s.created_on, s.visibility,
                   CASE WHEN OCTET_LENGTH(s.payload) <= 65536 THEN s.payload ELSE NULL END AS payload,
                   OCTET_LENGTH(s.payload) AS payload_bytes,
                   t.task_id AS joined_task_id, t.event_id, t.title AS task_title,
                   t.visibility AS task_visibility, e.event_id AS joined_event_id,
                   e.name AS event_name, e.visibility AS event_visibility,
                   e.published AS event_published, e.`public` AS event_public,
                   e.invite_only AS event_invite_only, e.networks_only AS event_networks_only,
                   e.product_id AS event_product_id
            FROM event_task_submissions s
            LEFT JOIN event_tasks t ON t.task_id = s.task_id
            LEFT JOIN events e ON e.event_id = t.event_id
            WHERE s.user_id = %s AND s.visibility IN (0,1,2,3,4,5)
              AND NOT EXISTS (
                  SELECT 1 FROM event_task_submissions newer
                  WHERE newer.user_id = s.user_id AND newer.task_id = s.task_id
                    AND newer.visibility IN (0,1,2,3,4,5)
                    AND (newer.created_on > s.created_on
                         OR (newer.created_on = s.created_on
                             AND newer.task_submission_id > s.task_submission_id))
              )
            ORDER BY s.created_on DESC, s.task_submission_id DESC LIMIT %s
        """, (athlete_id, MAX_SOURCE_ROWS + 1))
        return _rows(cursor)


def _submitted_film_rows(db, athlete_id):
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT s.user_id AS user_id, f.film_id, f.user_id AS direct_user_id, f.career_id,
                   f.task_submission_id, f.title, f.published_on, f.visibility,
                   f.approved, f.suggested_by, f.suggested_by_org_id,
                   f.service,
                   CASE WHEN OCTET_LENGTH(f.thumbnail_uri) <= 2048 THEN f.thumbnail_uri ELSE NULL END AS thumbnail_uri,
                   f.processed, f.dead_link, f.challenge_id, f.event_id AS film_event_id,
                   f.in_person_event_id, c.career_id AS joined_career_id,
                   c.user_id AS career_user_id, c.visibility AS career_visibility,
                   c.approved AS career_approved, c.suggested_by AS career_suggested_by,
                   c.suggested_by_org_id AS career_suggested_by_org_id,
                   s.task_submission_id AS joined_submission_id, s.user_id AS submission_user_id,
                   s.task_id, s.visibility AS submission_visibility,
                   t.task_id AS joined_task_id, t.event_id, t.title AS task_title,
                   t.visibility AS task_visibility, e.event_id AS joined_event_id,
                   e.name AS event_name, e.visibility AS event_visibility,
                   e.published AS event_published, e.`public` AS event_public,
                   e.invite_only AS event_invite_only, e.networks_only AS event_networks_only,
                   e.product_id AS event_product_id
            FROM film f
            JOIN event_task_submissions s ON s.task_submission_id = f.task_submission_id
            LEFT JOIN career c ON c.career_id = f.career_id
            LEFT JOIN event_tasks t ON t.task_id = s.task_id
            LEFT JOIN events e ON e.event_id = t.event_id
            WHERE s.user_id = %s AND f.visibility IN (0,1,2,3,4,5)
              AND f.challenge_id IS NULL
            ORDER BY f.published_on DESC, f.film_id DESC LIMIT %s
        """, (athlete_id, MAX_SOURCE_ROWS + 1))
        return _rows(cursor)


def _direct_film_rows(db, athlete_id):
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT f.user_id AS user_id, f.film_id, f.user_id AS direct_user_id, f.career_id,
                   f.task_submission_id, f.title, f.published_on, f.visibility,
                   f.approved, f.suggested_by, f.suggested_by_org_id,
                   f.service,
                   CASE WHEN OCTET_LENGTH(f.thumbnail_uri) <= 2048 THEN f.thumbnail_uri ELSE NULL END AS thumbnail_uri,
                   f.processed, f.dead_link, f.challenge_id, f.event_id AS film_event_id,
                   f.in_person_event_id, c.career_id AS joined_career_id,
                   c.user_id AS career_user_id, c.visibility AS career_visibility,
                   c.approved AS career_approved, c.suggested_by AS career_suggested_by,
                   c.suggested_by_org_id AS career_suggested_by_org_id,
                   e.event_id AS joined_event_id, e.name AS event_name,
                   e.visibility AS event_visibility, e.published AS event_published,
                   e.`public` AS event_public, e.invite_only AS event_invite_only,
                   e.networks_only AS event_networks_only, e.product_id AS event_product_id
            FROM film f
            LEFT JOIN career c ON c.career_id = f.career_id
            LEFT JOIN events e ON e.event_id = f.event_id
              AND e.published = 1 AND e.`public` = 1 AND e.visibility = 2
              AND e.invite_only = 0 AND e.networks_only = 0 AND e.product_id IS NULL
            WHERE f.user_id = %s AND f.task_submission_id IS NULL
              AND f.visibility IN (0,1,2,3,4,5) AND f.challenge_id IS NULL
            ORDER BY f.published_on DESC, f.film_id DESC LIMIT %s
        """, (athlete_id, MAX_SOURCE_ROWS + 1))
        return _rows(cursor)


def _career_film_rows(db, athlete_id):
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT c.user_id AS user_id, f.film_id, f.user_id AS direct_user_id, f.career_id,
                   f.task_submission_id, f.title, f.published_on, f.visibility,
                   f.approved, f.suggested_by, f.suggested_by_org_id,
                   f.service,
                   CASE WHEN OCTET_LENGTH(f.thumbnail_uri) <= 2048 THEN f.thumbnail_uri ELSE NULL END AS thumbnail_uri,
                   f.processed, f.dead_link, f.challenge_id, f.event_id AS film_event_id,
                   f.in_person_event_id, c.career_id AS joined_career_id,
                   c.user_id AS career_user_id, c.visibility AS career_visibility,
                   c.approved AS career_approved, c.suggested_by AS career_suggested_by,
                   c.suggested_by_org_id AS career_suggested_by_org_id,
                   e.event_id AS joined_event_id, e.name AS event_name,
                   e.visibility AS event_visibility, e.published AS event_published,
                   e.`public` AS event_public, e.invite_only AS event_invite_only,
                   e.networks_only AS event_networks_only, e.product_id AS event_product_id
            FROM film f
            JOIN career c ON c.career_id = f.career_id
            LEFT JOIN events e ON e.event_id = f.event_id
              AND e.published = 1 AND e.`public` = 1 AND e.visibility = 2
              AND e.invite_only = 0 AND e.networks_only = 0 AND e.product_id IS NULL
            WHERE c.user_id = %s AND f.user_id IS NULL AND f.task_submission_id IS NULL
              AND f.visibility IN (0,1,2,3,4,5) AND f.challenge_id IS NULL
            ORDER BY f.published_on DESC, f.film_id DESC LIMIT %s
        """, (athlete_id, MAX_SOURCE_ROWS + 1))
        return _rows(cursor)


def _same_id(left, right):
    return _positive(left) and _positive(right) and left == right


def _source_owner(value, athlete_id):
    if not _same_id(value, athlete_id):
        raise MaterialsSourceError("Source ownership is inconsistent")


def _submission_scope(row, athlete_id):
    _source_owner(row.get("user_id"), athlete_id)
    return (_positive(row.get("task_submission_id")) and _visibility(row.get("visibility"))
            and _same_id(row.get("task_id"), row.get("joined_task_id"))
            and _visibility(row.get("task_visibility"))
            and _same_id(row.get("event_id"), row.get("joined_event_id"))
            and _visibility(row.get("event_visibility")))


def _public_event(row):
    return (all(_flag(row.get(key), value) for key, value in (
                ("event_visibility", 2), ("event_published", 1), ("event_public", 1),
                ("event_invite_only", 0), ("event_networks_only", 0)))
            and "event_product_id" in row and row["event_product_id"] is None)


def _source_label(row, default):
    event = _text(row.get("event_name"), 200)
    task = _text(row.get("task_title"), 160)
    label = " · ".join(part for part in (event, task) if part)
    return label if label and len(label) <= 300 else default


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate answer keys")
        result[key] = value
    return result


def _questions(row):
    size = row.get("payload_bytes")
    if type(size) is not int or not 0 < size <= MAX_PAYLOAD_BYTES:
        return None
    raw = row.get("payload")
    try:
        if isinstance(raw, dict):
            raw = json.dumps(raw, ensure_ascii=False, allow_nan=False)
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            return None
        data = json.loads(raw, object_pairs_hook=_unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (TypeError, ValueError, OverflowError, RecursionError):
        return None
    questions = data.get("questions") if isinstance(data, dict) else None
    return questions if isinstance(questions, dict) and len(questions) <= MAX_QUESTIONS else None


def _numeric_result(question, key):
    if not isinstance(question, dict) or question.get("type") != "metric":
        return None
    if "key" in question and question["key"] != key:
        return None
    if not isinstance(key, str) or not key.startswith("metric:"):
        return None
    title = _text(key.partition(":")[2], 75)
    spec = _MEASUREMENTS.get(title.casefold()) if title else None
    value = question.get("value")
    if not spec or not isinstance(value, dict):
        return None
    unit = _text(value.get("unit"), 30)
    raw = value.get("value")
    if (not unit or isinstance(raw, bool) or not isinstance(raw, (str, int, float, Decimal))
            or len(str(raw)) > 25):
        return None
    try:
        number = Decimal(str(raw).strip())
        converted = float(number)
    except (InvalidOperation, ValueError, OverflowError):
        return None
    if (not math.isfinite(converted) or not 0 <= converted <= 1_000_000
            or (spec[1] != "count" and converted == 0)
            or (spec[1] == "count" and number != number.to_integral_value())):
        return None
    normalized_unit = _UNITS[spec[1]].get(unit.casefold())
    if not normalized_unit and spec[1] == "time" and unit.casefold() in _TIME_FORMATS:
        # GMTM MetricInput stores all documented formatted-time inputs in ms.
        # Preserve that explicit storage unit; do not apply an inferred factor.
        if number != number.to_integral_value():
            return None
        normalized_unit = "milliseconds"
    if not normalized_unit:
        return None
    return title, {"value": converted, "unit": normalized_unit}


def _submission_items(row):
    questions = _questions(row)
    if questions is None:
        return [], True
    items, omitted = [], False
    for key, question in questions.items():
        result = _numeric_result(question, key)
        if result is None:
            omitted = True
            continue
        title, numeric = result
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        items.append({
            "id": f"submission-{row['task_submission_id']}-{digest}",
            "kind": "submitted_result", "title": title,
            "source_label": _source_label(row, "Your GMTM submission"),
            "recorded_at": _recorded_at(row.get("created_on")), "date_label": "Submitted",
            "result": numeric, "source_url": None, "thumbnail_url": None,
            "can_include": (_flag(row.get("visibility"), 2)
                            and _flag(row.get("task_visibility"), 2) and _public_event(row)),
            "availability": "recorded",
        })
    return items, omitted


def _film_scope(row, athlete_id, path):
    _source_owner(row.get("user_id"), athlete_id)
    required = {"film_id", "direct_user_id", "career_id", "joined_career_id", "career_user_id",
                "task_submission_id", "film_event_id", "in_person_event_id", "challenge_id",
                "approved", "suggested_by", "suggested_by_org_id", "visibility",
                "processed", "dead_link"}
    # Validate every returned ownership reference before any omission, even if
    # another source field would make this row unusable or it is an overflow.
    for key in ("direct_user_id", "career_user_id", "submission_user_id"):
        if row.get(key) is not None:
            _source_owner(row[key], athlete_id)
    if path == "submission":
        _source_owner(row.get("submission_user_id"), athlete_id)
    elif path == "direct":
        _source_owner(row.get("direct_user_id"), athlete_id)
    elif path == "career":
        _source_owner(row.get("career_user_id"), athlete_id)
    else:
        raise MaterialsSourceError("Unknown film source")
    if not required.issubset(row) or not _positive(row.get("film_id")):
        return False
    if not _absent_event(row["film_event_id"]) and not _positive(row["film_event_id"]):
        return False
    if (not _visibility(row["visibility"]) or row["challenge_id"] is not None
            or not _approved(row)):
        return False
    if row["career_id"] is not None:
        if (not _same_id(row["career_id"], row["joined_career_id"])
                or row["career_user_id"] is None or not _visibility(row.get("career_visibility"))
                or not _approved(row, "career_")):
            return False
    elif any(row.get(key) is not None for key in ("joined_career_id", "career_user_id")):
        return False
    if path == "submission":
        if (not _same_id(row["task_submission_id"], row.get("joined_submission_id"))
                or not _visibility(row.get("submission_visibility"))
                or not _same_id(row.get("task_id"), row.get("joined_task_id"))
                or not _visibility(row.get("task_visibility"))
                or not _same_id(row.get("event_id"), row.get("joined_event_id"))
                or not _visibility(row.get("event_visibility"))):
            return False
        if not _absent_event(row["film_event_id"]) and not _same_id(row["film_event_id"], row["event_id"]):
            return False
    elif (row["task_submission_id"] is not None
          or (path == "career" and row["direct_user_id"] is not None)):
        return False
    return True


def _absent_event(value):
    # film.event_id has the documented historical default 0.
    return value is None or _flag(value, 0)


def _thumbnail_url(row):
    """Normalize a stored raster key without fetching or inventing a thumbnail.

    Source families: GMTM generate-thumbnail/index.js:66 and legacy
    thumbnail-extractor/index.js:57-58; film.resolver.js:438-458,1547 supplies
    service hosts and YouTube's vi path. The eleven-character video ID and
    raster/ASCII restrictions deliberately omit other legacy formats.
    """
    service, raw = row.get("service"), row.get("thumbnail_uri")
    if (service not in ("gmtm", "s3", "youtube", "youtu") or not isinstance(raw, str)
            or not 0 < len(raw) <= MAX_THUMBNAIL_BYTES or not raw.isascii()
            or any(ord(char) < 33 or ord(char) > 126 for char in raw)
            or any(char in raw for char in ("?", "#", "%", "\\"))):
        return None
    host = "cdn.gmtm.com" if service in ("gmtm", "s3") else "i.ytimg.com"
    if raw.startswith("https://"):
        try:
            parsed = urlsplit(raw)
        except ValueError:
            return None
        if parsed.netloc != host or parsed.query or parsed.fragment:
            return None
        path = parsed.path[1:] if parsed.path.startswith("/") else ""
    else:
        path = raw
    matcher = _CDN_THUMBNAIL_PATH if host == "cdn.gmtm.com" else _YOUTUBE_THUMBNAIL_PATH
    match = matcher.fullmatch(path)
    if not match:
        return None
    if host == "cdn.gmtm.com" and any(value is not None and not _positive(int(value)) for value in match.groups()):
        return None
    canonical = f"https://{host}/{path}"
    return canonical if len(canonical) <= MAX_THUMBNAIL_BYTES else None


def _film_item(row, path):
    event_id = row.get("event_id") if path == "submission" else row.get("film_event_id")
    event_known = _absent_event(event_id) or _same_id(event_id, row.get("joined_event_id"))
    event_public = _absent_event(event_id) or (event_known and _public_event(row))
    public = (_flag(row.get("visibility"), 2) and event_public
              and row.get("in_person_event_id") is None)
    # The career proves ownership only; no career metadata is exported. GMTM's
    # public Highlights query gates the film's visibility, not its career's.
    if path == "submission":
        public = public and _flag(row.get("submission_visibility"), 2) and _flag(row.get("task_visibility"), 2)
    unavailable = _flag(row.get("dead_link"), 1)
    # Legacy GMTM uploads can persist processed=0 while the API presents the
    # same film as processed=1. This flag cannot establish an active processing
    # state or playback. Inclusion adds only a public canonical page reference.
    link_not_marked_dead = row.get("dead_link") is None or _flag(row.get("dead_link"), 0)
    can_include = bool(public and link_not_marked_dead)
    return {
        "id": f"film-{row['film_id']}", "kind": "footage",
        "title": _text(row.get("title"), 160) or "Untitled footage",
        "source_label": (_source_label(row, "Your GMTM footage")
                         if (path == "submission" or (not _absent_event(event_id) and event_public))
                         else "Your GMTM footage"),
        "recorded_at": _recorded_at(row.get("published_on")), "date_label": "Published",
        "result": None,
        "source_url": None if unavailable else f"https://gmtm.com/film/{row['film_id']}",
        "can_include": can_include,
        "thumbnail_url": _thumbnail_url(row) if can_include else None,
        "availability": "unavailable" if unavailable else "unchecked",
    }


def _response(state, items=None, limitations=None, scope=None):
    return JSONResponse({"state": state, "items": items or [], "limitations": limitations or [],
                         "fetched_at": datetime.now(timezone.utc).isoformat(),
                         **({"owner_scope": scope} if scope is not None else {})}, headers=PRIVATE_HEADERS)


def _project(submissions, films, athlete_id):
    results, footage, seen_tasks, seen_films = [], [], set(), set()
    omitted, limited = False, len(submissions) > MAX_SOURCE_ROWS
    for index, row in enumerate(submissions):
        valid = _submission_scope(row, athlete_id)
        task_id = row.get("task_id")
        if _positive(task_id):
            if task_id in seen_tasks:
                raise MaterialsSourceError("Conflicting latest submission snapshots")
            seen_tasks.add(task_id)
        if index >= MAX_SOURCE_ROWS:
            continue
        if not valid:
            omitted = True
            continue
        items, skipped = _submission_items(row)
        results.extend(items)
        omitted = omitted or skipped
    for path, rows in films:
        limited = limited or len(rows) > MAX_SOURCE_ROWS
        for index, row in enumerate(rows):
            valid = _film_scope(row, athlete_id, path)
            film_id = row.get("film_id")
            if _positive(film_id):
                if film_id in seen_films:
                    raise MaterialsSourceError("Conflicting film sources")
                seen_films.add(film_id)
            if index >= MAX_SOURCE_ROWS:
                continue
            if not valid:
                omitted = True
                continue
            footage.append(_film_item(row, path))
    limited = limited or len(results) > MAX_RESULTS or len(footage) > MAX_FILMS
    # Each query already orders latest-first. A stable sort merges the three
    # footage streams without pretending naive SQL dates have a UTC offset.
    footage.sort(key=lambda item: (item["recorded_at"] or "", int(item["id"][5:])), reverse=True)
    limitations = [
        "Submitted results are self-reported records, not verified tests or selection outcomes. Submission dates are not measurement or last-edit dates.",
        "This view includes supported numeric submission answers and owned footage records. Other answers, footage and profile evidence may exist outside this view.",
        "Restricted material is private context and cannot be included in a draft here. Public source flags do not publish a new profile.",
        "Footage has not been played or analyzed. Unavailable means GMTM marks the link dead; every other footage record is unchecked. Legacy processing flags do not establish active processing or playback.",
        "Dates without an offset have no confirmed timezone. Formatted GMTM time inputs are shown in their stored milliseconds.",
    ]
    if omitted:
        limitations.append("Some source records or answer types were omitted because their ownership, shape, visibility or unit was unsupported or incomplete.")
    if limited:
        limitations.append("This view is limited to 20 submitted results and 10 footage records from up to 50 recent rows in each source path.")
    return results[:MAX_RESULTS] + footage[:MAX_FILMS], limitations


@router.get("/materials")
def current_athlete_materials(request: Request, caller_clerk_id: str = Depends(require_clerk_id)):
    if request.query_params:
        return JSONResponse({"detail": "This endpoint does not accept query parameters."},
                            status_code=400, headers=PRIVATE_HEADERS)
    scope = None
    try:
        agent = _get_agent_db()
        try:
            athlete_id = _linked_athlete(agent, caller_clerk_id)
        finally:
            agent.close()
        if athlete_id is None:
            return _response("unlinked", limitations=["Connect your GMTM athlete profile to view its existing material."])
        scope = owner_scope(caller_clerk_id, athlete_id)
        source = _get_gmtm_db()
        try:
            submissions = _submission_rows(source, athlete_id)
            films = [("submission", _submitted_film_rows(source, athlete_id)),
                     ("direct", _direct_film_rows(source, athlete_id)),
                     ("career", _career_film_rows(source, athlete_id))]
        finally:
            source.close()
        items, limitations = _project(submissions, films, athlete_id)
        return _response("ready", items, limitations, scope=scope)
    except HTTPException as error:
        return JSONResponse({"detail": error.detail}, status_code=error.status_code, headers=PRIVATE_HEADERS)
    except Exception:
        return _response("source_unavailable", scope=scope, limitations=[
            "Existing material could not be loaded. This does not mean your profile has no submissions or footage. Try again later."
        ])
