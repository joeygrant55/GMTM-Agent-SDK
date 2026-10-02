"""Offline preparation contract: fake connector, no schema or network access."""
import json

import pytest

import prepare_agent_schema as schema


ENV = {
    "AGENT_DB_HOST": "127.0.0.1", "AGENT_DB_PORT": "3307",
    "AGENT_DB_USER": "agent_schema_test", "AGENT_DB_PASSWORD": "synthetic-password-do-not-log",
    "AGENT_DB_NAME": "sparq_isolated",
}
ACK = {"expected_host": ENV["AGENT_DB_HOST"], "expected_database": ENV["AGENT_DB_NAME"]}


class DriverError(Exception):
    pass


class FakeConnection:
    def __init__(self, *, database="sparq_isolated", table_type="BASE TABLE", columns=None,
                 indexes=None, failures=None, close_error=None):
        self.database = database
        self.table_type = table_type
        self.columns = schema.CONVERSATION_COLUMNS if columns is None else columns
        self.indexes = indexes if indexes is not None else [
            {"index_name": "PRIMARY", "non_unique": 0, "column_name": "id"},
            {"index_name": "idx_clerk", "non_unique": 1, "column_name": "clerk_id"},
        ]
        self.failures = failures or {}
        self.close_error = close_error
        self.queries = []
        self.closed = False
        self.params = None
        self.rows = []

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        for prefix, error in self.failures.items():
            if sql.startswith(prefix):
                raise error
        if sql == "SELECT DATABASE() AS database_name":
            self.rows = [{"database_name": self.database}]
        elif "information_schema.TABLES" in sql:
            self.rows = [{"table_type": self.table_type}] if self.table_type else []
        elif "information_schema.COLUMNS" in sql:
            self.rows = [{"column_name": col} for col in self.columns]
        elif "information_schema.STATISTICS" in sql:
            self.rows = self.indexes
        else:
            assert sql.startswith(("CREATE TABLE IF NOT EXISTS", "ALTER TABLE"))
            assert "agent_conversations" not in sql
            self.rows = []

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True
        if self.close_error:
            raise self.close_error

    @property
    def ddl(self):
        return [sql for sql, _ in self.queries if sql.startswith(("CREATE", "ALTER"))]


def run(db, *, environ=None, **ack):
    def connector(**settings):
        db.params = settings
        return db
    return schema.prepare_schema(environ=ENV if environ is None else environ,
                                 connector=connector, **(ack or ACK))


def forbid_connect(**_):
    raise AssertionError("No connection should be attempted")


def test_default_command_is_a_plan_without_configuration_or_connection(capsys):
    class NoReads(dict):
        def get(self, *_):
            raise AssertionError("Dry run must not read environment")
    assert schema.main([], environ=NoReads(), connector=forbid_connect) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "dry_run"
    assert report["connected"] is False
    assert report["ddl_is_atomic"] is False
    assert len(report["statements"]) == 21


@pytest.mark.parametrize("suffix", ["HOST", "PORT", "USER", "PASSWORD", "NAME"])
@pytest.mark.parametrize("value", [None, ""])
def test_requires_each_explicit_agent_setting_without_source_fallback(suffix, value):
    env = {**ENV, "DB_HOST": "127.0.0.1", "DB_PORT": "3307", "DB_USER": "x", "DB_PASSWORD": "y", "DB_NAME": "sparq_isolated"}
    if value is None:
        del env[f"AGENT_DB_{suffix}"]
    else:
        env[f"AGENT_DB_{suffix}"] = value
    with pytest.raises(schema.PreparationError) as caught:
        schema.prepare_schema(environ=env, connector=forbid_connect, **ACK)
    assert caught.value.report["reason"] == f"explicit_agent_db_{suffix.lower()}_required"


@pytest.mark.parametrize("host", ["db2-dev", "pre-prod", "family-test", "x.abc.us-east-1.rds.amazonaws.com", "x.abc.cn-north-1.rds.amazonaws.com.cn", "GMTM.internal"])
def test_rejects_gmtm_and_rds_hosts_even_when_acknowledged(host):
    with pytest.raises(schema.PreparationError, match="gmtm_or_rds_target_forbidden"):
        schema.prepare_schema(environ={**ENV, "AGENT_DB_HOST": host},
                              expected_host=host, expected_database=ENV["AGENT_DB_NAME"],
                              connector=forbid_connect)


