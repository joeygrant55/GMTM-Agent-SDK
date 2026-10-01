"""Creation-only onboarding and synthetic entry-link/submission-return acceptance.

The real bootstrap, identity projection, and registered combine
routes run against explicit fake interfaces. This is not MySQL transaction,
GMTM login, or a real GMTM submission test. Fixture submission updates below
represent a saved source observation; no platform write endpoint is invoked.
"""

from copy import deepcopy
import json
import threading

from fastapi.testclient import TestClient
import pytest

import anthropic
import combine_api
import main
import openai
import profile_api
import workspace_bootstrap
from auth import require_identity
from backend.tests.test_combine_requirements import (
    ATHLETE, CALLER, PUBLIC, FakeDB as CombineDB, definition_rows, submission_for,
)


class WorkspaceDB:
    """Pending inserts become visible on commit; close discards pending writes.

    This models the bootstrap's interface/failure cleanup, not InnoDB behavior.
    """

    def __init__(self, state):
        self.state, self.pending, self.result = state, {}, None
        self.closed = False
        self.rowcount = 0
        state["workspace_connections"].append(self)

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        sql = " ".join(sql.split())
        self.state["workspace_queries"].append((sql, params))
        self.rowcount = 0
        if sql == "SELECT id, clerk_id FROM sparq_profiles WHERE clerk_id = %s":
            self.result = deepcopy(self.state["workspaces"].get(params[0]))
        elif sql.startswith("INSERT INTO sparq_profiles"):
            assert sql.split("ON DUPLICATE KEY UPDATE", 1)[1].replace(" ", "") == "id=id"
            assert len(params) == 8
            if self.state["failure"] == "insert":
                raise RuntimeError("synthetic workspace insert failure")
            clerk_id, name, position, school, year, city, region, metrics = params
            if self.state.get("raced_workspace") is not None:
                self.state["workspaces"][clerk_id] = deepcopy(self.state.pop("raced_workspace"))
            if clerk_id not in self.state["workspaces"]:
                self.rowcount = 1
                self.pending[clerk_id] = {
                    "id": 501, "clerk_id": clerk_id, "name": name, "position": position,
                    "school": school, "class_year": year, "city": city, "state": region,
                    "combine_metrics": json.loads(metrics) if metrics else {},
                    "enrichment_complete": 0,
                }
        else:
            raise AssertionError(f"Unexpected bootstrap SQL: {sql}")

    def fetchone(self):
        return deepcopy(self.result)

    def commit(self):
        self.state["commit_attempts"] += 1
        if self.state["failure"] == "commit":
            raise RuntimeError("synthetic workspace commit failure")
        self.state["workspaces"].update(deepcopy(self.pending))
        self.pending.clear()
        self.state["commits"] += 1

    def close(self):
        self.pending.clear()
        self.closed = True


class IdentityDB:
    """Read interface for the actual _gmtm_identity three-query projection."""

    def __init__(self, state):
        self.state, self.result, self.closed = state, None, False
        state["identity_connections"].append(self)

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        sql = " ".join(sql.split())
        assert sql.startswith("SELECT ") and params == (ATHLETE,)
        self.state["identity_queries"].append((sql, params))
        if "FROM users u LEFT JOIN locations" in sql:
            assert "WHERE u.user_id = %s" in sql
            self.result = deepcopy(self.state["identity"])
        elif "FROM career c" in sql:
            assert "WHERE c.user_id = %s" in sql
            self.result = {"position": "WR", "school": "Fixture High", "sport": "Flag Football"}
        elif "FROM metrics" in sql:
            assert "user_id = %s AND is_current = 1" in sql
            self.result = [{"title": "Height", "value": "70"}, {"title": "Weight", "value": "150"}]
        else:
            raise AssertionError(f"Unexpected identity SQL: {sql}")

    def fetchone(self):
        return deepcopy(self.result)

    def fetchall(self):
        return deepcopy(self.result)

    def close(self):
        self.closed = True


