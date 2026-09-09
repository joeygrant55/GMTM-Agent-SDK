"""Explicit one-table Agent workspace preparation; no startup/schema side effects.

Default invocation prints a plan without reading configuration or connecting.
Check inspects only target metadata inside a read-only transaction.
Inventory independently describes both tables without requiring compatibility.
Apply reuses the existing exact Agent-target guards. DDL is not transactional.
Existing tables must match the checked storage contract; no ALTER/repair occurs.
"""
from __future__ import annotations

import argparse
import json
import os
import re

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
    # The live legacy link table uses nullable VARCHAR(100); NULL means no
    # current owner. Runtime resolution still requires one exact non-null Clerk
    # subject in both directions before reading or writing any workspace.
    if columns["clerk_id"] not in {(f"varchar({width})", nullable) for width in (100, 255) for nullable in ("YES", "NO")}:
        raise _guard("existing_athlete_link_subject_type_required")
    indexes = _indexes(cursor, database, "athlete_profiles")
    # Retain the legacy PRIMARY(user_id). A separate exact UNIQUE(id) provides
    # the same link-row identity guarantee as the newer PRIMARY(id) layout.
    if (not any(unique == 0 and values == ["id"] for (_, unique), values in indexes.items())
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
_INVENTORY_TARGET = "SELECT DATABASE() AS database_name, VERSION() AS server_version"
_INVENTORY_TABLE = "SELECT TABLE_TYPE AS kind, ENGINE AS engine, TABLE_ROWS AS row_count_estimate, DATA_LENGTH AS data_bytes_estimate, INDEX_LENGTH AS index_bytes_estimate FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s LIMIT 2"
_INVENTORY_COLUMNS = """SELECT ORDINAL_POSITION AS ordinal, COLUMN_NAME AS name,
    CASE WHEN DATA_TYPE IN ('enum','set') THEN DATA_TYPE ELSE COLUMN_TYPE END AS kind,
    IS_NULLABLE AS nullable, COLLATION_NAME AS collation,
    CASE WHEN COLUMN_DEFAULT IS NULL THEN 'null_or_unspecified'
         WHEN LOWER(COLUMN_DEFAULT) REGEXP '^current_timestamp([(][0-6]?[)])?$' THEN 'current_timestamp'
         WHEN EXTRA LIKE '%%DEFAULT_GENERATED%%' THEN 'expression' ELSE 'literal' END AS default_class,
    EXTRA AS extra FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY ORDINAL_POSITION LIMIT 65"""
_INVENTORY_INDEXES = """SELECT INDEX_NAME AS name, NON_UNIQUE AS non_unique,
    COLUMN_NAME AS column_name, SEQ_IN_INDEX AS sequence, SUB_PART AS prefix_length,
    COLLATION AS ordering, INDEX_TYPE AS kind FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY INDEX_NAME, SEQ_IN_INDEX LIMIT 257"""
_INVENTORY_SELECTS = frozenset({_INVENTORY_TARGET, _INVENTORY_TABLE, _INVENTORY_COLUMNS, _INVENTORY_INDEXES})
_INVENTORY_TABLE_NAMES = ("athlete_profiles", "athlete_workspaces")
_SCHEMA_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_$]{0,63}\Z")
_COLUMN_TYPE = re.compile(r"(?:tinyint|smallint|mediumint|int|integer|bigint|bit|decimal|numeric|float|double|real|char|varchar|binary|varbinary|tinyblob|blob|mediumblob|longblob|tinytext|text|mediumtext|longtext|enum|set|date|datetime|timestamp|time|year|json|geometry|point|linestring|polygon|multipoint|multilinestring|multipolygon|geometrycollection)(?:\([0-9]{1,8}(?:,[0-9]{1,3})?\))?(?: unsigned)?(?: zerofill)?\Z")
_EXTRA_PART = r"(?:auto_increment|default_generated|stored generated|virtual generated|on update current_timestamp(?:\([0-6]\))?|invisible)"
_COLUMN_EXTRA = re.compile(rf"(?:{_EXTRA_PART}(?: {_EXTRA_PART})*)?\Z", re.I)
_SERVER_VERSION = re.compile(r"[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,3}(?:[-.+][A-Za-z0-9_-]{1,32}){0,3}\Z")
_TABLE_ESTIMATES = {"row_count_estimate", "data_bytes_estimate", "index_bytes_estimate"}


