"""Actual profile app authentication/route boundaries with synthetic local JWTs."""
from datetime import datetime, timezone
import hashlib
import secrets
import time

from fastapi.testclient import TestClient
import jwt
import pytest

import candidate_app
import junior_entry
import model_usage
from backend.tests.junior_fakes import ENTRY_ENV, GSH, SESSION_SECRET, mint_session
from backend.tests.test_candidate_app import ENV, signed


@pytest.fixture
def profile_app(monkeypatch):
    for name in candidate_app._CONFIGURATION_KEYS:
        monkeypatch.delenv(name, raising=False)
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    return candidate_app.create_app(surface="profile")


@pytest.fixture
def session(profile_app, monkeypatch):
    """SPARQ session headers (the profile surface's only sign-in). Each call makes
    its jti the active one for ``sub`` unless ``active=False``. Claim overrides
    replace token claims; None removes one."""
    for name, value in ENTRY_ENV.items():
        monkeypatch.setenv(name, value)

    return mint_session


def test_profile_manifest_is_explicit_and_excludes_legacy_and_combine_work(profile_app):
    schema = profile_app.openapi()
    expected = {
        "/api/athlete/evidence": "get", "/api/profile/by-owner/{clerk_id}": "get",
        "/api/athlete/materials": "get",
        "/api/athlete/workspace": ("get", "patch"),
        "/health": "get",
        "/gmtm-entry/exchange": "post", "/gmtm-entry/sign-out": "post", "/api/athlete/parent-notice": ("get", "post"),
        "/api/workspace/colleges/{clerk_id}": "get", "/api/workspace/trigger-matching/{clerk_id}": "post",
        "/api/workspace/colleges/{clerk_id}/{program_id}": "get",
        "/api/workspace/colleges/{clerk_id}/{program_id}/outreach-draft": ("get", "post"),
        "/api/workspace/saved-colleges/{clerk_id}": "get", "/api/workspace/saved-colleges/{clerk_id}/{program_id}": "post",
        "/api/workspace/college-research/{clerk_id}": "get",
        "/api/workspace/colleges/{clerk_id}/{program_id}/sent": "post",
        "/api/workspace/college-emails/{clerk_id}": "get", "/api/workspace/parent-contact/{clerk_id}": ("get", "post"),
        "/api/workspace/card/{clerk_id}": ("get", "post"), "/api/workspace/card/{clerk_id}/lead": "get",
    }
    assert set(schema["paths"]) == set(expected)
    assert all(set(schema["paths"][path]) == (set(method) if isinstance(method, tuple) else {method}) for path, method in expected.items())
    # Choosing this app never widens the original manifest.
    assert "/api/athlete/evidence" not in candidate_app.create_app().openapi()["paths"]
    assert "/api/athlete/materials" not in candidate_app.create_app().openapi()["paths"]
    assert "/api/athlete/debrief" not in candidate_app.create_app().openapi()["paths"]
    assert "/api/athlete/workspace" not in candidate_app.create_app().openapi()["paths"]
    assert "/api/athlete/opportunities" not in candidate_app.create_app().openapi()["paths"]
    assert "/api/athlete/opportunities/engagement" not in candidate_app.create_app().openapi()["paths"]
    with pytest.raises(ValueError):
        candidate_app.create_app(surface="unexpected")


