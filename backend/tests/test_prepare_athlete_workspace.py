"""Isolated workspace schema planning and exact one-table apply guards."""
from copy import deepcopy
import json

import pytest

import prepare_athlete_workspace as schema
from backend.tests.test_prepare_agent_schema import ENV, ACK


class FakeDB:
    def __init__(self):
        self.closed, self.created = False, False
        self.queries, self.rows = [], []
        self.database = ENV["AGENT_DB_NAME"]
        self.tables = {"athlete_profiles": {"kind": "BASE TABLE", "engine": "InnoDB"}}
        self.columns = {
            "athlete_profiles": {"id": ("int(11)", "NO"), "user_id": ("int(11)", "NO"), "clerk_id": ("varchar(255)", "NO")},
            "athlete_workspaces": deepcopy(schema.WORKSPACE_COLUMNS)}
        self.indexes = {"athlete_profiles": [("PRIMARY", 0, "id"), ("user_id", 0, "user_id"), ("idx_clerk", 1, "clerk_id")],
                        "athlete_workspaces": [("PRIMARY", 0, "clerk_id")]}
        self.fail_at, self.close_error, self.settings = None, None, None

    def cursor(self): return self
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        if self.fail_at and self.fail_at in sql:
            raise RuntimeError("SECRET PASSWORD SQL")
        if sql == "SELECT DATABASE() AS database_name":
            self.rows = [{"database_name": self.database}]
        elif "information_schema.TABLES" in sql:
            self.rows = [self.tables[params[1]]] if params[1] in self.tables else []
        elif "information_schema.COLUMNS" in sql:
            self.rows = [{"name": key, "kind": kind, "nullable": nullable} for key, (kind, nullable) in self.columns[params[1]].items()]
        elif "information_schema.STATISTICS" in sql:
            self.rows = [{"name": name, "non_unique": unique, "column_name": column} for name, unique, column in self.indexes[params[1]]]
        else:
            assert sql == schema.CREATE_SQL
            self.created = True
            self.tables["athlete_workspaces"] = {"kind": "BASE TABLE", "engine": "InnoDB"}
            self.rows = []
    def fetchone(self): return deepcopy(self.rows[0]) if self.rows else None
    def fetchall(self): return deepcopy(self.rows)
    def close(self):
        self.closed = True
        if self.close_error: raise self.close_error


def run(db, environ=None, **ack):
    def connect(**settings):
        db.settings = settings
        return db
    return schema.prepare_schema(environ=ENV if environ is None else environ, connector=connect, **(ack or ACK))


def test_dry_run_does_not_read_configuration_or_connect(capsys):
    class NoReads(dict):
        def get(self, *_): raise AssertionError("No settings on plan")
    assert schema.main([], environ=NoReads(), connector=lambda **_: (_ for _ in ()).throw(AssertionError("No connect"))) == 0
    assert json.loads(capsys.readouterr().out)["connected"] is False


def test_apply_only_creates_one_exact_agent_table_after_prerequisites():
    db = FakeDB()
    result = run(db)
    assert result["workspace_contract_checked"] and result["ddl_is_atomic"] is False
    assert db.closed and db.created
    assert [sql for sql, _ in db.queries if sql.startswith(("CREATE", "ALTER", "DROP"))] == [schema.CREATE_SQL]
    assert db.settings["autocommit"] is True


def test_existing_matching_table_is_checked_before_and_after_idempotent_create():
    db = FakeDB()
    db.tables["athlete_workspaces"] = {"kind": "BASE TABLE", "engine": "InnoDB"}
    assert run(db)["status"] == "preparation_applied"
    assert sum("information_schema.COLUMNS" in sql and params[1] == "athlete_workspaces" for sql, params in db.queries) == 2


@pytest.mark.parametrize("kind", ["bigint(20) unsigned", "bigint unsigned"])
def test_supported_mysql_integer_display_widths(kind):
    db = FakeDB()
    db.columns["athlete_workspaces"]["athlete_link_id"] = (kind, "NO")
    assert run(db)["workspace_contract_checked"]


@pytest.mark.parametrize("suffix", ["HOST", "PORT", "USER", "PASSWORD", "NAME"])
def test_requires_explicit_agent_configuration(suffix):
    db, env = FakeDB(), dict(ENV)
    env.pop("AGENT_DB_" + suffix)
    with pytest.raises(schema.PreparationError): run(db, env)
    assert not db.queries


@pytest.mark.parametrize("host", ["db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com", "pre-prod.example", "family-test.example", "x.rds.amazonaws.com"])
def test_forbids_gmtm_rds_targets_even_when_acknowledged(host):
    db = FakeDB()
    with pytest.raises(schema.PreparationError):
        run(db, {**ENV, "AGENT_DB_HOST": host}, expected_host=host, expected_database=ENV["AGENT_DB_NAME"])
    assert not db.queries


@pytest.mark.parametrize("defect", ["missing", "engine", "identity", "subject", "unique_user", "clerk_index", "workspace_columns", "workspace_index"])
def test_incompatible_preexisting_schema_is_not_repaired(defect):
    db = FakeDB()
    if defect == "missing": db.tables.clear()
    elif defect == "engine": db.tables["athlete_profiles"]["engine"] = "MyISAM"
    elif defect == "identity": db.columns["athlete_profiles"]["user_id"] = ("varchar(255)", "NO")
    elif defect == "subject": db.columns["athlete_profiles"]["clerk_id"] = ("varchar(255)", "YES")
    elif defect == "unique_user": db.indexes["athlete_profiles"] = [("PRIMARY", 0, "id"), ("idx_clerk", 1, "clerk_id")]
    elif defect == "clerk_index": db.indexes["athlete_profiles"] = [("PRIMARY", 0, "id"), ("user_id", 0, "user_id")]
    else:
        db.tables["athlete_workspaces"] = {"kind": "BASE TABLE", "engine": "InnoDB"}
        if defect == "workspace_columns": db.columns["athlete_workspaces"]["clerk_id"] = ("varchar(255)", "NO")
        else: db.indexes["athlete_workspaces"] = []
    with pytest.raises(schema.PreparationError): run(db)
    assert db.closed and not db.created


def test_wrong_connected_database_is_rejected_before_ddl():
    db = FakeDB()
    db.database = "unexpected"
    with pytest.raises(schema.PreparationError): run(db)
    assert db.closed and not db.created


@pytest.mark.parametrize("stage", ["information_schema.COLUMNS", "CREATE TABLE"])
def test_errors_are_redacted_and_connection_closes(stage):
    db = FakeDB()
    db.fail_at = stage
    with pytest.raises(schema.PreparationError) as caught: run(db)
    assert db.closed and "SECRET" not in str(caught.value)
    assert caught.value.report["ddl_is_atomic"] is False


def test_close_failure_does_not_report_success_or_rollback_ddl():
    db = FakeDB()
    db.close_error = RuntimeError("SECRET PASSWORD")
    with pytest.raises(schema.PreparationError) as caught: run(db)
    assert caught.value.report["completed_statements"] == ["create_athlete_workspaces"]
    assert caught.value.report["stage"] == "close" and "SECRET" not in str(caught.value)
