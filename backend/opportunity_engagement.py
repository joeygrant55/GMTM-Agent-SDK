"""Optional first-party opportunity measurement; no import-time I/O or storage.

Accepted records are emitted as one structured stdout line. This is a best-effort
log sink, not a durable conversion ledger. Export/retention must be verified at
deployment. The real-owner acceptance launcher intentionally blocks this route.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
import sys
from threading import Lock
import time
import uuid

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from auth import require_clerk_id
from athlete_evidence import PRIVATE_HEADERS
from athlete_workspace import WorkspaceError, _json, _owner, _revision, _close
from combine_api import _get_agent_db
from athlete_opportunities import _validated_record, _date
from opportunity_catalog import RECORDS

PREFIX = "SPARQ_OPPORTUNITY_ENGAGEMENT "
KINDS = ("card_visible", "details_opened", "outbound_activated")
MAX_BODY = 1024
_EMIT_LOCK = Lock()
CONFIG_KEYS = (
    "OPPORTUNITY_ENGAGEMENT_ENABLED", "OPPORTUNITY_ENGAGEMENT_COHORT",
    "OPPORTUNITY_ENGAGEMENT_PERIOD", "OPPORTUNITY_ENGAGEMENT_SECRET",
    "OPPORTUNITY_ENGAGEMENT_EXCLUDED_IDS", "OPPORTUNITY_ENGAGEMENT_PILOT_IDS",
)


@dataclass(frozen=True)
class Configuration:
    cohort: str
    period: str
    secret: bytes = field(repr=False)
    excluded_ids: frozenset[int] = field(repr=False)
    pilot_ids: frozenset[int] = field(repr=False)


def _ids(raw):
    if not isinstance(raw, str) or len(raw) > 17000:
        raise ValueError("Invalid engagement account classification")
    if not raw:
        return frozenset()
    parts = raw.split(",")
    if len(parts) > 1000 or any(not re.fullmatch(r"[1-9][0-9]{0,15}", p) or int(p) > 9_007_199_254_740_991 for p in parts):
        raise ValueError("Invalid engagement account classification")
    return frozenset(map(int, parts))


def validate_configuration(env):
    enabled = env.get("OPPORTUNITY_ENGAGEMENT_ENABLED", "false")
    if enabled in ("", "false"):
        return None
    if enabled != "true":
        raise ValueError("OPPORTUNITY_ENGAGEMENT_ENABLED must be true or false")
    cohort = env.get("OPPORTUNITY_ENGAGEMENT_COHORT", "internal")
    period = env.get("OPPORTUNITY_ENGAGEMENT_PERIOD", "")
    secret = env.get("OPPORTUNITY_ENGAGEMENT_SECRET", "")
    if cohort not in ("fixture", "internal", "pilot"):
        raise ValueError("Invalid engagement cohort")
    if not isinstance(period, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", period) or len(period) > 64:
        raise ValueError("Set a bounded engagement measurement period")
    if not isinstance(secret, str) or not re.fullmatch(r"[a-f0-9]{64}", secret):
        raise ValueError("Set a dedicated 32-byte hex engagement secret")
    excluded = _ids(env.get("OPPORTUNITY_ENGAGEMENT_EXCLUDED_IDS", "")) | {2}
    pilot = _ids(env.get("OPPORTUNITY_ENGAGEMENT_PILOT_IDS", ""))
    if cohort == "pilot" and not pilot - excluded:
        raise ValueError("Pilot measurement requires an explicit admitted account list")
    return Configuration(cohort, period, bytes.fromhex(secret), frozenset(excluded), pilot)


class RateLimit:
    """Bounded, process-local load protection, not a distributed anti-abuse ledger."""
    def __init__(self):
        self.lock, self.window, self.accounts, self.total = Lock(), None, {}, 0

    def admit(self, account, now=None):
        window = int((time.monotonic() if now is None else now) // 60)
        with self.lock:
            if window != self.window:
                self.window, self.accounts, self.total = window, {}, 0
            if self.total >= 6000 or self.accounts.get(account, 0) >= 60:
                return False
            if account not in self.accounts and len(self.accounts) >= 2048:
                return False
            self.accounts[account] = self.accounts.get(account, 0) + 1
            self.total += 1
            return True


def _request(value):
    keys = {"event_id", "opportunity_id", "kind", "link_revision", "reviewed_at"}
    if not isinstance(value, dict) or set(value) != keys or any(not isinstance(v, str) for v in value.values()):
        raise ValueError("Invalid engagement event")
    try:
        event_id = uuid.UUID(value["event_id"])
    except (ValueError, AttributeError):
        raise ValueError("Invalid engagement occurrence") from None
    if (event_id.version != 4 or str(event_id) != value["event_id"]
            or value["kind"] not in KINDS
            or not re.fullmatch(r"[a-f0-9]{64}", value["link_revision"])
            or len(value["opportunity_id"]) > 64
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value["opportunity_id"])):
        raise ValueError("Invalid engagement event")
    _date(value["reviewed_at"])
    return value


def _current_record(value, now):
    candidates = [r for r in RECORDS if r["id"] == value["opportunity_id"]]
    if len(candidates) != 1:
        raise ValueError("Unknown opportunity")
    record = _validated_record(candidates[0])
    if (now >= _date(record["valid_until"])
            or any(now < _date(s["checked_at"]) or now >= _date(s["expires_at"]) for s in record["sources"])
            or record["opens_at"] is not None and now < _date(record["opens_at"])
            or record["closes_at"] is not None and now >= _date(record["closes_at"])
            or value["reviewed_at"] != record["sources"][0]["checked_at"]
            or value["kind"] == "outbound_activated" and record["action"]["kind"] != "open_source"):
        raise ValueError("Unavailable opportunity event")
    return record


def _emit(record):
    # Only allowlisted fields reach this sink. No general request/body logging.
    line = PREFIX + json.dumps(record, separators=(",", ":"), sort_keys=True, allow_nan=False) + "\n"
    if len(line.encode("utf-8")) > 8192:
        raise ValueError("Engagement log record exceeds its bound")
    # Worker threads must not split or interleave a record and its newline.
    with _EMIT_LOCK:
        sys.stdout.write(line)
        sys.stdout.flush()


def capture(clerk_id, value, config, limiter, *, now=None, emit=None):
    value = _request(value)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset().total_seconds() != 0:
        raise ValueError("UTC engagement clock required")
    record = _current_record(value, now)
    throttle_key = hmac.new(config.secret, ("throttle:" + clerk_id).encode(), hashlib.sha256).hexdigest()
    if not limiter.admit(throttle_key):
        raise HTTPException(429, "Engagement measurement is temporarily limited.")
    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as cursor:
            owner = _owner(cursor, clerk_id)
        if value["link_revision"] != _revision(owner):
            raise WorkspaceError(409, "workspace_link_changed", "Your profile connection changed.")
    finally:
        _close(db)
    cohort = config.cohort
    if owner["user_id"] in config.excluded_ids or cohort == "pilot" and owner["user_id"] not in config.pilot_ids:
        cohort = "internal"
    pseudonym = hmac.new(config.secret, f"opportunity-v1:{config.period}:{cohort}:{owner['user_id']}".encode(), hashlib.sha256).hexdigest()
    event = {
        "schema": 1, "at": now.isoformat().replace("+00:00", "Z"),
        "catalog_revision": hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "opportunity_id": record["id"], "kind": value["kind"], "event_id": value["event_id"],
        "cohort": cohort, "account": pseudonym, "measurement_period": config.period,
        "destination_kind": "event_page" if record["kind"] == "event" else "contact_page" if record["kind"] == "contact" else "program_page",
    }
    from profile_admission import recheck_admission
    recheck_admission()
    (emit or _emit)(event)


def enabled_configuration(request: Request):
    config = getattr(request.app.state, "opportunity_engagement_configuration", None)
    if config is None:
        raise HTTPException(404, "Engagement measurement is disabled.")
    return config


async def current_opportunity_engagement(request: Request,
        config: Configuration = Depends(enabled_configuration), clerk_id: str = Depends(require_clerk_id)):
    async def read_body():
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_BODY:
                raise ValueError("Engagement body too large")
        return bytes(data)
    try:
        if request.query_params or request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise ValueError("Expected bounded JSON")
        value = _request(_json(await asyncio.wait_for(read_body(), timeout=5)))
        await run_in_threadpool(capture, clerk_id, value, config, request.app.state.opportunity_engagement_limiter)
    except (ValueError, asyncio.TimeoutError):
        return JSONResponse({"code": "engagement_invalid"}, status_code=400, headers=PRIVATE_HEADERS)
    except WorkspaceError as error:
        return JSONResponse({"code": error.code}, status_code=error.status, headers=PRIVATE_HEADERS)
    except HTTPException:
        raise
    except Exception:
        # Best effort for the product; do not leak identity, settings or sink errors.
        return JSONResponse({"code": "engagement_unavailable"}, status_code=503, headers=PRIVATE_HEADERS)
    return Response(status_code=204, headers=PRIVATE_HEADERS)