def test_profile_health_is_not_a_claim_of_live_data_or_provider_delivery(profile_app):
    with TestClient(profile_app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["surface"] == "profile_candidate"
        assert response.json()["connectivity_verified"] is False
        assert response.json()["provider_delivery_verified"] is False
        assert response.json()["help_provider_configured"] is False
        # Junior pilot: Ask SPARQ (debrief) and Opportunities are not part of this app.
        assert not {"debrief_enabled", "opportunity_engagement_enabled", "debrief_provider_configured"} & set(response.json())
        assert response.headers["cache-control"] == "private, no-store"
        assert "Authorization" in response.headers["vary"]
        assert model_usage._ledger is None


def test_profile_rejects_invalid_sessions_before_any_source_read(profile_app, session, signed):
    # Unmocked database/provider/network calls are blocked by conftest.
    with TestClient(profile_app) as client:
        for headers in ({}, signed(), session(active=False), session(exp=int(time.time()) - 1),
                        session(secret="another-secret-that-is-32-bytes-long!"), session(gsh=None), session(gsh="raw-session-id")):
            response = client.get("/api/athlete/evidence", headers=headers)
            assert response.status_code == 401
            assert response.headers["cache-control"] == "private, no-store"
            assert "Authorization" in response.headers["vary"]
            materials = client.get("/api/athlete/materials", headers=headers)
            assert materials.status_code == 401
            assert materials.headers["cache-control"] == "private, no-store"
            assert client.get("/api/athlete/workspace", headers=headers).status_code == 401
            assert client.patch("/api/athlete/workspace", headers=headers, json={}).status_code == 401


def test_profile_excludes_writes_research_help_and_public_sharing(profile_app, session):
    with TestClient(profile_app) as client:
        for method, path in (
            ("POST", "/api/athlete/evidence"), ("GET", "/api/athlete/evidence/"),
            ("POST", "/api/athlete/materials"), ("GET", "/api/athlete/materials/"),
            ("GET", "/api/athlete/debrief"), ("POST", "/api/athlete/debrief"), ("POST", "/api/athlete/debrief/"),
            ("GET", "/api/athlete/opportunities/engagement"), ("POST", "/api/athlete/opportunities/engagement"),
            ("GET", "/api/athlete/opportunities"), ("POST", "/api/athlete/opportunities"),
            ("POST", "/api/athlete/workspace"), ("DELETE", "/api/athlete/workspace"),
            ("GET", "/api/athlete/workspace/"), ("PATCH", "/api/athlete/workspace/"),
            ("GET", "/api/combine/current"), ("POST", "/api/combine/help"),
            ("POST", "/api/artifacts/draft-outreach"), ("POST", "/api/profile/connect"),
            ("GET", "/api/workspace/inbox/user"), ("GET", "/api/reports/public/token"),
            ("GET", "/docs"), ("GET", "/openapi.json"),
        ):
            response = client.request(method, path, headers=session())
            assert response.status_code in (404, 405)
            assert response.headers["cache-control"] == "private, no-store"


def test_profile_configuration_drift_and_query_overrides_fail_closed(profile_app, session, monkeypatch):
    with TestClient(profile_app) as client:
        response = client.get("/api/athlete/evidence?user_id=2", headers=session())
        assert response.status_code == 400
        assert client.get("/api/athlete/materials?user_id=2", headers=session()).status_code == 400
        assert client.get("/api/athlete/workspace?user_id=2", headers=session()).status_code == 400
        monkeypatch.setenv("DB_USER", "unexpected")
        response = client.get("/api/athlete/evidence", headers=session())
        assert response.status_code == 503
        assert response.headers["cache-control"] == "private, no-store"


def test_profile_cors_preserves_origin_and_authorization_variance(profile_app):
    with TestClient(profile_app) as client:
        response = client.get("/api/athlete/evidence", headers={"Origin": ENV["ALLOWED_ORIGINS"]})
        assert response.status_code == 401
        assert response.headers["access-control-allow-origin"] == ENV["ALLOWED_ORIGINS"]
        assert {"Origin", "Authorization"}.issubset(set(response.headers["vary"].split(", ")))


def test_profile_workspace_patch_preflight_is_allowed_only_in_profile_surface(profile_app):
    headers = {"Origin": ENV["ALLOWED_ORIGINS"], "Access-Control-Request-Method": "PATCH",
               "Access-Control-Request-Headers": "authorization,content-type"}
    with TestClient(profile_app) as client:
        response = client.options("/api/athlete/workspace", headers=headers)
        assert response.status_code == 200
        assert "PATCH" in response.headers["access-control-allow-methods"]
        assert client.options("/api/athlete/workspace", headers={**headers, "Origin": "https://foreign.example.invalid"}).status_code == 400
    with TestClient(candidate_app.create_app()) as client:
        assert client.options("/api/athlete/workspace", headers=headers).status_code == 400


def test_profile_ignores_retired_debrief_settings(profile_app, session, monkeypatch):
    # Ask SPARQ is off for the junior pilot: its settings neither start nor expose it.
    monkeypatch.setenv("PROFILE_DEBRIEF_ENABLED", "true")
    with TestClient(profile_app) as client:
        assert "debrief_enabled" not in client.get("/health").json()
        assert client.post("/api/athlete/debrief", headers=session(),
                           json={"track": "profile", "question": "What can I use?"}).status_code == 404
        assert model_usage._ledger is None
