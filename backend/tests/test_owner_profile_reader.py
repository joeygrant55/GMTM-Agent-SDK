"""Offline operator-runner regressions; actual handler, synthetic driver only."""
from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import signal
import socket
import sys
from types import SimpleNamespace

import pytest

from scripts import read_owner_profile_evidence as reader


CONFIG = {
    "DB_HOST": reader.GMTM_HOST, "DB_PORT": "3306", "DB_NAME": "gmtm",
    "DB_USER": "gmtmread", "DB_PASSWORD": "synthetic-private-password",
    "AGENT_DB_HOST": "synthetic.proxy.rlwy.net", "AGENT_DB_PORT": "12345",
    "AGENT_DB_NAME": "railway", "AGENT_DB_USER": "synthetic-user",
    "AGENT_DB_PASSWORD": "synthetic-private-password",
}
SUBJECT = "synthetic-private-subject"


class SyntheticCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        pass

    def execute(self, sql, params=None):
        connection = self.connection
        sql = reader.normalized(sql)
        connection.executed.append((sql, params))
        if connection.driver.on_execute:
            connection.driver.on_execute(connection, sql)
        if sql in reader.SETUP_SQL:
            self.rows = []
        elif "FROM athlete_profiles" in sql:
            self.rows = deepcopy(connection.driver.links)
        elif "FROM users u" in sql:
            self.rows = [dict(user_id=reader.OWNER, first_name="Synthetic", last_name="Athlete",
                              graduation_year=2027, city="Example", state="Example")]
        elif "FROM career c" in sql:
            self.rows = []
        elif "FROM metrics m" in sql:
            self.rows = [dict(user_id=reader.OWNER, metric_id=401, title="40 Yard Dash",
                              value="4.75", unit="seconds", created_on="2026-09-01",
                              is_current=1, visibility=2, user_approved=0,
                              suggested_by=None, event_id=None)]
        elif sql in connection.driver.material_rows:
            self.rows = deepcopy(connection.driver.material_rows[sql])
        else:
            raise AssertionError("Unexpected synthetic SQL")

    def fetchall(self):
        return deepcopy(self.rows)


class SyntheticConnection:
    def __init__(self, driver, kind):
        self.driver, self.kind = driver, kind
        self.executed = []
        self.rollbacks = self.closes = 0

    def cursor(self):
        return SyntheticCursor(self)

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


class SyntheticDriver:
    def __init__(self, on_execute=None, links=None, material_rows=None):
        self.on_execute = on_execute
        self.links = links if links is not None else [dict(user_id=reader.OWNER, clerk_id=SUBJECT)]
        self.connections = []
        self.material_rows = material_rows or {}

    def __call__(self, **kwargs):
        assert kwargs["connect_timeout"] == 5
        assert kwargs["read_timeout"] == kwargs["write_timeout"] == 10
        assert kwargs["autocommit"] is False and kwargs["local_infile"] is False
        kind = "agent" if kwargs["host"] == CONFIG["AGENT_DB_HOST"] else "gmtm"
        assert kwargs["host"] in (CONFIG["AGENT_DB_HOST"], reader.GMTM_HOST)
        connection = SyntheticConnection(self, kind)
        self.connections.append(connection)
        return connection


@contextmanager
def ledger_at(tmp_path, scope="profile"):
    directory = reader.output_directory(str(tmp_path.resolve() / "receipt"))
    ledger = reader.Ledger(directory, reader.source_hashes(scope), scope)
    try:
        yield ledger
    finally:
        os.close(ledger.fd)


def configure_main(monkeypatch, driver):
    """Keep env/signals/process flags local; exercise real main and projection."""
    handlers, alarms = {}, []
    monkeypatch.setattr(reader.os, "environ", dict(CONFIG))
    monkeypatch.setattr(reader, "sys", SimpleNamespace(
        flags=SimpleNamespace(isolated=True), path=sys.path, dont_write_bytecode=True))
    monkeypatch.setattr(reader.signal, "signal", lambda number, handler: handlers.__setitem__(number, handler))
    monkeypatch.setattr(reader.signal, "alarm", alarms.append)
    original_projection = reader.read_projection
    monkeypatch.setattr(reader, "read_projection", lambda config, ledger: original_projection(config, ledger, driver=driver))
    return handlers, alarms


