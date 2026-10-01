"""Offline source-fixture and fake-database contract tests; no service access."""

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import combine_api
from auth import require_identity
from combine_requirements import MAX_PAYLOAD_CHARS, MAX_TASKS, parse_activities, project_activity


PUBLIC = json.loads((Path(__file__).parent / "fixtures/usaf_2027_combine2_public.json").read_text())
CALLER = "sub_owner"
ATHLETE = 7201


def definition_rows(event_id):
    event = next(item for item in PUBLIC["events"] if item["event"]["event_id"] == event_id)
    return [{**deepcopy(task), "description": "<p>Organizer instructions</p>",
             "payload": json.dumps({"questions": task["questions"]})} for task in event["tasks"]]


def value_for(kind):
    if kind == "gender_id":
        return {"gender": {"value": 0, "label": "Private example"}}
    if kind == "address":
        return {"address_one": "PRIVATE_ADDRESS", "lat": 1, "lng": 2}
    if kind in {"video", "email", "date", "metric"}:
        return {"value": 0 if kind == "metric" else "PRIVATE_VALUE", "unit": "unused"}
    if kind == "height":
        return 70
    return "PRIVATE_VALUE"


def answers_for(task):
    questions = json.loads(task["payload"])["questions"]
    return {f'{question["type"]}:{question["title"]}': {"value": value_for(question["type"])}
            for question in questions if question["required"]}


def submission_for(task, *, sid=1, user_id=ATHLETE, visibility=1,
                   created_on="2026-09-06 12:00:00", answers=None):
    return {"task_submission_id": sid, "task_id": task["task_id"],
            "event_id": task["event_id"], "user_id": user_id, "visibility": visibility,
            "created_on": created_on,
            "payload": json.dumps({"questions": answers_for(task) if answers is None else answers})}


class FakeDB:
    """Evaluate fixture scope while asserting essential production SQL clauses.

    This is not MySQL execution coverage. Unexpected SQL is forbidden, and a
    missing scope clause fails before the fake can mask it with its own filter.
    """

    def __init__(self, store, source):
        self.store, self.source = store, source
        self.result = []
        self.closed = False

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def close(self):
        self.closed = True

    def execute(self, sql, params):
        sql = " ".join(sql.split())
        assert sql.startswith("SELECT "), "This adapter must only read"
        self.store["queries"].append((self.source, sql, params))
        if self.store.get("fail_source") == self.source:
            raise RuntimeError("PRIVATE_DRIVER_ERROR")
        if "FROM athlete_profiles" in sql:
            assert sql.startswith("SELECT user_id, clerk_id ")
            if "WHERE clerk_id = %s LIMIT 2" in sql:
                assert params == (CALLER,)
                self.result = [deepcopy(row) for row in self.store["profiles"]
                               if row["clerk_id"] == params[0]][:2]
            else:
                assert "WHERE user_id = %s LIMIT 2" in sql and params == (ATHLETE,)
                self.result = [deepcopy(row) for row in self.store["profiles"]
                               if row["user_id"] == params[0]][:2]
        elif "FROM claim_tokens" in sql:
            assert "clerk_id = %s AND user_id = %s AND claimed_at IS NOT NULL" in sql
            assert "event_id IN (%s, %s)" in sql and "LIMIT 3" in sql
            owner, athlete, *events = params
            self.result = [{"event_id": event} for event in sorted({row["event_id"] for row in self.store["claims"]
                           if row["clerk_id"] == owner and row["user_id"] == athlete
                           and row["claimed_at"] is not None and row["event_id"] in events})]
            if "claim_rows_override" in self.store:
                self.result = self.store["claim_rows_override"]
        elif "FROM events" in sql:
            assert "organization_id = %s" in sql and params == (1317, 1318, 249002)
            for predicate in ("published = 1", "`public` = 1", "visibility = 2", "invite_only = 0", "product_id IS NULL"):
                assert predicate in sql
            # Return even invalid rows so the additional Python public gate is tested.
            self.result = deepcopy(self.store["events"])
        elif "FROM event_tasks" in sql:
            assert "WHERE event_id = %s AND visibility = 2" in sql
            assert "ORDER BY list_order, task_id LIMIT %s" in sql
            self.result = [row for row in self.store["tasks"]
                           if row["event_id"] == params[0] and row["visibility"] == 2][:params[1]]
        elif "FROM event_task_submissions s" in sql:
            for clause in ("s.user_id = %s AND t.event_id = %s AND t.visibility = 2",
                           "s.visibility > 0 AND s.task_id IN (", "NOT EXISTS",
                           "newer.user_id = s.user_id AND newer.task_id = s.task_id",
                           "newer.visibility > 0", "newer.created_on > s.created_on",
                           "newer.created_on = s.created_on", "newer.task_submission_id > s.task_submission_id"):
                assert clause in sql
            athlete, event_id, *tail = params
            task_ids, limit = tail[:-1], tail[-1]
            assert athlete == ATHLETE and event_id in (1317, 1318)
            eligible = [row for row in self.store["submissions"] if row["user_id"] == athlete
                        and row["event_id"] == event_id and row["task_id"] in task_ids and row["visibility"] > 0]
            latest = {}
            for row in sorted(eligible, key=lambda item: (item["created_on"], item["task_submission_id"])):
                latest[row["task_id"]] = row
            self.result = list(latest.values())[:limit]
            if "submission_rows_override" in self.store:
                self.result = self.store["submission_rows_override"]
        else:
            raise AssertionError(f"Unexpected SQL: {sql}")

    def fetchall(self):
        return deepcopy(self.result)