@pytest.mark.parametrize("database", ["gmtm", "gmtm_development", "pre_prod", "family-test", "db2-dev"])
def test_rejects_gmtm_named_databases_even_when_acknowledged(database):
    with pytest.raises(schema.PreparationError, match="gmtm_or_rds_target_forbidden"):
        schema.prepare_schema(environ={**ENV, "AGENT_DB_NAME": database},
                              expected_host=ENV["AGENT_DB_HOST"], expected_database=database,
                              connector=forbid_connect)


@pytest.mark.parametrize("host", ["mysql://127.0.0.1", "127.0.0.1:3307", "/tmp/mysql.sock", "127.0.0.1 "])
def test_rejects_ambiguous_host_syntax(host):
    with pytest.raises(schema.PreparationError):
        schema.prepare_schema(environ={**ENV, "AGENT_DB_HOST": host},
                              expected_host=host, expected_database=ENV["AGENT_DB_NAME"],
                              connector=forbid_connect)


@pytest.mark.parametrize("port", ["0", "65536", "-1", "3307 ", "３３０７", "1e3", "999999999"])
def test_invalid_ports_do_not_connect(port):
    with pytest.raises(schema.PreparationError):
        schema.prepare_schema(environ={**ENV, "AGENT_DB_PORT": port}, connector=forbid_connect, **ACK)


@pytest.mark.parametrize("ack", [
    {"expected_host": None, "expected_database": "sparq_isolated"},
    {"expected_host": "127.0.0.1", "expected_database": None},
    {"expected_host": "localhost", "expected_database": "sparq_isolated"},
    {"expected_host": "127.0.0.1", "expected_database": "other"},
])
def test_apply_requires_both_exact_target_acknowledgments(ack):
    with pytest.raises(schema.PreparationError, match="target_acknowledgment_mismatch"):
        schema.prepare_schema(environ=ENV, connector=forbid_connect, **ack)


@pytest.mark.parametrize("kwargs,reason", [
    ({"database": "unexpected"}, "connected_database_mismatch"),
    ({"table_type": None}, "existing_conversation_table_required"),
    ({"table_type": "VIEW"}, "existing_conversation_table_required"),
    ({"columns": {"id", "clerk_id"}}, "existing_conversation_columns_required"),
    ({"indexes": [{"index_name": "arbitrary_name", "non_unique": 0, "column_name": "clerk_id"}]},
     "unique_conversation_owner_index_incompatible_with_forks"),
])
def test_missing_or_incompatible_conversation_baseline_fails_before_any_ddl(kwargs, reason):
    db = FakeConnection(**kwargs)
    with pytest.raises(schema.PreparationError) as caught:
        run(db)
    assert caught.value.report["reason"] == reason
    assert caught.value.report["stage"] == "conversation_preflight"
    assert caught.value.report["completed_statements"] == []
    assert db.ddl == []
    assert db.closed


def test_success_keeps_original_definitions_and_orders_preflight_before_ddl():
    db = FakeConnection()
    result = run(db)
    assert result["status"] == "preparation_applied"
    assert result["conversation_prerequisites"] == "passed"
    assert result["ddl_is_atomic"] is False
    assert result["full_schema_validated"] is False
    assert db.closed
    assert db.params == {
        "host": "127.0.0.1", "port": 3307, "user": ENV["AGENT_DB_USER"],
        "password": ENV["AGENT_DB_PASSWORD"], "database": "sparq_isolated",
        "connect_timeout": 5, "read_timeout": 10, "write_timeout": 10, "autocommit": True,
    }
    assert all(sql.startswith("SELECT") for sql, _ in db.queries[:4])
    assert all(params == ("sparq_isolated", "agent_conversations") for _, params in db.queries[1:4])
    assert db.ddl == [sql for _, sql, _ in schema.STATEMENTS]
    created = [sql.split()[5] for sql in db.ddl if sql.startswith("CREATE")]
    assert set(created) == {
        "sparq_profiles", "college_targets", "agent_sessions", "outreach_log",
        "agent_messages", "athlete_profiles", "athlete_links", "agent_reports",
        "artifacts", "artifact_actions", "claim_tokens",
        "sparq_entry_refusals", "sparq_entries", "sparq_parent_notices", "sparq_sessions", "sparq_college_lists",
            "sparq_saved_colleges", "sparq_sent_emails",
    }
    assert not any("ALTER TABLE agent_conversations" in sql for sql in db.ddl)
    assert len([sql for sql in db.ddl if sql.startswith("ALTER")]) == 3


