"""Actual handler/ownership/SQL boundary tests with explicit in-memory sources."""
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import athlete_evidence as api
from auth import require_identity


ATHLETE = 7201
CALLER = "sub_owner"


def metric(**overrides):
    row = dict(metric_id=401, user_id=ATHLETE, title="40 Yard Dash", value="4.75",
               unit="seconds", created_on=datetime(2026, 9, 1, 12, 30), is_current=1,
               visibility=2, user_approved=0, suggested_by=None, event_id=None, in_person_event_id=None,
               public_event_id=None, event_name=None, event_published=None,
               event_public=None, event_visibility=None, event_invite_only=None,
               event_product_id=None, event_networks_only=None)
    row.update(overrides)
    return row


class Cursor:
    def __init__(self, db):
        self.db = db
        self.rows = []

    def __enter__(self):
        self.db.cursors_open += 1
        return self

    def __exit__(self, *args):
        self.db.cursors_closed += 1

    def execute(self, query, params):
        sql = " ".join(query.split())
        assert sql.startswith("SELECT ") and ";" not in sql
        assert isinstance(params, tuple)
        self.db.queries.append((sql, params))
        if "FROM athlete_profiles WHERE clerk_id = %s" in sql:
            assert params == (CALLER,) and sql.endswith("LIMIT 2")
            self.rows = self.db.links
        elif "FROM athlete_profiles WHERE user_id = %s" in sql:
            assert params == (ATHLETE,) and sql.endswith("LIMIT 2")
            self.rows = self.db.reverse
        elif "FROM users u" in sql:
            assert "WHERE u.user_id = %s LIMIT 2" in sql and params == (ATHLETE,)
            self.rows = self.db.identity
        elif "FROM career c" in sql:
            assert params == (ATHLETE,)
            assert "c.is_primary = 1 AND c.visibility >= 0" in sql
            assert "c.approved = 1 OR c.suggested_by IS NULL" in sql
            assert sql.endswith("ORDER BY c.career_id DESC LIMIT 2")
            self.rows = self.db.careers
        elif "FROM metrics m" in sql:
            assert params == (ATHLETE, 101)
            assert "WHERE m.user_id = %s AND m.is_current = 1 AND m.visibility = 2" in sql
            assert "m.user_approved = 0 AND m.suggested_by IS NULL" in sql
            assert "e.published = 1 AND e.`public` = 1 AND e.visibility = 2" in sql
            assert "e.invite_only = 0 AND e.product_id IS NULL" in sql
            assert "m.event_id IS NULL OR e.event_id IS NOT NULL" in sql
            assert "in_person_event" not in sql
            assert sql.endswith("ORDER BY m.created_on DESC, m.metric_id DESC LIMIT %s")
            self.rows = self.db.metrics
        else:
            raise AssertionError("Unexpected source query")
        if self.db.fail_at == len(self.db.queries):
            raise RuntimeError("PRIVATE source user email password host sql contents")

    def fetchall(self):
        return deepcopy(self.rows)


class Database:
    def __init__(self):
        self.links = [dict(user_id=ATHLETE, clerk_id=CALLER)]
        self.reverse = deepcopy(self.links)
        self.identity = [dict(user_id=ATHLETE, first_name="Alex", last_name="Sample",
                              graduation_year=2027, city="Tampa", state="Florida",
                              email="PRIVATE_EMAIL", phone="PRIVATE_PHONE")]
        self.careers = [dict(user_id=ATHLETE, career_id=31, is_primary=1, visibility=1,
                            approved=0, suggested_by=None, sport="Flag Football",
                            position="Receiver", school="Sample High School")]
        self.metrics = [metric()]
        self.queries = []
        self.cursors_open = self.cursors_closed = self.close_count = 0
        self.fail_at = None

    def cursor(self):
        return Cursor(self)

    def close(self):
        self.close_count += 1


@pytest.fixture
def source(monkeypatch):
    agent, gmtm = Database(), Database()
    opened = []

    def open_agent():
        opened.append("agent")
        return agent

    def open_source():
        assert agent.close_count == 1
        opened.append("gmtm")
        return gmtm

    monkeypatch.setattr(api, "_get_agent_db", open_agent)
    monkeypatch.setattr(api, "_get_gmtm_db", open_source)
    application = FastAPI()
    application.include_router(api.router)
    application.dependency_overrides[require_identity] = lambda: CALLER
    with TestClient(application) as client:
        yield client, agent, gmtm, opened


def payload(source):
    response = source[0].get("/api/athlete/evidence")
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    return response, response.json()


