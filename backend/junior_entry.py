"""GMTM -> SPARQ entry: code exchange, SPARQ session, entry gate, parent notice.

GMTM sign-in is the only sign-in on every surface (Joey, 2026-10-01).

Inert on import. Every outside effect goes through a module-level seam that tests
replace: ``http`` (GMTM redeem), ``store`` (Agent DB) and
``junior_eligibility.reader`` (read-only GMTM).

Flow: the Next server calls ``POST /gmtm-entry/exchange`` with the shared
``SPARQ_ENTRY_SECRET`` and ``gsh`` = sha256 hex of the browser's GMTM sessionId.
We redeem the one-use GMTM code, check admission (profile: the junior gate; legacy
and combine: SPARQ_TEST_ALLOWLIST only), use the athlete's existing link id as the
subject (an id linked before October 2026 keeps all its rows reachable) or link
``gmtm_<user_id>`` for a new athlete, record the entry and return a 24 h HS256 SPARQ session token
(sub, jti, gsh, iat, exp) signed with ``SPARQ_SESSION_SECRET``. Only the newest
jti per user is active; a new entry or sign-out ends the old one.

``require_identity`` is the profile surface's authentication: a valid, unexpired,
active SPARQ token. ``require_allowlisted_identity`` (``auth.require_identity``) adds
the allow-list check for legacy and combine. Any other token is refused.

Each personal request from a gmtm-entry user passes ``gate``: entry is at
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
import secrets
import urllib.error
import urllib.parse
import urllib.request

from fastapi import Depends, Header, HTTPException, Request
import jwt
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

import junior_eligibility

EXCHANGE_PATH = "/gmtm-entry/exchange"
SIGN_OUT_PATH = "/gmtm-entry/sign-out"
NOTICE_PATH = "/api/athlete/parent-notice"
SESSION_MAX = timedelta(hours=24)
_OPAQUE = re.compile(r"[A-Za-z0-9_-]{16,512}\Z")
_GSH = re.compile(r"[0-9a-f]{64}\Z")
_CLAIMS = ("sub", "jti", "gsh", "iat", "exp", "aud")
SURFACES = ("profile", "combine", "legacy")

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
    KEY idx_entries_owner (clerk_id, entered_at)
)""",
    """CREATE TABLE IF NOT EXISTS sparq_parent_notices (
    clerk_id VARBINARY(255) PRIMARY KEY,
    accepted_at DATETIME(6) NOT NULL,
    attested_by_session_kind VARCHAR(16) NOT NULL
)""",
    """CREATE TABLE IF NOT EXISTS sparq_sessions (
    clerk_id VARBINARY(255) PRIMARY KEY,
    jti VARCHAR(64) NOT NULL,
    issued_at DATETIME(6) NOT NULL
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


ENTRY_KEYS = ("SPARQ_ENTRY_SECRET", "SPARQ_HANDOFF_SECRET", "GMTM_API_URL", "SPARQ_SESSION_SECRET")


def entry_configuration(env):
    """Pure check. None when entry is off (no key set); ValueError when partial or invalid."""
    values = {k: env.get(k, "").strip() for k in ENTRY_KEYS}
    if not any(values.values()):
        return None
    missing = [k for k, v in values.items() if not v]
    if missing:
        raise ValueError(f"GMTM entry needs {missing[0]}")
    if len(values["SPARQ_SESSION_SECRET"].encode()) < 32:
        raise ValueError("SPARQ_SESSION_SECRET must be at least 32 bytes")
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


# ── SPARQ session token ─────────────────────────────────────────────────────────

def subject_for(user_id: int) -> str:
    return f"gmtm_{user_id}"


def surface_of(app) -> str:
    """The app's token audience. Only create_app/main set it; anything else is legacy."""
    surface = getattr(app.state, "sparq_surface", "legacy")
    return surface if surface in SURFACES else "legacy"


def issue_session(sub: str, gsh: str, now: datetime, audience: str = "profile") -> str:
    """Sign a 24 h token for one surface (``aud``) and make its jti the only active one for ``sub``."""
    if audience not in SURFACES:
        raise ValueError("Unknown SPARQ surface")
    jti = secrets.token_urlsafe(32)
    iat = int(now.timestamp())
    token = jwt.encode({"sub": sub, "jti": jti, "gsh": gsh, "aud": audience, "iat": iat,
                        "exp": iat + int(SESSION_MAX.total_seconds())},
                       _setting("SPARQ_SESSION_SECRET"), algorithm="HS256")
    store.set_session(sub, jti, now)
    return token


def session_claims(token: str, audience: str) -> dict:
    """Signature, expiry, audience (surface) and shape only (no store read). 401 on any failure.
    A token issued for one surface is refused on every other surface."""
    try:
        secret = _setting("SPARQ_SESSION_SECRET")
    except EntryUnavailable:
        raise HTTPException(503, "SPARQ sign-in is temporarily unavailable.") from None
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], audience=audience,
                            options={"require": list(_CLAIMS)})
    except jwt.PyJWTError:
        raise HTTPException(401, "Your SPARQ session ended. Open SPARQ from GMTM again.") from None
    if not all(isinstance(claims.get(k), str) and claims[k] for k in ("sub", "jti", "gsh")) \
            or len(claims["sub"]) > 255 or not _GSH.fullmatch(claims["gsh"]):
        raise HTTPException(401, "Your SPARQ session ended. Open SPARQ from GMTM again.")
    return claims


