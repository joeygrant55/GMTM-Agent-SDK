"""Observed legacy schema compatibility, fixed DDL and partial-outcome safety."""
from copy import deepcopy
import json

import pytest
import prepare_athlete_workspace as schema
import prepare_workspace_link_upgrade as upgrade
from backend.tests.test_prepare_agent_schema import ENV, ACK


def column(n, name, kind, nullable="NO", collation=None, default="null_or_unspecified", extra=""):
    return dict(ordinal=n, name=name, kind=kind, nullable=nullable, collation=collation, default_class=default, extra=extra)


def index(name, field, unique=True):
    return dict(name=name, column_name=field, non_unique=0 if unique else 1,
                sequence=1, prefix_length=None, ordering="A", kind="BTREE")


def observed():
    profile = dict(exists=True, kind="BASE TABLE", engine="InnoDB", row_count_estimate=3,
                   data_bytes_estimate=16384, index_bytes_estimate=16384,
                   columns=[column(1, "user_id", "int"), column(2, "clerk_id", "varchar(100)", "YES", "utf8mb4_0900_ai_ci"),
                            column(3, "bio", "text", "YES", "utf8mb4_0900_ai_ci"),
                            column(4, "updated_at", "timestamp", "YES", default="current_timestamp", extra="DEFAULT_GENERATED on update CURRENT_TIMESTAMP")],
                   indexes=[index("PRIMARY", "user_id"), index("idx_clerk_id", "clerk_id", False)])
    missing = dict(exists=False, kind=None, engine=None, columns=[], indexes=[],
                   row_count_estimate=None, data_bytes_estimate=None, index_bytes_estimate=None)
    return dict(status="schema_inventory", server_version="9.4.0", tables=dict(athlete_profiles=profile, athlete_workspaces=missing),
                select_attempts=7, statement_attempts=9, connected=True, read_only_transaction_started=True,
                rollback_completed=True, connection_closed=True, ddl_attempts=0)


class Store:
    def __init__(self):
        self.value, self.connections, self.ddl = observed(), [], []
        self.fail_before = self.fail_after = self.fail_close = self.corrupt_after = None
    def connect(self, **settings):
        assert settings["host"] == ACK["expected_host"] and settings["database"] == ACK["expected_database"]
        db = Connection(self)
        self.connections.append(db)
        return db
    def add_id(self):
        profile = self.value["tables"]["athlete_profiles"]
        profile["columns"].append(column(5, "id", "bigint unsigned", extra="auto_increment"))
        profile["indexes"].append(index("sparq_link_id", "id"))
    def create_workspace(self):
        self.value["tables"]["athlete_workspaces"] = dict(exists=True, kind="BASE TABLE", engine="InnoDB",
            columns=[column(i, name, kind) for i, (name, kind) in enumerate([
                ("clerk_id", "varbinary(255)"), ("athlete_link_id", "bigint unsigned"), ("gmtm_user_id", "bigint unsigned"),
                ("version", "int unsigned"), ("payload", "json"), ("created_at", "datetime(6)"), ("updated_at", "datetime(6)"),
            ], 1)], indexes=[index("PRIMARY", "clerk_id")], row_count_estimate=0, data_bytes_estimate=16384, index_bytes_estimate=0)