@pytest.fixture
def client(monkeypatch):
    store = {"profiles": [{"clerk_id": CALLER, "user_id": ATHLETE}], "claims": [],
             "events": [deepcopy(item["event"]) for item in PUBLIC["events"]],
             "tasks": definition_rows(1317) + definition_rows(1318),
             "submissions": [], "queries": [], "connections": []}

    def connection(source):
        db = FakeDB(store, source)
        store["connections"].append(db)
        return db

    monkeypatch.setattr(combine_api, "_get_agent_db", lambda: connection("agent"))
    monkeypatch.setattr(combine_api, "_get_gmtm_db", lambda: connection("gmtm"))
    app = FastAPI()
    app.include_router(combine_api.router)
    app.dependency_overrides[require_identity] = lambda: CALLER
    with TestClient(app) as http:
        http.store = store
        http.app_under_test = app
        yield http


def get(client, event_id=1317):
    response = client.get("/api/combine/current", params={} if event_id is None else {"event_id": event_id})
    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "private, no-store"
    assert all(db.closed for db in client.store["connections"])
    return response.json()


def task_named(client, title, event_id=1317):
    return next(task for task in client.store["tasks"] if task["event_id"] == event_id and task["title"] == title)


def activity_named(body, title):
    return next(activity for activity in body["activities"] if activity["title"] == title)


def claim(event_id=1317, clerk_id=CALLER, user_id=ATHLETE, claimed_at="2026-09-01"):
    return dict(event_id=event_id, clerk_id=clerk_id, user_id=user_id, claimed_at=claimed_at)


def test_auth_required_before_connections(client):
    client.app_under_test.dependency_overrides.clear()
    response = client.get("/api/combine/current?event_id=1317")
    assert response.status_code == 401
    assert client.store["connections"] == []


@pytest.mark.parametrize("event_id", [1, 9999, -1, 0])
def test_unsupported_event_fails_before_connections(client, event_id):
    assert client.get(f"/api/combine/current?event_id={event_id}").status_code == 404
    assert client.store["connections"] == []


def test_zero_submission_athlete_has_real_public_requirements(client):
    body = get(client)
    assert set(body) == {"schema_version", "clerk_id", "athlete_id", "state", "events", "selected_event",
                         "activities", "counts", "fetched_at", "athlete_id_status"}
    assert body["schema_version"] == 1 and body["state"] == "ready"
    assert body["athlete_id"] == ATHLETE and body["clerk_id"] == CALLER
    assert body["athlete_id_status"] == "unknown"
    assert body["counts"] == {"activities": 9, "submitted": 0, "fields_present": 0}
    assert len({activity["task_id"] for activity in body["activities"]}) == 9
    assert all(activity["submission_state"] == "not_submitted" for activity in body["activities"])
    assert all(activity["evidence_state"] == "missing_fields" for activity in body["activities"])
    assert all(activity["continuation_url"] == "https://gmtm.com/virtuals/1317" for activity in body["activities"])
    assert set(body["activities"][0]) == {"task_id", "event_id", "title", "order", "kind", "description",
        "continuation_url", "submission_state", "evidence_state", "missing_fields", "required_field_count", "required_fields", "submitted_at"}
    assert body["selected_event"]["deadline_display"] == "September 21, 2026"
    assert body["selected_event"]["configured_end"] == "2026-09-22T23:59:00.000Z"
    assert body["selected_event"]["deadline_source_url"] == "https://usafootball.com/national-team/digital-combine"
    assert datetime.fromisoformat(body["fetched_at"]).tzinfo is not None
    assert not any("claim_tokens" in sql for _, sql, _ in client.store["queries"])