def invoke_main(directory, scope="profile", source_digest=None):
    return reader.main(["--execute-reviewed", "--source-digest", source_digest or reader.digest(reader.source_hashes(scope)),
                        "--output", str(directory), "--scope", scope])


def material_rows():
    """Independent source fixtures for each exact guarded query and owner path."""
    event = dict(event_id=1318, joined_event_id=1318, event_name="Synthetic combine",
                 event_visibility=2, event_published=1, event_public=1,
                 event_invite_only=0, event_networks_only=0, event_product_id=None)
    payload = json.dumps({"questions": {"metric:40 Yard Dash": {
        "type": "metric", "value": {"value": "4.75", "unit": "seconds"}}}})
    submission = dict(user_id=reader.OWNER, task_submission_id=101, task_id=21,
                      joined_task_id=21, task_title="Sprint", task_visibility=2,
                      visibility=2, created_on="2026-09-01", payload=payload,
                      payload_bytes=len(payload.encode()), **event)
    film = dict(user_id=reader.OWNER, film_id=301, direct_user_id=reader.OWNER,
                career_id=None, joined_career_id=None, career_user_id=None,
                task_submission_id=None, film_event_id=0, in_person_event_id=None,
                challenge_id=None, approved=0, suggested_by=None, suggested_by_org_id=None,
                visibility=2, processed=1, dead_link=0, title="Synthetic highlights",
                published_on="2026-09-01", joined_event_id=None)
    submitted = dict(film, film_id=302, task_submission_id=101, joined_submission_id=101,
                     submission_user_id=reader.OWNER, submission_visibility=2,
                     task_id=21, joined_task_id=21, task_visibility=2, **event)
    career = dict(film, film_id=303, direct_user_id=None, career_id=31,
                  joined_career_id=31, career_user_id=reader.OWNER, career_visibility=2,
                  career_approved=0, career_suggested_by=None, career_suggested_by_org_id=None)
    return dict(zip(reader.reviewed_queries("materials"), ([submission], [submitted], [film], [career])))


@pytest.mark.parametrize("interruption", [signal.SIGINT, signal.SIGTERM, signal.SIGALRM])
def test_interruption_inside_actual_handler_cannot_export_observation(tmp_path, monkeypatch, capsys, interruption):
    handlers = {}
    fired = []
    def interrupt_during_identity(connection, sql):
        if "FROM users u" in sql and not fired:
            fired.append(interruption)
            handlers[interruption](interruption, None)
    driver = SyntheticDriver(on_execute=interrupt_during_identity)
    handlers, alarms = configure_main(monkeypatch, driver)
    directory = tmp_path.resolve() / "cancelled"
    assert invoke_main(directory) == 2
    receipt = json.loads((directory / "receipt.json").read_text())
    expected = "runtime_deadline" if interruption == signal.SIGALRM else "operator_interrupted"
    assert receipt["status"] == "blocked" and receipt["complete"] is True
    assert receipt["forbidden_attempts"] == {expected: 1}
    assert receipt["all_connections_closed"] is True
    assert receipt["connections_created"] == receipt["connections_closed"] == 2
    assert not (directory / "private-profile-evidence.json").exists()
    assert fired == [interruption] and alarms == [90, 0]
    assert all(connection.rollbacks == connection.closes == 1 for connection in driver.connections)
    assert all(not any("FROM metrics m" in sql for sql, _ in connection.executed)
               for connection in driver.connections)
    assert "synthetic-private" not in capsys.readouterr().out


