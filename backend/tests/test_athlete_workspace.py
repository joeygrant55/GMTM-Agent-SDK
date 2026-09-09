"""Owner/link-bound persistence and actual HTTP parsing with in-memory SQL only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import athlete_workspace as api
from auth import require_clerk_id
from backend.tests.workspace_fixture_store import DriverError, WorkspaceStore


CALLER = "clerk_workspace_owner"
OWNER = 7201
LINK = {"id": 91, "user_id": OWNER, "clerk_id": CALLER}
GOAL = {"text": "Play flag football", "destination": "A coach I know", "timeframe": None}
DRAFT = {"kind": "introduction", "text": "My exact edited text.\n\tThank you!", "goal": GOAL["text"],
         "destination": "Coach", "selected_evidence_ids": ["metric-1"],
         "selected_material_ids": ["film-301", "submission-101-0123456789abcdef"], "inputs_changed": False}


@pytest.fixture
def store(monkeypatch):
    fixture = WorkspaceStore([LINK])
    monkeypatch.setattr(api, "_get_agent_db", fixture.connect)
    monkeypatch.setattr(api, "_get_gmtm_db", lambda: (_ for _ in ()).throw(AssertionError("Real source forbidden")))
    yield fixture
    assert all(db.closed and not db.transaction for db in fixture.connections)


@pytest.fixture
def client(store):
    app = FastAPI()
    app.add_api_route("/api/athlete/workspace", api.current_athlete_workspace, methods=["GET"])
    app.add_api_route("/api/athlete/workspace", api.update_athlete_workspace, methods=["PATCH"])
    app.dependency_overrides[require_clerk_id] = lambda: CALLER
    with TestClient(app) as instance:
        yield instance


def request(version=0, **changes):
    return {"link_revision": api._revision(LINK), "expected_version": version, "changes": changes}


def save(version=0, **changes):
    return api.save_workspace(CALLER, request(version, **changes))


def test_get_empty_never_creates_or_reads_gmtm(store):
    state = api.read_workspace(CALLER)
    assert state == {"state": "ready", "link_revision": api._revision(LINK), "version": 0,
                     "owner_scope": api.owner_scope(CALLER, OWNER),
                     "goal": None, "featured_source_id": None, "draft": None, "recent_work": [], "updated_at": None}
    assert not store.rows
    assert all(query.startswith("SELECT ") for query, _ in store.queries)


def test_goal_and_exact_draft_survive_reads_and_partial_changes(store):
    initial = save(goal=GOAL, draft=DRAFT)
    assert initial["version"] == 1
    assert api.read_workspace(CALLER) == initial
    second = save(1, goal={**GOAL, "text": "A new goal"})
    assert second["draft"] == DRAFT
    assert second["recent_work"][0]["kind"] == "goal_saved"
    assert [event["kind"] for event in initial["recent_work"]] == ["goal_saved", "draft_saved"]
    assert all(set(event) == {"id", "kind", "at"} for event in second["recent_work"])
    assert "Coach" not in json.dumps(second["recent_work"])


def test_explicit_remove_keeps_other_fields_and_noop_does_not_add_events(store):
    initial = save(goal=GOAL, draft=DRAFT)
    assert save(1, goal=GOAL) == initial
    assert sum(db.commits for db in store.connections) == 1
    removed = save(1, draft=None)
    assert removed["draft"] is None and removed["goal"] == GOAL
    assert removed["recent_work"][0]["kind"] == "draft_removed"
    assert save(2, goal=None)["goal"] is None


def test_source_outage_does_not_block_saved_goal_draft_or_get(store):
    state = save(goal=GOAL, draft=DRAFT)
    assert api.read_workspace(CALLER)["draft"] == DRAFT
    with pytest.raises(api.WorkspaceError) as caught:
        save(state["version"], featured_source_id="film-301")
    assert caught.value.status == 503
    assert api.read_workspace(CALLER) == state


def test_optional_table_failure_is_redacted_without_a_write(client, store):
    store.failures["read_workspace"] = RuntimeError("SECRET SQL PASSWORD")
    response = client.get("/api/athlete/workspace")
    assert response.status_code == 503 and response.json()["code"] == "workspace_unavailable"
    assert "SECRET" not in response.text and not store.rows
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"


@pytest.mark.parametrize("links,code", [([], "workspace_unlinked"),
    ([LINK, {**LINK, "id": 92, "user_id": 7202}], "workspace_link_changed"),
    ([LINK, {**LINK, "id": 92, "clerk_id": "other"}], "workspace_link_changed"),
    ([{**LINK, "id": True}], "workspace_link_changed"),
    ([{**LINK, "user_id": True}], "workspace_link_changed")])
def test_ambiguous_unlinked_and_malformed_owners_fail_before_workspace(store, links, code):
    store.links = deepcopy(links)
    with pytest.raises(api.WorkspaceError) as caught:
        api.read_workspace(CALLER)
    assert caught.value.code == code
    assert not any("athlete_workspaces" in query for query, _ in store.queries)


def test_case_insensitive_legacy_link_match_does_not_authorize(store):
    store.case_insensitive = True
    store.links = [{**LINK, "clerk_id": CALLER.upper()}]
    with pytest.raises(api.WorkspaceError, match="workspace_link_changed"):
        api.read_workspace(CALLER)


def test_new_link_version_zero_cannot_accept_stale_tab_payload(store):
    store.links = [{**LINK, "id": 92, "user_id": 7202}]
    with pytest.raises(api.WorkspaceError, match="workspace_link_changed"):
        save(goal=GOAL)
    assert not store.rows


@pytest.mark.parametrize("change", [{"id": 92}, {"user_id": 7202}])
def test_existing_workspace_never_restored_after_relink(store, change):
    save(goal=GOAL, draft=DRAFT)
    store.links = [{**LINK, **change}]
    with pytest.raises(api.WorkspaceError, match="workspace_link_changed"):
        api.read_workspace(CALLER)
    with pytest.raises(api.WorkspaceError, match="workspace_link_changed"):
        api.save_workspace(CALLER, {"link_revision": api._revision(store.links[0]), "expected_version": 1, "changes": {"goal": None}})


def test_other_account_gets_empty_state_not_previous_draft(store):
    save(draft=DRAFT)
    second = {"id": 92, "user_id": 7202, "clerk_id": "second_owner"}
    store.links.append(second)
    assert api.read_workspace("second_owner")["draft"] is None


def test_version_conflict_preserves_exact_winner_and_leaks_no_draft(client, store):
    first = save(draft=DRAFT)
    response = client.patch("/api/athlete/workspace", json=request(0, draft={**DRAFT, "text": "LOSER"}))
    assert response.status_code == 409 and response.json()["code"] == "workspace_conflict"
    assert "draft" not in response.json() and "LOSER" not in response.text
    assert api.read_workspace(CALLER) == first


def test_two_real_threads_only_one_same_version_mutation_commits(store):
    def attempt(label):
        try:
            return save(goal={**GOAL, "text": label})["version"]
        except api.WorkspaceError as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ("First", "Second")))
    assert sorted(map(str, results)) == ["1", "workspace_conflict"]
    assert sum(db.commits for db in store.connections) == 1


@pytest.mark.parametrize("stage", ["begin", "execute", "write", "commit", "close", "commit_after_apply"])
def test_failures_are_closed_redacted_and_never_report_success(store, stage):
    store.failures[stage] = RuntimeError("SECRET SQL DATA")
    with pytest.raises(api.WorkspaceError) as caught:
        save(goal=GOAL)
    assert caught.value.code == "workspace_unavailable" and "SECRET" not in caught.value.detail
    if stage not in ("close", "commit_after_apply"):
        assert not store.rows


@pytest.mark.parametrize("code", [1062, 1205, 1213])
def test_known_transaction_contention_is_conflict(store, code):
    store.failures["write"] = DriverError(code, "PRIVATE DRIVER ERROR")
    with pytest.raises(api.WorkspaceError) as caught:
        save(goal=GOAL)
    assert caught.value.code == "workspace_conflict" and not store.rows


def test_recent_work_is_bounded_and_server_generated(store):
    for version in range(25):
        state = save(version, goal={**GOAL, "text": str(version)})
    assert len(state["recent_work"]) == 20
    assert state["recent_work"][0]["id"] == "25:goal_saved"
    assert len({event["id"] for event in state["recent_work"]}) == 20


@pytest.mark.parametrize("corruption", ["not json", '{"goal":null,"goal":null}', '{}', '{"goal":NaN}',
    json.dumps({"goal": None, "draft": None, "featured_source_id": None, "recent_work": [{"id": "1:goal_saved", "kind": "goal_saved", "at": "2026-09-09T00:00:00"}]})])
def test_corrupted_stored_json_is_not_returned_or_repaired(store, corruption):
    save(goal=GOAL)
    store.rows[CALLER.encode()]["payload"] = corruption
    with pytest.raises(api.WorkspaceError, match="workspace_unavailable"):
        api.read_workspace(CALLER)


@pytest.mark.parametrize("changes", [{}, {"athlete_id": OWNER}, {"recent_work": []}, {"goal": {"text": "x"}},
    {"goal": {**GOAL, "text": " "}}, {"goal": {**GOAL, "text": "x" * 601}},
    {"featured_source_id": "film-0"}, {"featured_source_id": "film-9007199254740992"},
    {"featured_source_id": "https://gmtm.com/film/301"}, {"featured_source_id": "film-01"},
    {"draft": {**DRAFT, "inputs_changed": 1}}, {"draft": {**DRAFT, "text": "x" * 20001}},
    {"draft": {**DRAFT, "text": "bad\rtext"}}, {"draft": {**DRAFT, "selected_evidence_ids": ["metric-1", "metric-1"]}},
    {"draft": {**DRAFT, "selected_material_ids": ["film-0"]}}, {"draft": {**DRAFT, "selected_material_ids": ["submission-1-bad"]}}])
def test_invalid_changes_are_rejected_before_connect(client, store, changes):
    response = client.patch("/api/athlete/workspace", json=request(**changes))
    assert response.status_code == 400 and response.json()["code"] == "workspace_invalid"
    assert not store.connections


@pytest.mark.parametrize("body", ['{}', '{"link_revision":"x","expected_version":0,"changes":{"goal":null}}',
    '{"link_revision":"' + api._revision(LINK) + '","expected_version":0,"expected_version":0,"changes":{"goal":null}}',
    '[]', '{"x":NaN}', '"' + 'x' * api.MAX_BODY_BYTES + '"'])
def test_raw_json_bounded_duplicates_and_shapes_fail_closed(client, store, body):
    response = client.patch("/api/athlete/workspace", content=body, headers={"content-type": "application/json"})
    assert response.status_code == 400 and not store.connections


def test_query_parameters_and_wrong_content_type_rejected(client, store):
    assert client.get("/api/athlete/workspace?athlete_id=7201").status_code == 400
    assert client.patch("/api/athlete/workspace?x=1", json=request(goal=GOAL)).status_code == 400
    assert client.patch("/api/athlete/workspace", content=json.dumps(request(goal=GOAL))).status_code == 400
    assert not store.connections


def test_actual_http_roundtrip_exact_draft_and_private_headers(client):
    first = client.get("/api/athlete/workspace").json()
    response = client.patch("/api/athlete/workspace", json={"link_revision": first["link_revision"], "expected_version": first["version"], "changes": {"draft": DRAFT}})
    assert response.status_code == 200 and response.json()["draft"] == DRAFT
    assert client.get("/api/athlete/workspace").json() == response.json()
    assert response.headers["cache-control"] == "private, no-store"


def test_feature_selection_uses_real_projection_not_arbitrary_public_url(store, monkeypatch):
    from backend.tests.test_athlete_materials import Database, film
    source = Database()
    source.submitted_films, source.career_films = [], []
    source.direct_films = [film(film_id=301), film(film_id=302, visibility=0)]
    monkeypatch.setattr(api, "_get_gmtm_db", lambda: source)
    state = save(featured_source_id="film-301")
    assert state["featured_source_id"] == "film-301"
    assert len(source.queries) == 3 and source.closed
    assert all(query.startswith("SELECT ") for query, _ in source.queries)
    with pytest.raises(api.WorkspaceError, match="workspace_invalid"):
        save(1, featured_source_id="film-302")
    assert api.read_workspace(CALLER) == state


def test_relink_during_feature_validation_cannot_save_into_new_owner(store, monkeypatch):
    def validate(*_):
        store.links = [{**LINK, "id": 92, "user_id": 7202}]
    monkeypatch.setattr(api, "_check_feature", validate)
    with pytest.raises(api.WorkspaceError, match="workspace_link_changed"):
        save(featured_source_id="film-301")
    assert not store.rows


def test_removed_feature_needs_no_source_access_and_saved_ref_is_not_media(store, monkeypatch):
    monkeypatch.setattr(api, "_check_feature", lambda *_: None)
    save(featured_source_id="film-301")
    monkeypatch.setattr(api, "_check_feature", lambda *_: (_ for _ in ()).throw(AssertionError("No read")))
    state = api.read_workspace(CALLER)
    assert state["featured_source_id"] == "film-301" and "thumbnail" not in json.dumps(state)
    assert save(1, featured_source_id=None)["featured_source_id"] is None
