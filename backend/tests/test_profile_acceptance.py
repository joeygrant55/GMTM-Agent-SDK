"""Real candidate/HTTP/signature code with injected keys and in-memory SQL only."""
from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import time
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import jwt
import pytest

import auth
import candidate_app
import athlete_workspace as workspace
from verification import profile_acceptance as acceptance
from backend.tests.test_candidate_app import ENV as BASE_ENV
from backend.tests.workspace_fixture_store import WorkspaceStore
from backend.tests.test_profile_candidate_app import ENTRY_ENV, GSH, SESSION_SECRET
import junior_entry

ORIGIN, HOST, SUBJECT = "http://localhost:3218", "127.0.0.1:8118", "clerk_owner"
LINK = {"id": 1, "user_id": 2, "clerk_id": SUBJECT}
GOAL = {"text": "Understand my flag opportunities", "destination": None, "timeframe": None}
DRAFT = {"kind": "summary", "text": "Exact edit.\n\tMy words.", "goal": GOAL["text"], "destination": "",
         "selected_evidence_ids": [], "selected_material_ids": [], "inputs_changed": False}


class Cursor:
    def __init__(self, db): self.db, self.rows = db, []
    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def close(self): pass
    @property
    def rowcount(self): return self.db.base.rowcount
    def execute(self, sql, params=None):
        key = acceptance.normalized(sql)
        if key == "START TRANSACTION READ ONLY":
            self.db.readonly = True
            return
        if self.db.kind == "gmtm":
            self.db.store.source_queries.append((key, params))
            if "FROM users u" in key: self.rows = [{"user_id": self.db.store.source_owner, "first_name": "Joey", "last_name": "Fixture"}]
            else: self.rows = []
            return
        if key in (acceptance.PAIR_FORWARD, acceptance.PAIR_REVERSE):
            field = "clerk_id" if key == acceptance.PAIR_FORWARD else "user_id"
            self.rows = [{"user_id": row["user_id"], "clerk_id": row["clerk_id"]} for row in self.db.store.links if row[field] == params[0]][:2]
        elif key == acceptance.PROFILE_SQL:
            self.rows = [{"id": 9, "clerk_id": SUBJECT}]
        else:
            result = self.db.base.execute(sql, params)
            self.rows = self.db.base.fetchall()
            return result
    def fetchall(self): return deepcopy(self.rows)
    def fetchone(self): return deepcopy(self.rows[0]) if self.rows else None


class Raw:
    def __init__(self, store, kind):
        self.store, self.kind, self.readonly = store, kind, False
        self.base = store.connect()
    def cursor(self): return Cursor(self)
    def begin(self): return self.base.begin()
    def commit(self): return self.base.commit()
    def rollback(self): return self.base.rollback()
    def close(self): return self.base.close()


@pytest.fixture
def setup(monkeypatch, tmp_path):
    # No Clerk on profile (rev 3): the owner carries a SPARQ session token.
    env = {**BASE_ENV, **ENTRY_ENV, "ALLOWED_ORIGINS": ORIGIN, "PROFILE_DEBRIEF_ENABLED": "false",
           "AGENT_DB_HOST": "fixture.proxy.rlwy.net"}
    env.pop("CLERK_ISSUER", None); env.pop("CLERK_AUTHORIZED_PARTIES", None)
    for name in candidate_app._CONFIGURATION_KEYS: monkeypatch.delenv(name, raising=False)
    for key, value in env.items(): monkeypatch.setenv(key, value)
    jti = "owner-acceptance-session-jti"
    junior_entry.store.set_session(SUBJECT, jti, None)
    def headers(*, secret=SESSION_SECRET, **overrides):
        now = int(time.time())
        claims = {"sub": SUBJECT, "jti": jti, "gsh": GSH, "iat": now, "exp": now + 120, **overrides}
        claims = {k: v for k, v in claims.items() if v is not None}
        return {"Origin": ORIGIN, "Authorization": "Bearer " + jwt.encode(claims, secret, algorithm="HS256")}
    store = WorkspaceStore([LINK])
    store.source_owner, store.source_queries = 2, []
    monkeypatch.setattr(acceptance, "_raw_connect", lambda settings: Raw(store, "gmtm" if settings["database"] == "gmtm" else "agent"))
    def settings(prefix):
        return {"host": env[prefix + "HOST"], "port": int(env.get(prefix + "PORT", "3306")),
                "database": env.get(prefix + "NAME", "gmtm"), "user": env[prefix + "USER"], "password": env[prefix + "PASSWORD"]}
    run_dir = tmp_path / "acceptance"
    run_dir.mkdir(mode=0o700)
    kwargs = dict(agent_settings=settings("AGENT_DB_"), gmtm_settings=settings("DB_"), frontend_origin=ORIGIN, backend_host=HOST, run_dir=run_dir)
    app = acceptance.create_acceptance_app(**kwargs)
    return SimpleNamespace(app=app, store=store, headers=headers, run_dir=run_dir, kwargs=kwargs)