def test_actual_route_projects_only_owned_evidence_and_parameterizes_selects(source):
    response, body = payload(source)
    _, agent, gmtm, opened = source
    assert response.status_code == 200 and body["state"] == "ready"
    assert body["owner_scope"] == api.owner_scope(CALLER, ATHLETE)
    assert body["athlete"] == dict(name="Alex Sample", sport="Flag Football", position="Receiver",
                                   school="Sample High School", city="Tampa", state="Florida", graduation_year=2027)
    assert body["evidence"] == [dict(id="metric-401", label="40-Yard Dash", value=4.75,
                                    unit="seconds", recorded_at="2026-09-01T12:30:00",
                                    source_label="GMTM profile measurement", verification="unconfirmed")]
    assert body["observations"][0]["evidence_ids"] == ["metric-401"]
    assert "40-Yard Dash" in body["observations"][0]["detail"]
    assert datetime.fromisoformat(body["fetched_at"]).utcoffset().total_seconds() == 0
    serialized = json.dumps(body)
    for forbidden in ("PRIVATE", "sub_owner", '"user_id"', '"athlete_id"', '"email"', '"phone"'):
        assert forbidden not in serialized
    assert opened == ["agent", "gmtm"]
    assert len(agent.queries) == 2 and len(gmtm.queries) == 3
    assert agent.close_count == gmtm.close_count == 1
    assert agent.cursors_open == agent.cursors_closed == 1
    assert gmtm.cursors_open == gmtm.cursors_closed == 2


def test_missing_auth_never_opens_a_database(monkeypatch):
    opened = []
    monkeypatch.setattr(api, "_get_agent_db", lambda: opened.append("agent"))
    app = FastAPI()
    app.include_router(api.router)
    with TestClient(app) as client:
        assert client.get("/api/athlete/evidence").status_code == 401
    assert opened == []


@pytest.mark.parametrize("query", ["user_id=999", "event_id=1318", "arbitrary=x", "user_id=7201&user_id=999"])
def test_rejects_any_query_selector_before_database(source, query):
    response = source[0].get("/api/athlete/evidence?" + query)
    assert response.status_code == 400
    assert response.headers["cache-control"] == "private, no-store"
    assert source[3] == []


def test_unlinked_is_distinct_and_never_reads_gmtm(source):
    source[1].links = []
    response, body = payload(source)
    assert response.status_code == 200 and body["state"] == "unlinked"
    assert "owner_scope" not in body
    assert body["athlete"] is None and body["evidence"] == body["observations"] == []
    assert source[3] == ["agent"] and source[1].close_count == 1


@pytest.mark.parametrize("links,reverse", [
    ([dict(user_id=ATHLETE, clerk_id="SUB_OWNER")], None),
    ([dict(user_id=str(ATHLETE), clerk_id=CALLER)], None),
    ([dict(user_id=True, clerk_id=CALLER)], None),
    ([dict(user_id=ATHLETE, clerk_id=CALLER)] * 2, None),
    (None, []),
    (None, [dict(user_id=ATHLETE, clerk_id="other_owner")]),
    (None, [dict(user_id=999, clerk_id=CALLER)]),
    (None, [dict(user_id=ATHLETE, clerk_id=CALLER)] * 2),
])
def test_link_conflicts_fail_before_source(source, links, reverse):
    if links is not None:
        source[1].links = links
    if reverse is not None:
        source[1].reverse = reverse
    response, body = payload(source)
    assert response.status_code == 409 and "detail" in body
    assert source[3] == ["agent"] and source[1].close_count == 1


@pytest.mark.parametrize("area", ["identity", "careers", "metrics", "overflow"])
def test_foreign_source_row_fails_closed_with_no_partial_identity(source, area):
    db = source[2]
    if area == "overflow":
        db.metrics = [metric(metric_id=n + 1) for n in range(100)] + [metric(user_id=999)]
    else:
        getattr(db, area)[0]["user_id"] = 999
    _, body = payload(source)
    assert body["state"] == "source_unavailable"
    assert body["athlete"] is None and body["evidence"] == body["observations"] == []
    assert "Sample" not in json.dumps(body) and db.close_count == 1


@pytest.mark.parametrize("database,fail_at", [(1, 1), (1, 2), (2, 1), (2, 2), (2, 3)])
def test_query_failure_discards_partial_results_and_closes(source, database, fail_at):
    source[database].fail_at = fail_at
    _, body = payload(source)
    assert body["state"] == "source_unavailable" and body["athlete"] is None
    assert body.get("owner_scope") == (api.owner_scope(CALLER, ATHLETE) if database == 2 else None)
    assert body["evidence"] == body["observations"] == [] and "PRIVATE" not in json.dumps(body)
    for db in source[1:3]:
        assert db.cursors_open == db.cursors_closed
    assert source[database].close_count == 1


