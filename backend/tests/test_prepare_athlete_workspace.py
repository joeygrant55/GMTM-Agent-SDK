"""Isolated workspace schema planning and exact one-table apply guards."""
from copy import deepcopy
import json

import pytest
import pymysql

import prepare_athlete_workspace as schema
from backend.tests.test_prepare_agent_schema import ENV, ACK


def test_inventory_queries_format_with_real_pymysql_without_connecting():
    connection = pymysql.Connection(defer_connect=True)
    connection.server_status = 0
    try:
        with connection.cursor() as cursor:
            for sql in schema._INVENTORY_SELECTS:
                rendered = cursor.mogrify(sql, None if sql == schema._INVENTORY_TARGET else ("railway", "athlete_profiles"))
                assert isinstance(rendered, str)
                if sql == schema._INVENTORY_COLUMNS:
                    assert "LIKE '%DEFAULT_GENERATED%'" in rendered
    finally:
        connection.close()


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
        self.readonly, self.rollbacks, self.rollback_error = False, 0, None

    def cursor(self): return self
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        if self.fail_at and self.fail_at in sql:
            raise RuntimeError("SECRET PASSWORD SQL")
        if sql == "START TRANSACTION READ ONLY":
            self.readonly = True
            self.rows = []
        elif sql == "SELECT DATABASE() AS database_name":
            self.rows = [{"database_name": self.database}]
        elif "information_schema.TABLES" in sql:
            self.rows = [self.tables[params[1]]] if params[1] in self.tables else []
        elif "information_schema.COLUMNS" in sql:
            self.rows = [{"name": key, "kind": kind, "nullable": nullable} for key, (kind, nullable) in self.columns[params[1]].items()]
        elif "information_schema.STATISTICS" in sql:
            self.rows = [{"name": name, "non_unique": unique, "column_name": column} for name, unique, column in self.indexes[params[1]]]
        else:
            assert sql == schema.CREATE_SQL
            assert not self.readonly
            self.created = True
            self.tables["athlete_workspaces"] = {"kind": "BASE TABLE", "engine": "InnoDB"}
            self.rows = []
    def fetchone(self): return deepcopy(self.rows[0]) if self.rows else None
    def fetchall(self): return deepcopy(self.rows)
    def rollback(self):
        self.rollbacks += 1
        if self.rollback_error: raise self.rollback_error
        self.readonly = False
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
    elif defect == "subject": db.columns["athlete_profiles"]["clerk_id"] = ("text", "YES")
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


def inspect(db, environ=None, **ack):
    def connect(**settings):
        db.settings = settings
        return db
    return schema.inspect_schema(environ=ENV if environ is None else environ, connector=connect, **(ack or ACK))


@pytest.mark.parametrize("exists,readiness,selects", [(False, "requires_create", 5), (True, "ready", 8)])
def test_inspection_reads_only_metadata_and_cleans_up_without_creating(exists, readiness, selects):
    db = FakeDB()
    if exists:
        db.tables["athlete_workspaces"] = {"kind": "BASE TABLE", "engine": "InnoDB"}
    result = inspect(db)
    assert result == {"status": "schema_checked", "readiness": readiness,
                      "workspace_contract_checked": exists, "select_attempts": selects,
                      "statement_attempts": selects + 2, "connected": True,
                      "read_only_transaction_started": True, "rollback_completed": True,
                      "connection_closed": True, "ddl_attempts": 0}
    assert db.queries[0] == ("START TRANSACTION READ ONLY", None)
    assert len(db.queries) == selects + 1
    assert all(sql == "SELECT DATABASE() AS database_name" or "FROM information_schema." in sql
               for sql, _ in db.queries[1:])
    assert all(params is None or params in ((db.database, "athlete_profiles"), (db.database, "athlete_workspaces"))
               for _, params in db.queries)
    assert db.closed and db.rollbacks == 1 and not db.created and not db.readonly


@pytest.mark.parametrize("host", ["db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com", "x.rds.amazonaws.com", "pre-prod.example", "family-test.example"])
def test_inspection_forbids_gmtm_and_rds_before_connecting(host):
    db = FakeDB()
    with pytest.raises(schema.PreparationError):
        inspect(db, {**ENV, "AGENT_DB_HOST": host}, expected_host=host, expected_database=ENV["AGENT_DB_NAME"])
    assert db.settings is None and not db.queries and not db.closed and db.rollbacks == 0


