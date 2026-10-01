"""Synthetic first-party engagement boundaries; no telemetry or service delivery."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import re
from threading import Barrier, Lock
import time

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

import athlete_workspace as workspace
import combine_api
import opportunity_engagement as api
from auth import require_identity
from backend.tests.test_athlete_opportunities import record, contact_record
from backend.tests.workspace_fixture_store import WorkspaceStore


CALLER = "sub_engagement_private_owner"
LINK = {"id": 519, "user_id": 8201, "clerk_id": CALLER}
NOW = datetime(2026, 9, 10, 12, tzinfo=timezone.utc)
PATH = "/api/athlete/opportunity-engagement"
EVENT_ID = "11111111-2222-4333-8444-555555555555"


def environment(**changes):
    return {"OPPORTUNITY_ENGAGEMENT_ENABLED": "true",
            "OPPORTUNITY_ENGAGEMENT_COHORT": "internal",
            "OPPORTUNITY_ENGAGEMENT_PERIOD": "synthetic-september-2026",
            "OPPORTUNITY_ENGAGEMENT_SECRET": "a1" * 32,
            "OPPORTUNITY_ENGAGEMENT_EXCLUDED_IDS": "",
            "OPPORTUNITY_ENGAGEMENT_PILOT_IDS": "", **changes}


def event(**changes):
    return {"event_id": EVENT_ID, "opportunity_id": "synthetic-assessment",
            "kind": "card_visible", "link_revision": api._revision(LINK),
            "reviewed_at": "2026-09-09T12:00:00Z", **changes}


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        assert tz == timezone.utc
        return NOW


@pytest.fixture
def store(monkeypatch):
    fixture = WorkspaceStore([LINK])
    fixture.rows[CALLER.encode()] = {"payload": "PRIVATE EXISTING DRAFT"}
    before = deepcopy(fixture.rows)
    source_attempts = []

    def forbidden(*args, **kwargs):
        source_attempts.append(True)
        raise AssertionError("GMTM access forbidden")

    monkeypatch.setattr(api, "_get_agent_db", fixture.connect)
    monkeypatch.setattr(workspace, "_get_gmtm_db", forbidden)
    monkeypatch.setattr(combine_api, "_get_gmtm_db", forbidden)
    monkeypatch.setattr(api, "RECORDS", (record(),))
    monkeypatch.setattr(api, "datetime", FrozenDatetime)
    yield fixture
    assert not source_attempts and fixture.rows == before
    assert all(db.closed and not db.transaction and db.commits == 0 for db in fixture.connections)
    assert all(sql.startswith("SELECT ") and "athlete_profiles" in sql
               and "athlete_workspaces" not in sql for sql, _ in fixture.queries)


@pytest.fixture
def emitted(monkeypatch):
    output = []
    monkeypatch.setattr(api, "_emit", lambda item: output.append(deepcopy(item)))
    return output


def app(config, *, caller=CALLER):
    instance = FastAPI()
    instance.state.opportunity_engagement_configuration = config
    instance.state.opportunity_engagement_limiter = api.RateLimit()
    instance.add_api_route(PATH, api.current_opportunity_engagement, methods=["POST"])
    if caller is not None:
        instance.dependency_overrides[require_identity] = lambda: caller
    return instance


@pytest.fixture
def client(store, emitted):
    with TestClient(app(api.validate_configuration(environment()))) as instance:
        yield instance


def test_disabled_configuration_does_not_require_secrets_or_account_lists():
    assert api.validate_configuration({}) is None
    for disabled in ("", "false"):
        assert api.validate_configuration(environment(OPPORTUNITY_ENGAGEMENT_ENABLED=disabled,
                                                    OPPORTUNITY_ENGAGEMENT_SECRET=None,
                                                    OPPORTUNITY_ENGAGEMENT_PILOT_IDS=[])) is None


@pytest.mark.parametrize("name,value", [
    ("ENABLED", "TRUE"), ("ENABLED", "1"), ("ENABLED", None),
    ("COHORT", "external"), ("COHORT", "pilot"),
    ("PERIOD", ""), ("PERIOD", "a" * 65), ("PERIOD", "September 2026"),
    ("PERIOD", "-period"), ("PERIOD", "period--two"), ("PERIOD", "joey@gmtm.com"),
    ("SECRET", "a" * 63), ("SECRET", "A" * 64), ("SECRET", "g" * 64), ("SECRET", None),
    ("EXCLUDED_IDS", "0"), ("EXCLUDED_IDS", "01"), ("EXCLUDED_IDS", "1, 3"),
    ("EXCLUDED_IDS", "1,"), ("EXCLUDED_IDS", "-1"), ("EXCLUDED_IDS", "9007199254740992"),
    ("EXCLUDED_IDS", "1," * 1000 + "1"), ("EXCLUDED_IDS", "1" * 17001),
    ("PILOT_IDS", [8201]), ("PILOT_IDS", "1.0"),
])
def test_invalid_configuration_is_rejected_without_echoing_values(name, value):
    with pytest.raises(ValueError) as error:
        api.validate_configuration(environment(**{"OPPORTUNITY_ENGAGEMENT_" + name: value}))
    assert "joey@gmtm.com" not in str(error.value)
    assert "a1" * 32 not in str(error.value)


def test_valid_config_is_frozen_and_hides_secret_and_account_ids():
    config = api.validate_configuration(environment(OPPORTUNITY_ENGAGEMENT_COHORT="pilot",
                                                   OPPORTUNITY_ENGAGEMENT_PILOT_IDS="8201,8201,9007199254740991",
                                                   OPPORTUNITY_ENGAGEMENT_EXCLUDED_IDS="9302"))
    assert config.pilot_ids == frozenset({8201, 9007199254740991})
    assert config.excluded_ids == frozenset({2, 9302})
    assert len(config.secret) == 32
    assert all(value not in repr(config) for value in ("8201", "9302", "9007199254740991", "a1" * 32))
    with pytest.raises(AttributeError):
        config.period = "changed"
    with pytest.raises(ValueError):
        api.validate_configuration(environment(OPPORTUNITY_ENGAGEMENT_COHORT="pilot",
                                               OPPORTUNITY_ENGAGEMENT_PILOT_IDS="2,9302",
                                               OPPORTUNITY_ENGAGEMENT_EXCLUDED_IDS="9302"))


@pytest.mark.parametrize("changes", [
    {"user_id": 2}, {"clerk_id": "other"}, {"account": "forged"}, {"cohort": "pilot"},
    {"owner_scope": "other"}, {"email": "PRIVATE EMAIL"}, {"goal": "PRIVATE GOAL"},
    {"href": "https://evil.invalid"}, {"at": "2026-09-10T12:00:00Z"},
    {"kind": "registration"}, {"kind": "source_clicked"}, {"kind": None},
    {"opportunity_id": ""}, {"opportunity_id": "x" * 65}, {"opportunity_id": "event--two"},
    {"opportunity_id": "../other"}, {"opportunity_id": "MixedCase"},
    {"link_revision": "a" * 63}, {"link_revision": "A" * 64}, {"link_revision": True},
    {"event_id": "not-a-uuid"}, {"event_id": EVENT_ID.upper().replace("11111111", "AAAAAAAA")},
    {"event_id": "11111111-2222-1333-8444-555555555555"},
    {"event_id": "{11111111-2222-4333-8444-555555555555}"},
    {"reviewed_at": "2026-09-09"},
    {"reviewed_at": "2026-02-30T12:00:00Z"},
])
def test_malformed_and_actor_or_pii_fields_fail_before_database(client, store, emitted, changes):
    with pytest.raises(ValueError):
        api._request(event(**changes))
    response = client.post(PATH, json=event(**changes))
    assert response.status_code == 400
    assert not store.connections and not emitted and "PRIVATE" not in response.text


@pytest.mark.parametrize("body", [
    b"{}", b"[]", b"null", b"\xff", b'{"value":NaN}',
    ('{"kind":"card_visible",' + json.dumps(event())[1:]).encode(),
    b" " * api.MAX_BODY + b"{}", ("[" * 1100 + "]" * 1100).encode(),
])
def test_duplicate_invalid_or_oversize_json_never_connects(client, store, emitted, body):
    response = client.post(PATH, content=body, headers={"content-type": "application/json"})
    assert response.status_code == 400 and not store.connections and not emitted


def test_query_parameters_wrong_content_type_and_chunked_limit_fail_before_db(client, store, emitted):
    assert client.post(PATH + "?user_id=2", json=event()).status_code == 400
    assert client.post(PATH, content=json.dumps(event()), headers={"content-type": "text/plain"}).status_code == 400
    chunks = iter([b" " * (api.MAX_BODY // 2), b" " * (api.MAX_BODY // 2), b"{}"])
    assert client.post(PATH, content=chunks, headers={"content-type": "application/json"}).status_code == 400
    assert not store.connections and not emitted


def test_disabled_endpoint_returns_404_before_auth_and_database(store, emitted):
    application = app(None)
    auth_calls = []

    def forbidden_auth():
        auth_calls.append(True)
        raise AssertionError("Disabled collector should precede authentication")

    application.dependency_overrides[require_identity] = forbidden_auth
    with TestClient(application) as instance:
        assert instance.post(PATH, json=event()).status_code == 404
    assert not auth_calls and not store.connections and not emitted


def test_enabled_endpoint_requires_auth_before_any_data_read(store, emitted):
    with TestClient(app(api.validate_configuration(environment()), caller=None)) as instance:
        assert instance.post(PATH, json=event()).status_code == 401
    assert not store.connections and not emitted


@pytest.mark.parametrize("kind", api.KINDS)
def test_current_owned_capture_emits_exact_private_schema_with_two_owner_reads(client, store, emitted, kind):
    response = client.post(PATH, json=event(kind=kind))
    assert response.status_code == 204 and response.content == b""
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert store.queries == [
        ("SELECT id, user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2", (CALLER,)),
        ("SELECT id, user_id, clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 2", (LINK["user_id"],)),
    ]
    assert len(emitted) == 1 and len(store.connections) == 1 and store.connections[0].closed
    output = emitted[0]
    assert set(output) == {"schema", "at", "catalog_revision", "opportunity_id", "kind", "event_id",
                           "cohort", "account", "measurement_period", "destination_kind"}
    assert output["schema"] == 1 and output["at"] == "2026-09-10T12:00:00Z"
    assert output["kind"] == kind and output["event_id"] == EVENT_ID
    assert output["opportunity_id"] == "synthetic-assessment" and output["destination_kind"] == "program_page"
    assert output["cohort"] == "internal" and output["measurement_period"] == "synthetic-september-2026"
    assert re.fullmatch(r"[a-f0-9]{64}", output["account"])
    assert re.fullmatch(r"[a-f0-9]{64}", output["catalog_revision"])
    assert CALLER not in json.dumps(output) and "PRIVATE" not in json.dumps(output)


@pytest.mark.parametrize("change", [
    lambda x: x.update(valid_until="2026-09-10T12:00:00Z"),
    lambda x: x["sources"][0].update(checked_at="2026-09-10T13:00:00Z"),
    lambda x: (x.update(valid_until="2026-09-10T12:00:00Z"), x["sources"][0].update(expires_at="2026-09-10T12:00:00Z")),
    lambda x: x.update(opens_at="2026-09-11T12:00:00Z"),
    lambda x: x.update(closes_at="2026-09-10T12:00:00Z"),
    lambda x: x["action"].update(href="https://usafootball.com/unsupported"),
])
def test_stale_future_closed_or_invalid_catalog_never_reads_owner_or_emits(client, store, emitted, monkeypatch, change):
    item = record()
    change(item)
    monkeypatch.setattr(api, "RECORDS", (item,))
    assert client.post(PATH, json=event()).status_code == 400
    assert not store.connections and not emitted


def test_unknown_duplicate_opportunity_and_wrong_review_revision_are_rejected(client, store, emitted, monkeypatch):
    assert client.post(PATH, json=event(opportunity_id="unknown-opportunity")).status_code == 400
    assert client.post(PATH, json=event(reviewed_at="2026-09-08T12:00:00Z")).status_code == 400
    monkeypatch.setattr(api, "RECORDS", (record(), record()))
    assert client.post(PATH, json=event()).status_code == 400
    assert not store.connections and not emitted


def test_valid_utc_offset_still_requires_exact_catalog_review_timestamp(client, store, emitted):
    value = event(reviewed_at="2026-09-09T12:00:00+00:00")
    assert api._request(value) == value
    assert client.post(PATH, json=value).status_code == 400
    assert not store.connections and not emitted


def test_secondary_source_future_or_expiry_also_invalidates_capture(client, store, emitted, monkeypatch):
    item = record()
    item["sources"].append({**item["sources"][0], "id": "source-2", "checked_at": "2026-09-11T12:00:00Z"})
    monkeypatch.setattr(api, "RECORDS", (item,))
    assert client.post(PATH, json=event()).status_code == 400
    item["sources"][1].update(checked_at="2026-09-09T12:00:00Z", expires_at="2026-09-10T12:00:00Z")
    item["valid_until"] = "2026-09-10T12:00:00Z"
    assert client.post(PATH, json=event()).status_code == 400
    assert not store.connections and not emitted


def test_introduction_action_is_not_an_outbound_activation(client, store, emitted, monkeypatch):
    monkeypatch.setattr(api, "RECORDS", (contact_record(),))
    value = event(opportunity_id="synthetic-contact", kind="outbound_activated")
    assert client.post(PATH, json=value).status_code == 400
    assert not emitted and not store.connections
    for kind in ("card_visible", "details_opened"):
        assert client.post(PATH, json={**value, "kind": kind}).status_code == 204
    assert len(emitted) == 2 and all(x["destination_kind"] == "contact_page" for x in emitted)


def test_reviewed_event_primary_link_is_classified_as_event_page(client, emitted, monkeypatch):
    monkeypatch.setattr(api, "RECORDS", (record(kind="event"),))
    assert client.post(PATH, json=event(kind="outbound_activated")).status_code == 204
    assert emitted[0]["destination_kind"] == "event_page"


@pytest.mark.parametrize("links,code", [
    ([], "workspace_unlinked"),
    ([LINK, {**LINK, "id": 520, "user_id": 8202}], "workspace_link_changed"),
    ([LINK, {**LINK, "id": 520, "clerk_id": "another_account"}], "workspace_link_changed"),
    ([{**LINK, "id": True}], "workspace_link_changed"),
    ([{**LINK, "user_id": True}], "workspace_link_changed"),
    ([{**LINK, "id": 520}], "workspace_link_changed"),
    ([{**LINK, "user_id": 8202}], "workspace_link_changed"),
])
def test_missing_ambiguous_recreated_or_relinked_owner_never_emits(client, store, emitted, links, code):
    store.links = deepcopy(links)
    response = client.post(PATH, json=event())
    assert response.status_code == 409 and response.json()["code"] == code
    assert not emitted


def test_casefolded_forward_match_is_not_identity_authority(client, store, emitted):
    store.case_insensitive = True
    store.links = [{**LINK, "clerk_id": CALLER.upper()}]
    assert client.post(PATH, json=event()).status_code == 409
    assert not emitted


def test_reverse_owner_change_between_reads_fails_closed(client, store, emitted):
    reads = iter([[LINK], [{**LINK, "clerk_id": "different_private_owner"}]])
    store.link_reader = lambda: next(reads)
    assert client.post(PATH, json=event()).status_code == 409
    assert len(store.queries) == 2 and not emitted


@pytest.mark.parametrize("stage", ["connect", "execute", "close"])
def test_database_failures_are_redacted_and_never_logged(client, store, emitted, stage):
    store.failures[stage] = RuntimeError("PRIVATE PASSWORD HOST SQL")
    response = client.post(PATH, json=event())
    assert response.status_code == 503 and "PRIVATE" not in response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert not emitted


def test_sink_failure_is_best_effort_503_after_database_closes(client, store, emitted, monkeypatch):
    def failed_sink(value):
        assert all(db.closed for db in store.connections)
        raise RuntimeError("PRIVATE SINK SETTINGS")

    monkeypatch.setattr(api, "_emit", failed_sink)
    response = client.post(PATH, json=event())
    assert response.status_code == 503 and response.json() == {"code": "engagement_unavailable"}
    assert not emitted and "PRIVATE" not in response.text


@pytest.mark.parametrize("cohort,owner,pilot,excluded,expected", [
    ("internal", 8201, "", "", "internal"),
    ("fixture", 8201, "", "", "fixture"),
    ("fixture", 2, "", "", "internal"),
    ("pilot", 8201, "8201", "", "pilot"),
    ("pilot", 8201, "8202", "", "internal"),
    ("pilot", 8201, "8201,8202", "8201", "internal"),
    ("pilot", 2, "2,8202", "", "internal"),
])
def test_server_configuration_controls_classification(store, emitted, cohort, owner, pilot, excluded, expected):
    link = {**LINK, "user_id": owner}
    store.links = [link]
    config = api.validate_configuration(environment(OPPORTUNITY_ENGAGEMENT_COHORT=cohort,
                                                   OPPORTUNITY_ENGAGEMENT_PILOT_IDS=pilot,
                                                   OPPORTUNITY_ENGAGEMENT_EXCLUDED_IDS=excluded))
    api.capture(CALLER, event(link_revision=api._revision(link)), config, api.RateLimit(), now=NOW)
    assert emitted[0]["cohort"] == expected


def test_account_key_is_stable_across_actions_but_separate_for_period_cohort_secret_and_account(store, emitted):
    limiter = api.RateLimit()
    config = api.validate_configuration(environment())
    for kind in api.KINDS:
        api.capture(CALLER, event(kind=kind), config, limiter, now=NOW)
    assert len({x["account"] for x in emitted}) == 1
    base = emitted[0]["account"]
    for changes in ({"OPPORTUNITY_ENGAGEMENT_PERIOD": "next-window"},
                    {"OPPORTUNITY_ENGAGEMENT_COHORT": "fixture"},
                    {"OPPORTUNITY_ENGAGEMENT_SECRET": "b2" * 32}):
        other = api.validate_configuration(environment(**changes))
        api.capture(CALLER, event(), other, limiter, now=NOW)
    different_link = {**LINK, "id": 520, "user_id": 8202, "clerk_id": "sub_different_owner"}
    store.links = [different_link]
    api.capture(different_link["clerk_id"], event(link_revision=api._revision(different_link)), config, limiter, now=NOW)
    assert len({base, *(x["account"] for x in emitted[3:])}) == 5
    assert all(re.fullmatch(r"[a-f0-9]{64}", x) for x in limiter.accounts)
    assert all(x["account"] != api._revision(LINK) for x in emitted)


def test_retry_retains_occurrence_identity_for_reporting_dedupe(store, emitted):
    config = api.validate_configuration(environment())
    limiter = api.RateLimit()
    for _ in range(2):
        api.capture(CALLER, event(), config, limiter, now=NOW)
    # The stdout sink is not a durable dedupe ledger; downstream aggregation must dedupe.
    assert len(emitted) == 2 and emitted[0] == emitted[1]


def test_stdout_sink_is_one_prefixed_json_line_without_private_request_material(store, capsys):
    api.capture(CALLER, event(), api.validate_configuration(environment()), api.RateLimit(), now=NOW)
    output = capsys.readouterr()
    assert not output.err and len(output.out.splitlines()) == 1
    assert output.out.startswith(api.PREFIX)
    decoded = json.loads(output.out[len(api.PREFIX):])
    assert decoded["event_id"] == EVENT_ID and decoded["kind"] == "card_visible"
    assert all(value not in output.out for value in (CALLER, "PRIVATE EXISTING DRAFT", "a1" * 32,
                                                   api._revision(LINK), "https://"))


def test_concurrent_stdout_records_are_complete_serialized_lines(monkeypatch):
    class YieldingSink:
        def __init__(self):
            self.lock, self.chunks, self.active, self.overlap, self.flushes = Lock(), [], 0, False, 0

        def write(self, value):
            with self.lock:
                self.active += 1
                self.overlap |= self.active > 1
            # Deliberately release execution inside the sink, as I/O can do.
            time.sleep(0.002)
            with self.lock:
                self.chunks.append(value)
                self.active -= 1
            return len(value)

        def flush(self):
            with self.lock:
                self.flushes += 1

    sink, start = YieldingSink(), Barrier(8)
    monkeypatch.setattr(api.sys, "stdout", sink)

    def emit(index):
        start.wait(timeout=5)
        api._emit({"schema": 1, "synthetic_sequence": index})

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(emit, range(8)))
    assert not sink.overlap and sink.active == 0 and sink.flushes == 8
    assert len(sink.chunks) == 8
    assert all(chunk.startswith(api.PREFIX) and chunk.endswith("\n") and chunk.count("\n") == 1
               for chunk in sink.chunks)
    assert sorted(json.loads(chunk[len(api.PREFIX):])["synthetic_sequence"] for chunk in sink.chunks) == list(range(8))


def test_catalog_version_changes_without_resetting_account_or_event_cycle(store, emitted, monkeypatch):
    config = api.validate_configuration(environment())
    api.capture(CALLER, event(), config, api.RateLimit(), now=NOW)
    changed = record(summary="A newly reviewed synthetic summary.")
    monkeypatch.setattr(api, "RECORDS", (changed,))
    api.capture(CALLER, event(), config, api.RateLimit(), now=NOW)
    assert emitted[0]["catalog_revision"] != emitted[1]["catalog_revision"]
    assert emitted[0]["opportunity_id"] == emitted[1]["opportunity_id"]
    assert emitted[0]["account"] == emitted[1]["account"]


@pytest.mark.parametrize("now", [NOW.replace(tzinfo=None), NOW.astimezone(timezone(timedelta(hours=-4)))])
def test_capture_requires_utc_clock_before_database(store, emitted, now):
    with pytest.raises(ValueError):
        api.capture(CALLER, event(), api.validate_configuration(environment()), api.RateLimit(), now=now)
    assert not store.connections and not emitted


def test_per_account_rate_limit_and_minute_reset():
    limiter = api.RateLimit()
    assert all(limiter.admit("account", now=0) for _ in range(60))
    assert not limiter.admit("account", now=59.999)
    assert limiter.admit("other", now=59.999)
    assert limiter.admit("account", now=60)
    assert limiter.total == 1 and limiter.accounts == {"account": 1}


def test_process_rate_limit_and_distinct_account_memory_bound():
    limiter = api.RateLimit()
    for account in range(100):
        assert all(limiter.admit(str(account), now=0) for _ in range(60))
    assert not limiter.admit("new", now=0) and limiter.total == 6000
    limiter = api.RateLimit()
    assert all(limiter.admit(str(account), now=0) for account in range(2048))
    assert not limiter.admit("new", now=0) and len(limiter.accounts) == 2048
    assert limiter.admit("0", now=0)
    assert limiter.admit("new", now=60) and len(limiter.accounts) == 1


def test_rejected_rate_limit_does_not_open_owner_connection_or_emit(store, emitted):
    class Denied:
        def admit(self, account):
            assert re.fullmatch(r"[a-f0-9]{64}", account) and account != CALLER
            return False

    with pytest.raises(HTTPException) as error:
        api.capture(CALLER, event(), api.validate_configuration(environment()), Denied(), now=NOW)
    assert error.value.status_code == 429 and not store.connections and not emitted