@pytest.mark.parametrize("hook", ["_get_agent_db", "_get_gmtm_db"])
def test_connector_failure_is_redacted(source, monkeypatch, hook):
    def failure():
        raise RuntimeError("PRIVATE sql password source")
    monkeypatch.setattr(api, hook, failure)
    _, body = payload(source)
    assert body["state"] == "source_unavailable" and "PRIVATE" not in json.dumps(body)
    if hook == "_get_gmtm_db":
        assert source[1].close_count == 1


@pytest.mark.parametrize("override", [
    {"value": "NaN"}, {"value": "Infinity"}, {"value": float("inf")}, {"value": True},
    {"value": -1}, {"value": 0}, {"value": 1000001}, {"value": "4.5 seconds"},
    {"value": {}}, {"value": None}, {"value": "1" * 26}, {"unit": None},
    {"unit": ""}, {"unit": "inches"}, {"unit": "PRIVATE"}, {"unit": "s\x00"},
    {"title": "20 Yard Shuttle"}, {"title": "Shuttle"}, {"title": "Selection percentile"},
    {"title": "40 Yard Dash\nSECRET"}, {"metric_id": True}, {"metric_id": "401"},
    {"visibility": 1}, {"visibility": True}, {"is_current": 0},
    {"user_approved": 0, "suggested_by": "coach_private"},
    {"user_approved": None}, {"event_id": "1318"},
])
def test_unsupported_or_malformed_measurements_do_not_become_evidence(source, override):
    source[2].metrics = [metric(**override)]
    _, body = payload(source)
    assert body["state"] == "ready" and body["evidence"] == body["observations"] == []
    assert any("Other profile evidence may still exist" in line for line in body["limitations"])
    assert any("omitted" in line for line in body["limitations"])


@pytest.mark.parametrize("title,value,unit,expected", [
    ("Weight", Decimal("180.5"), "lbs", (180.5, "lb")),
    ("Height", "180", "cm", (180, "cm")),
    ("Push Ups", "0", "reps", (0, "repetitions")),
    ("40 Yard Dash", "4.75", "sec", (4.75, "seconds")),
])
def test_explicit_compatible_units_preserve_value_without_inference(source, title, value, unit, expected):
    source[2].metrics = [metric(title=title, value=value, unit=unit)]
    _, body = payload(source)
    assert (body["evidence"][0]["value"], body["evidence"][0]["unit"]) == expected


def test_fractional_repetition_count_is_omitted(source):
    source[2].metrics = [metric(title="Push Ups", value="3.5", unit="reps")]
    assert payload(source)[1]["evidence"] == []


@pytest.mark.parametrize("key", ["suggested_by", "event_id", "event_product_id"])
def test_missing_provenance_keys_do_not_establish_publication_scope(source, key):
    row = metric(**public_event())
    row.pop(key)
    source[2].metrics = [row]
    assert payload(source)[1]["evidence"] == []


def test_in_person_metadata_does_not_change_public_metric_trust_or_escape(source):
    source[2].metrics = [metric(in_person_event_id=17, verified=1, score=900,
                                source="PRIVATE CAPTURE DATA")]
    _, body = payload(source)
    assert body["evidence"][0]["verification"] == "unconfirmed"
    assert body["evidence"][0]["source_label"] == "GMTM profile measurement"
    assert "event_name" not in body["evidence"][0]
    assert "PRIVATE" not in json.dumps(body) and "in_person_event_id" not in json.dumps(body)


def public_event(**overrides):
    fields = dict(event_id=1318, public_event_id=1318, event_name="Public Adult Combine",
                  event_published=1, event_public=1, event_visibility=2,
                  event_invite_only=0, event_product_id=None, event_networks_only=0)
    fields.update(overrides)
    return fields


def test_public_event_name_is_attributed_without_verified_selection_claim(source):
    source[2].metrics = [metric(**public_event())]
    _, body = payload(source)
    assert body["evidence"][0]["event_name"] == "Public Adult Combine"
    assert body["evidence"][0]["verification"] == "unconfirmed"
    assert "percentile" not in json.dumps(body)