@pytest.mark.parametrize("ack", [{"expected_host": "different.example", "expected_database": ENV["AGENT_DB_NAME"]},
                                 {"expected_host": ENV["AGENT_DB_HOST"], "expected_database": "different"}])
def test_inspection_requires_exact_target_acknowledgment(ack):
    db = FakeDB()
    with pytest.raises(schema.PreparationError): inspect(db, **ack)
    assert db.settings is None and not db.queries


def test_inspection_wrong_connected_database_rolls_back_before_other_metadata():
    db = FakeDB()
    db.database = "unexpected"
    with pytest.raises(schema.PreparationError) as caught: inspect(db)
    assert caught.value.report["reason"] == "connected_database_mismatch"
    assert caught.value.report["select_attempts"] == 1
    assert caught.value.report["statement_attempts"] == 3
    assert db.closed and db.rollbacks == 1 and len(db.queries) == 2 and not db.created


@pytest.mark.parametrize("defect", ["missing_link", "link_engine", "link_index", "workspace_engine", "workspace_columns", "workspace_index"])
def test_inspection_incompatible_metadata_refuses_without_repair(defect):
    db = FakeDB()
    db.tables["athlete_workspaces"] = {"kind": "BASE TABLE", "engine": "InnoDB"}
    if defect == "missing_link": del db.tables["athlete_profiles"]
    elif defect == "link_engine": db.tables["athlete_profiles"]["engine"] = "MyISAM"
    elif defect == "link_index": db.indexes["athlete_profiles"] = []
    elif defect == "workspace_engine": db.tables["athlete_workspaces"]["engine"] = "MyISAM"
    elif defect == "workspace_columns": db.columns["athlete_workspaces"]["clerk_id"] = ("varchar(255)", "NO")
    else: db.indexes["athlete_workspaces"] = []
    with pytest.raises(schema.PreparationError) as caught: inspect(db)
    assert caught.value.report["status"] == "failed" and "readiness" not in caught.value.report
    assert caught.value.report["rollback_completed"] and caught.value.report["connection_closed"]
    assert db.rollbacks == 1 and db.closed and not db.created
    assert not any(sql.startswith(("CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE")) for sql, _ in db.queries)


@pytest.mark.parametrize("stage", ["START TRANSACTION", "information_schema.COLUMNS"])
def test_inspection_query_failures_are_counted_redacted_and_cleaned(stage):
    db = FakeDB()
    db.fail_at = stage
    with pytest.raises(schema.PreparationError) as caught: inspect(db)
    result = caught.value.report
    assert result["statement_attempts"] == len(db.queries) + 1
    assert result["select_attempts"] == sum(sql.startswith("SELECT") for sql, _ in db.queries)
    assert "SECRET" not in json.dumps(result)
    assert result["rollback_completed"] and result["connection_closed"] and db.rollbacks == 1


@pytest.mark.parametrize("failures", [(False, True, False), (False, False, True), (True, True, True)])
def test_inspection_cleanup_failures_never_report_ready_or_expose_details(failures):
    query_error, rollback_error, close_error = failures
    db = FakeDB()
    if query_error: db.fail_at = "information_schema.COLUMNS"
    if rollback_error: db.rollback_error = RuntimeError("SECRET ROLLBACK")
    if close_error: db.close_error = RuntimeError("SECRET CLOSE")
    with pytest.raises(schema.PreparationError) as caught: inspect(db)
    result = caught.value.report
    assert result["status"] == "failed" and "readiness" not in result and "SECRET" not in json.dumps(result)
    assert result["rollback_completed"] == (not rollback_error)
    assert result["connection_closed"] == (not close_error)
    assert db.rollbacks == 1 and db.closed  # close was attempted even if rollback failed.
    if query_error:
        assert result["stage"] == "athlete_link_preflight"
        assert result["rollback_error"]["type"] == "RuntimeError"
        assert result["close_error"]["type"] == "RuntimeError"