def test_actual_runner_retains_only_projection_with_exact_reserved_budgets(tmp_path, monkeypatch, capsys):
    driver = SyntheticDriver()
    configure_main(monkeypatch, driver)
    directory = tmp_path.resolve() / "observed"
    assert invoke_main(directory) == 0
    receipt = json.loads((directory / "receipt.json").read_text())
    projection = json.loads((directory / "private-profile-evidence.json").read_text())
    assert receipt["status"] == "observed" and receipt["complete"] is True
    assert receipt["attempts"] == {"connections": 2, "selects": 6, "statements": 10}
    assert receipt["forbidden_attempts"] == {}
    assert receipt["stored_owner_confirmed"] is True
    assert receipt["current_session_verified"] is receipt["authenticated_http_verified"] is False
    assert receipt["all_connections_closed"] is True
    assert projection["response"]["state"] == "ready"
    assert projection["response"]["evidence"][0]["value"] == 4.75
    assert "synthetic-private" not in json.dumps(receipt) + json.dumps(projection) + capsys.readouterr().out
    assert directory.stat().st_mode & 0o777 == 0o700
    assert (directory / "receipt.json").stat().st_mode & 0o777 == 0o600
    assert (directory / "private-profile-evidence.json").stat().st_mode & 0o777 == 0o600
    assert all(connection.rollbacks == connection.closes == 1 for connection in driver.connections)


@pytest.mark.parametrize("links,reason", [
    ([dict(user_id=999, clerk_id=SUBJECT)], "foreign_owner_row"),
    ([dict(user_id=reader.OWNER, clerk_id=SUBJECT)] * 2, "owner_link_missing_or_ambiguous"),
])
def test_invalid_owner_never_connects_gmtm(tmp_path, links, reason):
    driver = SyntheticDriver(links=links)
    with ledger_at(tmp_path) as ledger:
        with pytest.raises(reader.Blocked) as error:
            reader.read_projection(CONFIG, ledger, driver=driver)
        assert error.value.code == reason
        assert len(driver.connections) == 1
        assert driver.connections[0].kind == "agent"
        assert driver.connections[0].rollbacks == driver.connections[0].closes == 1


def test_transaction_setup_failure_still_rolls_back_and_closes(tmp_path):
    def fail_setup(connection, sql):
        if sql == reader.SETUP_SQL[1]:
            raise RuntimeError("synthetic setup failure")
    driver = SyntheticDriver(on_execute=fail_setup)
    with ledger_at(tmp_path) as ledger:
        with pytest.raises(RuntimeError, match="synthetic setup failure"):
            reader.read_projection(CONFIG, ledger, driver=driver)
        assert ledger.data["attempts"] == {"connections": 1, "selects": 0, "statements": 2}
        assert ledger.data["all_connections_closed"] is True
        assert driver.connections[0].rollbacks == driver.connections[0].closes == 1


def test_query_scope_and_exhaustion_deny_before_driver_execute(tmp_path):
    driver = SyntheticDriver()
    raw = SyntheticConnection(driver, "agent")
    with ledger_at(tmp_path) as ledger:
        connection = reader.ReadConnection(raw, "agent", ledger, reader.reviewed_queries())
        with connection.cursor() as cursor:
            with pytest.raises(reader.Blocked, match="query_scope"):
                cursor.execute(reader.OWNER_SQL, (999,))
            assert raw.executed == []
            for _ in range(reader.CAPS["selects"]):
                cursor.execute(reader.OWNER_SQL, (reader.OWNER,))
            with pytest.raises(reader.Blocked, match="budget_selects"):
                cursor.execute(reader.OWNER_SQL, (reader.OWNER,))
        assert len(raw.executed) == 6
        durable = json.loads(ledger.path.read_text())
        assert durable["attempts"]["selects"] == 6
        assert durable["forbidden_attempts"] == {"query_scope": 1, "budget_selects": 1}