def patch(client, setup, before, **changes):
    return client.patch("/api/athlete/workspace", headers=setup.headers(), json={
        "link_revision": before["link_revision"], "expected_version": before["version"], "changes": changes})


def test_actual_workspace_goal_draft_save_and_reload_preserves_before_state(setup):
    original = workspace._get_agent_db
    with TestClient(setup.app, base_url="http://" + HOST) as client:
        before = client.get("/api/athlete/workspace", headers=setup.headers()).json()
        saved = patch(client, setup, before, goal=GOAL).json()
        drafted = patch(client, setup, saved, draft=DRAFT).json()
        returned = client.get("/api/athlete/workspace", headers=setup.headers()).json()
        assert returned == drafted and returned["goal"] == GOAL and returned["draft"] == DRAFT
        assert json.loads((setup.run_dir / "private-workspace-before.json").read_text())["workspace"] == before
        assert returned["version"] == 2 and before["version"] == 0
        assert workspace._get_agent_db is not original
    assert workspace._get_agent_db is original
    ledger = json.loads((setup.run_dir / "acceptance-ledger.json").read_text())
    assert ledger["status"] == "stopped" and ledger["attempts"]["patch_attempts"] == 2
    assert ledger["connections_opened"] == ledger["connections_closed"]
    assert ledger["commits_acknowledged"] == 2 and ledger["provider_calls"] == ledger["gmtm_writes"] == 0
    assert all(db.closed for db in setup.store.connections)
    assert "Exact edit" not in json.dumps(ledger) and SUBJECT not in json.dumps(ledger)
    assert stat.S_IMODE((setup.run_dir / "private-workspace-before.json").stat().st_mode) == 0o600


@pytest.mark.parametrize("method,path", [("GET", "/api/claims/token"), ("POST", "/api/claims/token/redeem"),
    ("POST", "/api/athlete/debrief"), ("GET", "/api/combine/current"), ("DELETE", "/api/athlete/workspace"),
    ("GET", "/api/athlete/evidence?user_id=2"), ("GET", "/api/athlete/workspace/")])
def test_disallowed_routes_are_rejected_before_any_connection(setup, method, path):
    with TestClient(setup.app, base_url="http://" + HOST) as client:
        assert client.request(method, path, headers=setup.headers()).status_code == 403
    assert not setup.store.connections


