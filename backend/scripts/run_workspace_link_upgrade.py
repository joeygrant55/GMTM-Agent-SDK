"""Fixed, finite Railway launcher for the separately approved Agent schema upgrade.

Default is offline. --apply requires reviewed source and schema fingerprints and
an exclusive private receipt directory. Never retries DDL or changes credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

if __package__:
    from . import run_workspace_schema_check as check
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run_workspace_schema_check as check

owner = check.owner
SCRIPT = check.BACKEND / "prepare_workspace_link_upgrade.py"
SOURCES = (*check.SOURCE_PATHS, SCRIPT, Path(__file__))
OPERATIONS = ["add_link_id", "create_athlete_workspaces"]
STATES = {"needs_id_and_workspace", "needs_workspace", "ready"}
HEX = re.compile(r"[0-9a-f]{64}\Z")


def source_state():
    hashes = {str(p.relative_to(check.BACKEND)): hashlib.sha256(owner.read_regular(p, 256 * 1024)).hexdigest() for p in SOURCES}
    return hashes, hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def safe_result(value):
    """Keep only fixed operation/state names, fingerprints and outcome flags."""
    required = {"status", "ddl_is_atomic", "attempted_statements", "completed_statements", "observations",
                "ddl_outcome_uncertain", "ddl_connection_closed"}
    if not isinstance(value, dict) or not required <= set(value) or value["status"] not in ("ready", "failed"):
        raise owner.Blocked("upgrade_response_invalid")
    safe = {key: value[key] for key in required}
    if (safe["ddl_is_atomic"] is not False
            or type(safe["ddl_outcome_uncertain"]) is not bool or type(safe["ddl_connection_closed"]) is not bool):
        raise owner.Blocked("upgrade_response_invalid")
    valid_operations = ([], OPERATIONS[:1], OPERATIONS[1:], OPERATIONS)
    for key in ("attempted_statements", "completed_statements"):
        if safe[key] not in valid_operations:
            raise owner.Blocked("upgrade_response_invalid")
    if safe["completed_statements"] != safe["attempted_statements"][:len(safe["completed_statements"])]:
        raise owner.Blocked("upgrade_response_invalid")
    observations = safe["observations"]
    if not isinstance(observations, list) or len(observations) > 4:
        raise owner.Blocked("upgrade_response_invalid")
    for item in observations:
        if (not isinstance(item, dict) or set(item) != {"state", "fingerprint"} or item["state"] not in STATES
                or not isinstance(item["fingerprint"], str) or not HEX.fullmatch(item["fingerprint"])):
            raise owner.Blocked("upgrade_response_invalid")
    if safe["status"] == "ready" and (not observations or observations[-1]["state"] != "ready"
            or safe["ddl_outcome_uncertain"] or not safe["ddl_connection_closed"]
            or safe["attempted_statements"] != safe["completed_statements"]):
        raise owner.Blocked("upgrade_response_invalid")
    stages = {"initial_inventory", "ddl_connect", "ddl_target_check", "ddl_lock_timeout", *OPERATIONS,
              *(name + "_postflight" for name in OPERATIONS)}
    if value.get("stage") in stages:
        safe["stage"] = value["stage"]
    if "inventory_attempts" in value:
        if type(value["inventory_attempts"]) is not int or not 1 <= value["inventory_attempts"] <= 3:
            raise owner.Blocked("upgrade_response_invalid")
        safe["inventory_attempts"] = value["inventory_attempts"]
    if "metadata_failure" in value:
        if safe["status"] == "ready":
            raise owner.Blocked("upgrade_response_invalid")
        failure = value["metadata_failure"]
        flags = {"connected", "read_only_transaction_started", "rollback_completed", "connection_closed"}
        caps = {"select_attempts": 7, "statement_attempts": 9, "ddl_attempts": 0}
        if not isinstance(failure, dict) or not set(failure) <= flags | set(caps):
            raise owner.Blocked("upgrade_response_invalid")
        for key, item in failure.items():
            valid = type(item) is bool if key in flags else type(item) is int and 0 <= item <= caps[key]
            if not valid:
                raise owner.Blocked("upgrade_response_invalid")
        safe["metadata_failure"] = failure
    # Unknown reason/error strings and arbitrary extra fields never leave child RAM.
    return safe


def main(argv=None, *, runner=owner.run_bounded):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--source-digest")
    parser.add_argument("--schema-fingerprint")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report, directory = {"status": "blocked", "database_child_started": False, "gmtm_accessed": False}, None
    try:
        hashes, digest = source_state()
        report.update(source_digest=digest, source_hashes_before=hashes)
        if not args.apply:
            if args.source_digest or args.schema_fingerprint or args.output:
                raise owner.Blocked("execution_arguments_require_apply")
            print(json.dumps({"status": "offline_upgrade_plan", "source_digest": digest, "database_child_started": False,
                              "operations": OPERATIONS, "requires_live_authorization": True}))
            return 0
        if (args.source_digest != digest or not isinstance(args.schema_fingerprint, str)
                or not HEX.fullmatch(args.schema_fingerprint) or not args.output):
            raise owner.Blocked("reviewed_source_schema_and_output_required")
        directory = owner.output_path(str(args.output), must_be_new=True)
        directory.mkdir(mode=0o700)
        config = check.agent_configuration(runner)
        report.update(agent_service_binding_verified=True, expected_schema_fingerprint=args.schema_fingerprint,
                      target={"project": owner.PROJECT, "environment": owner.ENVIRONMENT, "service": owner.MYSQL_SERVICE,
                              "host": config["AGENT_DB_HOST"], "port": int(config["AGENT_DB_PORT"]), "database": config["AGENT_DB_NAME"]})
        if source_state()[0] != hashes:
            raise owner.Blocked("source_changed_before_upgrade")
        command = [str(owner.PYTHON), "-I", "-B", "-c", check.CHILD, str(check.BACKEND), str(SCRIPT),
                   "--apply", "--allow-live", "--expected-host", config["AGENT_DB_HOST"],
                   "--expected-database", config["AGENT_DB_NAME"], "--expected-fingerprint", args.schema_fingerprint]
        report["database_child_started"] = True
        result = runner(command, {**config, "PATH": owner.SAFE_PATH, "PYTHONDONTWRITEBYTECODE": "1"}, owner.READER_TIMEOUT)
        report["child"] = {"returncode": result.returncode, "timed_out": result.timed_out, "group_dead": result.group_dead,
                           "interrupted": result.interrupted, "output_limit": result.output_limit, "cleanup_signals": list(result.cleanup_signals)}
        report["source_hashes_after"] = source_state()[0]
        if result.group_dead and not (result.timed_out or result.interrupted or result.output_limit) and result.returncode in (0, 1):
            report["upgrade"] = safe_result(json.loads(result.stdout))
        if report["source_hashes_after"] != hashes:
            raise owner.Blocked("source_changed_during_upgrade_reconcile_server")
        if (result.returncode != 0 or not result.group_dead or result.timed_out or result.interrupted or result.output_limit
                or report.get("upgrade", {}).get("status") != "ready"):
            raise owner.Blocked("upgrade_incomplete_reconcile_server_before_retry")
        report["status"] = "observed_ready"
    except owner.Blocked as exc:
        report["reason"] = str(exc)
    except Exception:
        report["reason"] = "upgrade_failed_reconcile_server_before_retry"
    if directory is not None:
        check.write_receipt(directory, report)
    print(json.dumps({key: report[key] for key in ("status", "reason", "database_child_started", "upgrade", "gmtm_accessed") if key in report}))
    return 0 if report["status"] == "observed_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