def test_composite_unique_index_does_not_mean_one_conversation_per_subject():
    db = FakeConnection(indexes=[
        {"index_name": "composite", "non_unique": 0, "column_name": "clerk_id"},
        {"index_name": "composite", "non_unique": 0, "column_name": "id"},
    ])
    assert run(db)["status"] == "preparation_applied"


def test_duplicate_columns_only_are_expected_idempotent_results():
    db = FakeConnection(failures={"ALTER TABLE": DriverError(1060, ENV["AGENT_DB_PASSWORD"])})
    report = run(db)
    assert len(report["completed_statements"]) == 21
    assert len(report["duplicate_columns"]) == 3
    assert ENV["AGENT_DB_PASSWORD"] not in json.dumps(report)
    assert db.closed


@pytest.mark.parametrize("code", [1062, 1061, 1146, 1142, 2003])
def test_unexpected_alter_errors_stop_and_report_partial_nonatomic_progress(code):
    db = FakeConnection(failures={"ALTER TABLE": DriverError(code, ENV["AGENT_DB_PASSWORD"])})
    with pytest.raises(schema.PreparationError) as caught:
        run(db)
    report = caught.value.report
    assert report["stage"] == "add_sparq_profiles_enrichment_complete"
    assert report["error"] == {"type": "DriverError", "mysql_code": code}
    assert len(report["completed_statements"]) == 4
    assert len(db.ddl) == 5  # No later DDL after the first failed statement.
    assert report["ddl_is_atomic"] is False
    assert ENV["AGENT_DB_PASSWORD"] not in str(caught.value)
    assert db.closed


def test_duplicate_column_code_is_not_swallowed_on_create():
    db = FakeConnection(failures={"CREATE TABLE": DriverError(1060, "synthetic sensitive detail")})
    with pytest.raises(schema.PreparationError) as caught:
        run(db)
    assert caught.value.report["completed_statements"] == []
    assert caught.value.report["duplicate_columns"] == []
    assert db.closed


def test_connection_error_is_redacted_and_nonzero(capsys):
    def unavailable(**_):
        raise DriverError(1045, "sensitive connection details " + ENV["AGENT_DB_PASSWORD"])
    assert schema.main(["--apply", "--expected-host", "127.0.0.1", "--expected-database", "sparq_isolated"],
                       environ=ENV, connector=unavailable) == 1
    output = capsys.readouterr()
    report = json.loads(output.out)
    assert report["stage"] == "connect"
    assert report["error"] == {"type": "DriverError", "mysql_code": 1045}
    assert ENV["AGENT_DB_PASSWORD"] not in output.out + output.err
    assert "sensitive connection details" not in output.out + output.err


def test_cli_requires_ack_and_returns_nonzero_without_connecting(capsys):
    assert schema.main(["--apply"], environ=ENV, connector=forbid_connect) == 1
    assert json.loads(capsys.readouterr().out)["reason"] == "target_acknowledgment_mismatch"


def test_close_failure_is_not_reported_as_success():
    db = FakeConnection(close_error=DriverError(2013, ENV["AGENT_DB_PASSWORD"]))
    with pytest.raises(schema.PreparationError) as caught:
        run(db)
    assert caught.value.report["stage"] == "close"
    assert len(caught.value.report["completed_statements"]) == 21
    assert ENV["AGENT_DB_PASSWORD"] not in str(caught.value)


def test_close_failure_does_not_hide_original_preflight_failure():
    db = FakeConnection(table_type=None, close_error=DriverError(2013, ENV["AGENT_DB_PASSWORD"]))
    with pytest.raises(schema.PreparationError) as caught:
        run(db)
    assert caught.value.report["reason"] == "existing_conversation_table_required"
    assert caught.value.report["close_error"] == {"type": "DriverError", "mysql_code": 2013}
    assert db.ddl == []


def test_junior_pilot_tables_match_their_module_schema():
    import college_programs
    import junior_entry
    ddl = {sql for _, sql, _ in schema.STATEMENTS}
    assert set(junior_entry.SCHEMA) | set(college_programs.SCHEMA) <= ddl
    names = [sql.split()[5] for sql in junior_entry.SCHEMA + college_programs.SCHEMA]
    assert names == ["sparq_entry_refusals", "sparq_entries", "sparq_parent_notices", "sparq_sessions", "sparq_college_lists", "sparq_saved_colleges", "sparq_sent_emails"]
