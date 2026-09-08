"""
Claim tokens — the GMTM-to-SPARQ door (cohort-one spec, workstream 2a).

A combine submitter gets one signed link. Opening it shows a landing page with their
first name and the event name; redeeming it (after Clerk sign-up) links their GMTM
`user_id` to their Clerk id without replacing an existing owner's mapping.

Routes
    POST /api/claims/mint            admin (header X-Claims-Admin = CLAIMS_ADMIN_SECRET)
    GET  /api/claims/{token}         public — {valid, first_name, event_name, claimed}
    POST /api/claims/{token}/redeem  Clerk-authed — writes athlete_profiles, marks claimed

Token format
    base64url(json{"u": user_id, "e": event_id, "x": exp_unix}) + "." + base64url(HMAC-SHA256)
    Signed with SHARE_TOKEN_SECRET (already a required env var). Only sha256(token) is
    stored in `claim_tokens`, prepared explicitly in the separate Agent DB.

Status semantics
    400  malformed token or bad signature (tampered)
    410  signature valid but expired
    409  ownership conflict or another claim is being acquired; safe to retry
    404  token not minted here / GMTM user missing

The pure token helpers (`mint_token`, `verify_token`, `token_hash`) have no DB or
FastAPI dependency so they can be unit-tested without a connection.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import List, Optional

import pymysql
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from auth import require_clerk_id
from profile_api import _get_agent_db, _get_gmtm_db
from workspace_bootstrap import ensure_workspace_profile

router = APIRouter(prefix="/api", tags=["Claims"])

CLAIM_TTL_SECONDS = 30 * 24 * 3600  # spec: exp 30 days
DEFAULT_FRONTEND_URL = "https://sparq-agent.vercel.app"


# ── Pure token helpers (no DB, no FastAPI) ──────────────────────────────────

class ClaimTokenError(Exception):
    """Raised by verify_token. `code` is one of: malformed, bad_signature, expired."""

    STATUS = {"malformed": 400, "bad_signature": 400, "expired": 410}

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code

    @property
    def status_code(self) -> int:
        return self.STATUS.get(self.code, 400)


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    padding = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def _sign(payload: bytes, secret: bytes) -> str:
    return _b64e(hmac.new(secret, payload, hashlib.sha256).digest())


def mint_token(user_id: int, event_id: int, secret: bytes, exp: Optional[int] = None,
               now: Optional[float] = None) -> str:
    """Build a signed claim token. `exp` is a unix timestamp; default now + 30 days."""
    if exp is None:
        exp = int((now if now is not None else time.time()) + CLAIM_TTL_SECONDS)
    payload = json.dumps(
        {"u": int(user_id), "e": int(event_id), "x": int(exp)}, separators=(",", ":")
    ).encode()
    return f"{_b64e(payload)}.{_sign(payload, secret)}"


def verify_token(token: str, secret: bytes, now: Optional[float] = None) -> dict:
    """Return {"user_id", "event_id", "exp"} or raise ClaimTokenError.

    Signature is checked before expiry so a tampered-but-expired token is a 400, not a 410.
    """
    if not token or not isinstance(token, str) or len(token) > 512:
        raise ClaimTokenError("malformed")
    parts = token.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ClaimTokenError("malformed")
    payload_b64, provided_sig = parts
    try:
        payload = _b64d(payload_b64)
    except Exception:
        raise ClaimTokenError("malformed")
    expected_sig = _sign(payload, secret)
    if not hmac.compare_digest(provided_sig, expected_sig):
        raise ClaimTokenError("bad_signature")
    try:
        data = json.loads(payload.decode())
        user_id = int(data["u"])
        event_id = int(data["e"])
        exp = int(data["x"])
    except Exception:
        # Signed by us but not our shape — treat as a bad token, not a server error.
        raise ClaimTokenError("malformed")
    current = now if now is not None else time.time()
    if current >= exp:
        raise ClaimTokenError("expired")
    return {"user_id": user_id, "event_id": event_id, "exp": exp}


def token_hash(token: str) -> str:
    """sha256 hex of the full token — the only thing persisted."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── Config ──────────────────────────────────────────────────────────────────

def _get_share_secret() -> bytes:
    secret = os.getenv("SHARE_TOKEN_SECRET", "").strip()
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Claim links are not configured (SHARE_TOKEN_SECRET unset).",
        )
    return secret.encode()


