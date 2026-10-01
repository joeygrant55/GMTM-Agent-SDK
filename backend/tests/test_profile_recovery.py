"""Offline recovery reads: no bootstrap, model, mutation or real identity lookup."""

from copy import deepcopy
import sys
from types import ModuleType

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import profile_api
from auth import require_identity


CALLER = "user_alpha"


class FakeDB:
    def __init__(self, store):
        self.store, self.rows, self.closed, self.cursor_closed = store, [], False, False

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cursor_closed = True

    def execute(self, sql, params):
        sql = " ".join(sql.split())
        self.store["queries"].append((sql, params))
        if not sql.startswith("SELECT "):
            self.store["writes"] += 1
            raise AssertionError("Recovery may only SELECT")
        if self.store["query_failure"] == len(self.store["queries"]):
            raise RuntimeError("PRIVATE_SOURCE_ERROR")
        if "FROM athlete_profiles WHERE clerk_id = %s" in sql:
            assert params == (CALLER,)
            self.rows = deepcopy(self.store["forward"])
        elif "FROM athlete_profiles WHERE user_id = %s" in sql:
            assert params == (4521,)
            self.rows = deepcopy(self.store["reverse"])
        elif "FROM sparq_profiles WHERE clerk_id = %s" in sql:
            assert params == (CALLER,)
            self.rows = deepcopy(self.store["workspace"])
        else:
            raise AssertionError("Unexpected recovery query")

    def fetchall(self):
        return self.rows

    def fetchone(self):
        # Retains the old first-row behavior so ambiguity regressions fail if
        # this endpoint is reverted to its former implementation.
        return self.rows[0] if self.rows else None

    def commit(self):
        self.store["commits"] += 1
        raise AssertionError("Recovery cannot commit")

    def close(self):
        self.closed = True
        if self.store["close_failure"]:
            raise RuntimeError("PRIVATE_CLOSE_ERROR")


@pytest.fixture
def client(monkeypatch):
    store = {"forward": [], "reverse": [], "workspace": [], "connections": [], "queries": [],
             "writes": 0, "commits": 0, "bootstrap_calls": 0, "query_failure": None,
             "connect_failure": False, "close_failure": False}
    def database():
        if store["connect_failure"]:
            raise RuntimeError("PRIVATE_CONNECTION_ERROR")
        db = FakeDB(store)
        store["connections"].append(db)
        return db
    monkeypatch.setattr(profile_api, "_get_agent_db", database)
    bootstrap = ModuleType("workspace_bootstrap")
    def forbidden_bootstrap(*_, **__):
        store["bootstrap_calls"] += 1
        raise AssertionError("Recovery must not bootstrap or invoke models")
    bootstrap.ensure_workspace_profile = forbidden_bootstrap
    monkeypatch.setitem(sys.modules, "workspace_bootstrap", bootstrap)
    app = FastAPI()
    app.include_router(profile_api.router)
    app.dependency_overrides[require_identity] = lambda: CALLER
    with TestClient(app) as http:
        http.store = store
        yield http
    assert store["writes"] == store["commits"] == store["bootstrap_calls"] == 0
    assert all(db.closed for db in store["connections"])


def get(client, clerk_id=CALLER):
    return client.get(f"/api/profile/by-owner/{clerk_id}")


def linked(client):
    row = {"user_id": 4521, "clerk_id": CALLER}
    client.store.update(forward=[deepcopy(row)], reverse=[deepcopy(row)])


def test_unauthenticated_and_foreign_lookups_do_not_open_database(client):
    assert get(client, "user_beta").status_code == 403
    assert get(client, "USER_ALPHA").status_code == 403
    client.app.dependency_overrides.clear()
    assert get(client).status_code == 401
    assert client.store["connections"] == client.store["queries"] == []


@pytest.mark.parametrize("has_workspace", [False, True])
def test_existing_legacy_link_has_compatible_read_only_response(client, has_workspace):
    linked(client)
    if has_workspace:
        client.store["workspace"] = [{"id": 71, "clerk_id": CALLER}]
    expected = {"found": True, "user_id": 4521, "has_sparq_profile": has_workspace}
    for _ in range(2):
        response = get(client)
        assert response.status_code == 200 and response.json() == expected
    assert len(client.store["queries"]) == 6
    assert all(sql.endswith("LIMIT 2") for sql, _ in client.store["queries"])
    assert all(db.cursor_closed for db in client.store["connections"])


