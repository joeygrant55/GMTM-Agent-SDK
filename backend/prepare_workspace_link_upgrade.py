"""Explicit additive compatibility migration for the observed Railway schema.

Default is an offline plan. Apply requires exact target, reviewed schema
fingerprint and live approval. At most two fixed DDL statements are attempted;
DDL is not rollbackable and failed/uncertain attempts are never retried here.
Run under a finite external supervisor; socket timeouts are not a DDL deadline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re

from prepare_agent_schema import PreparationError, connection_settings, _default_connector, _error_summary
from prepare_athlete_workspace import CREATE_SQL, inventory_schema, validate_inventory_response


ALTER_SQL = ("ALTER TABLE athlete_profiles ADD COLUMN id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, "
             "ADD UNIQUE KEY sparq_link_id (id), ALGORITHM=INPLACE, LOCK=SHARED")
COLLATION = "utf8mb4_0900_ai_ci"
ESTIMATES = {"row_count_estimate", "data_bytes_estimate", "index_bytes_estimate"}


def _blocked(reason):
    return PreparationError({"status": "failed", "reason": reason})


def _column(ordinal, name, kind, nullable="NO", collation=None, default_class="null_or_unspecified", extra=""):
    return {"ordinal": ordinal, "name": name, "kind": kind, "nullable": nullable, "collation": collation,
            "default_class": default_class, "extra": extra}


def _index(name, column, non_unique=0):
    return {"name": name, "column_name": column, "non_unique": non_unique, "sequence": 1,
            "prefix_length": None, "ordering": "A", "kind": "BTREE"}


LEGACY_COLUMNS = [
    _column(1, "user_id", "int"),
    _column(2, "clerk_id", "varchar(100)", "YES", COLLATION),
    _column(3, "bio", "text", "YES", COLLATION),
    _column(4, "updated_at", "timestamp", "YES", default_class="current_timestamp",
            extra="DEFAULT_GENERATED on update CURRENT_TIMESTAMP"),
]
LINK_ID_COLUMN = _column(5, "id", "bigint unsigned", extra="auto_increment")
LEGACY_INDEXES = [_index("PRIMARY", "user_id"), _index("idx_clerk_id", "clerk_id", 1)]
LINK_ID_INDEX = _index("sparq_link_id", "id")
WORKSPACE_COLUMNS = [_column(i, name, kind) for i, (name, kind) in enumerate([
    ("clerk_id", "varbinary(255)"), ("athlete_link_id", "bigint unsigned"), ("gmtm_user_id", "bigint unsigned"),
    ("version", "int unsigned"), ("payload", "json"), ("created_at", "datetime(6)"), ("updated_at", "datetime(6)"),
], 1)]


def _structure(table):
    return {**{key: value for key, value in table.items() if key not in ESTIMATES},
            "indexes": sorted(table["indexes"], key=lambda row: (row["name"], row["sequence"]))}


def schema_fingerprint(inventory):
    """Hash exact version/schema only; volatile estimates are separately capped."""
    validate_inventory_response(inventory)
    value = {"server_version": inventory["server_version"],
             "tables": {name: _structure(table) for name, table in inventory["tables"].items()}}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def classify_inventory(inventory):
    validate_inventory_response(inventory)
    if inventory["server_version"] != "9.4.0":
        raise _blocked("reviewed_server_version_required")
    for table in inventory["tables"].values():
        if table["exists"] and (any(type(table[key]) is not int for key in ESTIMATES)
                or table["row_count_estimate"] > 1000
                or table["data_bytes_estimate"] + table["index_bytes_estimate"] > 16 * 1024 * 1024):
            raise _blocked("reviewed_small_table_estimates_required")
    link = _structure(inventory["tables"]["athlete_profiles"])
    original = {"exists": True, "kind": "BASE TABLE", "engine": "InnoDB", "columns": LEGACY_COLUMNS,
                "indexes": sorted(LEGACY_INDEXES, key=lambda row: (row["name"], row["sequence"]))}
    migrated = {**original, "columns": LEGACY_COLUMNS + [LINK_ID_COLUMN],
                "indexes": sorted(LEGACY_INDEXES + [LINK_ID_INDEX], key=lambda row: (row["name"], row["sequence"]))}
    if link != original and link != migrated:
        raise _blocked("reviewed_link_schema_required")
    workspace = _structure(inventory["tables"]["athlete_workspaces"])
    missing = {"exists": False, "kind": None, "engine": None, "columns": [], "indexes": []}
    ready = {"exists": True, "kind": "BASE TABLE", "engine": "InnoDB", "columns": WORKSPACE_COLUMNS,
             "indexes": [_index("PRIMARY", "clerk_id")]}
    if workspace != missing and workspace != ready:
        raise _blocked("reviewed_workspace_schema_required")
    if link == original:
        if workspace != missing:
            raise _blocked("unexpected_workspace_before_link_upgrade")
        return "needs_id_and_workspace"
    return "needs_workspace" if workspace == missing else "ready"


def upgrade_schema(*, environ, expected_host, expected_database, expected_fingerprint, allow_live=False, connector=None):
    """One explicitly approved attempt; metadata observations survive partial DDL."""
    if allow_live is not True:
        raise _blocked("explicit_live_approval_required")
    if not isinstance(expected_fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_fingerprint):
        raise _blocked("reviewed_schema_fingerprint_required")
    settings = connection_settings(environ, expected_host=expected_host, expected_database=expected_database)
    connect = connector or _default_connector
    report = {"status": "failed", "ddl_is_atomic": False, "attempted_statements": [], "completed_statements": [],
              "observations": [], "inventory_attempts": 0, "ddl_outcome_uncertain": False, "ddl_connection_closed": True}
    db, stage = None, "initial_inventory"

    def observe():
        report["inventory_attempts"] += 1
        try:
            observed = inventory_schema(environ=environ, expected_host=expected_host, expected_database=expected_database, connector=connect)
        except PreparationError as exc:
            report["metadata_failure"] = {key: exc.report[key] for key in
                ("connected", "read_only_transaction_started", "rollback_completed", "connection_closed", "select_attempts", "statement_attempts", "ddl_attempts") if key in exc.report}
            raise
        state = classify_inventory(observed)
        fingerprint = schema_fingerprint(observed)
        report["observations"].append({"state": state, "fingerprint": fingerprint})
        return state, fingerprint

    try:
        state, fingerprint = observe()
        if fingerprint != expected_fingerprint:
            raise _blocked("reviewed_schema_fingerprint_mismatch")
        if state != "ready":
            stage = "ddl_connect"
            db = connect(**settings)
            report["ddl_connection_closed"] = False
            with db.cursor() as cursor:
                stage = "ddl_target_check"
                cursor.execute("SELECT DATABASE() AS database_name, VERSION() AS server_version")
                if cursor.fetchone() != {"database_name": settings["database"], "server_version": "9.4.0"}:
                    raise _blocked("connected_database_or_version_mismatch")
                stage = "ddl_lock_timeout"
                cursor.execute("SET SESSION lock_wait_timeout = 3")
                operations = ([('add_link_id', ALTER_SQL, 'needs_workspace')] if state == "needs_id_and_workspace" else [])
                operations.append(('create_athlete_workspaces', CREATE_SQL, 'ready'))
                for name, sql, expected in operations:
                    stage = name
                    report["attempted_statements"].append(name)
                    try:
                        cursor.execute(sql)
                    except Exception:
                        report["ddl_outcome_uncertain"] = True
                        # One read-only reconciliation; never repeat the failed DDL.
                        try:
                            observe()
                        except Exception:
                            report["reconciliation_failed"] = True
                        raise
                    report["completed_statements"].append(name)
                    stage = name + "_postflight"
                    actual, _ = observe()
                    if actual != expected:
                        raise _blocked("unexpected_postflight_state")
        report["status"] = "ready"
    except PreparationError as exc:
        report.update(stage=stage, reason=exc.report.get("reason", "metadata_or_cleanup_failed"))
    except Exception as exc:
        report.update(stage=stage, error=_error_summary(exc))
    finally:
        if db is not None:
            try:
                db.close()
                report["ddl_connection_closed"] = True
            except Exception as exc:
                report.update(status="failed", close_error=_error_summary(exc))
    if report["status"] != "ready":
        raise PreparationError(report) from None
    return report


def plan():
    return {"status": "dry_run", "connected": False, "ddl_is_atomic": False,
            "statements": ["add_link_id", "create_athlete_workspaces"],
            "required": "Exact reviewed target, schema fingerprint and explicit live approval; no automatic retries."}


def main(argv=None, *, environ=None, connector=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--expected-host")
    parser.add_argument("--expected-database")
    parser.add_argument("--expected-fingerprint")
    args = parser.parse_args(argv)
    if not args.apply:
        print(json.dumps(plan(), sort_keys=True))
        return 0
    try:
        value = upgrade_schema(environ=os.environ if environ is None else environ,
                               expected_host=args.expected_host, expected_database=args.expected_database,
                               expected_fingerprint=args.expected_fingerprint, allow_live=args.allow_live, connector=connector)
    except PreparationError as exc:
        print(json.dumps(exc.report, sort_keys=True))
        return 1
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