class Connection:
    def __init__(self, store):
        self.store, self.rows, self.closed, self.readonly, self.lock_timeout = store, [], False, False, False
        self.queries, self.rollbacks = [], 0
    def cursor(self): return self
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        if sql == "START TRANSACTION READ ONLY":
            self.readonly = True
        elif sql == schema._INVENTORY_TARGET:
            self.rows = [dict(database_name=ENV["AGENT_DB_NAME"], server_version=self.store.value["server_version"])]
        elif sql in (schema._INVENTORY_TABLE, schema._INVENTORY_COLUMNS, schema._INVENTORY_INDEXES):
            assert self.readonly and params[0] == ENV["AGENT_DB_NAME"]
            table = self.store.value["tables"][params[1]]
            if sql == schema._INVENTORY_TABLE:
                self.rows = [{key: table[key] for key in ("kind", "engine", "row_count_estimate", "data_bytes_estimate", "index_bytes_estimate")}] if table["exists"] else []
            else: self.rows = table["columns" if sql == schema._INVENTORY_COLUMNS else "indexes"]
        elif sql == "SET SESSION lock_wait_timeout = 3":
            self.lock_timeout = True
        else:
            assert not self.readonly and self.lock_timeout and sql in (upgrade.ALTER_SQL, schema.CREATE_SQL)
            name = "add_link_id" if sql == upgrade.ALTER_SQL else "create_athlete_workspaces"
            self.store.ddl.append(name)
            if self.store.fail_before == name: raise RuntimeError("SECRET DDL ERROR")
            (self.store.add_id if sql == upgrade.ALTER_SQL else self.store.create_workspace)()
            if self.store.corrupt_after == name:
                self.store.value["tables"]["athlete_profiles"]["columns"][1]["nullable"] = "NO"
            if self.store.fail_after == name: raise RuntimeError("SECRET LOST ACK")
    def fetchone(self): return deepcopy(self.rows[0]) if self.rows else None
    def fetchall(self): return deepcopy(self.rows)
    def rollback(self): self.rollbacks += 1; self.readonly = False
    def close(self):
        self.closed = True
        if self.lock_timeout and self.store.fail_close: raise RuntimeError("SECRET CLOSE")


def run(store, **changes):
    kwargs = dict(environ=ENV, expected_fingerprint=upgrade.schema_fingerprint(store.value),
                  allow_live=True, connector=store.connect, **ACK)
    return upgrade.upgrade_schema(**{**kwargs, **changes})


def test_default_plan_never_reads_environment_or_connects(capsys):
    class NoReads(dict):
        def get(self, *_): raise AssertionError("No environment read")
    assert upgrade.main([], environ=NoReads(), connector=lambda **_: (_ for _ in ()).throw(AssertionError("No connect"))) == 0
    assert json.loads(capsys.readouterr().out)["connected"] is False


@pytest.mark.parametrize("initial,expected", [("original", ["add_link_id", "create_athlete_workspaces"]),
                                              ("migrated", ["create_athlete_workspaces"]), ("ready", [])])
def test_exact_three_states_preserve_existing_legacy_fields_and_indexes(initial, expected):
    store = Store()
    legacy = deepcopy(store.value["tables"]["athlete_profiles"])
    if initial != "original": store.add_id()
    if initial == "ready": store.create_workspace()
    report = run(store)
    assert report["status"] == "ready" and report["completed_statements"] == expected == store.ddl
    assert report["inventory_attempts"] == len(expected) + 1 and not report["ddl_outcome_uncertain"]
    assert store.value["tables"]["athlete_profiles"]["columns"][:4] == legacy["columns"]
    assert store.value["tables"]["athlete_profiles"]["indexes"][:2] == legacy["indexes"]
    assert all(db.closed for db in store.connections)
    assert all(db.rollbacks == 1 for db in store.connections if not db.lock_timeout)


@pytest.mark.parametrize("changes", [{"allow_live": False}, {"allow_live": 1}, {"expected_fingerprint": "bad"},
                                      {"expected_host": "wrong.example"}, {"expected_database": "wrong"}])
def test_explicit_approval_and_target_guards_precede_connection(changes):
    store = Store()
    with pytest.raises(upgrade.PreparationError): run(store, **changes)
    assert not store.connections and not store.ddl


def test_fingerprint_mismatch_does_not_start_ddl_connection():
    store = Store()
    with pytest.raises(upgrade.PreparationError) as caught: run(store, expected_fingerprint="0" * 64)
    assert caught.value.report["reason"] == "reviewed_schema_fingerprint_mismatch"
    assert len(store.connections) == 1 and store.connections[0].closed and not store.ddl


@pytest.mark.parametrize("defect", ["version", "legacy_nullability", "extra_column", "index_prefix", "size", "unknown_size", "workspace_without_id"])
def test_unreviewed_shapes_and_estimates_refuse_without_ddl(defect):
    store = Store()
    table = store.value["tables"]["athlete_profiles"]
    if defect == "version": store.value["server_version"] = "9.4.1"
    elif defect == "legacy_nullability": table["columns"][1]["nullable"] = "NO"
    elif defect == "extra_column": table["columns"].append(column(5, "unknown", "int"))
    elif defect == "index_prefix": table["indexes"][1]["prefix_length"] = 10
    elif defect == "size": table["row_count_estimate"] = 1001
    elif defect == "unknown_size": table["row_count_estimate"] = None
    else: store.create_workspace()
    with pytest.raises(upgrade.PreparationError): run(store)
    assert not store.ddl and all(db.closed for db in store.connections)


