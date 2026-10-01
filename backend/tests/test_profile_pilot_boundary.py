"""Actual pilot ASGI paths with local JWTs, private synthetic files and fake SQL."""
import asyncio
from datetime import datetime, timedelta, timezone
import json

from fastapi.testclient import TestClient
import pytest

import athlete_evidence
import athlete_materials
import athlete_workspace as workspace
import candidate_app
import profile_admission as admission
import profile_owner
from backend.tests.test_profile_candidate_app import profile_app, session
from backend.tests.workspace_fixture_store import WorkspaceStore, WorkspaceDB


LINK = {"id": 91, "user_id": 7201, "clerk_id": "sub_owner"}
PATHS = (
    ("GET", "/api/athlete/evidence"), ("GET", "/api/athlete/materials"),
    ("POST", "/api/athlete/opportunities"), ("POST", "/api/athlete/opportunities/engagement"),
    ("POST", "/api/athlete/debrief"), ("GET", "/api/athlete/workspace"),
    ("PATCH", "/api/athlete/workspace"), ("GET", "/api/profile/by-owner/sub_owner"),
)


@pytest.fixture
def pilot(profile_app, monkeypatch, tmp_path):
    now = datetime.now(timezone.utc)
    record = dict(clerk_id=LINK["clerk_id"], user_id=LINK["user_id"], link_row_id=LINK["id"],
                  link_revision=workspace._revision(LINK), adult_self_owned=True,
                  review_ref="synthetic-adult-review", reviewed_at=(now-timedelta(days=2)).isoformat(),
                  starts_at=(now-timedelta(days=1)).isoformat(),
                  expires_at=(now+timedelta(days=1)).isoformat(), revoked=False)
    path = (tmp_path / "admission.json").resolve()
    def publish(records=None):
        path.write_text(json.dumps({"schema": 1, "admissions": [record] if records is None else records}))
        path.chmod(0o600)
    publish()
    monkeypatch.setenv("PROFILE_ADMISSION_ENABLED", "true")
    monkeypatch.setenv("PROFILE_ADMISSION_FILE", str(path))
    return profile_app, record, publish, path


@pytest.mark.parametrize("change", ["absent", "revoked", "expired", "not_started", "wrong_subject"])
def test_all_personal_operations_deny_before_source_work(pilot, session, change):
    app, record, publish, _ = pilot
    now = datetime.now(timezone.utc)
    if change == "revoked": record["revoked"] = True
    elif change == "expired": record["expires_at"] = (now-timedelta(seconds=1)).isoformat()
    elif change == "not_started": record["starts_at"] = (now+timedelta(minutes=1)).isoformat()
    publish([] if change == "absent" else None)
    headers = session(sub="uninvited" if change == "wrong_subject" else LINK["clerk_id"])
    with TestClient(app) as client:
        for method, path in PATHS:
            response = client.request(method, path, headers=headers, json={})
            assert response.status_code == 403, (method, path, response.text)
            assert response.headers["cache-control"] == "private, no-store"
            assert LINK["clerk_id"] not in response.text
        assert client.get("/health").status_code == 200
    assert not admission.is_active()


def test_claim_routes_do_not_exist_in_pilot(pilot, session):
    with TestClient(pilot[0]) as client:
        for headers in ({}, session()):
            assert client.get("/api/claims/synthetic-token", headers=headers).status_code in (401, 403, 404)
            assert client.post("/api/claims/synthetic-token/redeem", headers=headers).status_code in (401, 403, 404)


def test_missing_and_invalid_auth_still_deny_before_admission(pilot, session):
    with TestClient(pilot[0]) as client:
        assert client.get("/api/athlete/workspace").status_code == 401
        assert client.get("/api/athlete/workspace", headers=session(active=False)).status_code == 401


def test_file_loss_malformed_contents_and_permissions_fail_closed(pilot, session):
    app, _, publish, path = pilot
    with TestClient(app) as client:
        for mutation in (lambda: path.unlink(), lambda: path.write_text("invalid"), lambda: (publish(), path.chmod(0o644))):
            mutation()
            response = client.get("/api/athlete/workspace", headers=session())
            assert response.status_code == 503
            assert str(path) not in response.text
            publish()


