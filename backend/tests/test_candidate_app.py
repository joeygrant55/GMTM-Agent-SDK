"""Actual candidate ASGI boundaries; synthetic services and local SPARQ sessions only."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

import auth
import candidate_app
import junior_entry
import model_usage
import profile_api
from backend.tests.junior_fakes import ENTRY_ENV, mint_session

ALLOWED_USER = 7201


ENV = {
    "ALLOWED_ORIGINS": "http://127.0.0.1:3218",
    "DB_HOST": candidate_app.GMTM_HOST, "DB_USER": "gmtmread", "DB_PASSWORD": "synthetic-source",
    "AGENT_DB_HOST": "127.0.0.1", "AGENT_DB_PORT": "3307", "AGENT_DB_USER": "synthetic",
    "AGENT_DB_PASSWORD": "synthetic-agent", "AGENT_DB_NAME": "sparq_fixture",
    "SHARE_TOKEN_SECRET": "synthetic-share", "COMBINE_HELP_TEST_MODE": "1",
    "COMBINE_HELP_MAX_MODEL_CALLS": "2", "COMBINE_HELP_MAX_CONCURRENT_CALLS": "1",
}


@pytest.fixture
def configured(monkeypatch):
    for name in candidate_app._CONFIGURATION_KEYS:
        monkeypatch.delenv(name, raising=False)
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    return candidate_app.create_app()


@pytest.fixture
def signed(monkeypatch):
    """SPARQ session headers for legacy/combine: GMTM entry recorded for an allow-listed
    user unless ``allowlisted=False``. Other options as junior_fakes.mint_session."""
    for name, value in ENTRY_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SPARQ_TEST_ALLOWLIST", str(ALLOWED_USER))
    def token(sub="sub_owner", *, allowlisted=True, **options):
        user_id = ALLOWED_USER if allowlisted else ALLOWED_USER + 1
        junior_entry.store.record_entry(sub, user_id, datetime.now(timezone.utc))
        return mint_session(sub, **{"aud": "combine", **options})
    return token


def test_exact_manifest_reuses_source_handlers_without_legacy_routes(configured):
    schema = configured.openapi()
    routes = candidate_app.BUSINESS_ROUTES + candidate_app.ENTRY_ROUTES
    expected = {path: method.lower() for method, path, _ in routes}
    assert set(schema["paths"]) == set(expected) | {"/health"}
    for method, path, endpoint in routes:
        assert set(schema["paths"][path]) == {method.lower()}
        assert any(route.path == path and route.endpoint is endpoint for route in configured.routes)
    import main
    assert auth.require_identity not in main.app.dependency_overrides
    assert auth.require_identity not in configured.dependency_overrides
    paths = main.app.openapi()["paths"]
    assert "/api/workspace/trigger-matching/{clerk_id}" in paths and "/gmtm-entry/exchange" in paths
    assert not any(path.startswith("/api/claims") or path == "/api/profile/connect" for path in paths)


def test_configuration_validation_does_not_initialize_usage_ledger(configured):
    assert model_usage._ledger is None
    config = candidate_app.validate_configuration(ENV)
    assert config.help_provider_configured is False
    assert model_usage._ledger is None
    with TestClient(configured) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "service": "SPARQ Combine Candidate", "surface": "combine_candidate",
            "configuration_ready": True, "connectivity_verified": False, "schema_verified": False,
            "provider_delivery_verified": False, "help_provider_configured": False,
            "gmtm_sign_in_configured": False,
        }
    assert model_usage._ledger is None


@pytest.mark.parametrize("name,value", [
    ("ALLOWED_ORIGINS", None), ("ALLOWED_ORIGINS", "*"), ("ALLOWED_ORIGINS", "https://evil.example.invalid/path"),
    ("SPARQ_ENTRY_SECRET", "partial-entry-settings"),
    ("ALLOWED_ORIGINS", "http://127.0.0.1:3218,"),
    ("DB_HOST", "127.0.0.1"), ("DB_HOST", "pre-prod"), ("DB_USER", "root"), ("DB_PASSWORD", ""),
    ("DB_PORT", "3307"), ("DB_NAME", "other"),
    ("AGENT_DB_HOST", "db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com"),
    ("AGENT_DB_HOST", "x.random.rds.amazonaws.com"), ("AGENT_DB_HOST", "mysql://host"),
    ("AGENT_DB_NAME", "gmtm"), ("AGENT_DB_PORT", "0"), ("AGENT_DB_PORT", "65536"),
    ("AGENT_DB_PORT", "３３０６"), ("AGENT_DB_USER", None), ("AGENT_DB_PASSWORD", None),
    ("SHARE_TOKEN_SECRET", None), ("COMBINE_HELP_MODEL", "unreviewed"),
    ("COMBINE_HELP_MAX_MODEL_CALLS", None), ("COMBINE_HELP_MAX_MODEL_CALLS", "0"),
    ("COMBINE_HELP_MAX_CONCURRENT_CALLS", "0"),
])
def test_invalid_configuration_fails_pure_validation(name, value):
    env = deepcopy(ENV)
    if value is None:
        env.pop(name, None)
    else:
        env[name] = value
    with pytest.raises(candidate_app.CandidateConfigurationError) as caught:
        candidate_app.validate_configuration(env)
    assert "synthetic-source" not in str(caught.value)
    assert "synthetic-agent" not in str(caught.value)


def test_import_factory_does_not_require_config_but_lifespan_does(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    app = candidate_app.create_app()
    with pytest.raises(candidate_app.CandidateConfigurationError):
        with TestClient(app):
            pass
    assert app.state.candidate_configuration is None


def test_unstarted_app_and_drifted_config_fail_before_source_work(configured, monkeypatch):
    with TestClient(configured) as client:
        monkeypatch.setenv("DB_HOST", "unexpected")
        assert client.get("/health").status_code == 503
        assert client.get("/api/combine/current?event_id=1318").status_code == 503
    client = TestClient(candidate_app.create_app())
    assert client.get("/api/combine/current?event_id=1318").status_code == 503


def test_missing_auth_and_unadmitted_sessions_fail_before_services(configured, signed):
    with TestClient(configured) as client:
        routes = [("GET", "/api/combine/current?event_id=1318", {}),
                  ("POST", "/api/combine/help", {"json": {"event_id": 1318, "message": "Help"}}),
                  ("GET", "/api/profile/by-owner/sub_owner", {})]
        for method, path, kwargs in routes:
            assert client.request(method, path, **kwargs).status_code == 401
            for headers, status in ((signed(active=False), 401), (signed(secret="w" * 40), 401),
                                    (signed(exp=1), 401), (signed(jti=None), 401),
                                    (signed("sub_outsider", allowlisted=False), 403)):
                assert client.request(method, path, headers=headers, **kwargs).status_code == status


def test_local_signed_auth_reaches_real_recovery_owner_guard(configured, signed):
    with TestClient(configured) as client:
        response = client.get("/api/profile/by-owner/another_owner", headers=signed())
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authorized."


def test_actual_recovery_handler_reads_only_synthetic_owned_rows(configured, signed, monkeypatch):
    calls = []
    class Database:
        def cursor(self): return self
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, sql, params):
            assert sql.startswith("SELECT")
            calls.append((sql, params))
            self.workspace = "FROM sparq_profiles" in sql
        def fetchall(self):
            return [{"id": 11, "clerk_id": "sub_owner"}] if self.workspace else [{"user_id": 7201, "clerk_id": "sub_owner"}]
        def close(self): calls.append("closed")
    monkeypatch.setattr(profile_api, "_get_agent_db", Database)
    with TestClient(configured) as client:
        response = client.get("/api/profile/by-owner/sub_owner", headers=signed())
        assert response.status_code == 200
        assert response.json() == {"found": True, "user_id": 7201, "has_sparq_profile": True}
    assert len(calls) == 4 and calls[-1] == "closed"


def test_excluded_routes_are_unreachable_even_with_valid_auth(configured, signed):
    with TestClient(configured) as client:
        for method, path in [
            ("GET", "/api/workspace/inbox/sub_owner"), ("GET", "/api/workspace/profile/sub_owner"),
            ("POST", "/api/profile/connect"), ("POST", "/api/claims/mint"),
            ("GET", "/api/claims/token"), ("POST", "/api/claims/token/redeem"),
            ("POST", "/api/workspace/trigger-matching/sub_owner"),
            ("POST", "/api/artifacts/1/approve"), ("POST", "/api/agent/chat"),
            ("GET", "/api/search"), ("GET", "/api/reports/7201"),
            ("GET", "/docs"), ("GET", "/redoc"), ("GET", "/openapi.json"),
            ("POST", "/api/combine/current"), ("GET", "/api/combine/current/"),
        ]:
            assert client.request(method, path, headers=signed()).status_code in (404, 405)


def test_cors_uses_exact_origins_and_preflight_does_not_call_auth(configured):
    with TestClient(configured) as client:
        headers = {"Origin": ENV["ALLOWED_ORIGINS"], "Access-Control-Request-Method": "POST",
                   "Access-Control-Request-Headers": "authorization,content-type"}
        response = client.options("/api/combine/help", headers=headers)
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == ENV["ALLOWED_ORIGINS"]
        assert response.headers["access-control-allow-credentials"] == "true"
        denied = client.options("/api/combine/help", headers={**headers, "Origin": "https://evil.example.invalid"})
        assert denied.status_code == 400
        assert "access-control-allow-origin" not in denied.headers
        assert client.get("/health").status_code == 200  # Server requests need not carry Origin.


@pytest.mark.parametrize("entry", ["candidate_app", "profile_candidate_app"])
def test_fresh_candidate_import_and_lifespan_attempt_no_external_work(entry):
    program = r'''
import asyncio, collections, os, socket, sys, threading
from unittest.mock import patch
attempts = collections.Counter()
def blocked(name):
    def call(*a, **k):
        attempts[name] += 1
        raise AssertionError(name)
    return call
def audit(event,args):
    if event == 'socket.getaddrinfo' or (event == 'socket.connect' and args[0].family in (socket.AF_INET,socket.AF_INET6)):
        blocked('network')()
    if event == 'open' and isinstance(args[0],(str,bytes)) and os.path.basename(os.fsdecode(args[0])).startswith('.env'):
        blocked('dotenv-file')()
    if event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn','os.fork'):
        blocked('process')()
sys.addaudithook(audit)
import anthropic, openai, pymysql, dotenv
pymysql.connect=blocked('db')
pymysql.connections.Connection.connect=blocked('db')
anthropic.Anthropic=anthropic.AsyncAnthropic=blocked('anthropic')
openai.OpenAI=openai.AsyncOpenAI=blocked('openai')
dotenv.load_dotenv=dotenv.dotenv_values=blocked('dotenv')
threading.Thread.start=blocked('thread')
sys.path.insert(0,sys.argv[1])
import importlib, model_usage
candidate_app = importlib.import_module(sys.argv[2])
assert 'main' not in sys.modules
assert not any(name in sys.modules for name in ('agent_api','artifacts_api','reports_api','search_api','enrichment_worker'))
assert model_usage._ledger is None
async def run():
    loop=asyncio.get_running_loop()
    with patch.object(loop,'create_task',blocked('task')), patch.object(asyncio,'create_task',blocked('task')):
        async with candidate_app.app.router.lifespan_context(candidate_app.app):
            assert candidate_app.app.state.candidate_configuration is not None
            assert model_usage._ledger is None
    assert candidate_app.app.state.candidate_configuration is None
asyncio.run(run())
assert dict(attempts)=={},dict(attempts)
print('CANDIDATE_COMPOSITION zero external attempts')
'''
    result = subprocess.run([sys.executable, "-I", "-B", "-c", program, str(Path(__file__).resolve().parents[1]), entry],
                            env={**ENV, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "zero external attempts" in result.stdout
