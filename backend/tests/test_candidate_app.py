"""Actual candidate ASGI boundaries; synthetic services and local JWT keys only."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import jwt
import pytest

import auth
import candidate_app
import model_usage
import profile_api


ENV = {
    "AUTH_ENFORCED": "true", "CLERK_ISSUER": "https://clerk.example.invalid",
    "CLERK_AUTHORIZED_PARTIES": "http://127.0.0.1:3218", "ALLOWED_ORIGINS": "http://127.0.0.1:3218",
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
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(auth, "_jwks_issuer", ENV["CLERK_ISSUER"])
    monkeypatch.setattr(auth, "_jwks_client", SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=key.public_key())))
    def token(**overrides):
        claims = {"sub": "clerk_owner", "iss": ENV["CLERK_ISSUER"], "exp": int(time.time()) + 120,
                  "azp": ENV["CLERK_AUTHORIZED_PARTIES"]}
        claims.update(overrides)
        if claims.get("azp") is None:
            del claims["azp"]
        return {"Authorization": "Bearer " + jwt.encode(claims, key, algorithm="RS256")}
    return token


def test_exact_manifest_reuses_source_handlers_without_legacy_routes(configured):
    schema = configured.openapi()
    expected = {path: method.lower() for method, path, _ in candidate_app.BUSINESS_ROUTES}
    assert set(schema["paths"]) == set(expected) | {"/health"}
    for method, path, endpoint in candidate_app.BUSINESS_ROUTES:
        assert set(schema["paths"][path]) == {method.lower()}
        assert any(route.path == path and route.endpoint is endpoint for route in configured.routes)
    import main
    assert auth.require_clerk_id not in main.app.dependency_overrides
    assert "/api/workspace/trigger-matching/{clerk_id}" in main.app.openapi()["paths"]


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
        }
    assert model_usage._ledger is None


@pytest.mark.parametrize("name,value", [
    ("AUTH_ENFORCED", None), ("AUTH_ENFORCED", "false"),
    ("CLERK_ISSUER", "http://clerk.example.invalid"), ("CLERK_ISSUER", "https://clerk.example.invalid/path"),
    ("CLERK_ISSUER", "https://user:pass@clerk.example.invalid"),
    ("CLERK_AUTHORIZED_PARTIES", "*"), ("ALLOWED_ORIGINS", "https://evil.example.invalid"),
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
    monkeypatch.delenv("AUTH_ENFORCED", raising=False)
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
    assert client.get("/api/claims/synthetic-token").status_code == 503


def test_missing_auth_and_bad_azp_fail_before_services(configured, signed):
    with TestClient(configured) as client:
        routes = [("GET", "/api/combine/current?event_id=1318", {}),
                  ("POST", "/api/combine/help", {"json": {"event_id": 1318, "message": "Help"}}),
                  ("GET", "/api/profile/by-clerk/clerk_owner", {}),
                  ("POST", "/api/claims/synthetic-token/redeem", {})]
        for method, path, kwargs in routes:
            assert client.request(method, path, **kwargs).status_code == 401
            for headers in (signed(azp=None), signed(azp="https://another.example.invalid"), signed(sub=" ")):
                assert client.request(method, path, headers=headers, **kwargs).status_code == 401


def test_local_signed_auth_reaches_real_recovery_owner_guard(configured, signed):
    with TestClient(configured) as client:
        response = client.get("/api/profile/by-clerk/another_owner", headers=signed())
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
            return [{"id": 11, "clerk_id": "clerk_owner"}] if self.workspace else [{"user_id": 7201, "clerk_id": "clerk_owner"}]
        def close(self): calls.append("closed")
    monkeypatch.setattr(profile_api, "_get_agent_db", Database)
    with TestClient(configured) as client:
        response = client.get("/api/profile/by-clerk/clerk_owner", headers=signed())
        assert response.status_code == 200
        assert response.json() == {"found": True, "user_id": 7201, "has_sparq_profile": True}
    assert len(calls) == 4 and calls[-1] == "closed"


def test_excluded_routes_are_unreachable_even_with_valid_auth(configured, signed):
    with TestClient(configured) as client:
        for method, path in [
            ("GET", "/api/workspace/inbox/clerk_owner"), ("GET", "/api/workspace/profile/clerk_owner"),
            ("POST", "/api/profile/connect"), ("POST", "/api/claims/mint"),
            ("POST", "/api/workspace/trigger-matching/clerk_owner"),
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
