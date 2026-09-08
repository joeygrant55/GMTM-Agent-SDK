"""Controlled operator-only verification; never starts the application.

Use existing environment configuration. No dotenv, login, token creation, or
identity mutation. --check-config does not import service modules or connect.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ALLOWED_GMTM_HOST = "db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com"
EVENTS = {1317, 1318}
REQUIRED = ("DB_HOST", "DB_USER", "DB_PASSWORD", "AGENT_DB_HOST", "AGENT_DB_PORT",
            "AGENT_DB_USER", "AGENT_DB_PASSWORD", "AGENT_DB_NAME")


class Blocked(Exception):
    def __init__(self, code):
        self.code = code


def check_config(env):
    missing = [key for key in REQUIRED if not isinstance(env.get(key), str) or not env[key].strip()]
    if missing:
        return {"status": "blocked", "reason": "missing_configuration", "missing_keys": missing}
    if env["DB_HOST"] != ALLOWED_GMTM_HOST:
        return {"status": "blocked", "reason": "gmtm_host_not_allowed"}
    agent_host = env["AGENT_DB_HOST"]
    if (not re.fullmatch(r"[A-Za-z0-9.-]+", agent_host) or "pre-prod" in agent_host.lower()
            or "preprod" in agent_host.lower() or agent_host == ALLOWED_GMTM_HOST):
        return {"status": "blocked", "reason": "agent_host_not_allowed"}
    try:
        if not 1 <= int(env["AGENT_DB_PORT"]) <= 65535:
            raise ValueError
    except ValueError:
        return {"status": "blocked", "reason": "invalid_agent_port"}
    return {"status": "configured", "gmtm_host_allowlist_matched": True,
            "agent_configuration_present": True, "connectivity_verified": False}


def validate_select(sql):
    # Only the runner and reviewed adapter supply SQL. Reject multi-statements,
    # comments, file output, side-effect functions, locks and other SQL verbs.
    if not isinstance(sql, str) or not re.match(r"^\s*SELECT\b", sql, re.I):
        raise Blocked("non_read_query")
    if re.search(r";|--|/\*|\*/|#|\b(INTO|INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP|TRUNCATE|CALL|DO|SET|LOAD|OUTFILE|DUMPFILE|FOR|LOCK|SLEEP|BENCHMARK|GET_LOCK|RELEASE_LOCK)\b", sql, re.I):
        raise Blocked("non_read_query")
    tables = re.findall(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z_0-9]*)", sql, re.I)
    if not tables or any(table.lower() not in {"athlete_profiles", "events", "event_tasks", "event_task_submissions"} for table in tables):
        raise Blocked("unapproved_table")


class ReadCursor:
    def __init__(self, cursor, owner):
        self.cursor, self.owner = cursor, owner

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cursor.close()

    def execute(self, sql, params):
        validate_select(sql)
        self.owner.query_count += 1
        return self.cursor.execute(sql, params)

    def fetchall(self):
        return self.cursor.fetchall()


class ReadConnection:
    def __init__(self, raw):
        self.raw, self.closed, self.query_count = raw, False, 0
        try:
            with raw.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                cursor.execute("START TRANSACTION READ ONLY")
        except Exception:
            self.close()
            raise Blocked("readonly_transaction_failed") from None

    def cursor(self):
        if self.closed:
            raise Blocked("connection_closed")
        return ReadCursor(self.raw.cursor(), self)

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.raw.rollback()
            finally:
                self.raw.close()


def connect_readonly(env, source, driver):
    if source == "agent":
        options = dict(host=env["AGENT_DB_HOST"], port=int(env["AGENT_DB_PORT"]),
                       user=env["AGENT_DB_USER"], password=env["AGENT_DB_PASSWORD"],
                       database=env["AGENT_DB_NAME"])
    else:
        options = dict(host=env["DB_HOST"], port=3306, user=env["DB_USER"],
                       password=env["DB_PASSWORD"], database="gmtm")
    return ReadConnection(driver.connect(**options, cursorclass=driver.cursors.DictCursor,
        connect_timeout=5, read_timeout=10, write_timeout=10, autocommit=False,
        local_infile=False))


def safe_projection(snapshot, athlete_id, event_id):
    if (snapshot.get("athlete_id") != athlete_id or snapshot.get("state") != "ready"
            or not isinstance(snapshot.get("selected_event"), dict)
            or snapshot["selected_event"].get("event_id") != event_id):
        raise Blocked("owner_or_event_mismatch")
    activities = snapshot.get("activities")
    if not isinstance(activities, list) or not 0 < len(activities) <= 50:
        raise Blocked("invalid_projection")
    projected = []
    seen = set()
    for item in activities:
        task_id = item.get("task_id")
        if (type(task_id) is not int or task_id <= 0 or task_id in seen
                or item.get("event_id") != event_id
                or item.get("submission_state") not in {"submitted", "not_submitted"}
                or item.get("evidence_state") not in {"unknown", "missing_fields", "fields_present"}):
            raise Blocked("invalid_projection")
        seen.add(task_id)
        projected.append({key: item[key] for key in ("task_id", "submission_state", "evidence_state")})
    counts = {"activities": len(projected),
              "submitted": sum(a["submission_state"] == "submitted" for a in projected),
              "fields_present": sum(a["evidence_state"] == "fields_present" for a in projected)}
    if snapshot.get("counts") != counts:
        raise Blocked("projection_count_mismatch")
    result = {"event_id": event_id, "ownership_match": True, "counts": counts,
              "activities": projected, "eligibility_verified": False}
    result["projection_sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result


def verify(athlete_id, event_id, env, *, service=None, driver=None):
    if type(athlete_id) is not int or athlete_id <= 0 or event_id not in EVENTS:
        return {"status": "blocked", "reason": "invalid_scope"}
    config = check_config(env)
    if config["status"] != "configured":
        return config
    if service is None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import combine_api as service
    if driver is None:
        import pymysql as driver
    connections = []
    originals = service._get_agent_db, service._get_gmtm_db
    receipt = None
    try:
        agent = connect_readonly(env, "agent", driver)
        connections.append(agent)
        with agent.cursor() as cursor:
            cursor.execute("SELECT clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 2", (athlete_id,))
            rows = cursor.fetchall()
        if not rows:
            raise Blocked("unlinked_athlete")
        if len(rows) != 1 or not isinstance(rows[0].get("clerk_id"), str) or not rows[0]["clerk_id"].strip():
            raise Blocked("ambiguous_owner")
        clerk_id = rows[0]["clerk_id"]
        # Check reverse uniqueness before accessing any GMTM data.
        if service._linked_athlete(agent, clerk_id) != athlete_id:
            raise Blocked("owner_or_event_mismatch")
        def gmtm_factory():
            connection = connect_readonly(env, "gmtm", driver)
            connections.append(connection)
            return connection
        service._get_agent_db = lambda: agent
        service._get_gmtm_db = gmtm_factory
        receipt = {"status": "observed", **safe_projection(service.load_current_combine(clerk_id, event_id), athlete_id, event_id)}
    except Blocked as exc:
        receipt = {"status": "blocked", "reason": exc.code}
    except Exception:
        receipt = {"status": "blocked", "reason": "source_or_dependency_failure"}
    finally:
        service._get_agent_db, service._get_gmtm_db = originals
        for connection in connections:
            try:
                connection.close()
            except Exception:
                receipt = {"status": "blocked", "reason": "connection_cleanup_failed"}
    receipt["read_query_count"] = sum(c.query_count for c in connections)
    receipt["connections_closed"] = all(c.closed for c in connections)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--athlete-id", required=True, type=int)
    parser.add_argument("--event-id", required=True, type=int, choices=sorted(EVENTS))
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.athlete_id <= 0:
        parser.error("--athlete-id must be positive")
    # Reserve an exclusive private receipt before any possible service access.
    try:
        fd = os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError:
        print("Receipt path unavailable; no verification attempted.")
        return 2
    with os.fdopen(fd, "w") as output:
        try:
            result = check_config(os.environ) if args.check_config else verify(args.athlete_id, args.event_id, os.environ)
        except Exception:
            result = {"status": "blocked", "reason": "source_or_dependency_failure"}
        result["checked_at"] = datetime.now(timezone.utc).isoformat()
        result["mode"] = "configuration_only" if args.check_config else "readonly_source_check"
        result["source_sha256"] = {name: hashlib.sha256((Path(__file__).resolve().parents[1] / name).read_bytes()).hexdigest()
                                    for name in ("combine_api.py", "combine_requirements.py")}
        json.dump(result, output, indent=2)
        output.write("\n")
    print("Receipt written: " + result["status"])
    return 0 if result["status"] in {"configured", "observed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