@pytest.mark.parametrize("event_id", [1317, 1318])
def test_unlinked_can_see_explicit_public_requirements_without_personal_query(client, event_id):
    client.store["profiles"] = []
    body = get(client, event_id)
    assert body["state"] == "link_required" and body["athlete_id"] is None
    assert body["selected_event"]["event_id"] == event_id
    assert body["counts"] == {"activities": 9, "submitted": None, "fields_present": None}
    assert all(activity["submission_state"] == "unavailable" and activity["evidence_state"] == "unknown"
               and activity["missing_fields"] == [] for activity in body["activities"])
    assert not any("claim_tokens" in sql or "event_task_submissions" in sql for _, sql, _ in client.store["queries"])


def test_unlinked_no_selection_only_public_choices(client):
    client.store["profiles"] = []
    body = get(client, None)
    assert body["state"] == "link_required" and body["selected_event"] is None
    assert body["activities"] == []
    assert body["counts"] == {"activities": 0, "submitted": None, "fields_present": None}
    assert [event["event_id"] for event in body["events"]] == [1317, 1318]


@pytest.mark.parametrize("profiles", [
    [{"clerk_id": CALLER, "user_id": ATHLETE}, {"clerk_id": CALLER, "user_id": 7202}],
    [{"clerk_id": CALLER, "user_id": ATHLETE}, {"clerk_id": CALLER, "user_id": ATHLETE}],
])
def test_ambiguous_link_rejected_before_gmtm(client, profiles):
    client.store["profiles"] = profiles
    assert client.get("/api/combine/current?event_id=1317").status_code == 409
    assert all(source == "agent" for source, _, _ in client.store["queries"])
    assert all(db.closed for db in client.store["connections"])


def test_caller_cannot_select_another_identity_with_query_params(client):
    foreign = submission_for(task_named(client, "20-Yard Dash"), user_id=9999)
    client.store["submissions"] = [foreign]
    body = client.get("/api/combine/current?event_id=1317&athlete_id=9999&clerk_id=other").json()
    assert body["athlete_id"] == ATHLETE and body["clerk_id"] == CALLER
    assert body["counts"]["submitted"] == 0


def test_default_event_requires_unique_supported_redeemed_owner_and_athlete_claim(client):
    client.store["claims"] = [claim(), claim(), claim(1318, clerk_id="other"),
        claim(1318, user_id=9999), claim(1318, claimed_at=None), claim(55)]
    body = get(client, None)
    assert body["state"] == "ready" and body["selected_event"]["event_id"] == 1317


@pytest.mark.parametrize("claims", [[], [claim(1317), claim(1318)], [claim(55)],
    [claim(clerk_id="other")], [claim(user_id=9999)], [claim(claimed_at=None)]])
def test_no_unambiguous_claim_means_choose_event(client, claims):
    client.store["claims"] = claims
    body = get(client, None)
    assert body["state"] == "choose_event" and body["selected_event"] is None
    assert body["activities"] == []
    assert body["counts"] == {"activities": 0, "submitted": None, "fields_present": None}
    assert not any("FROM event_tasks" in sql for _, sql, _ in client.store["queries"])


@pytest.mark.parametrize("rows", [[{"event_id": "wrong"}], [{"event_id": 1317}, {"event_id": None}], [{"event_id": 3}]])
def test_malformed_claim_rows_cannot_choose_an_event(client, rows):
    client.store["claim_rows_override"] = rows
    assert get(client, None)["state"] == "choose_event"


@pytest.mark.parametrize("field,value", [("organization_id", 1), ("public", 0), ("published", 0),
    ("visibility", -1), ("visibility", 1), ("invite_only", 1), ("product_id", 123)])
def test_event_that_loses_public_gate_is_unavailable(client, field, value):
    client.store["events"][0][field] = value
    response = client.get("/api/combine/current?event_id=1317")
    assert response.status_code == 404
    assert not any("FROM event_tasks" in sql for _, sql, _ in client.store["queries"])


def test_claim_does_not_override_newly_private_event(client):
    client.store["claims"] = [claim()]
    client.store["events"][0]["public"] = 0
    body = get(client, None)
    assert body["state"] == "choose_event" and body["selected_event"] is None


@pytest.mark.parametrize("event_id,expected", [(1317, 11), (1318, 10)])
def test_background_flags_and_standalone_highlight_remain_separate(client, event_id, expected):
    task = task_named(client, "Athlete Background", event_id)
    client.store["submissions"] = [submission_for(task)]
    body = get(client, event_id)
    background = activity_named(body, "Athlete Background")
    assert background["required_field_count"] == expected
    assert background["evidence_state"] == "fields_present"
    assert activity_named(body, "Highlight Reel")["missing_fields"] == ["Upload your Highlight Reel"]
    assert body["counts"] == {"activities": 9, "submitted": 1, "fields_present": 1}
    assert body["athlete_id_status"] == "unknown"  # A present membership string proves nothing further.
    assert "PRIVATE_" not in json.dumps(body)


