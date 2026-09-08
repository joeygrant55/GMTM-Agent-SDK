"""One reviewed, owner-2-only profile read. Default is offline preflight.

Credentials must already be injected into this process; never loads dotenv,
starts Railway, or starts a web server. Direct handler invocation proves a
stored ownership link and source projection, NOT a current Clerk JWT/session.
"""
from __future__ import annotations

import argparse
import ast
import builtins
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import signal
import socket
import sys
import threading


OWNER = 2
GMTM_HOST = "db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com"
BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
CAPS = {"connections": 2, "selects": 6, "statements": 10}
SOURCE_FILES = ("scripts/read_owner_profile_evidence.py", "athlete_evidence.py",
                "combine_api.py", "combine_requirements.py", "auth.py")
ENV_KEYS = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
            "AGENT_DB_HOST", "AGENT_DB_PORT", "AGENT_DB_USER",
            "AGENT_DB_PASSWORD", "AGENT_DB_NAME")
OWNER_SQL = "SELECT user_id, clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 2"
FORWARD_SQL = "SELECT user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2"
SETUP_SQL = ("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ", "START TRANSACTION READ ONLY")


class Blocked(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def normalized(sql):
    return " ".join(sql.split())


def source_hashes():
    result = {}
    for name in SOURCE_FILES:
        path = BACKEND / name
        if path.is_symlink() or not path.is_file():
            raise Blocked("source_missing_or_symlink")
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def digest(hashes):
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def configuration(env):
    required = set(ENV_KEYS) - {"DB_PORT", "DB_NAME"}
    missing = sorted(key for key in required if not isinstance(env.get(key), str)
                     or not env[key].strip() or "${{" in env[key])
    if missing:
        raise Blocked("required_configuration_missing")
    if (env["DB_HOST"] != GMTM_HOST or env["DB_USER"] != "gmtmread"
            or env.get("DB_PORT", "3306") != "3306"
            or env.get("DB_NAME", "gmtm") != "gmtm"):
        raise Blocked("gmtm_configuration_not_pinned")
    host, port = env["AGENT_DB_HOST"], env["AGENT_DB_PORT"]
    # Local execution requires the already-existing Railway TCP proxy. Private
    # domains, arbitrary IPs, pre-prod and the GMTM destination are not accepted.
    if not re.fullmatch(r"[a-z0-9-]+\.proxy\.rlwy\.net", host):
        raise Blocked("agent_existing_public_proxy_required")
    if not re.fullmatch(r"[0-9]{1,5}", port) or not 1 <= int(port) <= 65535:
        raise Blocked("agent_port_invalid")
    if not re.fullmatch(r"[A-Za-z0-9_]+", env["AGENT_DB_NAME"]):
        raise Blocked("agent_database_name_invalid")
    return {key: env[key] for key in ENV_KEYS if key in env}


def output_directory(raw):
    path = Path(raw)
    if not path.is_absolute() or path.name in ("", ".", ".."):
        raise Blocked("output_must_be_absolute_new_directory")
    # Do not resolve away a dangling symlink or admit an artifact inside any
    # Git checkout, including the outer Codex workspace or another project.
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise Blocked("output_symlink_forbidden")
    parent = path.parent.resolve(strict=True)
    if any((ancestor / ".git").exists() for ancestor in (parent, *parent.parents)):
        raise Blocked("output_must_be_outside_git")
    if path.exists() or not parent.is_dir():
        raise Blocked("output_must_be_exclusive")
    path.mkdir(mode=0o700)
    return path


class Ledger:
    def __init__(self, directory, hashes):
        self.path = directory / "receipt.json"
        self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.data = {
            "schema_version": 1, "status": "prepared", "complete": False,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "caps": dict(CAPS), "attempts": dict.fromkeys(CAPS, 0),
            "statement_counter_scope": "guarded_selects_and_explicit_transaction_setup_not_driver_protocol",
            "forbidden_attempts": {}, "source_hashes_before": hashes,
            "scope": "designated_owner_profile_projection",
            "stored_owner_confirmed": False, "current_clerk_jwt_verified": False,
            "authenticated_http_verified": False, "historical_submissions_read": False,
            "provider_calls": 0, "application_data_writes": False,
            "connections_created": 0, "connections_closed": 0,
        }
        self.flush()

    def flush(self):
        payload = (json.dumps(self.data, indent=2, sort_keys=True) + "\n").encode()
        os.lseek(self.fd, 0, os.SEEK_SET)
        view = memoryview(payload)
        while view:
            view = view[os.write(self.fd, view):]
        os.ftruncate(self.fd, len(payload))
        os.fsync(self.fd)

    def reserve(self, kind):
        if self.data["attempts"][kind] >= CAPS[kind]:
            self.deny("budget_" + kind)
        self.data["attempts"][kind] += 1
        self.flush()  # Durable reservation occurs before the operation.

    def deny(self, kind):
        denied = self.data["forbidden_attempts"]
        denied[kind] = denied.get(kind, 0) + 1
        self.flush()
        raise Blocked(kind)


def reviewed_queries():
    """Only fixed SQL literals from the hash-pinned, reviewed source functions.

    Never derives authority from runtime SQL. The operator-approved source
    digest includes these functions; changes require a new reviewed digest.
    """
    tree = ast.parse((BACKEND / "athlete_evidence.py").read_text())
    queries = []
    for name, expected in (("_identity", 2), ("_metric_rows", 1)):
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        calls = sorted((node for node in ast.walk(function) if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute) and node.func.attr == "execute"),
                       key=lambda node: node.lineno)
        if len(calls) != expected:
            raise Blocked("reviewed_sql_shape_changed")
        for call in calls:
            if len(call.args) != 2 or not isinstance(call.args[0], ast.Constant) or not isinstance(call.args[0].value, str):
                raise Blocked("reviewed_sql_not_literal")
            sql = normalized(call.args[0].value)
            if not sql.startswith("SELECT ") or re.search(r";|--|/\*|\*/|#|\b(?:INTO|UPDATE|DELETE|INSERT|LOCK|SLEEP|OUTFILE|DUMPFILE)\b", sql, re.I):
                raise Blocked("reviewed_sql_not_readonly")
            queries.append(sql)
    return dict(zip(queries, ((OWNER,), (OWNER,), (OWNER, 101))))