@pytest.fixture
def bootstrap(monkeypatch):
    state = {
        "workspaces": {}, "workspace_connections": [], "workspace_queries": [],
        "identity_connections": [], "identity_queries": [], "metric_reads": [],
        "identity": {"user_id": ATHLETE, "first_name": "Ava", "last_name": "Fixture",
                     "graduation_year": 2027, "gender": 0, "city": "Austin", "state": "TX"},
        "metrics": [{"drill": "40-Yard Dash", "value": 4.8, "ideal": "lower"},
                    {"drill": "40-Yard Dash", "value": 4.5, "ideal": "lower"},
                    {"drill": "Vertical Jump", "value": 30.0, "ideal": "higher"},
                    {"drill": "Vertical Jump", "value": 32.0, "ideal": "higher"}],
        "failure": None, "commit_attempts": 0, "commits": 0,
        "threads_constructed": [], "threads_started": [], "forbidden": [],
    }
    monkeypatch.setattr(profile_api, "_get_agent_db", lambda: WorkspaceDB(state))
    monkeypatch.setattr(profile_api, "_get_gmtm_db", lambda: IdentityDB(state))

    def metrics(user_id, connection_factory):
        assert user_id == ATHLETE and connection_factory is profile_api._get_gmtm_db
        state["metric_reads"].append(user_id)
        if state["failure"] == "metrics":
            raise RuntimeError("synthetic metrics source failure")
        return deepcopy(state["metrics"])

    monkeypatch.setattr(workspace_bootstrap, "get_combine_results", metrics)

    def forbidden(name):
        def blocked(*args, **kwargs):
            state["forbidden"].append(name)
            raise AssertionError(f"Onboarding attempted {name}")
        return blocked

    monkeypatch.setattr(profile_api, "_run_matching_thread", forbidden("matching"))
    for module, names in ((anthropic, ("Anthropic", "AsyncAnthropic")),
                          (openai, ("OpenAI", "AsyncOpenAI"))):
        for name in names:
            monkeypatch.setattr(module, name, forbidden(f"provider.{name}"))

    original_init, original_start = threading.Thread.__init__, threading.Thread.start

    def transport_target(thread):
        target = getattr(thread, "_target", None)
        module = getattr(target, "__module__", "")
        return (module in ("anyio.from_thread", "concurrent.futures.thread", "asyncio.base_events")
                or type(thread).__module__.startswith("anyio."))

    def record_init(thread, *args, **kwargs):
        original_init(thread, *args, **kwargs)
        if not transport_target(thread):
            state["threads_constructed"].append(thread.name)

    def record_start(thread, *args, **kwargs):
        if transport_target(thread):
            return original_start(thread, *args, **kwargs)
        # Preserve the observable pre-fix creation result without actually
        # running background code. The nonzero counter still fails the test.
        state["threads_started"].append(thread.name)

    monkeypatch.setattr(threading.Thread, "__init__", record_init)
    monkeypatch.setattr(threading.Thread, "start", record_start)
    yield state
    assert state["threads_constructed"] == []
    assert state["threads_started"] == []
    assert state["forbidden"] == []
    assert all(db.closed for db in state["workspace_connections"] + state["identity_connections"])


def test_creates_workspace_with_projected_identity_and_best_metrics_only(bootstrap):
    result = workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE)
    assert result == {"ready": True, "created": True, "profile_id": 501}
    assert bootstrap["workspaces"][CALLER] == {
        "id": 501, "clerk_id": CALLER, "name": "Ava Fixture", "position": "WR",
        "school": "Fixture High", "class_year": 2027, "city": "Austin", "state": "TX",
        "combine_metrics": {"fortyYardDash": 4.5, "vertical": 32.0,
                            "heightFeet": 5, "heightInches": 10, "weight": 150.0},
        "enrichment_complete": 0,
    }
    assert bootstrap["commits"] == 1 and len(bootstrap["identity_queries"]) == 3
    assert bootstrap["metric_reads"] == [ATHLETE]


