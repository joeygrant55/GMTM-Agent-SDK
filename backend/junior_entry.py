"""GMTM -> SPARQ junior entry: code exchange, Clerk ticket, entry gate, parent notice.

Inert on import. Every outside effect goes through a module-level seam that tests
replace: ``http`` (GMTM redeem + Clerk Backend API), ``store`` (Agent DB) and
``junior_eligibility.reader`` (read-only GMTM).

Flow: the Next server calls ``POST /gmtm-entry/exchange`` with the shared
``SPARQ_ENTRY_SECRET``. We redeem the one-use GMTM code, check eligibility, find
or create the Clerk user ``external_id = gmtm:<user_id>``, ensure the athlete link
row, record the entry time and return a 60-second Clerk sign-in ticket.

Each personal request from a gmtm-entry Clerk user passes ``gate``: entry is at
most 24 h old, eligibility still holds (10 min cache) and the parent notice is
accepted (the notice routes themselves are exempt).

Required Agent tables are in ``SCHEMA``. Prepare them separately; the app never
creates them. Refusals store only user_id, decision and time (no DOB).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from auth import require_clerk_id
import junior_eligibility

EXCHANGE_PATH = "/gmtm-entry/exchange"
NOTICE_PATH = "/api/athlete/parent-notice"
CLERK_API = "https://api.clerk.com/v1"
SESSION_MAX = timedelta(hours=24)
TICKET_SECONDS = 60
_OPAQUE = re.compile(r"[A-Za-z0-9_-]{16,512}\Z")

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS sparq_entry_refusals (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    decision VARCHAR(32) NOT NULL,
    decided_at DATETIME(6) NOT NULL,
    KEY idx_entry_refusals_user (user_id)
)""",
    """CREATE TABLE IF NOT EXISTS sparq_entries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    clerk_id VARBINARY(255) NOT NULL,
    user_id BIGINT NOT NULL,
    entered_at DATETIME(6) NOT NULL,
    KEY idx_entries_clerk (clerk_id, entered_at)
)""",
    """CREATE TABLE IF NOT EXISTS sparq_parent_notices (
    clerk_id VARBINARY(255) PRIMARY KEY,
    accepted_at DATETIME(6) NOT NULL,
    attested_by_session_kind VARCHAR(16) NOT NULL
)""",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


# ── HTTP seam (stdlib; the candidate image ships no extra HTTP dependency) ──────