class ReadCursor:
    def __init__(self, connection, raw):
        self.connection, self.raw = connection, raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.raw.close()

    def execute(self, sql, params):
        owner = self.connection
        key = normalized(sql)
        allowed = ({normalized(OWNER_SQL): (OWNER,), normalized(FORWARD_SQL): (owner.clerk,)}
                   if owner.kind == "agent" else owner.queries)
        if key not in allowed or not isinstance(params, tuple) or params != allowed[key]:
            owner.ledger.deny("query_scope")
        if key == normalized(FORWARD_SQL) and not owner.clerk:
            owner.ledger.deny("owner_unresolved")
        owner.ledger.reserve("selects")
        owner.ledger.reserve("statements")
        return self.raw.execute(sql, params)

    def fetchall(self):
        rows = self.raw.fetchall()
        # No foreign owner record is retained or passed to the endpoint, even
        # if a driver unexpectedly violates the parameterized WHERE condition.
        if not isinstance(rows, (list, tuple)):
            self.connection.ledger.deny("source_rows_invalid")
        for row in rows:
            if (not isinstance(row, dict) or type(row.get("user_id")) is not int
                    or row["user_id"] != OWNER):
                self.connection.ledger.deny("foreign_owner_row")
            if self.connection.kind == "agent" and self.connection.clerk is not None and row.get("clerk_id") != self.connection.clerk:
                self.connection.ledger.deny("case_or_reverse_owner_conflict")
        return rows


class ReadConnection:
    def __init__(self, raw, kind, ledger, queries):
        self.raw, self.kind, self.ledger, self.queries = raw, kind, ledger, queries
        self.clerk, self.closed = None, False

    def start(self):
        with self.raw.cursor() as cursor:
            for sql in SETUP_SQL:
                self.ledger.reserve("statements")
                cursor.execute(sql)

    def cursor(self):
        if self.closed:
            self.ledger.deny("closed_connection_reuse")
        return ReadCursor(self, self.raw.cursor())

    def close(self):
        if self.closed:
            return
        try:
            self.raw.rollback()
        finally:
            self.raw.close()
            self.closed = True
            self.ledger.data["connections_closed"] += 1
            self.ledger.flush()