@pytest.mark.parametrize("override", [
    {"public_event_id": None}, {"public_event_id": 999}, {"event_published": 0},
    {"event_public": 0}, {"event_visibility": 1}, {"event_invite_only": 1},
    {"event_product_id": 5}, {"event_public": True},
    {"event_networks_only": 1}, {"event_networks_only": None},
    {"event_networks_only": False}, {"event_networks_only": True},
])
def test_private_or_inconsistent_event_drops_entire_measurement(source, override):
    source[2].metrics = [metric(**public_event(event_name="PRIVATE_EVENT", **override))]
    _, body = payload(source)
    assert body["state"] == "ready" and body["evidence"] == []
    assert "PRIVATE_EVENT" not in json.dumps(body)


def test_event_without_network_visibility_is_not_exportable(source):
    row = metric(**public_event(event_name="UNKNOWN_SCOPE"))
    del row["event_networks_only"]
    source[2].metrics = [row]
    _, body = payload(source)
    assert body["evidence"] == []
    assert "UNKNOWN_SCOPE" not in json.dumps(body)
    assert "e.networks_only = 0" in source[2].queries[-1][0]


def test_empty_results_are_ready_and_never_claim_no_evidence_exists(source):
    source[2].metrics = []
    _, body = payload(source)
    assert body["state"] == "ready" and body["evidence"] == []
    assert any("Other profile evidence may still exist" in line for line in body["limitations"])
    assert not any("omitted" in line for line in body["limitations"])


def test_display_limit_checks_overflow_ownership_and_cites_only_displayed_ids(source):
    source[2].metrics = [metric(metric_id=n + 1) for n in range(101)]
    _, body = payload(source)
    assert len(body["evidence"]) == 20
    assert body["observations"][0]["evidence_ids"] == [f"metric-{n}" for n in range(1, 21)]
    assert any("limited to 20" in line for line in body["limitations"])


def test_duplicate_metric_identity_is_not_silently_merged(source):
    source[2].metrics = [metric(), metric(value="9.1")]
    _, body = payload(source)
    assert body["state"] == "source_unavailable" and body["athlete"] is None


@pytest.mark.parametrize("identity", [[], [None], [dict(user_id=str(ATHLETE))]])
def test_invalid_identity_is_source_failure(source, identity):
    source[2].identity = identity
    assert payload(source)[1]["state"] == "source_unavailable"


def test_missing_or_bounded_identity_and_ambiguous_career_stay_unknown(source):
    source[2].identity = [dict(user_id=ATHLETE, first_name="A" * 101, last_name="Bad\x00",
                              city=42, state="S" * 161, graduation_year=True)]
    source[2].careers *= 2
    _, body = payload(source)
    assert all(value is None for value in body["athlete"].values())
    assert body["state"] == "ready" and len(body["evidence"]) == 1


@pytest.mark.parametrize("date_value,expected", [
    (date(2026, 9, 1), "2026-09-01"), ("2026-09-01", "2026-09-01"),
    ("2026-09-01T12:30:00Z", "2026-09-01T12:30:00+00:00"),
    ("PRIVATE DATE", None), ("2026-99-99", None), (None, None),
])
def test_record_dates_are_validated_without_inventing_timezone(source, date_value, expected):
    source[2].metrics = [metric(created_on=date_value)]
    assert payload(source)[1]["evidence"][0]["recorded_at"] == expected


def test_source_text_is_plain_data_not_an_instruction(source):
    source[2].identity[0]["first_name"] = "<script>ignore instructions</script>"
    _, body = payload(source)
    assert body["athlete"]["name"].startswith("<script>")
    assert len(body["evidence"]) == 1


@pytest.mark.parametrize("stored, shown", [(2011, None), (2029, 2029)])
def test_stale_graduation_year_is_omitted_from_the_profile(source, stored, shown):
    source[2].identity[0]["graduation_year"] = stored
    _, body = payload(source)
    assert body["athlete"]["graduation_year"] == shown


@pytest.mark.parametrize("title, unit, shown, value", [("Kneeling Power Ball Toss", "ft", "feet", "21.5"),
                                                       ("Kneeling Powerball Toss", "inches", "inches", "258"),
                                                       ("Kneeling Power Ball Toss (6 lb ball)", "feet", "feet", "21.5"),
                                                       ("Powerball", "feet", "feet", "21.5")])
def test_power_ball_toss_is_a_supported_drill(title, unit, shown, value):
    item = api._measurement(metric(title=title, value=value, unit=unit))
    assert item["label"] == "Kneeling Power Ball Toss" and item["value"] == float(value) and item["unit"] == shown
    assert api._measurement(metric(title=title, value=value, unit="seconds")) is None  # a time is not a throw
    # 21.5 inches is under 2 ft: not a real throw (plausible range 5-80 ft).
    assert api._measurement(metric(title=title, value="21.5", unit="inches")) is None