def _inventory_invalid():
    return _guard("inventory_metadata_invalid")


def validate_inventory_tables(tables):
    """Pure schema-only shape check, also used before parent receipt retention."""
    def named(value):
        return isinstance(value, str) and _SCHEMA_NAME.fullmatch(value) is not None
    if not isinstance(tables, dict) or set(tables) != set(_INVENTORY_TABLE_NAMES):
        raise _inventory_invalid()
    for table in tables.values():
        if (not isinstance(table, dict) or set(table) != {"exists", "kind", "engine", "columns", "indexes"} | _TABLE_ESTIMATES
                or type(table["exists"]) is not bool or not isinstance(table["columns"], list)
                or not isinstance(table["indexes"], list) or len(table["columns"]) > 64 or len(table["indexes"]) > 256):
            raise _inventory_invalid()
        if not table["exists"]:
            if table != {"exists": False, "kind": None, "engine": None, "columns": [], "indexes": [], **dict.fromkeys(_TABLE_ESTIMATES)}:
                raise _inventory_invalid()
            continue
        if (table["kind"] not in ("BASE TABLE", "VIEW", "SYSTEM VIEW") or not table["columns"]
                or (table["engine"] is not None and not named(table["engine"]))
                or (table["kind"] == "BASE TABLE" and table["engine"] is None)):
            raise _inventory_invalid()
        if any(table[key] is not None and (type(table[key]) is not int or not 0 <= table[key] <= 2**63 - 1) for key in _TABLE_ESTIMATES):
            raise _inventory_invalid()
        names = set()
        for ordinal, column in enumerate(table["columns"], 1):
            if (not isinstance(column, dict) or set(column) != {"ordinal", "name", "kind", "nullable", "collation", "default_class", "extra"}
                    or type(column["ordinal"]) is not int or column["ordinal"] != ordinal or not named(column["name"])
                    or column["name"] in names or not isinstance(column["kind"], str) or not _COLUMN_TYPE.fullmatch(column["kind"])
                    or column["nullable"] not in ("YES", "NO") or (column["collation"] is not None and not named(column["collation"]))
                    or column["default_class"] not in ("null_or_unspecified", "current_timestamp", "expression", "literal")
                    or not isinstance(column["extra"], str) or len(column["extra"]) > 128 or not _COLUMN_EXTRA.fullmatch(column["extra"])):
                raise _inventory_invalid()
            names.add(column["name"])
        indexes = {}
        for index in table["indexes"]:
            if (not isinstance(index, dict) or set(index) != {"name", "non_unique", "column_name", "sequence", "prefix_length", "ordering", "kind"}
                    or not named(index["name"]) or type(index["non_unique"]) is not int or index["non_unique"] not in (0, 1)
                    or (index["column_name"] is not None and (not named(index["column_name"]) or index["column_name"] not in names))
                    or type(index["sequence"]) is not int or not 1 <= index["sequence"] <= 64
                    or (index["prefix_length"] is not None and (type(index["prefix_length"]) is not int or not 1 <= index["prefix_length"] <= 65535))
                    or index["ordering"] not in (None, "A", "D") or index["kind"] not in ("BTREE", "HASH", "FULLTEXT", "RTREE")):
                raise _inventory_invalid()
            previous = indexes.get(index["name"])
            if ((previous is None and index["sequence"] != 1) or (previous is not None
                    and (index["sequence"] != previous["sequence"] + 1 or index["non_unique"] != previous["non_unique"] or index["kind"] != previous["kind"]))):
                raise _inventory_invalid()
            indexes[index["name"]] = index
        if len(indexes) > 64:
            raise _inventory_invalid()
    return tables


def validate_inventory_response(value):
    keys = {"status", "tables", "server_version", "select_attempts", "statement_attempts", "connected",
            "read_only_transaction_started", "rollback_completed", "connection_closed", "ddl_attempts"}
    if (not isinstance(value, dict) or set(value) != keys or value["status"] != "schema_inventory"
            or not isinstance(value["server_version"], str) or not _SERVER_VERSION.fullmatch(value["server_version"])
            or any(value[key] is not True for key in ("connected", "read_only_transaction_started", "rollback_completed", "connection_closed"))
            or any(type(value[key]) is not int or value[key] != expected for key, expected in
                   (("select_attempts", 7), ("statement_attempts", 9), ("ddl_attempts", 0)))):
        raise _inventory_invalid()
    validate_inventory_tables(value["tables"])
    return value


