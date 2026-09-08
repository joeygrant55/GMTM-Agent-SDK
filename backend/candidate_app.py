"""Restricted combine entry point; ordinary ``main:app`` is unchanged.

Imports are inert. Lifespan validates process configuration without connecting or
initializing a model ledger. This is a route boundary, not a network sandbox.
Claim preview/redemption can write Agent data; GMTM access must use gmtmread.

Launch with access logging disabled: claim URLs contain bearer-like invitations.
Profile connectors used by preview/bootstrap retain their existing timeout gap;
this module does not mutate shared connector globals to claim app-local limits.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
import hashlib
import json
import os
import re
from urllib.parse import urlsplit

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import auth
from claims_api import get_claim, redeem_claim
from combine_api import current_combine
from combine_help_api import combine_help
from model_usage import MODELS, _configuration as model_limit_configuration
from profile_api import get_profile_by_clerk


GMTM_HOST = "db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com"
BUSINESS_ROUTES = (
    ("GET", "/api/combine/current", current_combine),
    ("POST", "/api/combine/help", combine_help),
    ("GET", "/api/profile/by-clerk/{clerk_id}", get_profile_by_clerk),
    ("GET", "/api/claims/{token}", get_claim),
    ("POST", "/api/claims/{token}/redeem", redeem_claim),
)
_CONFIGURATION_KEYS = (
    "AUTH_ENFORCED", "CLERK_ISSUER", "CLERK_AUTHORIZED_PARTIES", "ALLOWED_ORIGINS",
    "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
    "AGENT_DB_HOST", "AGENT_DB_PORT", "AGENT_DB_NAME", "AGENT_DB_USER", "AGENT_DB_PASSWORD",
    "SHARE_TOKEN_SECRET", "COMBINE_HELP_MODEL", "COMBINE_HELP_TEST_MODE",
    "COMBINE_HELP_MAX_MODEL_CALLS", "COMBINE_HELP_MAX_CONCURRENT_CALLS",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
)


class CandidateConfigurationError(ValueError):
    """An actionable setting name/reason, never the setting's value."""


@dataclass(frozen=True)
class CandidateConfiguration:
    origins: tuple[str, ...]
    authorized_parties: tuple[str, ...]
    signature: str
    help_provider_configured: bool


def _signature(env: Mapping[str, str]) -> str:
    # Snapshot critical settings without retaining or reporting raw secrets.
    payload = json.dumps({key: env.get(key) for key in _CONFIGURATION_KEYS}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name)
    if not isinstance(value, str) or not value.strip():
        raise CandidateConfigurationError(f"Explicit {name} is required.")
    return value


def _origin(value: str, *, loopback_http: bool) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise CandidateConfigurationError("A configured origin is malformed.") from None
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.path or parsed.query or parsed.fragment
            or "*" in value or value != value.strip()
            or (port is not None and not 1 <= port <= 65535)):
        raise CandidateConfigurationError("Use exact origins without paths, credentials or wildcards.")
    if parsed.scheme != "https" and not (
        loopback_http and parsed.hostname in ("localhost", "127.0.0.1", "::1")
    ):
        raise CandidateConfigurationError("HTTPS origins are required except explicit loopback UI origins.")
    # Require a canonical hostname and scheme, preserving a deliberately set port.
    hostname = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    canonical = f"{parsed.scheme}://{hostname}" + (f":{port}" if port is not None else "")
    if value != canonical or not re.fullmatch(r"[A-Za-z0-9.:[\]-]+", parsed.netloc):
        raise CandidateConfigurationError("Use canonical origin syntax.")
    return value


def _origins(env: Mapping[str, str], name: str) -> tuple[str, ...]:
    values = _required(env, name).split(",")
    if any(not value.strip() for value in values):
        raise CandidateConfigurationError(f"{name} has an empty origin.")
    return tuple(dict.fromkeys(_origin(value.strip(), loopback_http=True) for value in values))


