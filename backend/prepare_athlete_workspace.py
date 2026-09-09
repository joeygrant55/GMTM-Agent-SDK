"""Explicit one-table Agent workspace preparation; no startup/schema side effects.

Default invocation prints a plan without reading configuration or connecting.
Check inspects only target metadata inside a read-only transaction.
Apply reuses the existing exact Agent-target guards. DDL is not transactional.
Existing tables must match the checked storage contract; no ALTER/repair occurs.
"""
from __future__ import annotations

import argparse
import json
import os

from prepare_agent_schema import PreparationError, connection_settings, _default_connector, _error_summary


CREATE_SQL = """CREATE TABLE IF NOT EXISTS athlete_workspaces (
    clerk_id VARBINARY(255) NOT NULL PRIMARY KEY,
    athlete_link_id BIGINT UNSIGNED NOT NULL,
    gmtm_user_id BIGINT UNSIGNED NOT NULL,
    version INT UNSIGNED NOT NULL,
    payload JSON NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL
) ENGINE=InnoDB"""
WORKSPACE_COLUMNS = {
    "clerk_id": ("varbinary(255)", "NO"), "athlete_link_id": ("bigint unsigned", "NO"),
    "gmtm_user_id": ("bigint unsigned", "NO"), "version": ("int unsigned", "NO"),
    "payload": ("json", "NO"), "created_at": ("datetime(6)", "NO"), "updated_at": ("datetime(6)", "NO"),
}


def _guard(reason):
    return PreparationError({"status": "failed", "reason": reason})


def _columns(cursor, database, table):
    cursor.execute("SELECT COLUMN_NAME AS name, COLUMN_TYPE AS kind, IS_NULLABLE AS nullable FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s", (database, table))
    rows = cursor.fetchall()
    result = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("name") in result:
            raise _guard("column_metadata_invalid")
        result[row.get("name")] = (row.get("kind"), row.get("nullable"))
    return result


def _table(cursor, database, table):
    cursor.execute("SELECT TABLE_TYPE AS kind, ENGINE AS engine FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s", (database, table))
    rows = cursor.fetchall()
    if not rows:
        return False
    if len(rows) != 1 or rows[0] != {"kind": "BASE TABLE", "engine": "InnoDB"}:
        raise _guard("transactional_base_table_required")
    return True


def _indexes(cursor, database, table):
    cursor.execute("SELECT INDEX_NAME AS name, NON_UNIQUE AS non_unique, COLUMN_NAME AS column_name FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY INDEX_NAME, SEQ_IN_INDEX", (database, table))
    indexes = {}
    for row in cursor.fetchall():
        if not isinstance(row, dict) or type(row.get("non_unique")) is not int:
            raise _guard("index_metadata_invalid")
        key = (row.get("name"), row["non_unique"])
        indexes.setdefault(key, []).append(row.get("column_name"))
    return indexes


def _prerequisite(cursor, database):
    if not _table(cursor, database, "athlete_profiles"):
        raise _guard("existing_athlete_link_table_required")
    columns = _columns(cursor, database, "athlete_profiles")
    if not {"id", "user_id", "clerk_id"} <= set(columns):
        raise _guard("existing_athlete_link_columns_required")
    for key in ("id", "user_id"):
        kind, nullable = columns[key]
        # The existing preparation uses signed INT; tolerate MySQL display
        # widths without weakening the requirement for integer identities.
        import re
        if nullable != "NO" or not isinstance(kind, str) or not re.fullmatch(r"(?:int|bigint)(?:\([0-9]+\))?(?: unsigned)?", kind):
            raise _guard("existing_athlete_link_identity_types_required")
    if columns["clerk_id"] != ("varchar(255)", "NO"):
        raise _guard("existing_athlete_link_subject_type_required")
    indexes = _indexes(cursor, database, "athlete_profiles")
    if (indexes.get(("PRIMARY", 0)) != ["id"]
            or not any(unique == 0 and values == ["user_id"] for (_, unique), values in indexes.items())
            or not any(values and values[0] == "clerk_id" for values in indexes.values())):
        raise _guard("existing_athlete_link_indexes_required")


