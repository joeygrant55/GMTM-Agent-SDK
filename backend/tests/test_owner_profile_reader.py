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
CLERK = "synthetic-private-clerk"


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
    def __init__(self, on_execute=None, links=None):
        self.on_execute = on_execute
        self.links = links if links is not None else [dict(user_id=reader.OWNER, clerk_id=CLERK)]
        self.connections = []

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
def ledger_at(tmp_path):
    directory = reader.output_directory(str(tmp_path.resolve() / "receipt"))
    ledger = reader.Ledger(directory, reader.source_hashes())
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


def invoke_main(directory):
    return reader.main(["--execute-reviewed", "--source-digest", reader.digest(reader.source_hashes()),
                        "--output", str(directory)])


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
    assert receipt["current_clerk_jwt_verified"] is receipt["authenticated_http_verified"] is False
    assert receipt["all_connections_closed"] is True
    assert projection["response"]["state"] == "ready"
    assert projection["response"]["evidence"][0]["value"] == 4.75
    assert "synthetic-private" not in json.dumps(receipt) + json.dumps(projection) + capsys.readouterr().out
    assert directory.stat().st_mode & 0o777 == 0o700
    assert (directory / "receipt.json").stat().st_mode & 0o777 == 0o600
    assert (directory / "private-profile-evidence.json").stat().st_mode & 0o777 == 0o600
    assert all(connection.rollbacks == connection.closes == 1 for connection in driver.connections)


@pytest.mark.parametrize("links,reason", [
    ([dict(user_id=999, clerk_id=CLERK)], "foreign_owner_row"),
    ([dict(user_id=reader.OWNER, clerk_id=CLERK)] * 2, "owner_link_missing_or_ambiguous"),
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
