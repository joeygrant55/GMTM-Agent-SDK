"""Verify the existing SPARQ Agent binding and, explicitly, read schema metadata.

Default fetches Railway configuration into memory only. --check invokes a fixed
metadata reader in a finite isolated child. No DDL, athlete rows or GMTM access.
This wrapper cannot apply schema; all output is metadata or redacted status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

if __package__:
    from . import run_owner_profile_read as owner
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run_owner_profile_read as owner

BACKEND = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (Path(__file__), Path(owner.__file__), BACKEND / "prepare_athlete_workspace.py", BACKEND / "prepare_agent_schema.py")
CHILD = """import runpy,sys
sys.path.insert(0,sys.argv.pop(1))
runpy.run_path(sys.argv.pop(1),run_name='__main__')
"""


def source_state():
    hashes = {str(path.relative_to(BACKEND)): hashlib.sha256(owner.read_regular(path, 256 * 1024)).hexdigest() for path in SOURCE_PATHS}
    return hashes, hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def agent_configuration(runner):
    # Reuse the exact existing project/environment/service binding comparison.
    # Its GMTM credential argument is unused here and is never sent to the child.
    backend = owner.variables(owner.BACKEND_SERVICE, runner)
    mysql = owner.variables(owner.MYSQL_SERVICE, runner)
    config = owner.configuration(backend, mysql, {"DB_USER": "gmtmread", "DB_PASSWORD": "unused-metadata-check"})
    return {key: value for key, value in config.items() if key.startswith("AGENT_DB_")}


def write_receipt(directory, value):
    directory = owner.output_path(str(directory), must_be_new=False)
    dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(dir_fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise owner.Blocked("output_permissions_invalid")
        fd = os.open("receipt.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dir_fd)
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(dir_fd)


def checked_response(value):
    keys = {"status", "readiness", "workspace_contract_checked", "select_attempts", "statement_attempts",
            "connected", "read_only_transaction_started", "rollback_completed", "connection_closed", "ddl_attempts"}
    if not isinstance(value, dict) or set(value) != keys or value.get("status") != "schema_checked" or value.get("readiness") not in ("ready", "requires_create"):
        raise owner.Blocked("schema_check_response_invalid")
    ready = value["readiness"] == "ready"
    if (any(value[key] is not True for key in ("connected", "read_only_transaction_started", "rollback_completed", "connection_closed"))
            or value["workspace_contract_checked"] is not ready
            or any(type(value[key]) is not int for key in ("select_attempts", "statement_attempts", "ddl_attempts"))
            or value["select_attempts"] != (8 if ready else 5)
            or value["statement_attempts"] != (10 if ready else 7) or value["ddl_attempts"] != 0):
        raise owner.Blocked("schema_check_response_invalid")
    return value


def failure_summary(value):
    # Never retain arbitrary child keys, driver messages or exception class names.
    if not isinstance(value, dict) or value.get("status") != "failed":
        raise owner.Blocked("schema_check_response_invalid")
    stages = {"validation", "connect", "start_readonly_transaction", "target_preflight", "athlete_link_preflight",
              "existing_workspace_preflight", "rollback", "close"}
    reasons = {"connected_database_mismatch", "existing_athlete_link_table_required", "existing_athlete_link_columns_required",
               "existing_athlete_link_identity_types_required", "existing_athlete_link_subject_type_required",
               "existing_athlete_link_indexes_required", "transactional_base_table_required", "column_metadata_invalid",
               "index_metadata_invalid", "workspace_table_missing_after_apply", "workspace_column_contract_mismatch",
               "workspace_index_contract_mismatch", "inspection_metadata_query_required", "inspection_query_budget_exhausted"}
    safe = {"stage": value["stage"] if value.get("stage") in stages else "unknown"}
    if value.get("reason") in reasons:
        safe["reason"] = value["reason"]
    columns = value.get("required_link_columns")
    if isinstance(columns, dict) and set(columns) == {"id", "user_id", "clerk_id"} and all(type(flag) is bool for flag in columns.values()):
        safe["required_link_columns"] = columns
    for key in ("connected", "read_only_transaction_started", "rollback_completed", "connection_closed"):
        if type(value.get(key)) is bool:
            safe[key] = value[key]
    for key, cap in (("select_attempts", 8), ("statement_attempts", 10), ("ddl_attempts", 0)):
        if type(value.get(key)) is int and 0 <= value[key] <= cap:
            safe[key] = value[key]
    error = value.get("error")
    if isinstance(error, dict) and type(error.get("mysql_code")) is int and 0 <= error["mysql_code"] <= 65535:
        safe["mysql_code"] = error["mysql_code"]
    return safe


def main(argv=None, *, runner=owner.run_bounded):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--source-digest")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    directory = None
    report = {"status": "incomplete", "schema_applied": False, "athlete_rows_read": False,
              "gmtm_accessed": False, "database_child_started": False}
    try:
        hashes, digest = source_state()
        report.update(source_hashes_before=hashes, source_digest=digest)
        if args.check:
            if not args.output or args.source_digest != digest:
                raise owner.Blocked("reviewed_source_and_exclusive_output_required")
            directory = owner.output_path(str(args.output), must_be_new=True)
            directory.mkdir(mode=0o700)
        elif args.output or args.source_digest:
            raise owner.Blocked("execution_arguments_require_check")
        config = agent_configuration(runner)
        report.update(agent_service_binding_verified=True, target={
            "project": owner.PROJECT, "environment": owner.ENVIRONMENT, "service": owner.MYSQL_SERVICE,
            "host": config["AGENT_DB_HOST"], "port": int(config["AGENT_DB_PORT"]), "database": config["AGENT_DB_NAME"],
        })
        if not args.check:
            print(json.dumps({"status": "configuration_preflight", "agent_service_binding_verified": True,
                              "source_digest": digest, "database_child_started": False}))
            return 0
        if source_state()[0] != hashes:
            raise owner.Blocked("source_changed_before_check")
        report["database_child_started"] = True
        command = [str(owner.PYTHON), "-I", "-B", "-c", CHILD, str(BACKEND),
                   str(BACKEND / "prepare_athlete_workspace.py"), "--check",
                   "--expected-host", config["AGENT_DB_HOST"], "--expected-database", config["AGENT_DB_NAME"]]
        result = runner(command, {**config, "PATH": owner.SAFE_PATH, "PYTHONDONTWRITEBYTECODE": "1"}, owner.READER_TIMEOUT)
        report["child"] = {"returncode": result.returncode, "timed_out": result.timed_out,
                           "group_dead": result.group_dead, "output_limit": result.output_limit,
                           "interrupted": result.interrupted, "cleanup_signals": list(result.cleanup_signals)}
        if result.returncode == 1 and result.group_dead and not (result.timed_out or result.interrupted or result.output_limit):
            report["schema_failure"] = failure_summary(json.loads(result.stdout))
            raise owner.Blocked("metadata_check_failed")
        owner.require_process(result)
        report["schema"] = checked_response(json.loads(result.stdout))
        report["source_hashes_after"] = source_state()[0]
        if report["source_hashes_after"] != hashes:
            raise owner.Blocked("source_changed_during_check")
        report["status"] = "observed"
    except owner.Blocked as exc:
        report.update(status="blocked", reason=str(exc))
    except Exception:
        report.update(status="blocked", reason="schema_check_failed")
    if directory is not None:
        write_receipt(directory, report)
    print(json.dumps({key: report[key] for key in ("status", "reason", "schema", "schema_failure", "schema_applied", "athlete_rows_read", "gmtm_accessed") if key in report}))
    return 0 if report["status"] == "observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