def test_shuttle_requires_both_directions_and_video(client):
    task = task_named(client, "5-10-5 Shuttle Run")
    answers = answers_for(task)
    del answers["metric:5-10-5 Shuttle Run Starting to the Left"]
    del answers["video:5-10-5 Shuttle Run"]
    client.store["submissions"] = [submission_for(task, answers=answers)]
    activity = activity_named(get(client), task["title"])
    assert activity["required_field_count"] == 3
    assert activity["evidence_state"] == "missing_fields"
    assert set(activity["missing_fields"]) == {"5-10-5 Shuttle Run Starting to the Left", "5-10-5 Shuttle Run"}


def test_overhead_squat_needs_only_its_video(client):
    task = task_named(client, "Stick Overhead Squat")
    client.store["submissions"] = [submission_for(task)]
    activity = activity_named(get(client), task["title"])
    assert activity["required_field_count"] == 1 and activity["evidence_state"] == "fields_present"


def test_adult_dash_retains_correct_activity_and_exact_conflicting_answer_key(client):
    task = task_named(client, "20-Yard Dash", 1318)
    answers = answers_for(task)
    assert "metric:40 Yard Dash Time" in answers
    client.store["submissions"] = [submission_for(task, answers=answers)]
    activity = activity_named(get(client, 1318), "20-Yard Dash")
    assert activity["evidence_state"] == "fields_present"
    answers["metric:20 Yard Dash Time"] = answers.pop("metric:40 Yard Dash Time")
    client.store["submissions"] = [submission_for(task, answers=answers)]
    activity = activity_named(get(client, 1318), "20-Yard Dash")
    assert activity["missing_fields"] == ["40 Yard Dash Time"]


def test_source_trailing_space_is_part_of_lookup_key(client):
    task = task_named(client, "Max. Sit Ups")
    answers = answers_for(task)
    assert "metric:How many sit ups did you do? " in answers
    client.store["submissions"] = [submission_for(task, answers=answers)]
    assert activity_named(get(client), task["title"])["evidence_state"] == "fields_present"
    answers["metric:How many sit ups did you do?"] = answers.pop("metric:How many sit ups did you do? ")
    client.store["submissions"] = [submission_for(task, answers=answers)]
    assert activity_named(get(client), task["title"])["missing_fields"] == ["How many sit ups did you do? "]


def test_latest_visible_attempt_wins_by_timestamp_then_id_and_counts_once(client):
    task = task_named(client, "20-Yard Dash")
    old = submission_for(task, sid=100, created_on="2026-09-05 12:00:00")
    newer = submission_for(task, sid=2, answers={})
    tie_later = submission_for(task, sid=3)
    hidden = submission_for(task, sid=4, answers={}, visibility=-1)
    other = submission_for(task, sid=5, answers={}, user_id=9999)
    junior_task_with_adult_event = submission_for(task, sid=6, answers={})
    junior_task_with_adult_event["event_id"] = 1318
    client.store["submissions"] = [old, newer, tie_later, hidden, other, junior_task_with_adult_event]
    body = get(client)
    assert body["counts"]["submitted"] == body["counts"]["fields_present"] == 1
    activity = activity_named(body, "20-Yard Dash")
    assert activity["submitted_at"] == "2026-09-06 12:00:00"


@pytest.mark.parametrize("payload", [None, "{broken", "[]", "{}", '{"questions": []}',
                                    '{"questions": null}', "x" * (MAX_PAYLOAD_CHARS + 1)])
def test_malformed_latest_answer_stays_submitted_unknown(client, payload):
    task = task_named(client, "20-Yard Dash")
    latest = submission_for(task, sid=2)
    latest["payload"] = payload
    client.store["submissions"] = [submission_for(task, sid=1), latest]
    body = get(client)
    assert body["counts"] == {"activities": 9, "submitted": 1, "fields_present": 0}
    activity = activity_named(body, "20-Yard Dash")
    assert activity["submission_state"] == "submitted" and activity["evidence_state"] == "unknown"