def _urllib_http(method, url, *, headers, body=None, params=None):
    """Return (status, parsed JSON or None). Never raises for HTTP status codes."""
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method,
                                     headers={**headers, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status, raw = response.status, response.read(256 * 1024)
    except urllib.error.HTTPError as exc:
        return exc.code, None
    try:
        return status, json.loads(raw) if raw else None
    except ValueError:
        return status, None


http = _urllib_http


class EntryUnavailable(HTTPException):
    def __init__(self, status=503, detail="SPARQ sign-in is temporarily unavailable."):
        super().__init__(status_code=status, detail=detail)


ENTRY_KEYS = ("SPARQ_ENTRY_SECRET", "SPARQ_HANDOFF_SECRET", "GMTM_API_URL", "CLERK_SECRET_KEY")


def entry_configuration(env):
    """Pure check. None when entry is off (no key set); ValueError when partial or invalid."""
    values = {k: env.get(k, "").strip() for k in ENTRY_KEYS}
    if not any(values.values()):
        return None
    missing = [k for k, v in values.items() if not v]
    if missing:
        raise ValueError(f"GMTM entry needs {missing[0]}")
    try:
        url = urllib.parse.urlsplit(values["GMTM_API_URL"])
        host = url.hostname
    except ValueError:
        raise ValueError("GMTM_API_URL is malformed") from None
    loopback = host in ("localhost", "127.0.0.1", "::1")
    if (not host or url.username or url.password or url.query or url.fragment
            or not (url.scheme == "https" or (url.scheme == "http" and loopback))):
        raise ValueError("GMTM_API_URL must be https (http only for loopback)")
    return values


def _setting(name: str) -> str:
    try:
        values = entry_configuration(os.environ)
    except ValueError:
        values = None
    if not values:
        raise EntryUnavailable()
    return values[name]


# ── GMTM redeem ─────────────────────────────────────────────────────────────────

def redeem(code: str, state: str) -> int:
    base = _setting("GMTM_API_URL").rstrip("/")
    try:
        status, data = http("POST", f"{base}/v2/sparq/redeem",
                            headers={"x-sparq-secret": _setting("SPARQ_HANDOFF_SECRET")},
                            body={"code": code, "state": state})
    except OSError:
        raise EntryUnavailable(502) from None
    user_id = data.get("user_id") if isinstance(data, dict) else None
    if status != 200 or type(user_id) is not int or user_id <= 0:
        raise HTTPException(401, "This sign-in link is not valid. Open SPARQ from GMTM again.")
    return user_id


# ── Clerk Backend API ───────────────────────────────────────────────────────────

def _clerk(method, path, *, body=None, params=None):
    try:
        status, data = http(method, CLERK_API + path, body=body, params=params,
                            headers={"Authorization": "Bearer " + _setting("CLERK_SECRET_KEY")})
    except OSError:
        raise EntryUnavailable() from None
    if status not in (200, 201) or data is None:
        raise EntryUnavailable()  # e.g. 422 when the instance requires another identifier
    return data


def clerk_user_for(user_id: int) -> str:
    external_id = f"gmtm:{user_id}"
    found = _clerk("GET", "/users", params={"external_id": external_id})
    matches = [u for u in found if isinstance(u, dict) and u.get("external_id") == external_id] if isinstance(found, list) else None
    if matches is None or len(matches) > 1:
        raise HTTPException(409, "This account needs review before SPARQ can open.")
    # Clerk usernames: 4-64 chars of letters, digits, "_" or "-". gmtm_<id> fits.
    user = matches[0] if matches else _clerk("POST", "/users", body={
        "external_id": external_id, "username": f"gmtm_{user_id}", "skip_password_requirement": True})
    clerk_id = user.get("id") if isinstance(user, dict) else None
    if not isinstance(clerk_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,255}", clerk_id) \
            or user.get("external_id") != external_id:
        raise EntryUnavailable()
    return clerk_id


def clerk_ticket(clerk_id: str) -> str:
    data = _clerk("POST", "/sign_in_tokens", body={"user_id": clerk_id, "expires_in_seconds": TICKET_SECONDS})
    token = data.get("token") if isinstance(data, dict) else None
    if not isinstance(token, str) or not token:
        raise EntryUnavailable()
    return token


# ── Agent DB store ──────────────────────────────────────────────────────────────

class LinkConflict(HTTPException):
    def __init__(self):
        super().__init__(409, "This athlete is connected to another SPARQ account. Contact support.")


class MySQLStore:
    """Agent DB access; each call opens and closes its own connection."""

    def _db(self):
        from profile_api import _get_agent_db  # lazy
        return _get_agent_db()

    def _run(self, fn):
        db = self._db()
        try:
            with db.cursor() as c:
                result = fn(c)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def record_refusal(self, user_id, decision, at):
        self._run(lambda c: c.execute(
            "INSERT INTO sparq_entry_refusals (user_id, decision, decided_at) VALUES (%s, %s, %s)",
            (user_id, decision, at.replace(tzinfo=None))))

    def record_entry(self, clerk_id, user_id, at):
        self._run(lambda c: c.execute(
            "INSERT INTO sparq_entries (clerk_id, user_id, entered_at) VALUES (%s, %s, %s)",
            (clerk_id.encode(), user_id, at.replace(tzinfo=None))))

    def latest_entry(self, clerk_id):
        def read(c):
            c.execute("SELECT user_id, entered_at FROM sparq_entries WHERE clerk_id = %s "
                      "ORDER BY entered_at DESC LIMIT 1", (clerk_id.encode(),))
            row = c.fetchone()
            return None if row is None else {"user_id": int(row["user_id"]), "entered_at": _utc(row["entered_at"])}
        return self._run(read)

    def notice_accepted(self, clerk_id):
        def read(c):
            c.execute("SELECT 1 AS ok FROM sparq_parent_notices WHERE clerk_id = %s", (clerk_id.encode(),))
            return c.fetchone() is not None
        return self._run(read)

    def accept_notice(self, clerk_id, at):
        self._run(lambda c: c.execute(
            "INSERT INTO sparq_parent_notices (clerk_id, accepted_at, attested_by_session_kind) "
            "VALUES (%s, %s, 'unknown') ON DUPLICATE KEY UPDATE clerk_id = clerk_id",
            (clerk_id.encode(), at.replace(tzinfo=None))))

    def ensure_link(self, clerk_id, user_id):
        """Same lock name and no-overwrite insert as claim redemption (claims_api)."""
        lock = "sparq.claim." + hashlib.sha256(clerk_id.encode()).hexdigest()[:48]
        db = self._db()
        locked = False
        try:
            with db.cursor() as c:
                c.execute("SELECT GET_LOCK(%s, 5) AS acquired", (lock,))
                locked = (c.fetchone() or {}).get("acquired") == 1
                if not locked:
                    raise EntryUnavailable()
            db.begin()
            with db.cursor() as c:
                c.execute("SELECT user_id FROM athlete_profiles WHERE clerk_id = %s AND user_id <> %s LIMIT 1 FOR UPDATE",
                          (clerk_id, user_id))
                if c.fetchone():
                    raise LinkConflict()
                c.execute("INSERT INTO athlete_profiles (user_id, clerk_id) VALUES (%s, %s) "
                          "ON DUPLICATE KEY UPDATE user_id = user_id", (user_id, clerk_id))
                c.execute("SELECT clerk_id FROM athlete_profiles WHERE user_id = %s FOR UPDATE", (user_id,))
                owner = c.fetchone()
                if not owner or owner.get("clerk_id") != clerk_id:
                    raise LinkConflict()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            try:
                if locked:
                    with db.cursor() as c:
                        c.execute("SELECT RELEASE_LOCK(%s)", (lock,))
            finally:
                db.close()


store = MySQLStore()


# ── Exchange route (Next server only) ──────────────────────────────────────────

def _exchange(code: str, state: str) -> dict:
    # Validate every setting before redeem: a missing one must not burn the one-use code.
    try:
        if entry_configuration(os.environ) is None:
            raise EntryUnavailable()
    except ValueError:
        raise EntryUnavailable() from None
    user_id = redeem(code, state)
    try:
        eligible = junior_eligibility.is_eligible(user_id)
    except Exception:
        raise EntryUnavailable() from None
    now = _now()
    if not eligible:
        store.record_refusal(user_id, "ineligible", now)
        return {"eligible": False}
    clerk_id = clerk_user_for(user_id)
    store.ensure_link(clerk_id, user_id)
    try:
        from workspace_bootstrap import ensure_workspace_profile
        ensure_workspace_profile(clerk_id, user_id)
    except Exception:
        print("[gmtm-entry] workspace bootstrap failed")  # never log ids, codes or tickets
    store.record_entry(clerk_id, user_id, now)
    return {"eligible": True, "ticket": clerk_ticket(clerk_id)}


async def exchange(request: Request):
    expected = os.environ.get("SPARQ_ENTRY_SECRET", "").strip()
    if not expected:
        raise EntryUnavailable()
    supplied = request.headers.get("x-sparq-entry-secret", "")
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(401, "Not authorized.")
    try:
        body = await request.json()
    except ValueError:
        body = None
    code = body.get("code") if isinstance(body, dict) else None
    state = body.get("state") if isinstance(body, dict) else None
    if not all(isinstance(v, str) and _OPAQUE.fullmatch(v) for v in (code, state)):
        raise HTTPException(400, "Invalid entry request.")
    return JSONResponse(await run_in_threadpool(_exchange, code, state))


# ── Per-request gate (called by the profile admission boundary) ─────────────────

def _gate(clerk_id: str, path: str, now: datetime) -> bool:
    """Return False for non-entry users. Raise for denied gmtm-entry users."""
    entry = store.latest_entry(clerk_id)
    if entry is None:
        return False
    if not entry["entered_at"] <= now < entry["entered_at"] + SESSION_MAX:
        raise HTTPException(401, "Your SPARQ session ended. Open SPARQ from GMTM again.")
    if not junior_eligibility.is_eligible_cached(entry["user_id"]):
        raise HTTPException(403, "SPARQ is open to a small group of junior flag athletes right now.")
    if path != NOTICE_PATH and not store.notice_accepted(clerk_id):
        raise HTTPException(403, "parent_notice_required")
    return True


async def gate(clerk_id: str, path: str, *, now: datetime | None = None) -> bool:
    try:
        return await run_in_threadpool(_gate, clerk_id, path, now or _now())
    except HTTPException:
        raise
    except Exception:
        raise EntryUnavailable() from None


# ── Parent notice routes ────────────────────────────────────────────────────────

def _notice(clerk_id: str, accept: bool) -> dict:
    if store.latest_entry(clerk_id) is None:
        return {"required": False, "accepted": False}
    if accept:
        store.accept_notice(clerk_id, _now())
    return {"required": True, "accepted": store.notice_accepted(clerk_id)}


async def get_parent_notice(caller_clerk_id: str = Depends(require_clerk_id)):
    return await run_in_threadpool(_notice, caller_clerk_id, False)


async def accept_parent_notice(caller_clerk_id: str = Depends(require_clerk_id)):
    return await run_in_threadpool(_notice, caller_clerk_id, True)
