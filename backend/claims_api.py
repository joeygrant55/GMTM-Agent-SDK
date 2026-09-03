"""
Claim tokens — the GMTM-to-SPARQ door (cohort-one spec, workstream 2a).

A combine submitter gets one signed link. Opening it shows a landing page with their
first name and the event name; redeeming it (after Clerk sign-up) links their GMTM
`user_id` to their Clerk id exactly the way `POST /api/profile/connect` does.

Routes
    POST /api/claims/mint            admin (header X-Claims-Admin = CLAIMS_ADMIN_SECRET)
    GET  /api/claims/{token}         public — {valid, first_name, event_name, claimed}
    POST /api/claims/{token}/redeem  Clerk-authed — writes athlete_profiles, marks claimed

Token format
    base64url(json{"u": user_id, "e": event_id, "x": exp_unix}) + "." + base64url(HMAC-SHA256)
    Signed with SHARE_TOKEN_SECRET (already a required env var). Only sha256(token) is
    stored, in the self-created `claim_tokens` table (Railway agent DB).

Status semantics
    400  malformed token or bad signature (tampered)
    410  signature valid but expired
    409  already redeemed by a different Clerk id
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

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from auth import require_clerk_id
from profile_api import _get_agent_db, _get_gmtm_db

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


# ── Table ───────────────────────────────────────────────────────────────────

def _ensure_claim_tables():
    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS claim_tokens (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    token_hash CHAR(64) NOT NULL UNIQUE,
                    user_id INT NOT NULL,
                    event_id INT NOT NULL,
                    minted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    opened_at DATETIME NULL,
                    claimed_at DATETIME NULL,
                    clerk_id VARCHAR(255) NULL,
                    INDEX idx_user (user_id),
                    INDEX idx_event (event_id)
                )
            """)
        db.commit()
    except Exception as e:
        print(f"⚠️ claim_tokens table setup skipped: {e}")
    finally:
        if db:
            db.close()


_ensure_claim_tables()


# ── Helpers ─────────────────────────────────────────────────────────────────

def _verify_or_http(token: str) -> dict:
    try:
        return verify_token(token, _get_share_secret())
    except ClaimTokenError as e:
        raise HTTPException(status_code=e.status_code, detail={"valid": False, "reason": e.code})


def _lookup_claim_row(c, thash: str) -> dict:
    c.execute(
        "SELECT id, user_id, event_id, opened_at, claimed_at, clerk_id FROM claim_tokens WHERE token_hash = %s",
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
    """Link the token's GMTM user_id to the caller's Clerk id. Idempotent for the same
    Clerk id; 409 if a different Clerk id already redeemed it."""
    data = _verify_or_http(token)
    thash = token_hash(token)
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            row = _lookup_claim_row(c, thash)
            if row["claimed_at"] is not None and row["clerk_id"] and row["clerk_id"] != caller_clerk_id:
                raise HTTPException(
                    status_code=409,
                    detail="This link was already used by another account. Sign in with that account, or connect manually.",
                )
            user_id = int(row["user_id"])
            # Never let a claim link re-point a GMTM athlete that is already linked to a
            # different Clerk account (a leaked link must not hijack an existing user).
            c.execute("SELECT clerk_id FROM athlete_profiles WHERE user_id = %s", (user_id,))
            existing = c.fetchone()
            if existing and existing.get("clerk_id") and existing["clerk_id"] != caller_clerk_id:
                raise HTTPException(
                    status_code=409,
                    detail="These results are already connected to another account. Sign in with that account, or connect manually.",
                )
            # Same write as POST /api/profile/connect.
            c.execute(
                "INSERT INTO athlete_profiles (user_id, clerk_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE clerk_id = %s",
                (user_id, caller_clerk_id, caller_clerk_id),
            )
            c.execute(
                "UPDATE claim_tokens SET claimed_at = COALESCE(claimed_at, NOW()), clerk_id = %s WHERE id = %s",
                (caller_clerk_id, row["id"]),
            )
        db.commit()
    finally:
        db.close()
    return {"connected": True, "user_id": user_id, "event_id": int(row["event_id"]), "clerk_id": caller_clerk_id}
