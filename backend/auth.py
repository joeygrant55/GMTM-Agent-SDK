"""
Authentication for the SPARQ backend: GMTM sign-in only (Joey, 2026-10-01).

Every workspace request carries a SPARQ session token as `Authorization: Bearer
<token>`. The token is minted by `POST /gmtm-entry/exchange` (junior_entry) after a
GMTM sign-in, signed with SPARQ_SESSION_SECRET, and only the newest jti per subject
is active. Endpoints then check that the resource belongs to that subject
(ownership), which closes IDOR holes.

`require_identity` is the default for every surface: an active SPARQ session whose
GMTM user is in SPARQ_TEST_ALLOWLIST (legacy and combine have no other admission
rule). The profile surface overrides it with `junior_entry.require_identity` and
applies the junior gate in its middleware.

Fail closed: without SPARQ_SESSION_SECRET (and the other entry settings) every
protected endpoint returns 503. There is no development bypass; tests mint tokens.

DEMO_PROXY_SECRET — shared secret the Next.js /api/demo-chat route sends as
`X-Demo-Secret` so the public demo can reach the agent without a session. Unset
means the demo bypass is off.
"""

import os
import time
from typing import Optional

from fastapi import Header, HTTPException, Request


def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        return parts[1].strip()
    return None


async def require_identity(request: Request, authorization: Optional[str] = Header(default=None)) -> str:
    """FastAPI dependency: an active, allow-listed SPARQ session issued for this app's
    surface (token ``aud``). Returns its subject."""
    import junior_entry  # lazy: junior_entry imports PyJWT and the store seam
    return await junior_entry.require_allowlisted_identity(authorization, junior_entry.surface_of(request.app))


async def optional_identity(request: Request, authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    """The subject when a bearer token is present (and valid), else None.

    Used by dual-mode endpoints (signed-in user vs public demo) that apply their
    own fallback authorization. An invalid token still raises.
    """
    if not _bearer_token(authorization):
        return None
    return await require_identity(request, authorization)


def assert_owner(resource_owner_id: Optional[str], caller_id: str) -> None:
    """Raise 403/404 unless the caller owns the resource.

    404 (not 403) when the resource has no owner, so we don't leak which ids exist.
    """
    if not resource_owner_id:
        raise HTTPException(status_code=404, detail="Not found.")
    if resource_owner_id != caller_id:
        raise HTTPException(status_code=403, detail="Not authorized for this resource.")


def demo_secret_ok(x_demo_secret: Optional[str]) -> bool:
    """True when the request carries the configured demo proxy secret (unset = off)."""
    expected = os.environ.get("DEMO_PROXY_SECRET", "").strip()
    return bool(expected) and bool(x_demo_secret) and x_demo_secret.strip() == expected


# ── Lightweight in-memory rate limiter (per key, sliding window) ────────────────
# Bounds abuse of the public demo endpoint. In-process only (per Railway instance);
# good enough as a first line against runaway cost, not a substitute for a real WAF.
_rate_buckets: dict[str, list[float]] = {}


def rate_limit(key: str, max_calls: int, window_seconds: int) -> bool:
    """Return True if the call is allowed, False if the key exceeded its budget."""
    now = time.time()
    cutoff = now - window_seconds
    bucket = [t for t in _rate_buckets.get(key, []) if t > cutoff]
    if len(bucket) >= max_calls:
        _rate_buckets[key] = bucket
        return False
    bucket.append(now)
    _rate_buckets[key] = bucket
    return True


def auth_status() -> dict:
    """Report auth configuration for the /health endpoint (no secrets)."""
    import junior_entry
    try:
        configured = junior_entry.entry_configuration(os.environ) is not None
    except ValueError:
        configured = False
    return {
        "gmtm_sign_in_configured": configured,
        "demo_bypass_configured": bool(os.environ.get("DEMO_PROXY_SECRET", "").strip()),
    }