@pytest.mark.parametrize("value", [{"unit": "seconds"}, [], True, {"value": {"metadata": 1}}])
def test_unrecognized_metric_value_shape_is_unknown(client, value):
    task = task_named(client, "20-Yard Dash")
    answers = answers_for(task)
    answers["metric:20 Yard Dash Time"] = {"value": value}
    client.store["submissions"] = [submission_for(task, answers=answers)]
    assert activity_named(get(client), "20-Yard Dash")["evidence_state"] == "unknown"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_empty_known_answer_is_missing(client, value):
    task = task_named(client, "20-Yard Dash")
    answers = answers_for(task)
    answers["metric:20 Yard Dash Time"] = {"value": {"value": value}}
    client.store["submissions"] = [submission_for(task, answers=answers)]
    assert activity_named(get(client), "20-Yard Dash")["missing_fields"] == ["20 Yard Dash Time"]


def test_unknown_required_question_type_is_unknown_not_complete(client):
    task = task_named(client, "20-Yard Dash")
    payload = json.loads(task["payload"])
    payload["questions"].append({"type": "new_widget", "title": "New input", "required": True})
    task["payload"] = json.dumps(payload)
    client.store["submissions"] = [submission_for(task)]
    assert activity_named(get(client), "20-Yard Dash")["evidence_state"] == "unknown"


def test_unrecognized_address_shape_cannot_complete_background(client):
    task = task_named(client, "Athlete Background")
    answers = answers_for(task)
    answers["address:Home Address"] = {"value": {"address_one": 99}}
    client.store["submissions"] = [submission_for(task, answers=answers)]
    assert activity_named(get(client), "Athlete Background")["evidence_state"] == "unknown"


@pytest.mark.parametrize("payload", [None, "{}", "{bad", '{"questions": []}', '{"questions": {}}',
                                    '{"questions": [{"title": "A", "type": "essay"}]}'])
def test_malformed_definition_is_503_not_empty_progress(client, payload):
    task_named(client, "20-Yard Dash")["payload"] = payload
    response = client.get("/api/combine/current?event_id=1317")
    assert response.status_code == 503
    assert "activities" not in response.json()


def test_duplicate_question_keys_are_source_failure(client):
    task = task_named(client, "20-Yard Dash")
    payload = json.loads(task["payload"])
    payload["questions"].append(payload["questions"][0])
    task["payload"] = json.dumps(payload)
    assert client.get("/api/combine/current?event_id=1317").status_code == 503


def test_missing_or_excessive_tasks_fail_instead_of_empty_requirements(client):
    client.store["tasks"] = []
    assert client.get("/api/combine/current?event_id=1317").status_code == 503
    template = definition_rows(1317)[0]
    client.store["tasks"] = [{**template, "task_id": 50000 + index} for index in range(MAX_TASKS + 1)]
    assert client.get("/api/combine/current?event_id=1317").status_code == 503


@pytest.mark.parametrize("source", ["agent", "gmtm"])
def test_database_failure_is_generic_503_and_closes_connections(client, source):
    client.store["fail_source"] = source
    response = client.get("/api/combine/current?event_id=1317")
    assert response.status_code == 503 and "PRIVATE_DRIVER_ERROR" not in response.text
    assert all(db.closed for db in client.store["connections"])


@pytest.mark.parametrize("field,value", [("user_id", 9999), ("event_id", 1318),
                                       ("visibility", -1), ("task_id", 8888), ("created_on", None)])
def test_unexpected_submission_scope_rejected_even_if_source_returns_it(client, field, value):
    row = submission_for(task_named(client, "20-Yard Dash"))
    row[field] = value
    client.store["submission_rows_override"] = [row]
    assert client.get("/api/combine/current?event_id=1317").status_code == 503


def test_public_description_plain_text_has_no_script_or_markup(client):
    task_named(client, "20-Yard Dash")["description"] = '<p>Run <b>20 yards</b>.</p><script>bad()</script><p>**Keep video.**</p>'
    description = activity_named(get(client), "20-Yard Dash")["description"]
    assert description == "Run 20 yards.\n**Keep video.**"


def test_real_db_factory_rejects_unconfigured_or_retired_host_without_connect(monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    with pytest.raises(ValueError):
        combine_api._get_gmtm_db()
    monkeypatch.setenv("DB_HOST", "pre-prod.example.invalid")
    monkeypatch.setenv("DB_USER", "unused")
    with pytest.raises(ValueError):
        combine_api._get_gmtm_db()


def test_datetime_source_values_are_serializable_without_timezone_claim():
    activity = parse_activities(definition_rows(1317), 1317)[0]
    submission = submission_for(definition_rows(1317)[0])
    submission["created_on"] = datetime(2026, 9, 6, 12, 0)
    projected = project_activity(activity, submission, personal_available=True)
    assert projected["submitted_at"] == "2026-09-06T12:00:00"