@contextmanager
def guarded_runtime(ledger):
    """Python instrumentation, not an OS network firewall. No child processes.

    DNS/connect are admitted only while the guarded connector resolves and
    connects to one configured DB. All other destinations and startup effects
    are counted and rejected, including exceptions swallowed by application code.
    """
    import asyncio
    originals = []
    active = {"target": None, "addresses": set()}
    def patch(obj, name, value):
        originals.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)
    def forbidden(name):
        def stop(*args, **kwargs):
            ledger.deny(name)
        return stop
    original_import, original_dns, original_connect = builtins.__import__, socket.getaddrinfo, socket.socket.connect
    def import_guard(name, *args, **kwargs):
        if name.split(".")[0] in {"dotenv", "anthropic", "openai", "smtplib", "subprocess", "mysql"}:
            ledger.deny("forbidden_module")
        return original_import(name, *args, **kwargs)
    def dns(host, port, *args, **kwargs):
        if active["target"] != (host, port):
            ledger.deny("dns_destination")
        result = original_dns(host, port, *args, **kwargs)
        active["addresses"].update(item[4] for item in result)
        return result
    def connect(sock, address):
        if active["target"] is None or address not in active["addresses"]:
            ledger.deny("socket_destination")
        return original_connect(sock, address)
    patch(builtins, "__import__", import_guard)
    patch(socket, "getaddrinfo", dns)
    for name in ("gethostbyname", "gethostbyname_ex", "gethostbyaddr", "getnameinfo"):
        patch(socket, name, forbidden("other_dns"))
    patch(socket.socket, "connect", connect)
    for name in ("connect_ex", "bind", "sendto", "sendmsg"):
        if hasattr(socket.socket, name):
            patch(socket.socket, name, forbidden("other_socket"))
    patch(threading.Thread, "start", forbidden("background_thread"))
    patch(asyncio, "create_task", forbidden("background_task"))
    patch(asyncio.BaseEventLoop, "create_task", forbidden("background_task"))
    for name in ("system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp", "execv", "execve", "execvp", "execvpe"):
        if hasattr(os, name):
            patch(os, name, forbidden("subprocess"))
    original_open, original_io_open, original_os_open = builtins.open, io.open, os.open
    def env_file(path):
        if isinstance(path, (str, bytes, os.PathLike)):
            name = os.path.basename(os.fsdecode(path)).casefold()
            if name.startswith(".env") or name in {"_env.json", "env.yml", "env.yaml"}:
                ledger.deny("environment_file")
    def safe_open(path, *args, **kwargs):
        env_file(path)
        return original_open(path, *args, **kwargs)
    def safe_os_open(path, *args, **kwargs):
        env_file(path)
        return original_os_open(path, *args, **kwargs)
    def safe_io_open(path, *args, **kwargs):
        env_file(path)
        return original_io_open(path, *args, **kwargs)
    patch(builtins, "open", safe_open)
    patch(io, "open", safe_io_open)
    patch(os, "open", safe_os_open)
    try:
        yield active
    finally:
        for obj, name, original in reversed(originals):
            setattr(obj, name, original)