@pytest.mark.parametrize("has_workspace", [False, True])
def test_workspace_only_and_no_profile_responses_are_compatible(client, has_workspace):
    if has_workspace:
        client.store["workspace"] = [{"id": 71, "clerk_id": CALLER}]
    response = get(client)
    assert response.status_code == 200
    assert response.json() == {"found": False, "user_id": None, "has_sparq_profile": has_workspace}
    assert len(client.store["queries"]) == 2
    assert all(sql.endswith("LIMIT 2") for sql, _ in client.store["queries"])


@pytest.mark.parametrize("rows", [
    [{"user_id": 4521, "clerk_id": CALLER}, {"user_id": 4522, "clerk_id": CALLER}],
    [{"user_id": 4521, "clerk_id": CALLER}] * 2,
])
def test_multiple_forward_rows_never_select_first_or_fall_back_to_workspace(client, rows):
    client.store["forward"] = rows
    client.store["workspace"] = [{"id": 71, "clerk_id": CALLER}]
    response = get(client)
    assert response.status_code == 409 and "user_id" not in response.json()
    assert len(client.store["queries"]) == 1


@pytest.mark.parametrize("rows", [[], [{"user_id": 4521, "clerk_id": "user_beta"}],
    [{"user_id": 4521, "clerk_id": CALLER}, {"user_id": 4521, "clerk_id": "user_beta"}],
    [{"user_id": 4521, "clerk_id": CALLER}] * 2,
    [{"user_id": 9999, "clerk_id": CALLER}], [None],
    [{"user_id": 4521, "clerk_id": "USER_ALPHA"}],
])
def test_reverse_link_must_be_present_unique_and_exactly_owned(client, rows):
    linked(client)
    client.store["reverse"] = rows
    response = get(client)
    assert response.status_code == 409 and "user_id" not in response.json()
    assert len(client.store["queries"]) == 2


@pytest.mark.parametrize("bad", [None, 0, -1, True, 4521.0, "4521", "invalid"])
def test_malformed_forward_identity_never_becomes_a_match(client, bad):
    client.store["forward"] = [{"user_id": bad, "clerk_id": CALLER}]
    assert get(client).status_code == 409
    assert len(client.store["queries"]) == 1


@pytest.mark.parametrize("row", [None, {}, {"user_id": 4521},
    {"user_id": 4521, "clerk_id": "user_beta"}, {"user_id": 4521, "clerk_id": "USER_ALPHA"}])
def test_forward_owner_must_match_case_sensitively(client, row):
    client.store["forward"] = [row]
    assert get(client).status_code == 409


@pytest.mark.parametrize("rows", [
    [{"id": 71, "clerk_id": CALLER}, {"id": 72, "clerk_id": CALLER}],
    [{"id": 71, "clerk_id": CALLER}] * 2,
    [None], [{"id": None, "clerk_id": CALLER}], [{"id": True, "clerk_id": CALLER}],
    [{"id": 0, "clerk_id": CALLER}], [{"id": "71", "clerk_id": CALLER}],
    [{"id": 71, "clerk_id": "user_beta"}], [{"id": 71, "clerk_id": "USER_ALPHA"}],
])
def test_ambiguous_or_invalid_workspace_does_not_claim_recovery(client, rows):
    client.store["workspace"] = rows
    assert get(client).status_code == 409


@pytest.mark.parametrize("query", [1, 2, 3])
def test_source_query_failures_are_generic_errors_not_no_match(client, query):
    linked(client)
    client.store["query_failure"] = query
    response = get(client)
    assert response.status_code == 503
    assert "PRIVATE" not in response.text and "found" not in response.json()
    assert all(db.cursor_closed for db in client.store["connections"])


@pytest.mark.parametrize("failure", ["connect_failure", "close_failure"])
def test_connection_lifecycle_failure_never_returns_success_or_raw_error(client, failure):
    client.store[failure] = True
    response = get(client)
    assert response.status_code == 503 and "PRIVATE" not in response.text
