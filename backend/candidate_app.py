"""Restricted combine entry point; ordinary ``main:app`` is unchanged.

Imports are inert. Lifespan validates process configuration without connecting or
initializing a model ledger. This is a route boundary, not a network sandbox.
GMTM sign-in (/gmtm-entry/exchange) can write Agent data; GMTM access must use gmtmread.

Launch with access logging disabled.
Shared profile connectors use finite socket timeouts. These do not establish
an overall request deadline or cancel an executing database query.
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

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import auth
from combine_api import current_combine
from combine_help_api import combine_help
from model_usage import MODELS, _configuration as model_limit_configuration
from profile_api import get_profile_by_owner
from junior_entry import exchange, sign_out, entry_configuration


GMTM_HOST = "db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com"
BUSINESS_ROUTES = (
    ("GET", "/api/combine/current", current_combine),
    ("POST", "/api/combine/help", combine_help),
    ("GET", "/api/profile/by-owner/{clerk_id}", get_profile_by_owner),
)
ENTRY_ROUTES = (
    ("POST", "/gmtm-entry/exchange", exchange),
    ("POST", "/gmtm-entry/sign-out", sign_out),
)
_CONFIGURATION_KEYS = (
    "ALLOWED_ORIGINS",
    "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
    "AGENT_DB_HOST", "AGENT_DB_PORT", "AGENT_DB_NAME", "AGENT_DB_USER", "AGENT_DB_PASSWORD",
    "SHARE_TOKEN_SECRET", "COMBINE_HELP_MODEL", "COMBINE_HELP_TEST_MODE",
    "COMBINE_HELP_MAX_MODEL_CALLS", "COMBINE_HELP_MAX_CONCURRENT_CALLS",
    "PROFILE_DEBRIEF_ENABLED", "PROFILE_DEBRIEF_MODEL",
    "PROFILE_DEBRIEF_MAX_MODEL_CALLS", "PROFILE_DEBRIEF_MAX_CONCURRENT_CALLS",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
    "OPPORTUNITY_ENGAGEMENT_ENABLED", "OPPORTUNITY_ENGAGEMENT_COHORT",
    "OPPORTUNITY_ENGAGEMENT_PERIOD", "OPPORTUNITY_ENGAGEMENT_SECRET",
    "OPPORTUNITY_ENGAGEMENT_EXCLUDED_IDS", "OPPORTUNITY_ENGAGEMENT_PILOT_IDS",
    "SPARQ_ENTRY_SECRET", "SPARQ_HANDOFF_SECRET", "GMTM_API_URL", "SPARQ_SESSION_SECRET", "SPARQ_TEST_ALLOWLIST",
    "SENDGRID_API_KEY", "SPARQ_FROM_EMAIL",
)


class CandidateConfigurationError(ValueError):
    """An actionable setting name/reason, never the setting's value."""


@dataclass(frozen=True)
class CandidateConfiguration:
    origins: tuple[str, ...]
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


def validate_configuration(env: Mapping[str, str], surface: str = "combine") -> CandidateConfiguration:
    """Validate declarations only: no file reads, services, or usage-ledger resets.

    GMTM sign-in is the only sign-in (SPARQ session). Entry settings are off when
    none is set (every request then gets 503); partial or invalid settings stop startup."""
    origins = _origins(env, "ALLOWED_ORIGINS")
    try:
        entry = entry_configuration(env)
    except ValueError as exc:
        raise CandidateConfigurationError(str(exc)) from None
    # Every profile session comes from GMTM entry; a hosted profile without it can
    # admit no one. Loopback-only previews may run without entry (handlers 503/401).
    if (surface == "profile" and entry is None
            and any(urlsplit(o).hostname not in ("localhost", "127.0.0.1", "::1") for o in origins)):
        raise CandidateConfigurationError(
            "Hosted profile origins require GMTM entry configuration (SPARQ_ENTRY_SECRET, "
            "SPARQ_HANDOFF_SECRET, GMTM_API_URL, SPARQ_SESSION_SECRET).")
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
    return CandidateConfiguration(origins, _signature(env), bool(env.get(key_name, "").strip()))


class CandidateBoundaryMiddleware:
    """Fail closed before source handlers, then apply framework CORS policy."""
    def __init__(self, app, surface="combine"):
        self.app = app
        self.surface = surface
        self.methods = ["GET", "POST", "PATCH"] if surface == "profile" else ["GET", "POST"]

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
        async def admitted_app(scope, receive, send):
            # Exchange uses the Next server secret; sign-out checks its own token.
            if self.surface != "profile" or scope["path"] in ("/health", "/gmtm-entry/exchange", "/gmtm-entry/sign-out"):
                await self.app(scope, receive, send)
                return
            authorization = Request(scope).headers.get("authorization")
            if authorization:
                import junior_entry
                try:
                    # Profile accepts ONLY a SPARQ session token, and only for a
                    # current GMTM entry. No entry row (gate False) is refused.
                    subject = await junior_entry.require_identity(authorization)
                    if not await junior_entry.gate(subject, scope["path"]):
                        raise HTTPException(403, "SPARQ is not open to this account here.")
                except HTTPException as exc:
                    await JSONResponse({"detail": exc.detail}, status_code=exc.status_code)(scope, receive, send)
                    return
            # Without Authorization, every personal handler requires identity (401).
            await self.app(scope, receive, send)

        cors = CORSMiddleware(admitted_app, allow_origins=list(config.origins),
                              allow_credentials=True, allow_methods=self.methods,
                              allow_headers=["Authorization", "Content-Type"])
        await cors(scope, receive, send)


