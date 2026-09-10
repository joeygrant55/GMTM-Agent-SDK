"""Explicit, owner-bound exploration of a small reviewed opportunity collection.

No provider calls, website fetching, GMTM reads, writes, or import-time work.
Relevance describes the athlete's chosen search, not inferred ability/eligibility.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import re
from urllib.parse import urlsplit

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from auth import require_clerk_id
from combine_api import _get_agent_db
from athlete_evidence import PRIVATE_HEADERS
from athlete_workspace import WorkspaceError, _json, _owner, _revision, _close
from source_scope import owner_scope
from opportunity_catalog import RECORDS

MAX_BODY = 4096
HOSTS = {"usafootball.com", "www.usafootball.com", "gmtm.com", "events.usafootball.com", "iflag.org", "www.iflag.org"}
STATES = frozenset("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split())
FOCUSES = ("national_team", "competition", "any")
FACT_KEYS = {"dates", "location", "cost", "eligibility", "contact"}
KINDS = {"assessment", "event", "contact", "pathway"}
STATUSES = {"registration_open", "published_route", "check_details"}
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)\Z")


def _now():
    return datetime.now(timezone.utc)


def _error(status, code, detail):
    return JSONResponse({"code": code, "detail": detail}, status_code=status, headers=PRIVATE_HEADERS)


def _text(value, limit):
    return (isinstance(value, str) and 0 < len(value) <= limit and value == value.strip()
            and not re.search(r"[\x00-\x1f\x7f\ud800-\udfff]", value))


def _date(value):
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        raise ValueError("Invalid source time")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _url(value):
    if not isinstance(value, str) or len(value) > 2048 or re.search(r"[^\x21-\x7e]|[\\%?#]", value):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == "https" and parsed.netloc in HOSTS and bool(parsed.path) and "//" not in parsed.path and not any(p in {".", ".."} for p in parsed.path.split("/"))


def _references(value, known, *, optional=False):
    return (isinstance(value, list) and (optional or bool(value)) and len(value) <= 8
            and all(isinstance(x, str) and x in known for x in value) and len(set(value)) == len(value))


def validate_query(value):
    required = {"pathway", "category", "format", "link_revision"}
    optional = {"focus", "state", "entry"}
    if (not isinstance(value, dict) or not required <= set(value) or set(value) - required - optional
            or value["pathway"] != "adult_flag" or value["category"] not in ("men", "women", "unspecified")
            or value["format"] not in ("any", "remote", "in_person")
            or not isinstance(value["link_revision"], str) or not re.fullmatch(r"[a-f0-9]{64}", value["link_revision"])):
        raise ValueError("Invalid opportunity search")
    query = {"focus": "national_team", "state": None, "entry": "any", **value}
    if (query["focus"] not in FOCUSES or query["entry"] not in ("any", "individual", "team")
            or query["state"] is not None and (not isinstance(query["state"], str) or query["state"] not in STATES)):
        raise ValueError("Invalid opportunity constraints")
    return query


def _validated_record(record):
    """Structural/source-reference verification. Actual claims require source review."""
    fields = {"id", "title", "organization", "kind", "summary", "status", "valid_until", "facts", "action", "sources",
              "categories", "format", "opens_at", "closes_at", "focuses", "state", "participation"}
    if not isinstance(record, dict) or set(record) != fields:
        raise ValueError("Invalid reviewed record")
    for field, limit in (("id", 64), ("title", 180), ("organization", 120), ("summary", 300)):
        if not _text(record[field], limit):
            raise ValueError("Invalid record text")
    if (not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", record["id"]) or record["kind"] not in KINDS
            or record["status"] not in STATUSES or record["format"] not in ("remote", "in_person", "any")
            or not isinstance(record["categories"], list) or not record["categories"]
            or any(x not in ("men", "women") for x in record["categories"])
            or len(set(record["categories"])) != len(record["categories"])):
        raise ValueError("Invalid opportunity classification")
    if (not isinstance(record["focuses"], list) or not record["focuses"]
            or any(value not in FOCUSES[:2] for value in record["focuses"])
            or len(set(record["focuses"])) != len(record["focuses"])
            or record["participation"] not in ("individual", "team", "information")
            or record["state"] is not None and (not isinstance(record["state"], str) or record["state"] not in STATES)
            or record["format"] != "in_person" and record["state"] is not None):
        raise ValueError("Invalid opportunity constraints")
    valid_until = _date(record["valid_until"])
    if not isinstance(record["sources"], list) or not 1 <= len(record["sources"]) <= 8:
        raise ValueError("Sources required")
    known = {}
    for source in record["sources"]:
        if (not isinstance(source, dict) or set(source) != {"id", "title", "url", "checked_at", "expires_at"}
                or not _text(source["id"], 64) or not _text(source["title"], 180) or not _url(source["url"])
                or source["id"] in known or _date(source["checked_at"]) >= _date(source["expires_at"])
                or valid_until > _date(source["expires_at"])):
            raise ValueError("Invalid source reference")
        known[source["id"]] = source
    facts = record["facts"]
    if not isinstance(facts, list) or len(facts) != 5 or {f.get("key") for f in facts if isinstance(f, dict)} != FACT_KEYS:
        raise ValueError("All material fact fields required")
    for fact in facts:
        if (set(fact) != {"key", "label", "value", "source_ids"} or not _text(fact["label"], 80)
                or not _references(fact["source_ids"], known, optional=fact["value"] is None)
                or fact["value"] is not None and not _text(fact["value"], 600)
                or fact["value"] is None and fact["source_ids"]):
            raise ValueError("Unsupported fact")
    if (record["state"] is not None and not next(f for f in facts if f["key"] == "location")["value"]
            or record["participation"] in ("individual", "team") and not next(f for f in facts if f["key"] == "eligibility")["value"]):
        raise ValueError("Participation and location need published evidence")
    action = record["action"]
    if (not isinstance(action, dict) or set(action) != {"kind", "label", "href", "recipient", "purpose", "source_ids"}
            or action["kind"] not in ("open_source", "prepare_introduction") or not _text(action["label"], 100)
            or not _references(action["source_ids"], known) or not _url(action["href"])
            or action["href"] not in [known[x]["url"] for x in action["source_ids"]]):
        raise ValueError("Unsupported action")
    if action["kind"] == "prepare_introduction":
        contact = next(f for f in facts if f["key"] == "contact")
        if (not _text(action["recipient"], 200) or not _text(action["purpose"], 600)
                or contact["value"] is None or not set(action["source_ids"]) & set(contact["source_ids"])):
            raise ValueError("Introduction needs a sourced public recipient")
    elif action["recipient"] is not None or action["purpose"] is not None:
        raise ValueError("Unexpected introduction context")
    opens = _date(record["opens_at"]) if record["opens_at"] is not None else None
    closes = _date(record["closes_at"]) if record["closes_at"] is not None else None
    if opens and closes and opens >= closes:
        raise ValueError("Invalid opportunity window")
    if record["status"] == "registration_open" and (not opens or not closes or not next(f for f in facts if f["key"] == "dates")["value"]):
        raise ValueError("Open registration requires reviewed dates")
    return record


def reviewed_shortlist(query, records, now):
    query = validate_query(query)
    if now.tzinfo is None or now.utcoffset().total_seconds() != 0:
        raise ValueError("UTC review clock required")
    if not isinstance(records, (tuple, list)) or len(records) > 30:
        raise ValueError("Collection bound exceeded")
    items, seen, omitted = [], set(), False
    for raw in records:
        record = _validated_record(raw)
        if record["id"] in seen:
            raise ValueError("Duplicate reviewed record")
        seen.add(record["id"])
        if (query["category"] != "unspecified" and query["category"] not in record["categories"]
                or query["format"] != "any" and record["format"] != query["format"]
                or query["focus"] != "any" and query["focus"] not in record["focuses"]
                or query["entry"] != "any" and record["participation"] not in (query["entry"], "information")
                or query["state"] is not None and record["format"] == "in_person" and record["state"] != query["state"]):
            continue
        if (now >= _date(record["valid_until"]) or any(now < _date(s["checked_at"]) or now >= _date(s["expires_at"]) for s in record["sources"])
                or record["closes_at"] is not None and now >= _date(record["closes_at"])
                or record["opens_at"] is not None and now < _date(record["opens_at"])):
            omitted = True
            continue
        item = deepcopy({k: record[k] for k in record if k not in {"categories", "format", "opens_at", "closes_at", "focuses", "state"}})
        if record["closes_at"] is not None:
            item["valid_until"] = min(_date(item["valid_until"]), _date(record["closes_at"])).isoformat()
        scope = "adult flag football" if query["category"] == "unspecified" else f"adult {query['category']}'s flag football"
        item["relevance"] = f"You chose {scope}. " + ({"assessment": "This is a published assessment route.", "event": "This is a published in-person opportunity.", "contact": "This official contact can clarify the pathway and its requirements.", "pathway": "This published pathway helps you identify the next participation step."}[item["kind"]])
        if record["kind"] == "event":
            location = f" in {record['state']}" if record["state"] else ""
            item["relevance"] = f"For your {scope} competition search: an in-person event{location}. " + (
                "Enter with a team; confirm your division and roster requirements." if record["participation"] == "team" else "Review the participation requirements before planning travel.")
        elif record["kind"] == "contact" and record["focuses"] == ["competition"]:
            item["relevance"] = f"For your {scope} competition search: ask this organizer about team access and participation requirements."
        items.append(item)
    limitations = ["This reviewed collection covers adult flag football. Options follow your search choices, not an assessment of your ability or eligibility.",
                   "Competition events are separate from national-team evaluations. Inclusion does not establish a USA Football or Olympic qualification route."]
    if query["state"] is not None:
        limitations.append("Travel destination filters in-person events by their published state; remote options remain available. Your home location was not inferred.")
    if len(items) > 3:
        limitations.append(f"Showing 3 of {len(items)} current options. Choose a search focus to narrow the collection.")
    if omitted:
        limitations.append("Some records are outside their reviewed dates and are not shown.")
    if not items:
        limitations.append("No current reviewed options match these filters. Try another format; no opportunity has been invented to fill the list.")
    return items[:3], limitations


def search_opportunities(clerk_id, query):
    query = validate_query(query)
    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as cursor:
            owner = _owner(cursor, clerk_id)
        revision = _revision(owner)
        if query["link_revision"] != revision:
            raise WorkspaceError(409, "workspace_link_changed", "Your profile connection changed. Reload your saved work.")
    finally:
        _close(db)
    now = _now()
    items, limitations = reviewed_shortlist(query, RECORDS, now)
    return {"state": "ready", "owner_scope": owner_scope(clerk_id, owner["user_id"]), "link_revision": revision,
            "generated_at": now.isoformat(), "items": items, "limitations": limitations}


async def current_athlete_opportunities(request: Request, clerk_id: str = Depends(require_clerk_id)):
    async def read_body():
        data = bytearray()
        async for part in request.stream():
            data.extend(part)
            if len(data) > MAX_BODY:
                raise ValueError("Body too large")
        return bytes(data)
    try:
        if request.query_params or request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise ValueError("Expected JSON")
        query = validate_query(_json(await asyncio.wait_for(read_body(), timeout=10)))
    except (ValueError, WorkspaceError, asyncio.TimeoutError):
        return _error(400, "opportunities_invalid", "Choose a supported pathway, category and format.")
    try:
        return JSONResponse(await run_in_threadpool(search_opportunities, clerk_id, query), headers=PRIVATE_HEADERS)
    except WorkspaceError as exc:
        return _error(exc.status, exc.code, exc.detail)
    except Exception:
        return _error(503, "opportunities_unavailable", "The reviewed opportunity collection is unavailable. Your profile and draft are unchanged.")
