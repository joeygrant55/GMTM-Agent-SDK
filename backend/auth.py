"""
Clerk authentication for the SPARQ backend.

Every workspace request must carry a Clerk session JWT as `Authorization: Bearer <token>`.
We verify the token against Clerk's JWKS (RS256) and treat the `sub` claim as the
authenticated `clerk_id`. Endpoints then check that the resource being touched
belongs to that clerk_id (ownership), which closes the IDOR holes where any caller
could read or mutate another athlete's data by guessing an id.

Configuration (set in the backend environment):
    CLERK_ISSUER   — required. Your Clerk Frontend API origin, e.g.
                     https://clerk.your-domain.com (production) or
                     https://<slug>.clerk.accounts.dev (development).
                     JWKS is fetched from {CLERK_ISSUER}/.well-known/jwks.json.
    CLERK_AUTHORIZED_PARTIES — optional, comma-separated allowed `azp` origins
                     (e.g. https://sparq-agent.vercel.app). If set, tokens whose
                     azp is not in this list are rejected.
    AUTH_ENFORCED  — optional. Defaults to "true". Set to "false" ONLY for local
                     development to bypass verification. Never set false in prod.
    DEMO_PROXY_SECRET — shared secret the Next.js /api/demo-chat route sends as
                     `X-Demo-Secret` so the public demo can reach the agent without
                     a Clerk token. Requests without a token AND without this secret
                     are rejected.

Fail-closed: if AUTH_ENFORCED is true (the default) and CLERK_ISSUER is missing,
protected endpoints return 503 rather than silently allowing unauthenticated access.
"""

import os
import time
from typing import Optional

from fastapi import Header, HTTPException

try:
    import jwt
    from jwt import PyJWKClient
    _JWT_AVAILABLE = True
except Exception as _e:  # pragma: no cover - import guard
    _JWT_AVAILABLE = False
    _JWT_IMPORT_ERROR = str(_e)


def _auth_enforced() -> bool:
    return os.environ.get("AUTH_ENFORCED", "true").strip().lower() not in ("false", "0", "no")


def _issuer() -> Optional[str]:
    iss = os.environ.get("CLERK_ISSUER", "").strip()
    return iss.rstrip("/") if iss else None


def _authorized_parties() -> list[str]:
    raw = os.environ.get("CLERK_AUTHORIZED_PARTIES", "").strip()
    return [p.strip() for p in raw.split(",") if p.strip()]


# JWKS client is cached per-issuer; PyJWKClient keeps its own key cache with TTL.
_jwks_client: Optional["PyJWKClient"] = None
_jwks_issuer: Optional[str] = None


def _get_jwks_client() -> "PyJWKClient":
    global _jwks_client, _jwks_issuer
    issuer = _issuer()
    if not issuer:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured (CLERK_ISSUER unset).",
        )
    if not _JWT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Authentication dependency missing (PyJWT not installed).",
        )
    if _jwks_client is None or _jwks_issuer != issuer:
        _jwks_client = PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_keys=True)
        _jwks_issuer = issuer
    return _jwks_client


def _verify_token(token: str) -> dict:
    """Verify a Clerk session JWT and return its claims, or raise HTTPException(401)."""
    issuer = _issuer()
    client = _get_jwks_client()
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False},
            leeway=10,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid session token: {e}")

    parties = _authorized_parties()
    if parties:
        azp = claims.get("azp")
        if azp and azp not in parties:
            raise HTTPException(status_code=401, detail="Token azp not authorized.")

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing subject.")
    return claims


def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        return parts[1].strip()
    return None


def require_clerk_id(authorization: Optional[str] = Header(default=None)) -> str:
    """FastAPI dependency: require a valid Clerk token, return the authenticated clerk_id.

    When AUTH_ENFORCED=false (local dev only) a token is still honored if present,
    otherwise a placeholder dev identity is returned so the app runs without Clerk.
    """
    token = _bearer_token(authorization)
    if not _auth_enforced():
        if token and _JWT_AVAILABLE and _issuer():
            return _verify_token(token)["sub"]
        return os.environ.get("DEV_CLERK_ID", "dev-user")
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization bearer token.")
    return _verify_token(token)["sub"]


def optional_clerk_id(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    """Return the authenticated clerk_id if a valid token is present, else None.

    Does not raise on a missing token — used by dual-mode endpoints (authed user vs
    public demo) that apply their own fallback authorization.
    """
    token = _bearer_token(authorization)
    if not token:
        return None
    if not _auth_enforced():
        if _JWT_AVAILABLE and _issuer():
            try:
                return _verify_token(token)["sub"]
            except HTTPException:
                return None
        return os.environ.get("DEV_CLERK_ID", "dev-user")
    return _verify_token(token)["sub"]


def assert_owner(resource_clerk_id: Optional[str], caller_clerk_id: str) -> None:
    """Raise 403/404 unless the caller owns the resource.

    404 (not 403) when the resource has no owner, so we don't leak which ids exist.
    """
    if not resource_clerk_id:
        raise HTTPException(status_code=404, detail="Not found.")
    if resource_clerk_id != caller_clerk_id:
        raise HTTPException(status_code=403, detail="Not authorized for this resource.")


def demo_secret_ok(x_demo_secret: Optional[str]) -> bool:
    """True when the request carries the configured demo proxy secret."""
    expected = os.environ.get("DEMO_PROXY_SECRET", "").strip()
    if not expected:
        # No secret configured → demo bypass is disabled (fail closed) when auth enforced.
        return not _auth_enforced()
    return bool(x_demo_secret) and x_demo_secret.strip() == expected


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
    return {
        "enforced": _auth_enforced(),
        "clerk_issuer_configured": bool(_issuer()),
        "jwt_lib_available": _JWT_AVAILABLE,
        "demo_bypass_configured": bool(os.environ.get("DEMO_PROXY_SECRET", "").strip()),
    }