def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", DEFAULT_FRONTEND_URL).strip().rstrip("/") or DEFAULT_FRONTEND_URL


def _require_admin(x_claims_admin: Optional[str]) -> None:
    expected = os.getenv("CLAIMS_ADMIN_SECRET", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Claim minting is not configured (CLAIMS_ADMIN_SECRET unset).")
    if not x_claims_admin or not hmac.compare_digest(x_claims_admin.strip(), expected):
        raise HTTPException(status_code=401, detail="Invalid admin secret.")


# ── Helpers ─────────────────────────────────────────────────────────────────

def _verify_or_http(token: str) -> dict:
    try:
        return verify_token(token, _get_share_secret())
    except ClaimTokenError as e:
        raise HTTPException(status_code=e.status_code, detail={"valid": False, "reason": e.code})


def _lookup_claim_row(c, thash: str, *, for_update: bool = False) -> dict:
    c.execute(
        "SELECT id, user_id, event_id, opened_at, claimed_at, clerk_id FROM claim_tokens WHERE token_hash = %s"
        + (" FOR UPDATE" if for_update else ""),
        (thash,),
    )
    row = c.fetchone()
    if not row:
        # Signed correctly but never minted here (or revoked by deleting the row).
        raise HTTPException(status_code=404, detail={"valid": False, "reason": "unknown"})
    return row


def _gmtm_names(user_id: int, event_id: int) -> tuple[Optional[str], Optional[str]]:
    """(first_name, event_name) from GMTM. Never reads email or last name."""
    gmtm = _get_gmtm_db()
    try:
        with gmtm.cursor() as c:
            c.execute("SELECT first_name FROM users WHERE user_id = %s", (user_id,))
            u = c.fetchone()
            c.execute("SELECT name FROM events WHERE event_id = %s", (event_id,))
            ev = c.fetchone()
        return (u["first_name"] if u else None, ev["name"] if ev else None)
    finally:
        gmtm.close()


# ── Routes ──────────────────────────────────────────────────────────────────

class MintRequest(BaseModel):
    user_ids: List[int] = Field(..., min_length=1, max_length=5000)
    event_id: int


@router.post("/claims/mint")
async def mint_claims(request: MintRequest, x_claims_admin: Optional[str] = Header(default=None)):
    """Admin-only. One signed claim link per GMTM user_id. Stores only the token hash."""
    _require_admin(x_claims_admin)
    secret = _get_share_secret()
    base = _frontend_url()
    now = time.time()
    out = []
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            for uid in dict.fromkeys(request.user_ids):  # dedupe, keep order
                exp = int(now + CLAIM_TTL_SECONDS)
                token = mint_token(uid, request.event_id, secret, exp=exp)
                c.execute(
                    """INSERT INTO claim_tokens (token_hash, user_id, event_id, expires_at)
                       VALUES (%s, %s, %s, %s)""",
                    (token_hash(token), uid, request.event_id, datetime.fromtimestamp(exp, timezone.utc).replace(tzinfo=None)),
                )
                out.append({"user_id": uid, "token": token, "url": f"{base}/claim/{token}"})
        db.commit()
    finally:
        db.close()
    return out


@router.get("/claims/{token}")
async def get_claim(token: str):
    """Public landing data. Logs first open (opened_at) — the funnel's 'opened' signal."""
    data = _verify_or_http(token)
    thash = token_hash(token)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            row = _lookup_claim_row(c, thash)
            if row["opened_at"] is None:
                c.execute(
                    "UPDATE claim_tokens SET opened_at = NOW() WHERE id = %s AND opened_at IS NULL",
                    (row["id"],),
                )
                db.commit()
    finally:
        db.close()

    first_name, event_name = _gmtm_names(data["user_id"], data["event_id"])
    if first_name is None:
        raise HTTPException(status_code=404, detail={"valid": False, "reason": "unknown_user"})
    return {
        "valid": True,
        "first_name": first_name,
        "event_name": event_name or "digital combine",
        "claimed": row["claimed_at"] is not None,
    }


@router.post("/claims/{token}/redeem")
async def redeem_claim(token: str, caller_clerk_id: str = Depends(require_clerk_id)):
    """Atomically acquire one athlete mapping and claim; same-owner retries are safe.

    Requires transactional tables and UNIQUE athlete_profiles.user_id. The existing
    Clerk index is not unique, so cooperating claim writers also serialize by Clerk
    on the same MySQL server. GET_LOCK is session-scoped, not transaction-scoped:
    https://dev.mysql.com/doc/refman/8.0/en/locking-functions.html
    Keep the lock until commit/rollback and release it on this exact connection.
    """
    data = _verify_or_http(token)
    thash = token_hash(token)
    # Application-prefixed, opaque and below MySQL's 64-character name limit.
    lock_name = "sparq.claim." + hashlib.sha256(caller_clerk_id.encode()).hexdigest()[:48]
    db = _get_agent_db()
    lock_acquired = False
    try:
        with db.cursor() as c:
            c.execute("SELECT GET_LOCK(%s, 0) AS acquired", (lock_name,))
            lock = c.fetchone()
            if not lock or lock.get("acquired") != 1:
                raise HTTPException(
                    status_code=409,
                    detail="Your connection could not be acquired. Please retry the secure invitation.",
                )
            lock_acquired = True
        db.begin()
        with db.cursor() as c:
            # Same-token contenders must read the latest committed claimant.
            row = _lookup_claim_row(c, thash, for_update=True)
            if (int(row["user_id"]), int(row["event_id"])) != (data["user_id"], data["event_id"]):
                raise HTTPException(status_code=400, detail={"valid": False, "reason": "mismatch"})
            if row["clerk_id"] not in (None, caller_clerk_id) or (
                row["claimed_at"] is not None and row["clerk_id"] is None
            ):
                raise HTTPException(status_code=409, detail="This invitation is already connected to another account.")
            user_id = int(row["user_id"])
            # The workspace assumes one athlete per Clerk. Do not silently select a
            # second athlete or repair historical ambiguous mappings during a claim.
            c.execute(
                "SELECT user_id FROM athlete_profiles WHERE clerk_id = %s AND user_id <> %s LIMIT 1 FOR UPDATE",
                (caller_clerk_id, user_id),
            )
            if c.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail="This account is already connected to a different athlete. Use the correct account or contact support.",
                )
            # Different tokens for the same athlete contend on UNIQUE user_id.
            # A duplicate is deliberately a no-op: never overwrite its owner.
            c.execute(
                "INSERT INTO athlete_profiles (user_id, clerk_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE user_id = user_id",
                (user_id, caller_clerk_id),
            )
            c.execute("SELECT clerk_id FROM athlete_profiles WHERE user_id = %s FOR UPDATE", (user_id,))
            owner = c.fetchone()
            if not owner or owner.get("clerk_id") != caller_clerk_id:
                raise HTTPException(status_code=409, detail="This athlete is already connected to another account.")
            if row["claimed_at"] is None:
                c.execute(
                    """UPDATE claim_tokens SET claimed_at = NOW(), clerk_id = %s
                       WHERE id = %s AND claimed_at IS NULL AND (clerk_id IS NULL OR clerk_id = %s)""",
                    (caller_clerk_id, row["id"], caller_clerk_id),
                )
                if c.rowcount != 1:
                    raise HTTPException(status_code=409, detail="This invitation changed. Please retry the secure invitation.")
        db.commit()
    except Exception as exc:
        db.rollback()
        if isinstance(exc, (pymysql.err.IntegrityError, pymysql.err.OperationalError)) and exc.args and exc.args[0] in (1062, 1205, 1213):
            raise HTTPException(status_code=409, detail="Another connection is being acquired. Please retry the secure invitation.") from exc
        raise
    finally:
        try:
            if lock_acquired:
                with db.cursor() as c:
                    c.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
        finally:
            # Closing also releases session locks if explicit release fails.
            db.close()
    # Land the athlete in the workspace, not the legacy dashboard: make sure a sparq_profiles
    # row exists (built from GMTM) and college matching is running.
    try:
        ws = ensure_workspace_profile(caller_clerk_id, user_id)
    except Exception as e:  # never fail the claim because of the bootstrap
        print(f"[claims] workspace bootstrap failed for user {user_id}: {e}")
        ws = {"ready": False, "created": False, "profile_id": None}
    return {"connected": True, "user_id": user_id, "event_id": int(row["event_id"]), "clerk_id": caller_clerk_id,
            "workspace_ready": bool(ws.get("ready")), "workspace_created": bool(ws.get("created"))}