@pytest.mark.parametrize("operation,reason", [
    (lambda: socket.getaddrinfo("unapproved.invalid", 443), "dns_destination"),
    (lambda: Path(".env.local").read_text(), "environment_file"),
    (lambda: __import__("subprocess"), "forbidden_module"),
])
def test_guard_denials_are_durable_and_patches_are_restored(tmp_path, operation, reason):
    original_dns = socket.getaddrinfo
    with ledger_at(tmp_path) as ledger:
        with pytest.raises(reader.Blocked, match=reason):
            with reader.guarded_runtime(ledger):
                operation()
        assert socket.getaddrinfo is original_dns
        assert json.loads(ledger.path.read_text())["forbidden_attempts"] == {reason: 1}


def test_output_refuses_git_existing_and_symlink_destinations(tmp_path):
    tmp_path = tmp_path.resolve()
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".git").mkdir()
    with pytest.raises(reader.Blocked, match="output_must_be_outside_git"):
        reader.output_directory(str(checkout / "private"))
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(reader.Blocked, match="output_must_be_exclusive"):
        reader.output_directory(str(existing))
    symlink = tmp_path / "dangling"
    symlink.symlink_to(tmp_path / "absent")
    with pytest.raises(reader.Blocked, match="output_symlink_forbidden"):
        reader.output_directory(str(symlink))


@pytest.mark.parametrize("overrides,reason", [
    ({"DB_HOST": "pre-prod.invalid"}, "gmtm_configuration_not_pinned"),
    ({"DB_USER": "root"}, "gmtm_configuration_not_pinned"),
    ({"AGENT_DB_HOST": "mysql.railway.internal"}, "agent_existing_public_proxy_required"),
    ({"AGENT_DB_PORT": "65536"}, "agent_port_invalid"),
])
def test_configuration_rejects_unreviewed_destinations(overrides, reason):
    with pytest.raises(reader.Blocked, match=reason):
        reader.configuration({**CONFIG, **overrides})


def test_materials_scope_retains_actual_projection_with_exact_separate_budgets(tmp_path, monkeypatch, capsys):
    driver = SyntheticDriver(material_rows=material_rows())
    configure_main(monkeypatch, driver)
    directory = tmp_path.resolve() / "materials"
    assert invoke_main(directory, "materials") == 0
    receipt = json.loads((directory / "receipt.json").read_text())
    projection = json.loads((directory / "private-athlete-materials.json").read_text())
    assert receipt["scope"] == "designated_owner_materials_projection"
    assert receipt["requested_scope"] == "materials"
    assert receipt["caps"] == receipt["attempts"] == {"connections": 2, "selects": 7, "statements": 11}
    assert receipt["source_row_counts"] == dict(submissions=1, submitted_films=1, direct_films=1, career_films=1)
    assert receipt["historical_submissions_read"] is True and receipt["stored_owner_confirmed"] is True
    assert receipt["all_connections_closed"] is True and receipt["forbidden_attempts"] == {}
    assert "athlete_materials.py" in receipt["source_hashes_before"]
    assert not (directory / "private-profile-evidence.json").exists()
    assert projection["response"]["state"] == "ready" and len(projection["response"]["items"]) == 4
    assert projection["response"]["items"][0]["result"] == {"value": 4.75, "unit": "seconds"}
    assert all(item["source_url"].startswith("https://gmtm.com/film/") for item in projection["response"]["items"][1:])
    assert "synthetic-private" not in json.dumps(receipt) + json.dumps(projection) + capsys.readouterr().out
    assert (directory / "private-athlete-materials.json").stat().st_mode & 0o777 == 0o600
    assert all(connection.rollbacks == connection.closes == 1 for connection in driver.connections)
    sql = [query for connection in driver.connections for query, _ in connection.executed]
    assert not any("FROM users u" in query or "FROM metrics m" in query for query in sql)


@pytest.mark.parametrize("index,field", [(0, "user_id"), (1, "submission_user_id"),
    (1, "direct_user_id"), (1, "career_user_id"), (2, "user_id"),
    (2, "direct_user_id"), (2, "career_user_id"), (3, "career_user_id")])