def _workspace(cursor, database):
    if not _table(cursor, database, "athlete_workspaces"):
        raise _guard("workspace_table_missing_after_apply")
    columns = _columns(cursor, database, "athlete_workspaces")
    # MySQL 5.7 includes integer display widths, 8.x may omit them.
    import re
    columns = {name: (re.sub(r"\((?:10|11|20)\)(?= unsigned$)", "", kind) if isinstance(kind, str) else kind, nullable)
               for name, (kind, nullable) in columns.items()}
    if columns != WORKSPACE_COLUMNS:
        raise _guard("workspace_column_contract_mismatch")
    indexes = _indexes(cursor, database, "athlete_workspaces")
    if indexes != {("PRIMARY", 0): ["clerk_id"]}:
        raise _guard("workspace_index_contract_mismatch")


_METADATA_SELECTS = frozenset({
    "SELECT DATABASE() AS database_name",
    "SELECT TABLE_TYPE AS kind, ENGINE AS engine FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
    "SELECT COLUMN_NAME AS name, COLUMN_TYPE AS kind, IS_NULLABLE AS nullable FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
    "SELECT INDEX_NAME AS name, NON_UNIQUE AS non_unique, COLUMN_NAME AS column_name FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY INDEX_NAME, SEQ_IN_INDEX",
})


class _MetadataCursor:
    """Restrict inspection to the existing exact metadata helpers and budget."""
    def __init__(self, cursor, database, counts):
        self.cursor, self.database, self.counts = cursor, database, counts
        self.required_link_columns = None
        self.last_query = None

    def execute(self, sql, params=None):
        permitted_params = (params is None if sql == "SELECT DATABASE() AS database_name"
                            else params in ((self.database, "athlete_profiles"), (self.database, "athlete_workspaces")))
        if sql not in _METADATA_SELECTS or not permitted_params:
            raise _guard("inspection_metadata_query_required")
        if self.counts["select_attempts"] >= 8:
            raise _guard("inspection_query_budget_exhausted")
        self.counts["select_attempts"] += 1
        self.counts["statement_attempts"] += 1
        self.last_query = (sql, params)
        return self.cursor.execute(sql, params)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        rows = self.cursor.fetchall()
        if self.last_query and "information_schema.COLUMNS" in self.last_query[0] and self.last_query[1] == (self.database, "athlete_profiles"):
            names = {row.get("name") for row in rows if isinstance(row, dict) and isinstance(row.get("name"), str)}
            self.required_link_columns = {key: key in names for key in ("id", "user_id", "clerk_id")}
        return rows