def _inventory(cursor, database):
    tables = {}
    for name in _INVENTORY_TABLE_NAMES:
        params = (database, name)
        cursor.execute(_INVENTORY_TABLE, params)
        rows = cursor.fetchall()
        if not isinstance(rows, (tuple, list)) or len(rows) > 1 or (rows and (not isinstance(rows[0], dict) or set(rows[0]) != {"kind", "engine"} | _TABLE_ESTIMATES)):
            raise _inventory_invalid()
        table = {"exists": bool(rows), "kind": rows[0]["kind"] if rows else None,
                 "engine": rows[0]["engine"] if rows else None,
                 **{key: rows[0][key] if rows else None for key in _TABLE_ESTIMATES}}
        for sql, field in ((_INVENTORY_COLUMNS, "columns"), (_INVENTORY_INDEXES, "indexes")):
            cursor.execute(sql, params)
            records = cursor.fetchall()
            if not isinstance(records, (tuple, list)):
                raise _inventory_invalid()
            table[field] = list(records)
        tables[name] = table
    return validate_inventory_tables(tables)


class _MetadataCursor:
    """Restrict inspection to the existing exact metadata helpers and budget."""
    def __init__(self, cursor, database, counts, *, inventory=False):
        self.cursor, self.database, self.counts = cursor, database, counts
        self.selects = _INVENTORY_SELECTS if inventory else _METADATA_SELECTS
        self.maximum = 7 if inventory else 8
        self.required_link_columns = None
        self.last_query = None

    def execute(self, sql, params=None):
        permitted_params = (params is None if sql in ("SELECT DATABASE() AS database_name", _INVENTORY_TARGET)
                            else params in ((self.database, "athlete_profiles"), (self.database, "athlete_workspaces")))
        if sql not in self.selects or not permitted_params:
            raise _guard("inspection_metadata_query_required")
        if self.counts["select_attempts"] >= self.maximum:
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


def _inspect_metadata(*, environ, expected_host, expected_database, connector=None, inventory=False):
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
            cursor = _MetadataCursor(raw_cursor, settings["database"], counts, inventory=inventory)
            stage = "target_preflight"
            cursor.execute(_INVENTORY_TARGET if inventory else "SELECT DATABASE() AS database_name")
            target = cursor.fetchone()
            if inventory:
                if (not isinstance(target, dict) or set(target) != {"database_name", "server_version"}
                        or not isinstance(target["server_version"], str) or not _SERVER_VERSION.fullmatch(target["server_version"])):
                    raise _inventory_invalid()
                server_version = target["server_version"]
                target = {"database_name": target["database_name"]}
            if target != {"database_name": settings["database"]}:
                raise _guard("connected_database_mismatch")
            if inventory:
                stage = "metadata_inventory"
                tables = _inventory(cursor, settings["database"])
            else:
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
    if inventory:
        return validate_inventory_response({"status": "schema_inventory", "tables": tables, "server_version": server_version, **common})
    return {"status": "schema_checked", "readiness": "ready" if workspace_exists else "requires_create",
            "workspace_contract_checked": workspace_exists, **common}


def inspect_schema(*, environ, expected_host, expected_database, connector=None):
    return _inspect_metadata(environ=environ, expected_host=expected_host, expected_database=expected_database, connector=connector)


def inventory_schema(*, environ, expected_host, expected_database, connector=None):
    return _inspect_metadata(environ=environ, expected_host=expected_host, expected_database=expected_database, connector=connector, inventory=True)


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
    modes.add_argument("--inventory", action="store_true")
    parser.add_argument("--expected-host")
    parser.add_argument("--expected-database")
    args = parser.parse_args(argv)
    if not args.apply and not args.check and not args.inventory:
        print(json.dumps(plan(), sort_keys=True))
        return 0
    try:
        operation = inventory_schema if args.inventory else inspect_schema if args.check else prepare_schema
        result = operation(environ=os.environ if environ is None else environ,
                           expected_host=args.expected_host, expected_database=args.expected_database, connector=connector)
    except PreparationError as exc:
        print(json.dumps(exc.report, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