def test_inspection_rejects_data_queries_before_driver_access(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(schema, "_prerequisite", lambda cursor, database: cursor.execute("SELECT * FROM athlete_profiles"))
    with pytest.raises(schema.PreparationError) as caught: inspect(db)
    assert caught.value.report["reason"] == "inspection_metadata_query_required"
    assert len(db.queries) == 2 and db.rollbacks == 1 and db.closed


def test_inspection_rejects_other_metadata_targets_before_driver_access(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(schema, "_prerequisite", lambda cursor, database: schema._table(cursor, "other_database", "athlete_profiles"))
    with pytest.raises(schema.PreparationError) as caught: inspect(db)
    assert caught.value.report["reason"] == "inspection_metadata_query_required"
    assert len(db.queries) == 2 and db.rollbacks == 1 and db.closed


def test_inspection_connection_failure_has_no_success_flags_or_details():
    def unavailable(**settings):
        raise RuntimeError("SECRET HOST PASSWORD")
    with pytest.raises(schema.PreparationError) as caught:
        schema.inspect_schema(environ=ENV, connector=unavailable, **ACK)
    result = caught.value.report
    assert result["stage"] == "connect" and result["select_attempts"] == result["statement_attempts"] == 0
    assert not any(result[key] for key in ("connected", "read_only_transaction_started", "rollback_completed", "connection_closed"))
    assert "SECRET" not in json.dumps(result) and "readiness" not in result


def test_inspection_caps_metadata_queries_before_driver_access(monkeypatch):
    db = FakeDB()
    db.tables["athlete_workspaces"] = {"kind": "BASE TABLE", "engine": "InnoDB"}
    def excessive(cursor, database):
        for _ in range(9): cursor.execute("SELECT DATABASE() AS database_name")
    monkeypatch.setattr(schema, "_workspace", excessive)
    with pytest.raises(schema.PreparationError) as caught: inspect(db)
    assert caught.value.report["reason"] == "inspection_query_budget_exhausted"
    assert caught.value.report["select_attempts"] == 8 and caught.value.report["statement_attempts"] == 10
    assert len(db.queries) == 9 and db.rollbacks == 1 and db.closed


def test_check_cli_uses_metadata_inspection_not_apply(capsys):
    db = FakeDB()
    args = ["--check", "--expected-host", ACK["expected_host"], "--expected-database", ACK["expected_database"]]
    assert schema.main(args, environ=ENV, connector=lambda **_: db) == 0
    assert json.loads(capsys.readouterr().out)["readiness"] == "requires_create"
    assert db.closed and not db.created


def test_check_and_apply_are_mutually_exclusive_before_configuration(capsys):
    class NoReads(dict):
        def get(self, *_): raise AssertionError("No configuration")
    with pytest.raises(SystemExit) as caught:
        schema.main(["--check", "--apply"], environ=NoReads(), connector=lambda **_: (_ for _ in ()).throw(AssertionError("No connect")))
    assert caught.value.code == 2


@pytest.mark.parametrize("missing", ["id", "user_id", "clerk_id"])
def test_inspection_identifies_only_known_missing_columns_without_raw_metadata(missing):
    db = FakeDB()
    db.columns["athlete_profiles"].pop(missing)
    db.columns["athlete_profiles"]["PRIVATE_SCHEMA_CANARY"] = ("varchar(100)", "YES")
    with pytest.raises(schema.PreparationError) as caught:
        inspect(db)
    report = caught.value.report
    assert report["reason"] == "existing_athlete_link_columns_required"
    assert report["required_link_columns"] == {name: name != missing for name in ("id", "user_id", "clerk_id")}
    assert report["select_attempts"] == 3 and report["statement_attempts"] == 5
    assert db.rollbacks == 1 and db.closed and not db.created
    assert "PRIVATE_SCHEMA_CANARY" not in json.dumps(report)


class InventoryDB(FakeDB):
    def __init__(self):
        super().__init__()
        self.columns["athlete_profiles"].pop("id")
        self.columns["athlete_profiles"]["created_at"] = ("timestamp(6)", "NO")
        self.indexes["athlete_profiles"] = [("PRIMARY", 0, "user_id"), ("idx_clerk", 1, "clerk_id")]
        self.server_version = "8.4.6"

    def execute(self, sql, params=None):
        if sql not in schema._INVENTORY_SELECTS:
            return super().execute(sql, params)
        self.queries.append((sql, params))
        if self.fail_at and self.fail_at in sql:
            raise RuntimeError("SECRET INVENTORY ERROR")
        if sql == schema._INVENTORY_TARGET:
            self.rows = [{"database_name": self.database, "server_version": self.server_version}]
        elif sql == schema._INVENTORY_TABLE:
            self.rows = [{**self.tables[params[1]], "row_count_estimate": 7, "data_bytes_estimate": 16384,
                          "index_bytes_estimate": 16384}] if params[1] in self.tables else []
        elif params[1] not in self.tables:
            self.rows = []
        elif sql == schema._INVENTORY_COLUMNS:
            self.rows = [{"ordinal": i, "name": key, "kind": kind, "nullable": nullable,
                          "collation": "utf8mb4_0900_ai_ci" if key == "clerk_id" else None,
                          "default_class": "current_timestamp" if key == "created_at" else "null_or_unspecified",
                          "extra": "DEFAULT_GENERATED" if key == "created_at" else ""}
                         for i, (key, (kind, nullable)) in enumerate(self.columns[params[1]].items(), 1)]
        else:
            sequence = {}
            self.rows = []
            for name, non_unique, column in self.indexes[params[1]]:
                sequence[name] = sequence.get(name, 0) + 1
                self.rows.append({"name": name, "non_unique": non_unique, "column_name": column,
                                  "sequence": sequence[name], "prefix_length": None, "ordering": "A", "kind": "BTREE"})


def inventory(db=None):
    db = db or InventoryDB()
    return schema.inventory_schema(environ=ENV, connector=lambda **_: db, **ACK)


@pytest.mark.parametrize("workspace_exists", [False, True])
def test_inventory_collects_both_tables_without_requiring_link_id(workspace_exists):
    db = InventoryDB()
    if workspace_exists: db.tables["athlete_workspaces"] = {"kind": "BASE TABLE", "engine": "InnoDB"}
    value = inventory(db)
    assert value["status"] == "schema_inventory" and value["server_version"] == "8.4.6"
    assert value["select_attempts"] == 7 and value["statement_attempts"] == 9 and value["ddl_attempts"] == 0
    assert value["tables"]["athlete_workspaces"]["exists"] is workspace_exists
    columns = value["tables"]["athlete_profiles"]["columns"]
    assert [row["name"] for row in columns] == ["user_id", "clerk_id", "created_at"]
    assert columns[-1]["kind"] == "timestamp(6)" and columns[-1]["default_class"] == "current_timestamp"
    assert columns[1]["collation"] == "utf8mb4_0900_ai_ci"
    assert value["tables"]["athlete_profiles"]["row_count_estimate"] == 7
    assert len(db.queries) == 8 and db.queries[0][0] == "START TRANSACTION READ ONLY"
    assert all(sql in schema._INVENTORY_SELECTS for sql, _ in db.queries[1:])
    assert db.rollbacks == 1 and db.closed and not db.created


@pytest.mark.parametrize("defect", ["wrong_database", "bad_version", "query", "rollback", "close", "overflow"])
def test_inventory_failures_are_redacted_and_cleanup_is_attempted(defect):
    db = InventoryDB()
    if defect == "wrong_database": db.database = "other"
    elif defect == "bad_version": db.server_version = "SECRET VERSION"
    elif defect == "query": db.fail_at = "information_schema.COLUMNS"
    elif defect == "rollback": db.rollback_error = RuntimeError("SECRET ROLLBACK")
    elif defect == "close": db.close_error = RuntimeError("SECRET CLOSE")
    else:
        db.columns["athlete_profiles"] = {f"c{i}": ("int", "NO") for i in range(65)}
    with pytest.raises(schema.PreparationError) as caught: inventory(db)
    assert "SECRET" not in str(caught.value) and db.closed and db.rollbacks == 1
    assert not db.created and len(db.queries) <= 8


@pytest.mark.parametrize("field,bad", [("kind", "enum('SECRET DEFAULT')"), ("default_class", "SECRET DEFAULT"),
                                      ("extra", "SECRET EXTRA"), ("collation", "bad collation"), ("ordinal", True)])
def test_inventory_schema_validator_rejects_unbounded_column_values(field, bad):
    value = inventory()
    value["tables"]["athlete_profiles"]["columns"][0][field] = bad
    with pytest.raises(schema.PreparationError): schema.validate_inventory_response(value)


@pytest.mark.parametrize("field,bad", [("prefix_length", -1), ("sequence", 2), ("non_unique", True),
                                      ("ordering", "SECRET"), ("column_name", "missing_column")])
def test_inventory_schema_validator_rejects_invalid_index_evidence(field, bad):
    value = inventory()
    value["tables"]["athlete_profiles"]["indexes"][0][field] = bad
    with pytest.raises(schema.PreparationError): schema.validate_inventory_response(value)


def test_inventory_cli_and_exclusive_modes(capsys):
    db = InventoryDB()
    args = ["--inventory", "--expected-host", ACK["expected_host"], "--expected-database", ACK["expected_database"]]
    assert schema.main(args, environ=ENV, connector=lambda **_: db) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "schema_inventory"
    for second in ("--check", "--apply"):
        with pytest.raises(SystemExit) as caught: schema.main(["--inventory", second], environ={})
        assert caught.value.code == 2