def test_existing_workspace_returns_without_gmtm_or_model_work(bootstrap):
    existing = {"id": 88, "clerk_id": CALLER, "name": "Keep my edits"}
    bootstrap["workspaces"][CALLER] = deepcopy(existing)
    result = workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE)
    assert result == {"ready": True, "created": False, "profile_id": 88}
    assert bootstrap["workspaces"][CALLER] == existing
    assert bootstrap["identity_connections"] == bootstrap["metric_reads"] == []
    assert bootstrap["commit_attempts"] == 0


@pytest.mark.parametrize("row", [
    {"id": 88, "clerk_id": CALLER.upper()},
    {"id": 88, "clerk_id": "a-different-synthetic-owner"},
    {"id": "88", "clerk_id": CALLER},
    {"id": True, "clerk_id": CALLER},
    {"id": 0, "clerk_id": CALLER},
    {"id": -1, "clerk_id": CALLER},
    {"id": None, "clerk_id": CALLER},
    {"clerk_id": CALLER},
    {"id": 88, "clerk_id": None},
])
def test_unconfirmed_existing_owner_fails_before_gmtm_or_writes(bootstrap, row):
    # A legacy case-insensitive lookup can return a different owner subject.
    bootstrap["workspaces"][CALLER] = deepcopy(row)
    with pytest.raises(ValueError, match="Workspace ownership could not be confirmed"):
        workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE)
    assert bootstrap["workspaces"][CALLER] == row
    assert bootstrap["identity_connections"] == bootstrap["metric_reads"] == []
    assert bootstrap["commit_attempts"] == 0


def test_same_owner_insert_race_keeps_existing_values_and_reports_not_created(bootstrap):
    raced = {"id": 88, "clerk_id": CALLER, "name": "Concurrent profile", "updated_at": "unchanged"}
    bootstrap["raced_workspace"] = deepcopy(raced)
    assert workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE) == {
        "ready": True, "created": False, "profile_id": 88,
    }
    assert bootstrap["workspaces"] == {CALLER: raced}


def test_foreign_owner_insert_race_does_not_touch_the_row_or_report_ready(bootstrap):
    raced = {"id": 88, "clerk_id": CALLER.upper(), "name": "Another owner", "updated_at": "unchanged"}
    bootstrap["raced_workspace"] = deepcopy(raced)
    with pytest.raises(ValueError, match="Workspace ownership could not be confirmed"):
        workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE)
    assert bootstrap["workspaces"] == {CALLER: raced}


def test_missing_identity_is_not_ready_and_does_not_create_workspace(bootstrap):
    bootstrap["identity"] = None
    assert workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE) == {
        "ready": False, "created": False, "profile_id": None,
    }
    assert len(bootstrap["identity_queries"]) == 1
    assert bootstrap["workspaces"] == {} and bootstrap["metric_reads"] == []
    assert bootstrap["commit_attempts"] == 0


def test_metric_source_failure_preserves_identity_only_creation(bootstrap):
    bootstrap["failure"] = "metrics"
    assert workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE)["ready"] is True
    assert bootstrap["workspaces"][CALLER]["name"] == "Ava Fixture"
    assert bootstrap["workspaces"][CALLER]["combine_metrics"] == {
        "heightFeet": 5, "heightInches": 10, "weight": 150.0,
    }
    assert bootstrap["metric_reads"] == [ATHLETE] and bootstrap["commits"] == 1


def test_create_then_same_owner_retry_is_idempotent(bootstrap):
    first = workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE)
    bootstrap["workspaces"][CALLER]["name"] = "My corrected name"
    second = workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE)
    assert first == {"ready": True, "created": True, "profile_id": 501}
    assert second == {"ready": True, "created": False, "profile_id": 501}
    assert bootstrap["workspaces"][CALLER]["name"] == "My corrected name"
    assert len(bootstrap["workspaces"]) == bootstrap["commits"] == 1
    assert bootstrap["metric_reads"] == [ATHLETE]
    assert len(bootstrap["identity_connections"]) == 1