def _active(claims: dict) -> str:
    active = store.session_jti(claims["sub"])
    if not isinstance(active, str) or not hmac.compare_digest(active.encode(), claims["jti"].encode()):
        raise HTTPException(401, "Your SPARQ session ended. Open SPARQ from GMTM again.")
    return claims["sub"]


async def require_identity(authorization: str | None = Header(default=None)) -> str:
    """Profile surface authentication: ONLY an active SPARQ session token. Returns sub."""
    return await _identity(authorization, "profile", _active)


def _allowlisted(claims: dict) -> str:
    sub = _active(claims)
    entry = store.latest_entry(sub)
    if entry is None or entry["user_id"] not in junior_eligibility.allowlist(os.environ):
        raise HTTPException(403, "SPARQ is not open to this account here.")
    return sub


async def require_allowlisted_identity(authorization: str | None, audience: str) -> str:
    """Legacy and combine: an active SPARQ session for this surface whose GMTM user is allow-listed."""
    return await _identity(authorization, audience, _allowlisted)


async def _identity(authorization, audience, check) -> str:
    parts = (authorization or "").split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(401, "Missing Authorization bearer token.")
    claims = session_claims(parts[1].strip(), audience)
    try:
        return await run_in_threadpool(check, claims)
    except HTTPException:
        raise
    except Exception:
        raise EntryUnavailable() from None


# ── Agent DB store ──────────────────────────────────────────────────────────────

class LinkConflict(HTTPException):
    """``gmtm_<id>`` already names another athlete row: data needs review."""
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

    def set_session(self, clerk_id, jti, at):
        self._run(lambda c: c.execute(
            "INSERT INTO sparq_sessions (clerk_id, jti, issued_at) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE jti = VALUES(jti), issued_at = VALUES(issued_at)",
            (clerk_id.encode(), jti, at.replace(tzinfo=None))))

    def session_jti(self, clerk_id):
        def read(c):
            c.execute("SELECT jti FROM sparq_sessions WHERE clerk_id = %s", (clerk_id.encode(),))
            row = c.fetchone()
            return None if row is None else row["jti"]
        return self._run(read)

    def end_session(self, clerk_id, jti):
        self._run(lambda c: c.execute("DELETE FROM sparq_sessions WHERE clerk_id = %s AND jti = %s",
                                      (clerk_id.encode(), jti)))

    def linked_owner_id(self, user_id):
        def read(c):
            c.execute("SELECT clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 1", (user_id,))
            row = c.fetchone()
            return None if row is None else row["clerk_id"]
        return self._run(read)

    def ensure_link(self, clerk_id, user_id):
        """Lock per subject and a no-overwrite insert: one athlete per subject, never repointed."""
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

def _exchange(code: str, state: str, gsh: str, junior: bool = True, audience: str = "profile") -> dict:
    # Validate every setting before redeem: a missing one must not burn the one-use code.
    try:
        if entry_configuration(os.environ) is None:
            raise EntryUnavailable()
    except ValueError:
        raise EntryUnavailable() from None
    user_id = redeem(code, state)
    try:
        # Profile: the junior gate. Legacy and combine: the allow-list only.
        eligible = (junior_eligibility.is_eligible(user_id) if junior
                    else user_id in junior_eligibility.allowlist(os.environ))
    except Exception:
        raise EntryUnavailable() from None
    now = _now()
    if not eligible:
        store.record_refusal(user_id, "ineligible", now)
        return {"eligible": False}
    # The GMTM session proves the person. An athlete already linked (an id from
    # before October 2026) keeps that id as the subject, so every row keyed by it
    # stays reachable. It is accepted only inside a SPARQ-signed token.
    sub = store.linked_owner_id(user_id) or subject_for(user_id)
    store.ensure_link(sub, user_id)
    try:
        from workspace_bootstrap import ensure_workspace_profile
        ensure_workspace_profile(sub, user_id)
    except Exception:
        print("[gmtm-entry] workspace bootstrap failed")  # never log codes or tokens
    store.record_entry(sub, user_id, now)
    return {"eligible": True, "token": issue_session(sub, gsh, now, audience)}


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
    gsh = body.get("gsh") if isinstance(body, dict) else None
    if not all(isinstance(v, str) and _OPAQUE.fullmatch(v) for v in (code, state)) \
            or not isinstance(gsh, str) or not _GSH.fullmatch(gsh):
        raise HTTPException(400, "Invalid entry request.")
    # Only the profile app sets entry_admission = "junior"; every other app is allow-list only.
    junior = getattr(request.app.state, "entry_admission", None) == "junior"
    return JSONResponse(await run_in_threadpool(_exchange, code, state, gsh, junior, surface_of(request.app)))


async def sign_out(request: Request, authorization: str | None = Header(default=None)):
    """Next server only: end the caller's active jti. Idempotent; never needs the gate."""
    parts = (authorization or "").split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(401, "Missing Authorization bearer token.")
    claims = session_claims(parts[1].strip(), surface_of(request.app))
    await run_in_threadpool(store.end_session, claims["sub"], claims["jti"])
    return {"signed_out": True}


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


async def get_parent_notice(caller_id: str = Depends(require_identity)):
    return await run_in_threadpool(_notice, caller_id, False)


async def accept_parent_notice(caller_id: str = Depends(require_identity)):
    return await run_in_threadpool(_notice, caller_id, True)