def create_app(*, surface: str = "combine") -> FastAPI:
    if surface not in ("combine", "profile"):
        raise ValueError("Unsupported candidate surface")
    # Explicit entry-point choice only, never inferred from a request or env.
    # The default combine package keeps its existing import/source manifest.
    routes = BUSINESS_ROUTES + ENTRY_ROUTES
    title = "SPARQ Combine Candidate"
    if surface == "profile":
        from athlete_evidence import current_athlete_evidence
        from athlete_materials import current_athlete_materials
        from athlete_workspace import current_athlete_workspace, update_athlete_workspace
        from profile_owner import current_profile_recovery
        from junior_entry import get_parent_notice, accept_parent_notice
        import college_programs as colleges
        routes = (
            *ENTRY_ROUTES,
            ("GET", "/api/athlete/parent-notice", get_parent_notice),
            ("POST", "/api/athlete/parent-notice", accept_parent_notice),
            ("GET", "/api/athlete/evidence", current_athlete_evidence),
            ("GET", "/api/athlete/materials", current_athlete_materials),
            ("GET", "/api/athlete/workspace", current_athlete_workspace),
            ("PATCH", "/api/athlete/workspace", update_athlete_workspace),
            ("GET", "/api/profile/by-owner/{clerk_id}", current_profile_recovery),
            # Reviewed recruiting set (junior pilot): owner-checked by the URL clerk_id.
            ("GET", "/api/workspace/colleges/{clerk_id}", colleges.list_colleges),
            ("POST", "/api/workspace/trigger-matching/{clerk_id}", colleges.build_colleges),
            ("GET", "/api/workspace/colleges/{clerk_id}/{program_id}", colleges.college_detail),
            ("GET", "/api/workspace/colleges/{clerk_id}/{program_id}/outreach-draft", colleges.get_outreach_draft),
            ("POST", "/api/workspace/colleges/{clerk_id}/{program_id}/outreach-draft", colleges.create_outreach_draft),
            # Saves (heart) and "I sent it" marks: owner-checked, idempotent, no email text stored.
            ("GET", "/api/workspace/saved-colleges/{clerk_id}", colleges.saved_colleges),
            ("POST", "/api/workspace/saved-colleges/{clerk_id}/{program_id}", colleges.save_college),
            ("POST", "/api/workspace/colleges/{clerk_id}/{program_id}/sent", colleges.mark_sent),
            # Emails page (drafts + sent marks) and "CC my parent" (address only; SPARQ never sends).
            ("GET", "/api/workspace/college-emails/{clerk_id}", colleges.college_emails),
            ("GET", "/api/workspace/parent-contact/{clerk_id}", colleges.get_parent_contact),
            ("POST", "/api/workspace/parent-contact/{clerk_id}", colleges.set_parent_contact),
        )
        title = "SPARQ Profile Candidate"

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        config = validate_configuration(os.environ, surface)
        if surface == "profile":
            # Juniors send outreach from their own email; this app never sends.
            if any(os.environ.get(name, "").strip() for name in ("SENDGRID_API_KEY", "SPARQ_FROM_EMAIL")):
                raise CandidateConfigurationError("The profile surface must not configure outreach email sending.")
            # A bad college data file stops startup instead of showing broken cards.
            colleges.programs()
        # Pure configuration work only; no schema, provider or shared override.
        application.state.candidate_configuration = config
        try:
            yield
        finally:
            application.state.candidate_configuration = None

    application = FastAPI(title=title, version="1.0.0",
                          docs_url=None, redoc_url=None, openapi_url=None,
                          lifespan=lifespan, redirect_slashes=False)
    application.state.candidate_configuration = None
    application.state.sparq_surface = surface  # SPARQ token audience
    # Read by artifacts_api approve if outreach routes are ever mounted here.
    application.state.outreach_send_disabled = surface == "profile"
    if surface == "profile":
        # Profile: SPARQ session + the junior gate (middleware). Combine keeps the
        # default auth.require_identity: SPARQ session + SPARQ_TEST_ALLOWLIST only.
        import junior_entry
        application.state.entry_admission = "junior"
        application.dependency_overrides[auth.require_identity] = junior_entry.require_identity
    for method, path, endpoint in routes:
        application.add_api_route(path, endpoint, methods=[method])

    @application.get("/health")
    async def health():
        config = application.state.candidate_configuration
        ready = config is not None and config.signature == _signature(os.environ)
        body = {
            "service": title, "surface": f"{surface}_candidate",
            "configuration_ready": ready, "connectivity_verified": False,
            "schema_verified": False, "provider_delivery_verified": False,
            "help_provider_configured": config.help_provider_configured if ready and surface == "combine" else False,
        }
        try:
            body["gmtm_sign_in_configured"] = bool(ready and entry_configuration(os.environ) is not None)
        except ValueError:
            body["gmtm_sign_in_configured"] = False
        return JSONResponse(body, status_code=200 if ready else 503)

    @application.exception_handler(Exception)
    async def unavailable(request: Request, exc: Exception):
        # No token-bearing request paths or raw driver/provider exception text.
        return JSONResponse({"detail": "Combine service is temporarily unavailable."}, status_code=500)

    application.add_middleware(CandidateBoundaryMiddleware, surface=surface)

    if surface == "profile":
        @application.middleware("http")
        async def private_profile_responses(request: Request, call_next):
            response = await call_next(request)
            response.headers["Cache-Control"] = "private, no-store"
            vary = [part.strip() for part in response.headers.get("Vary", "").split(",") if part.strip()]
            if not any(part.lower() == "authorization" for part in vary):
                vary.append("Authorization")
            response.headers["Vary"] = ", ".join(vary)
            return response

    return application


app = create_app()