def validate_configuration(env: Mapping[str, str]) -> CandidateConfiguration:
    """Validate declarations only: no file reads, services, or usage-ledger resets."""
    if env.get("AUTH_ENFORCED") != "true":
        raise CandidateConfigurationError("Candidate AUTH_ENFORCED must be explicitly true.")
    _origin(_required(env, "CLERK_ISSUER"), loopback_http=False)
    parties = _origins(env, "CLERK_AUTHORIZED_PARTIES")
    origins = _origins(env, "ALLOWED_ORIGINS")
    if set(parties) != set(origins):
        raise CandidateConfigurationError("Candidate authorized parties and CORS origins must match.")
    if env.get("DB_HOST") != GMTM_HOST or env.get("DB_USER") != "gmtmread":
        raise CandidateConfigurationError("Candidate GMTM must use the reviewed db2-dev host and gmtmread account.")
    if env.get("DB_PORT", "3306") != "3306" or env.get("DB_NAME", "gmtm") != "gmtm":
        raise CandidateConfigurationError("Candidate GMTM database and port must remain gmtm and 3306.")
    _required(env, "DB_PASSWORD")
    agent = {name: _required(env, f"AGENT_DB_{name}") for name in ("HOST", "PORT", "NAME", "USER", "PASSWORD")}
    if (not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?", agent["HOST"])
            or re.search(r"gmtm|pre[-_]?prod|db2[-_]dev|family[-_]test|\.rds\.amazonaws\.", agent["HOST"], re.I)):
        raise CandidateConfigurationError("Candidate Agent host must be explicit and separate from GMTM/RDS.")
    if (not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_$-]{0,63}", agent["NAME"])
            or re.search(r"gmtm|pre[-_]?prod|db2[-_]dev|family[-_]test", agent["NAME"], re.I)):
        raise CandidateConfigurationError("Candidate Agent database must be explicit and separate from GMTM.")
    port = agent["PORT"]
    if not port.isascii() or not port.isdecimal() or len(port) > 5 or not 1 <= int(port) <= 65535:
        raise CandidateConfigurationError("Candidate Agent port must be a valid explicit integer.")
    _required(env, "SHARE_TOKEN_SECRET")
    model = env.get("COMBINE_HELP_MODEL", "claude-sonnet-4-6")
    if model not in MODELS:
        raise CandidateConfigurationError("Candidate combine-help model is not supported.")
    for name in ("COMBINE_HELP_MAX_MODEL_CALLS", "COMBINE_HELP_MAX_CONCURRENT_CALLS"):
        _required(env, name)
    try:
        model_limit_configuration(env)
    except ValueError:
        raise CandidateConfigurationError("Candidate combine-help limits are invalid.") from None
    key_name = "OPENAI_API_KEY" if MODELS[model] == "openai" else "ANTHROPIC_API_KEY"
    return CandidateConfiguration(origins, parties, _signature(env), bool(env.get(key_name, "").strip()))


async def require_candidate_clerk_id(request: Request, authorization: str | None = Header(default=None)) -> str:
    """Reuse signature verification, with candidate-only mandatory azp/subject rules."""
    config = getattr(request.app.state, "candidate_configuration", None)
    if config is None:
        raise HTTPException(status_code=503, detail="Combine service configuration is not ready.")
    token = auth._bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization bearer token.")
    claims = auth._verify_token(token)
    subject = claims.get("sub")
    if (not isinstance(subject, str) or not subject.strip() or subject != subject.strip()
            or len(subject) > 255 or claims.get("azp") not in config.authorized_parties):
        raise HTTPException(status_code=401, detail="Session is not authorized for this combine application.")
    return subject


class CandidateBoundaryMiddleware:
    """Fail closed before source handlers, then apply framework CORS policy."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        config = getattr(scope["app"].state, "candidate_configuration", None)
        if config is None or config.signature != _signature(os.environ):
            if scope["path"] == "/health":
                await self.app(scope, receive, send)
            else:
                response = JSONResponse({"detail": "Combine service configuration is not ready."}, status_code=503)
                await response(scope, receive, send)
            return
        # This is a request-local wrapper around the existing ASGI pipeline, not
        # a retained call_next closure or a mutation of application middleware.
        cors = CORSMiddleware(self.app, allow_origins=list(config.origins),
                              allow_credentials=True, allow_methods=["GET", "POST"],
                              allow_headers=["Authorization", "Content-Type"])
        await cors(scope, receive, send)


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        config = validate_configuration(os.environ)
        # Pure configuration work only; no schema, provider or shared override.
        application.state.candidate_configuration = config
        try:
            yield
        finally:
            application.state.candidate_configuration = None

    application = FastAPI(title="SPARQ Combine Candidate", version="1.0.0",
                          docs_url=None, redoc_url=None, openapi_url=None,
                          lifespan=lifespan, redirect_slashes=False)
    application.state.candidate_configuration = None
    application.dependency_overrides[auth.require_clerk_id] = require_candidate_clerk_id
    for method, path, endpoint in BUSINESS_ROUTES:
        application.add_api_route(path, endpoint, methods=[method])

    @application.get("/health")
    async def health():
        config = application.state.candidate_configuration
        ready = config is not None and config.signature == _signature(os.environ)
        return JSONResponse({
            "service": "SPARQ Combine Candidate", "surface": "combine_candidate",
            "configuration_ready": ready, "connectivity_verified": False,
            "schema_verified": False, "provider_delivery_verified": False,
            "help_provider_configured": config.help_provider_configured if ready else False,
        }, status_code=200 if ready else 503)

    @application.exception_handler(Exception)
    async def unavailable(request: Request, exc: Exception):
        # No token-bearing request paths or raw driver/provider exception text.
        return JSONResponse({"detail": "Combine service is temporarily unavailable."}, status_code=500)

    application.add_middleware(CandidateBoundaryMiddleware)

    return application


app = create_app()
