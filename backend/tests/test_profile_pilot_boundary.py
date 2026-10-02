"""Actual profile ASGI paths: the GMTM entry gate is the only admission.

Converted from the adult admission-file tests (file removed 2026-10-01): absent,
expired, ended and wrong-subject authority now come from the junior entry gate.
"""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest

import athlete_evidence
import athlete_materials
import athlete_workspace as workspace
import junior_entry
import profile_owner
from backend.tests.junior_fakes import ENTRY_USER_ID
from backend.tests.test_profile_candidate_app import profile_app, session  # noqa: F401  (fixtures)
from backend.tests.workspace_fixture_store import WorkspaceStore


LINK = {"id": 91, "user_id": 7201, "clerk_id": "sub_owner"}
PATHS = (
    ("GET", "/api/athlete/evidence"), ("GET", "/api/athlete/materials"),
    ("POST", "/api/athlete/opportunities"), ("POST", "/api/athlete/opportunities/engagement"),
    ("POST", "/api/athlete/debrief"), ("GET", "/api/athlete/workspace"),
    ("PATCH", "/api/athlete/workspace"), ("GET", "/api/profile/by-owner/sub_owner"),
)


@pytest.fixture
def pilot(profile_app, session, monkeypatch):
    # Hosted origin: startup requires GMTM entry (set by the session fixture).
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://sparq.gmtm.com")
    return profile_app


def _no_source_work(monkeypatch):
    for module in (workspace, profile_owner, athlete_evidence, athlete_materials):
        if hasattr(module, "_get_agent_db"):
            monkeypatch.setattr(module, "_get_agent_db", lambda: pytest.fail("source work before admission"))


@pytest.mark.parametrize("change,status", [
    ("absent", 403), ("expired", 401), ("ended", 401), ("notice_missing", 403),
    ("ineligible", 403), ("wrong_subject", 403),
])
def test_all_personal_operations_deny_before_source_work(pilot, session, monkeypatch, change, status):
    _no_source_work(monkeypatch)
    store = junior_entry.store
    if change == "wrong_subject":
        session(sub="another_athlete")  # an entry exists, but for someone else
        headers = session(sub=LINK["clerk_id"], entry=False)
    else:
        headers = session(sub=LINK["clerk_id"], entry=change != "absent")
    if change == "expired":
        store.entries[-1]["entered_at"] -= timedelta(hours=24, seconds=1)
    elif change == "ended":
        store.end_session(LINK["clerk_id"], store.session_jti(LINK["clerk_id"]))
    elif change == "notice_missing":
        store.notices.pop(LINK["clerk_id"])
    elif change == "ineligible":
        import junior_eligibility
        junior_eligibility._cache[ENTRY_USER_ID] = (False, junior_eligibility.time.monotonic())
    with TestClient(pilot) as client:
        for method, path in PATHS:
            response = client.request(method, path, headers=headers, json={})
            assert response.status_code == status, (method, path, response.text)
            assert response.headers["cache-control"] == "private, no-store"
            assert LINK["clerk_id"] not in response.text
        assert client.get("/health").status_code == 200


def test_claim_routes_do_not_exist_in_pilot(pilot, session):
    with TestClient(pilot) as client:
        for headers in ({}, session()):
            assert client.get("/api/claims/synthetic-token", headers=headers).status_code in (401, 403, 404)
            assert client.post("/api/claims/synthetic-token/redeem", headers=headers).status_code in (401, 403, 404)


def test_missing_and_invalid_auth_still_deny_before_admission(pilot, session):
    with TestClient(pilot) as client:
        assert client.get("/api/athlete/workspace").status_code == 401
        assert client.get("/api/athlete/workspace", headers=session(active=False)).status_code == 401


def test_gated_cors_and_health_do_not_require_identity(pilot):
    origin = "https://sparq.gmtm.com"
    with TestClient(pilot) as client:
        response = client.options("/api/athlete/workspace", headers={"Origin": origin,
            "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "authorization,content-type"})
        assert response.status_code == 200
        assert client.get("/health").json()["gmtm_sign_in_configured"] is True
        response = client.get("/api/athlete/workspace", headers={"Origin": origin})
        assert response.headers["access-control-allow-origin"] == origin


def test_admitted_workspace_save_reload_then_ended_session_is_refused(pilot, session, monkeypatch):
    store = WorkspaceStore([LINK])
    monkeypatch.setattr(workspace, "_get_agent_db", store.connect)
    headers = session(sub=LINK["clerk_id"])
    with TestClient(pilot) as client:
        state = client.get("/api/athlete/workspace", headers=headers).json()
        assert state["version"] == 0
        response = client.patch("/api/athlete/workspace", headers=headers, json={
            "link_revision": state["link_revision"], "expected_version": 0,
            "changes": {"goal": {"text": "Find flag opportunities", "destination": "A program", "timeframe": None}}})
        assert response.status_code == 200, response.text
        assert client.get("/api/athlete/workspace", headers=headers).json() == response.json()
        junior_entry.store.end_session(LINK["clerk_id"], junior_entry.store.session_jti(LINK["clerk_id"]))
        assert client.get("/api/athlete/workspace", headers=headers).status_code == 401
    assert all(db.closed and not db.transaction for db in store.connections)
    assert sum(db.commits for db in store.connections) == 1


@pytest.mark.parametrize("change", [{"id": 92}, {"user_id": 7202}, {"clerk_id": "Sub_owner"}])
def test_changed_or_recreated_link_denies_workspace(pilot, session, monkeypatch, change):
    store = WorkspaceStore([{**LINK, **change}])
    monkeypatch.setattr(workspace, "_get_agent_db", store.connect)
    headers = session(sub=LINK["clerk_id"])
    with TestClient(pilot) as client:
        state = client.get("/api/athlete/workspace", headers=headers)
        if state.status_code == 200:
            # The tab's link revision is from the original link: a write must not land.
            response = client.patch("/api/athlete/workspace", headers=headers, json={
                "link_revision": workspace._revision(LINK), "expected_version": 0,
                "changes": {"goal": {"text": "Synthetic", "destination": "Test", "timeframe": None}}})
            assert response.status_code in (403, 409), response.text
        else:
            assert state.status_code in (403, 409), state.text
        assert not store.rows
    assert all(db.closed for db in store.connections)


def test_hosted_profile_refuses_startup_without_gmtm_entry(profile_app, monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://pilot.example.invalid")
    for name in junior_entry.ENTRY_KEYS:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="GMTM entry"):
        with TestClient(profile_app):
            pass