def inspect_schema(*, environ, expected_host, expected_database, connector=None):
    """Read metadata only; readiness is an observation, never authority to apply.

    Five SELECTs cover a missing workspace; eight check an existing workspace.
    Counts reserve before each driver attempt, including transaction start and
    rollback. MySQL metadata can change after inspection; apply rechecks it.
    """
    settings = connection_settings(environ, expected_host=expected_host, expected_database=expected_database)
    db, failure, workspace_exists, cursor = None, None, False, None
    started = rolled_back = closed = False
    counts = {"select_attempts": 0, "statement_attempts": 0}
    stage = "connect"
    try:
        db = (connector or _default_connector)(**settings)
        with db.cursor() as raw_cursor:
            stage = "start_readonly_transaction"
            counts["statement_attempts"] += 1
            raw_cursor.execute("START TRANSACTION READ ONLY")
            started = True
            cursor = _MetadataCursor(raw_cursor, settings["database"], counts)
            stage = "target_preflight"
            cursor.execute("SELECT DATABASE() AS database_name")
            if cursor.fetchone() != {"database_name": settings["database"]}:
                raise _guard("connected_database_mismatch")
            stage = "athlete_link_preflight"
            _prerequisite(cursor, settings["database"])
            stage = "existing_workspace_preflight"
            workspace_exists = _table(cursor, settings["database"], "athlete_workspaces")
            if workspace_exists:
                _workspace(cursor, settings["database"])
    except PreparationError as exc:
        failure = {**exc.report, "stage": stage}
        if cursor is not None and cursor.required_link_columns is not None:
            failure["required_link_columns"] = cursor.required_link_columns
    except Exception as exc:
        failure = {"status": "failed", "stage": stage, "error": _error_summary(exc)}
    finally:
        if db is not None:
            try:
                counts["statement_attempts"] += 1
                db.rollback()
                rolled_back = True
            except Exception as exc:
                if failure is None:
                    failure = {"status": "failed", "stage": "rollback", "error": _error_summary(exc)}
                else:
                    failure["rollback_error"] = _error_summary(exc)
            finally:
                try:
                    db.close()
                    closed = True
                except Exception as exc:
                    if failure is None:
                        failure = {"status": "failed", "stage": "close", "error": _error_summary(exc)}
                    else:
                        failure["close_error"] = _error_summary(exc)
    common = {**counts, "connected": db is not None, "read_only_transaction_started": started,
              "rollback_completed": rolled_back, "connection_closed": closed, "ddl_attempts": 0}
    if failure:
        raise PreparationError({**failure, **common}) from None
    return {"status": "schema_checked", "readiness": "ready" if workspace_exists else "requires_create",
            "workspace_contract_checked": workspace_exists, **common}


def prepare_schema(*, environ, expected_host, expected_database, connector=None):
    settings = connection_settings(environ, expected_host=expected_host, expected_database=expected_database)
    db, failure, completed = None, None, False
    stage = "connect"
    try:
        db = (connector or _default_connector)(**settings)
        with db.cursor() as cursor:
            stage = "target_preflight"
            cursor.execute("SELECT DATABASE() AS database_name")
            if cursor.fetchone() != {"database_name": settings["database"]}:
                raise _guard("connected_database_mismatch")
            stage = "athlete_link_preflight"
            _prerequisite(cursor, settings["database"])
            stage = "existing_workspace_preflight"
            if _table(cursor, settings["database"], "athlete_workspaces"):
                _workspace(cursor, settings["database"])
            stage = "create_athlete_workspaces"
            cursor.execute(CREATE_SQL)
            completed = True
            stage = "workspace_postflight"
            _workspace(cursor, settings["database"])
    except PreparationError as exc:
        failure = {**exc.report, "stage": stage}
    except Exception as exc:
        failure = {"status": "failed", "stage": stage, "error": _error_summary(exc)}
    finally:
        if db is not None:
            try:
                db.close()
            except Exception as exc:
                if failure is None:
                    failure = {"status": "failed", "stage": "close", "error": _error_summary(exc)}
                else:
                    failure["close_error"] = _error_summary(exc)
    common = {"ddl_is_atomic": False, "completed_statements": ["create_athlete_workspaces"] if completed else []}
    if failure:
        raise PreparationError({**failure, **common}) from None
    return {"status": "preparation_applied", "workspace_contract_checked": True, **common}


def plan():
    return {"status": "dry_run", "connected": False, "ddl_is_atomic": False,
            "statements": ["create_athlete_workspaces"],
            "prerequisite": "Existing transactional athlete_profiles with exact identity/index prerequisites; existing workspace is never repaired."}


def main(argv=None, *, environ=None, connector=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--check", action="store_true")
    parser.add_argument("--expected-host")
    parser.add_argument("--expected-database")
    args = parser.parse_args(argv)
    if not args.apply and not args.check:
        print(json.dumps(plan(), sort_keys=True))
        return 0
    try:
        operation = inspect_schema if args.check else prepare_schema
        result = operation(environ=os.environ if environ is None else environ,
                           expected_host=args.expected_host, expected_database=args.expected_database, connector=connector)
    except PreparationError as exc:
        print(json.dumps(exc.report, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