def test_fingerprint_ignores_only_estimates_and_index_order():
    value = observed()
    before = upgrade.schema_fingerprint(value)
    value["tables"]["athlete_profiles"]["row_count_estimate"] = 4
    value["tables"]["athlete_profiles"]["indexes"].reverse()
    assert upgrade.schema_fingerprint(value) == before
    value["tables"]["athlete_profiles"]["columns"][1]["collation"] = "utf8mb4_bin"
    assert upgrade.schema_fingerprint(value) != before


@pytest.mark.parametrize("failure,statement", [("fail_before", "add_link_id"), ("fail_after", "add_link_id"),
                                               ("fail_before", "create_athlete_workspaces"), ("fail_after", "create_athlete_workspaces")])
def test_uncertain_ddl_retains_progress_reconciles_once_and_never_retries(failure, statement):
    store = Store()
    setattr(store, failure, statement)
    with pytest.raises(upgrade.PreparationError) as caught: run(store)
    report = caught.value.report
    assert report["ddl_outcome_uncertain"] and report["attempted_statements"].count(statement) == 1
    assert report["completed_statements"] == ([] if statement == "add_link_id" else ["add_link_id"])
    assert report["inventory_attempts"] <= 3 and all(db.closed for db in store.connections)
    assert "SECRET" not in json.dumps(report) and store.ddl.count(statement) == 1


def test_postflight_changed_legacy_schema_stops_before_workspace_creation():
    store = Store()
    store.corrupt_after = "add_link_id"
    with pytest.raises(upgrade.PreparationError) as caught: run(store)
    assert caught.value.report["completed_statements"] == ["add_link_id"]
    assert store.ddl == ["add_link_id"] and all(db.closed for db in store.connections)


def test_failed_metadata_after_acknowledged_alter_prevents_second_ddl(monkeypatch):
    store = Store()
    inventory = upgrade.inventory_schema
    calls = 0
    def inspect(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise upgrade.PreparationError({"status": "failed", "connected": True,
                "read_only_transaction_started": True, "rollback_completed": True, "connection_closed": True,
                "select_attempts": 3, "statement_attempts": 5, "ddl_attempts": 0})
        return inventory(**kwargs)
    monkeypatch.setattr(upgrade, "inventory_schema", inspect)
    with pytest.raises(upgrade.PreparationError) as caught:
        run(store)
    report = caught.value.report
    assert calls == 2 and store.ddl == ["add_link_id"]
    assert report["completed_statements"] == ["add_link_id"]
    assert report["metadata_failure"]["connection_closed"] is True
    assert report["status"] == "failed" and all(db.closed for db in store.connections)


def test_close_failure_does_not_claim_success_or_rollback_completed_ddl():
    store = Store()
    store.fail_close = True
    with pytest.raises(upgrade.PreparationError) as caught: run(store)
    assert caught.value.report["status"] == "failed" and not caught.value.report["ddl_connection_closed"]
    assert caught.value.report["completed_statements"] == ["add_link_id", "create_athlete_workspaces"]
    assert "SECRET" not in str(caught.value)


def test_real_pymysql_formats_exact_ddl_without_connecting():
    import pymysql
    db = pymysql.Connection(defer_connect=True)
    try:
        assert db._sock is None
        cursor = db.cursor()
        assert cursor.mogrify(upgrade.ALTER_SQL) == upgrade.ALTER_SQL
        assert cursor.mogrify(schema.CREATE_SQL) == schema.CREATE_SQL
        assert "ALGORITHM=INPLACE, LOCK=SHARED" in upgrade.ALTER_SQL
        assert "PRIMARY KEY" not in upgrade.ALTER_SQL and "DROP " not in upgrade.ALTER_SQL
    finally:
        db.close()