@pytest.mark.parametrize("failure", ["insert", "commit"])
def test_write_failure_closes_connections_without_research(bootstrap, failure):
    bootstrap["failure"] = failure
    with pytest.raises(RuntimeError, match=f"synthetic workspace {failure} failure"):
        workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE)
    assert bootstrap["workspaces"] == {} and bootstrap["commits"] == 0
    assert all(db.closed and not db.pending for db in bootstrap["workspace_connections"])


@pytest.fixture
def journey(bootstrap, monkeypatch):
    # GMTM entry (junior_entry._exchange) links the athlete, then runs the real bootstrap.
    claims = {"claims": {}, "athlete_profiles": {}, "connections": [], "named_locks": {}, "row_locks": {}}
    source = {"profiles": [], "claims": [], "events": [deepcopy(item["event"]) for item in PUBLIC["events"]],
              "tasks": definition_rows(1317) + definition_rows(1318), "submissions": [],
              "queries": [], "connections": []}

    def combine_connection(kind):
        source["profiles"] = [{"user_id": uid, "clerk_id": owner}
                              for uid, owner in claims["athlete_profiles"].items()]
        source["claims"] = list(claims["claims"].values())
        db = CombineDB(source, kind)
        source["connections"].append(db)
        return db

    monkeypatch.setattr(combine_api, "_get_agent_db", lambda: combine_connection("agent"))
    monkeypatch.setattr(combine_api, "_get_gmtm_db", lambda: combine_connection("gmtm"))
    identity = {"clerk_id": CALLER}
    monkeypatch.setitem(main.app.dependency_overrides, require_identity, lambda: identity["clerk_id"])
    with TestClient(main.app) as client:
        yield client, claims, source, identity
    assert all(db.closed for db in claims["connections"] + source["connections"])
    assert claims["named_locks"] == claims["row_locks"] == {}


def test_gmtm_entry_link_creates_workspace_then_reports_saved_fixture_submission(journey, bootstrap):
    client, claims, source, _ = journey
    claims["athlete_profiles"][ATHLETE] = CALLER
    assert workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE)["created"] is True
    first = client.get("/api/combine/current?event_id=1318")
    assert first.status_code == 200 and first.headers["Cache-Control"] == "private, no-store"
    first = first.json()
    assert first["clerk_id"] == CALLER and first["athlete_id"] == ATHLETE
    assert first["selected_event"]["event_id"] == 1318
    assert first["counts"] == {"activities": 9, "submitted": 0, "fields_present": 0}

    adult = next(task for task in source["tasks"] if task["event_id"] == 1318)
    junior = next(task for task in source["tasks"] if task["event_id"] == 1317)
    source["submissions"].extend([
        # This is fixture state changing as if GMTM had saved a submission.
        # The SPARQ request never writes or confirms a real platform submission.
        submission_for(adult, sid=401, user_id=ATHLETE, created_on="2026-09-08 12:00:00"),
        submission_for(junior, sid=402, user_id=ATHLETE),
        submission_for(adult, sid=403, user_id=ATHLETE + 1),
    ])
    response = client.get("/api/combine/current?event_id=1318")
    assert response.status_code == 200
    refreshed = response.json()
    assert refreshed["selected_event"]["event_id"] == 1318
    assert refreshed["athlete_id"] == ATHLETE and refreshed["clerk_id"] == CALLER
    assert refreshed["counts"] == {"activities": 9, "submitted": 1, "fields_present": 1}
    submitted = [item for item in refreshed["activities"] if item["submission_state"] == "submitted"]
    assert len(submitted) == 1 and submitted[0]["task_id"] == adult["task_id"]
    assert submitted[0]["evidence_state"] == "fields_present"
    assert workspace_bootstrap.ensure_workspace_profile(CALLER, ATHLETE)["created"] is False
    assert len(bootstrap["workspaces"]) == bootstrap["commits"] == 1
    assert all(sql.startswith("SELECT ") for _, sql, _ in source["queries"])
