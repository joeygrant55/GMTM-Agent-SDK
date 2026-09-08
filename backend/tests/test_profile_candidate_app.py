"""Actual profile app authentication/route boundaries with synthetic local JWTs."""
from fastapi.testclient import TestClient
import pytest

import candidate_app
import model_usage
from backend.tests.test_candidate_app import ENV, signed


@pytest.fixture
def profile_app(monkeypatch):
    for name in candidate_app._CONFIGURATION_KEYS:
        monkeypatch.delenv(name, raising=False)
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    return candidate_app.create_app(surface="profile")


def test_profile_manifest_is_explicit_and_excludes_legacy_and_combine_work(profile_app):
    schema = profile_app.openapi()
    expected = {
        "/api/athlete/evidence": "get", "/api/profile/by-clerk/{clerk_id}": "get",
        "/api/claims/{token}": "get", "/api/claims/{token}/redeem": "post",
        "/health": "get",
    }
    assert set(schema["paths"]) == set(expected)
    assert all(set(schema["paths"][path]) == {method} for path, method in expected.items())
    # Choosing this app never widens the original manifest.
    assert "/api/athlete/evidence" not in candidate_app.create_app().openapi()["paths"]
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
        assert response.headers["cache-control"] == "private, no-store"
        assert "Authorization" in response.headers["vary"]
        assert model_usage._ledger is None


def test_profile_rejects_invalid_sessions_before_any_source_read(profile_app, signed):
    # Unmocked database/provider/network calls are blocked by conftest.
    with TestClient(profile_app) as client:
        for headers in ({}, signed(azp=None), signed(sub=" user"), signed(azp="https://foreign.example.invalid")):
            response = client.get("/api/athlete/evidence", headers=headers)
            assert response.status_code == 401
            assert response.headers["cache-control"] == "private, no-store"
            assert "Authorization" in response.headers["vary"]


def test_profile_excludes_writes_research_help_and_public_sharing(profile_app, signed):
    with TestClient(profile_app) as client:
        for method, path in (
            ("POST", "/api/athlete/evidence"), ("GET", "/api/athlete/evidence/"),
            ("GET", "/api/combine/current"), ("POST", "/api/combine/help"),
            ("POST", "/api/artifacts/draft-outreach"), ("POST", "/api/profile/connect"),
            ("GET", "/api/workspace/inbox/user"), ("GET", "/api/reports/public/token"),
            ("GET", "/docs"), ("GET", "/openapi.json"),
        ):
            response = client.request(method, path, headers=signed())
            assert response.status_code in (404, 405)
            assert response.headers["cache-control"] == "private, no-store"


def test_profile_configuration_drift_and_query_overrides_fail_closed(profile_app, signed, monkeypatch):
    with TestClient(profile_app) as client:
        response = client.get("/api/athlete/evidence?user_id=2", headers=signed())
        assert response.status_code == 400
        monkeypatch.setenv("DB_USER", "unexpected")
        response = client.get("/api/athlete/evidence", headers=signed())
        assert response.status_code == 503
        assert response.headers["cache-control"] == "private, no-store"


def test_profile_cors_preserves_origin_and_authorization_variance(profile_app):
    with TestClient(profile_app) as client:
        response = client.get("/api/athlete/evidence", headers={"Origin": ENV["ALLOWED_ORIGINS"]})
        assert response.status_code == 401
        assert response.headers["access-control-allow-origin"] == ENV["ALLOWED_ORIGINS"]
        assert {"Origin", "Authorization"}.issubset(set(response.headers["vary"].split(", ")))