@pytest.mark.parametrize("headers", ["missing", "wrong_origin", "wrong_host", "expired", "inactive_jti", "wrong_secret", "clerk_jwt", "wrong_subject_path"])
def test_actual_auth_and_http_boundaries_precede_personal_reads(setup, headers):
    values, path = setup.headers(), "/api/athlete/workspace"
    if headers == "missing": values.pop("Authorization")
    elif headers == "wrong_origin": values["Origin"] = "http://localhost:9999"
    elif headers == "wrong_host": values["Host"] = "other.invalid"
    elif headers == "expired": values = setup.headers(exp=int(time.time()) - 60)
    elif headers == "inactive_jti": values = setup.headers(jti="replaced-by-a-newer-entry")
    elif headers == "wrong_secret": values = setup.headers(secret="w" * 40)
    elif headers == "clerk_jwt":
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        values["Authorization"] = "Bearer " + jwt.encode({"sub": SUBJECT, "exp": int(time.time()) + 120}, key, algorithm="RS256")
    else: path = "/api/profile/by-clerk/other"
    with TestClient(setup.app, base_url="http://" + HOST) as client:
        assert client.get(path, headers=values).status_code in (401, 403)
    assert not setup.store.connections


def test_profile_evidence_and_materials_use_current_real_routes_with_owned_fixture(setup):
    with TestClient(setup.app, base_url="http://" + HOST) as client:
        assert client.get("/api/profile/by-clerk/" + SUBJECT, headers=setup.headers()).json()["user_id"] == 2
        evidence = client.get("/api/athlete/evidence", headers=setup.headers())
        assert evidence.status_code == 200 and evidence.json()["state"] == "ready"
        materials = client.get("/api/athlete/materials", headers=setup.headers())
        assert materials.status_code == 200 and materials.json()["state"] == "ready"
    assert setup.store.source_queries and all(params[0] == 2 for _, params in setup.store.source_queries)


def test_foreign_link_and_changed_link_never_expose_workspace(setup):
    setup.store.links = [{**LINK, "user_id": 3}]
    with TestClient(setup.app, base_url="http://" + HOST) as client:
        assert client.get("/api/athlete/workspace", headers=setup.headers()).status_code == 409
    assert not setup.store.rows and not setup.store.source_queries


def test_three_explicit_patch_attempts_and_before_state_gate(setup):
    with TestClient(setup.app, base_url="http://" + HOST) as client:
        invalid = {"link_revision": workspace._revision(LINK), "version": 0}
        assert patch(client, setup, invalid, goal=GOAL).status_code == 409
        before = client.get("/api/athlete/workspace", headers=setup.headers()).json()
        saved = patch(client, setup, before, goal=GOAL).json()
        assert patch(client, setup, saved, draft=DRAFT).status_code == 200
        assert patch(client, setup, saved, draft=DRAFT).status_code == 429
    assert setup.app.ledger.data["attempts"]["patch_attempts"] == 3


def test_preexisting_state_survives_partial_goal_change(setup):
    from datetime import datetime
    setup.store.rows[SUBJECT.encode()] = {"clerk_id": SUBJECT.encode(), "athlete_link_id": 1, "gmtm_user_id": 2,
        "version": 1, "payload": json.dumps({"goal": GOAL, "featured_source_id": None, "draft": DRAFT, "recent_work": []}),
        "created_at": datetime.now(), "updated_at": datetime.now()}
    with TestClient(setup.app, base_url="http://" + HOST) as client:
        before = client.get("/api/athlete/workspace", headers=setup.headers()).json()
        response = patch(client, setup, before, goal={**GOAL, "text": "Updated goal"})
        assert response.status_code == 200 and response.json()["draft"] == DRAFT
    assert json.loads((setup.run_dir / "private-workspace-before.json").read_text())["workspace"]["draft"] == DRAFT


def test_uncertain_commit_blocks_replay_but_allows_reconciliation_get(setup):
    with TestClient(setup.app, base_url="http://" + HOST) as client:
        before = client.get("/api/athlete/workspace", headers=setup.headers()).json()
        setup.store.failures["commit_after_apply"] = RuntimeError("SECRET LOST ACK")
        response = patch(client, setup, before, goal=GOAL)
        assert response.status_code == 503 and "SECRET" not in response.text
        setup.store.failures.clear()
        actual = client.get("/api/athlete/workspace", headers=setup.headers()).json()
        assert actual["goal"] == GOAL and actual["version"] == 1
        assert patch(client, setup, actual, draft=DRAFT).status_code == 409
    assert setup.app.ledger.data["writes_closed"]