def test_gated_cors_and_health_do_not_require_identity(pilot):
    with TestClient(pilot[0]) as client:
        response = client.options("/api/athlete/workspace", headers={"Origin": "http://127.0.0.1:3218",
            "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "authorization,content-type"})
        assert response.status_code == 200
        assert client.get("/health").json()["pilot_admission_enabled"] is True
        response = client.get("/api/athlete/workspace", headers={"Origin": "http://127.0.0.1:3218"})
        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3218"


def test_admitted_workspace_save_reload_revocation_and_context_cleanup(pilot, session, monkeypatch):
    app, record, publish, _ = pilot
    store = WorkspaceStore([LINK])
    monkeypatch.setattr(workspace, "_get_agent_db", store.connect)
    with TestClient(app) as client:
        state = client.get("/api/athlete/workspace", headers=session()).json()
        assert state["version"] == 0
        response = client.patch("/api/athlete/workspace", headers=session(), json={
            "link_revision": state["link_revision"], "expected_version": 0,
            "changes": {"goal": {"text": "Find flag opportunities", "destination": "A program", "timeframe": None}}})
        assert response.status_code == 200, response.text
        assert client.get("/api/athlete/workspace", headers=session()).json() == response.json()
        record["revoked"] = True
        publish()
        assert client.get("/api/athlete/workspace", headers=session()).status_code == 403
    assert not admission.is_active()
    assert all(db.closed and not db.transaction for db in store.connections)
    assert sum(db.commits for db in store.connections) == 1


@pytest.mark.parametrize("change", [{"id": 92}, {"user_id": 7202}, {"clerk_id": "Sub_owner"}])
def test_changed_or_recreated_link_denies_all_read_adapters(pilot, session, monkeypatch, change):
    store = WorkspaceStore([{**LINK, **change}])
    for module in (workspace, profile_owner, athlete_evidence, athlete_materials):
        monkeypatch.setattr(module, "_get_agent_db", store.connect)
    with TestClient(pilot[0]) as client:
        for path in ("/api/athlete/workspace", "/api/athlete/evidence", "/api/athlete/materials", "/api/profile/by-owner/sub_owner"):
            response = client.get(path, headers=session())
            assert response.status_code in (403, 409), (path, response.text)
            assert "7202" not in response.text
    assert all(db.closed for db in store.connections)


def test_revocation_after_write_before_commit_rolls_back(pilot, session, monkeypatch):
    app, record, publish, _ = pilot
    store = WorkspaceStore([LINK])
    monkeypatch.setattr(workspace, "_get_agent_db", store.connect)
    original = WorkspaceDB.execute
    def execute(db, sql, params=None):
        original(db, sql, params)
        if sql.startswith("INSERT INTO athlete_workspaces"):
            record["revoked"] = True
            publish()
    monkeypatch.setattr(WorkspaceDB, "execute", execute)
    with TestClient(app) as client:
        response = client.patch("/api/athlete/workspace", headers=session(), json={
            "link_revision": workspace._revision(LINK), "expected_version": 0,
            "changes": {"goal": {"text": "Synthetic", "destination": "Test", "timeframe": None}}})
        assert response.status_code == 403, response.text
    assert not store.rows
    assert all(db.closed and not db.transaction and db.commits == 0 for db in store.connections)


def test_hosted_profile_refuses_disabled_gate(profile_app, monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://pilot.example.invalid")
    with pytest.raises(ValueError, match="admission"):
        with TestClient(profile_app):
            pass


def test_revocation_stops_model_call_before_provider_work(pilot):
    import profile_debrief
    _, record, publish, path = pilot
    token = admission.begin_request(admission.Configuration(str(path)), LINK["clerk_id"])
    try:
        record["revoked"] = True
        publish()
        with pytest.raises(admission.AdmissionError):
            # No body/client/model interfaces supplied: admission must stop the
            # operation before constructing any provider payload or client.
            asyncio.run(profile_debrief._generate(None, None, None, None, None))
    finally:
        admission.reset_request(token)


def test_revocation_after_measurement_owner_read_prevents_emission(pilot, monkeypatch):
    import opportunity_engagement as engagement
    from backend.tests.test_opportunity_engagement import environment, event, NOW
    from backend.tests.test_athlete_opportunities import record as opportunity_record
    _, record, publish, path = pilot
    store, emitted = WorkspaceStore([LINK]), []
    monkeypatch.setattr(engagement, "_get_agent_db", store.connect)
    monkeypatch.setattr(engagement, "RECORDS", (opportunity_record(),))
    close = engagement._close
    def revoke_after_read(db):
        close(db)
        record["revoked"] = True
        publish()
    monkeypatch.setattr(engagement, "_close", revoke_after_read)
    token = admission.begin_request(admission.Configuration(str(path)), LINK["clerk_id"])
    try:
        with pytest.raises(admission.AdmissionError):
            engagement.capture(LINK["clerk_id"], event(link_revision=workspace._revision(LINK)),
                engagement.validate_configuration(environment()), engagement.RateLimit(), now=NOW, emit=emitted.append)
        assert not emitted
    finally:
        admission.reset_request(token)
