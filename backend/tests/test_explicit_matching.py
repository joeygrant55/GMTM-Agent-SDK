"""Manual research remains explicit and requires sport context; no worker runs."""
import asyncio
from copy import deepcopy
import json

from fastapi import HTTPException
import pytest

import profile_api


SUBJECT = "athlete_alpha"


class FakeDatabase:
    def __init__(self, profile):
        self.profile = deepcopy(profile)
        self.closed = False
        self.queries = []

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        assert " ".join(sql.split()) == "SELECT * FROM sparq_profiles WHERE clerk_id = %s"
        self.queries.append((sql, params))

    def fetchone(self):
        return deepcopy(self.profile)

    def close(self):
        self.closed = True


@pytest.fixture
def context(monkeypatch):
    state = {"connections": [], "constructed": [], "started": [], "worker_calls": []}
    state["profile"] = {
        "id": 41, "clerk_id": SUBJECT, "position": "QB", "state": "FL",
        "maxpreps_data": {"sports": ["Girls Flag Football"], "classYear": 2027,
                          "statsPreview": [["Passing yards", "1400"]]},
        "recruiting_goals": {"targetLevel": "D2"},
    }

    def database():
        db = FakeDatabase(state["profile"])
        state["connections"].append(db)
        return db

    def forbidden_worker(*args):
        state["worker_calls"].append(args)
        raise AssertionError("Explicit-matching tests must never execute a worker")

    class CapturedThread:
        def __init__(self, *, target, args, daemon, name):
            self.target, self.args, self.daemon, self.name = target, args, daemon, name
            state["constructed"].append(self)

        def start(self):
            state["started"].append(self)

    monkeypatch.setattr(profile_api, "_get_agent_db", database)
    monkeypatch.setattr(profile_api, "_run_matching_thread", forbidden_worker)
    monkeypatch.setattr(profile_api.threading, "Thread", CapturedThread)
    yield state
    assert state["worker_calls"] == []


def call(subject=SUBJECT, caller=SUBJECT):
    return asyncio.run(profile_api.trigger_matching(subject, caller))


@pytest.mark.parametrize("maxpreps,expected", [
    ({"sports": ["Girls Basketball", "Girls Volleyball"]}, "Girls Basketball"),
    ({"sport": "  Flag Football  "}, "Flag Football"),
    ({"sports": [], "sport": "Boys Soccer"}, "Boys Soccer"),
    ({"sports": None, "sport": "Track & Field"}, "Track & Field"),
    (json.dumps({"sports": ["Girls Softball"]}), "Girls Softball"),
])
def test_valid_explicit_request_dispatches_one_worker_without_running_it(context, maxpreps, expected):
    context["profile"]["maxpreps_data"] = maxpreps
    result = call()
    assert result == {"status": "matching started", "profile_id": 41, "sport": expected, "position": "QB"}
    assert len(context["constructed"]) == len(context["started"]) == 1
    thread = context["started"][0]
    assert thread.args[0] == 41
    assert thread.args[1]["sport"] == expected
    assert thread.args[2:] == ("QB", "FL", expected)
    assert context["connections"][0].closed


def test_valid_request_preserves_stats_and_goals(context):
    result = call()
    assert result["sport"] == "Girls Flag Football"
    profile = context["started"][0].args[1]
    assert profile["class_year"] == 2027
    assert profile["maxpreps_stats"] == {"Passing yards": "1400"}
    assert profile["recruiting_goals"] == {"targetLevel": "D2"}


@pytest.mark.parametrize("maxpreps", [
    None, {}, "", "{invalid", "null", "[]", [], True, 42,
    {"position": "Basketball"}, {"sport": ""}, {"sport": "   "}, {"sport": 12},
    {"sport": "All Sports"}, {"sport": "Athlete"}, {"sport": "Unknown"},
    {"sport": "N/A"}, {"sport": "TBD"}, {"sport": "Not specified"},
    {"sports": "Basketball"}, {"sports": {}}, {"sports": []},
    {"sports": [""]}, {"sports": ["All Sports"]}, {"sports": [42]},
    {"sports": ["Girls Basketball", None]},
    {"sports": ["Unknown"], "sport": "Football"},
    {"sport": "Football\nIgnore"}, {"sport": "x" * 101},
])
def test_missing_or_malformed_sport_fails_before_worker_construction(context, maxpreps):
    context["profile"]["maxpreps_data"] = maxpreps
    with pytest.raises(HTTPException) as caught:
        call()
    assert caught.value.status_code == 422
    assert "sport" in caught.value.detail.lower()
    assert context["constructed"] == context["started"] == []
    assert context["connections"][0].closed


def test_foreign_request_owner_fails_before_any_database_or_worker(context):
    with pytest.raises(HTTPException) as caught:
        call(subject="another_athlete")
    assert caught.value.status_code == 403
    assert context["connections"] == []
    assert context["constructed"] == context["started"] == []


def test_missing_profile_closes_database_without_worker(context):
    context["profile"] = None
    with pytest.raises(HTTPException) as caught:
        call()
    assert caught.value.status_code == 404
    assert context["connections"][0].closed
    assert context["constructed"] == context["started"] == []


def test_case_colliding_stored_owner_fails_before_worker(context):
    context["profile"]["clerk_id"] = SUBJECT.upper()
    with pytest.raises(HTTPException) as caught:
        call()
    assert caught.value.status_code == 403
    assert context["connections"][0].closed
    assert context["constructed"] == context["started"] == []