def read_projection(config, ledger, *, driver=None):
    connections = []
    queries = reviewed_queries()
    try:
        with guarded_runtime(ledger) as network:
            sys.path.insert(0, str(BACKEND))
            try:
                import pymysql
            finally:
                sys.path.pop(0)
            connect_driver = driver or pymysql.connect
            # Only our reviewed connector may call the original real driver.
            original_connect = pymysql.connect
            original_connection_class = pymysql.connections.Connection
            pymysql.connect = lambda *a, **kw: ledger.deny("unguarded_database_connect")
            pymysql.connections.Connection = pymysql.connect
            service = None
            try:
                sys.path.insert(0, str(BACKEND))
                import athlete_evidence as service
                from starlette.requests import Request
            except BaseException:
                pymysql.connect = original_connect
                pymysql.connections.Connection = original_connection_class
                raise
            finally:
                sys.path.pop(0)
            old_agent, old_gmtm = service._get_agent_db, service._get_gmtm_db
            def connect(kind):
                ledger.reserve("connections")
                prefix = "AGENT_DB_" if kind == "agent" else "DB_"
                host = config[prefix + "HOST"]
                port = int(config["AGENT_DB_PORT"]) if kind == "agent" else 3306
                network.update(target=(host, port), addresses=set())
                try:
                    raw = connect_driver(host=host, port=port, user=config[prefix + "USER"],
                        password=config[prefix + "PASSWORD"],
                        database=config["AGENT_DB_NAME"] if kind == "agent" else "gmtm",
                        cursorclass=pymysql.cursors.DictCursor, connect_timeout=5,
                        read_timeout=10, write_timeout=10, autocommit=False,
                        local_infile=False, client_flag=0, charset="utf8mb4")
                finally:
                    network.update(target=None, addresses=set())
                connection = ReadConnection(raw, kind, ledger, queries)
                connections.append(connection)
                ledger.data["connections_created"] += 1
                ledger.flush()
                connection.start()
                return connection
            try:
                if ledger.data["forbidden_attempts"]:
                    raise Blocked("import_attempted_forbidden_operation")
                agent = connect("agent")
                with agent.cursor() as cursor:
                    cursor.execute(OWNER_SQL, (OWNER,))
                    rows = cursor.fetchall()
                if len(rows) != 1 or not isinstance(rows[0].get("clerk_id"), str) or not rows[0]["clerk_id"].strip():
                    raise Blocked("owner_link_missing_or_ambiguous")
                clerk = rows[0]["clerk_id"]
                agent.clerk = clerk
                service._get_agent_db = lambda: agent
                service._get_gmtm_db = lambda: connect("gmtm")
                response = service.current_athlete_evidence(
                    Request({"type": "http", "method": "GET", "path": "/api/athlete/evidence",
                             "query_string": b"", "headers": []}), caller_clerk_id=clerk)
                if ledger.data["forbidden_attempts"]:
                    raise Blocked("forbidden_operation_attempted")
                body = json.loads(response.body)
                if response.status_code != 200 or body.get("state") not in {"ready", "source_unavailable"}:
                    raise Blocked("ownership_or_projection_rejected")
                ledger.data["stored_owner_confirmed"] = len(connections) == 2
                if body.get("state") == "ready" and not ledger.data["stored_owner_confirmed"]:
                    raise Blocked("source_without_confirmed_owner")
                # Response has no owner ID. Every fetched row was separately
                # checked against hard-coded user2 before adapter processing.
                expected = {"state", "athlete", "evidence", "observations", "limitations", "fetched_at"}
                if set(body) != expected or not isinstance(body["evidence"], list) or len(body["evidence"]) > 20:
                    raise Blocked("unexpected_response_contract")
                return {"http_status": response.status_code, "response": body}
            finally:
                service._get_agent_db, service._get_gmtm_db = old_agent, old_gmtm
                pymysql.connect = original_connect
                pymysql.connections.Connection = original_connection_class
    finally:
        cleanup_failed = False
        with guarded_runtime(ledger):
            for connection in connections:
                try:
                    connection.close()
                except Exception:
                    cleanup_failed = True
        ledger.data["all_connections_closed"] = bool(connections) and all(connection.closed for connection in connections)
        if cleanup_failed:
            raise Blocked("connection_cleanup_failed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-reviewed", action="store_true")
    parser.add_argument("--source-digest")
    parser.add_argument("--output", help="New absolute directory outside every Git checkout")
    args = parser.parse_args(argv)
    try:
        hashes = source_hashes()
        config = configuration(os.environ)
        configured, reason = True, None
    except Blocked as error:
        configured, reason = False, error.code
        hashes = source_hashes()
    if not args.execute_reviewed:
        print(json.dumps({"mode": "offline_preflight", "configured": configured,
                          "reason": reason, "source_digest": digest(hashes),
                          "connectivity_verified": False, "database_attempts": 0}))
        return 0 if configured else 2
    if (not sys.flags.isolated or not args.output or not configured
            or args.source_digest != digest(hashes)):
        print("Owner-profile read blocked before any database access.")
        return 2
    ledger = None
    try:
        directory = output_directory(args.output)
        ledger = Ledger(directory, hashes)
        # Inherit only explicitly validated DB configuration. No provider keys,
        # proxies, auth tokens or previous live-test allowances survive.
        os.environ.clear()
        os.environ.update(config)
        os.environ.update(PATH="/usr/bin:/bin", PYTHONDONTWRITEBYTECODE="1")
        sys.dont_write_bytecode = True
        def interrupted(signum, frame):
            # The application deliberately catches ordinary source exceptions.
            # Persist cancellation before raising so a caught signal cannot be
            # exported as an ordinary source_unavailable observation.
            ledger.deny("operator_interrupted")
        signal.signal(signal.SIGTERM, interrupted)
        signal.signal(signal.SIGINT, interrupted)
        signal.signal(signal.SIGALRM, lambda *args: ledger.deny("runtime_deadline"))
        signal.alarm(90)
        projection = read_projection(config, ledger)
        if source_hashes() != hashes:
            raise Blocked("source_changed_during_read")
        payload = (json.dumps(projection, indent=2, sort_keys=True) + "\n").encode()
        target = directory / "private-profile-evidence.json"
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        ledger.data.update(status="observed", projection_state=projection["response"]["state"],
                           evidence_count=len(projection["response"]["evidence"]),
                           private_projection_sha256=hashlib.sha256(payload).hexdigest())
    except Blocked as error:
        if ledger:
            ledger.data.update(status="blocked", reason=error.code)
    except Exception:
        if ledger:
            ledger.data.update(status="blocked", reason="source_dependency_or_output_failure")
    finally:
        signal.alarm(0)
        if ledger:
            try:
                ledger.data["source_hashes_after"] = source_hashes()
                if ledger.data["source_hashes_after"] != hashes:
                    ledger.data.update(status="blocked", reason="source_changed_during_read")
                ledger.data["complete"] = True
                ledger.data["finished_at"] = datetime.now(timezone.utc).isoformat()
                ledger.flush()
            finally:
                os.close(ledger.fd)
    result = ledger.data["status"] if ledger else "blocked"
    print("Owner-profile receipt status: " + result)
    return 0 if result == "observed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