def test_ledger_is_exclusive_and_config_rejects_provider_credentials(setup, monkeypatch):
    with pytest.raises(FileExistsError): acceptance.create_acceptance_app(**setup.kwargs)
    monkeypatch.setenv("OPENAI_API_KEY", "SECRET CANARY")
    with pytest.raises(ValueError): acceptance.create_acceptance_app(**setup.kwargs)
    setup.app.ledger.close()


def test_cors_preflight_has_no_source_reads(setup):
    with TestClient(setup.app, base_url="http://" + HOST) as client:
        headers = {"Origin": ORIGIN, "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "authorization,content-type"}
        assert client.options("/api/athlete/workspace", headers=headers).status_code == 204
        assert client.options("/api/athlete/debrief", headers=headers).status_code == 403
    assert not setup.store.connections


def test_read_only_keeps_owned_source_gets_and_rejects_patch_before_auth_or_db(setup):
    assert setup.app.ledger.data["caps"]["patch_attempts"] == 3
    setup.app.ledger.close()
    run_dir = setup.run_dir.parent / "read-only"
    run_dir.mkdir(mode=0o700)
    app = acceptance.create_acceptance_app(**{**setup.kwargs, "run_dir": run_dir, "read_only": True})
    with TestClient(app, base_url="http://" + HOST) as client:
        assert client.patch("/api/athlete/workspace", headers={"Origin": ORIGIN}, json={}).status_code == 403
        preflight = {"Origin": ORIGIN, "Access-Control-Request-Method": "PATCH"}
        assert client.options("/api/athlete/workspace", headers=preflight).status_code == 403
        assert not setup.store.connections
        assert all(value == 0 for value in app.ledger.data["attempts"].values())
        assert client.get("/api/profile/by-clerk/" + SUBJECT, headers=setup.headers()).json()["user_id"] == 2
        for path in ("evidence", "materials", "workspace"):
            response = client.get("/api/athlete/" + path, headers=setup.headers())
            assert response.status_code == 200 and response.json()["state"] == "ready"
        source_queries = list(setup.store.source_queries)
        response = client.post("/api/athlete/opportunities", headers=setup.headers(), json={
            "pathway": "adult_flag", "category": "unspecified", "format": "any",
            "link_revision": response.json()["link_revision"],
        })
        assert response.status_code == 200 and response.json()["state"] == "ready"
        assert setup.store.source_queries == source_queries
        connections = len(setup.store.connections)
        attempts = dict(app.ledger.data["attempts"])
        assert client.patch("/api/athlete/workspace", headers=setup.headers(), json={}).status_code == 403
        assert len(setup.store.connections) == connections and app.ledger.data["attempts"] == attempts
        assert client.post("/api/athlete/opportunities/engagement", headers=setup.headers(), json={}).status_code == 403
        assert len(setup.store.connections) == connections and app.ledger.data["attempts"] == attempts
    ledger = json.loads((run_dir / "acceptance-ledger.json").read_text())
    assert ledger["caps"] == {**acceptance.CAPS, "patch_attempts": 0}
    assert ledger["attempts"]["patch_attempts"] == ledger["commits_attempted"] == 0
    assert ledger["attempts"]["personal_requests"] == 5
    assert not setup.store.rows
    assert setup.store.source_queries and all(params[0] == 2 for _, params in setup.store.source_queries)
    assert acceptance.CAPS["patch_attempts"] == setup.app.ledger.data["caps"]["patch_attempts"] == 3


@pytest.mark.parametrize("read_only", [None, 0, 1, "true", "false"])
def test_read_only_requires_boolean_before_configuration_or_ledger_creation(setup, read_only, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "SECRET CANARY")
    with pytest.raises(ValueError, match="Acceptance read_only must be a boolean"):
        acceptance.create_acceptance_app(**setup.kwargs, read_only=read_only)
    assert not setup.store.connections
    setup.app.ledger.close()