def test_materials_driver_foreign_owner_never_reaches_projection_or_count(tmp_path, index, field):
    rows = material_rows()
    query = list(rows)[index]
    rows[query][0][field] = 999
    driver = SyntheticDriver(material_rows=rows)
    with ledger_at(tmp_path, "materials") as ledger:
        with pytest.raises(reader.Blocked, match="forbidden_operation_attempted"):
            reader.read_projection(CONFIG, ledger, driver=driver)
        assert ledger.data["forbidden_attempts"] == {"foreign_owner_row": 1}
        assert len(ledger.data["source_row_counts"]) == index
        assert ledger.data["all_connections_closed"] is True


def test_materials_scope_bounds_source_rows_before_projection_or_count(tmp_path):
    rows = material_rows()
    first = next(iter(rows))
    rows[first] *= 52
    with ledger_at(tmp_path, "materials") as ledger:
        with pytest.raises(reader.Blocked, match="forbidden_operation_attempted"):
            reader.read_projection(CONFIG, ledger, driver=SyntheticDriver(material_rows=rows))
        assert ledger.data["forbidden_attempts"] == {"source_row_bound": 1}
        assert ledger.data["source_row_counts"] == {} and ledger.data["all_connections_closed"] is True


def test_materials_empty_read_records_four_zero_counts_not_missing_source(tmp_path):
    rows = {query: [] for query in reader.reviewed_queries("materials")}
    with ledger_at(tmp_path, "materials") as ledger:
        projection = reader.read_projection(CONFIG, ledger, driver=SyntheticDriver(material_rows=rows))
        assert projection["response"]["state"] == "ready" and projection["response"]["items"] == []
        assert ledger.data["source_row_counts"] == dict(submissions=0, submitted_films=0, direct_films=0, career_films=0)


def test_materials_scope_cannot_reuse_profile_digest(tmp_path, monkeypatch):
    driver = SyntheticDriver(material_rows=material_rows())
    configure_main(monkeypatch, driver)
    directory = tmp_path.resolve() / "wrong-scope"
    assert invoke_main(directory, "materials", reader.digest(reader.source_hashes())) == 2
    assert not directory.exists() and driver.connections == []
    assert set(reader.source_hashes("materials")) == set(reader.SOURCE_FILES) | {"athlete_materials.py"}
    assert reader.CAPS == {"connections": 2, "selects": 6, "statements": 10}


@pytest.mark.parametrize("bad_query,bad_params", [
    ("profile_query", (reader.OWNER,)), ("materials_query", (999, 51)),
    ("materials_query", (reader.OWNER, 52)),
])
def test_materials_query_scope_cannot_expand_owner_or_bound(tmp_path, bad_query, bad_params):
    queries = reader.reviewed_queries("materials")
    sql = next(iter(reader.reviewed_queries())) if bad_query == "profile_query" else next(iter(queries))
    raw = SyntheticConnection(SyntheticDriver(), "gmtm")
    with ledger_at(tmp_path, "materials") as ledger:
        connection = reader.ReadConnection(raw, "gmtm", ledger, queries)
        with connection.cursor() as cursor:
            with pytest.raises(reader.Blocked, match="query_scope"):
                cursor.execute(sql, bad_params)
        assert raw.executed == [] and ledger.data["attempts"]["selects"] == 0


@pytest.mark.parametrize("scope", ["profile", "materials"])
def test_each_scope_offline_preflight_has_zero_database_attempts(scope, monkeypatch, capsys):
    monkeypatch.setattr(reader.os, "environ", dict(CONFIG))
    monkeypatch.setattr(reader, "read_projection", lambda *args: pytest.fail("No source access during preflight"))
    assert reader.main(["--scope", scope]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["scope"] == scope and body["caps"] == reader.SCOPES[scope]["caps"]
    assert body["database_attempts"] == 0 and body["connectivity_verified"] is False
