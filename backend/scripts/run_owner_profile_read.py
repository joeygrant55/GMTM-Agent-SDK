"""Bounded, explicitly reviewed launcher for the designated owner's profile read.

Default mode retrieves configuration into memory and runs only offline preflight.
It never changes Railway settings, creates a proxy, or writes credentials. The
separate reader owns its source digest, SQL budgets and private projection.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import time


RAILWAY = Path("/Users/joey/.npm/_npx/d991ede4b4a6395c/node_modules/@railway/cli/bin/railway")
PROJECT = "27aa6c0a-9218-49ac-a182-08f6fe36249e"
ENVIRONMENT = "32a909ef-4bb6-4745-a0fe-aa86e7656b3c"
BACKEND_SERVICE = "0669f1fc-2cbe-473b-8c64-bc86f4594cf3"
MYSQL_SERVICE = "c6becf80-b58f-4fa0-99c6-45f87f405756"
FABLE_CREDENTIALS = Path("/Users/joey/Desktop/gmtmmcp/.env")
PYTHON = Path("/Users/joey/GMTM-Agent-SDK/backend/.venv/bin/python")
READER = Path(__file__).with_name("read_owner_profile_evidence.py")
GMTM_HOST = "db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com"
CLI_TIMEOUT = 30.0
READER_TIMEOUT = 105.0
TERM_GRACE = 2.0
KILL_GRACE = 2.0
MAX_CAPTURE = 1024 * 1024
SAFE_PATH = "/usr/bin:/bin"
INTERRUPT_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


class Blocked(Exception):
    """Codes are fixed local strings; never include command output or values."""


@dataclass
class ProcessResult:
    returncode: int | None
    stdout: bytes
    timed_out: bool
    group_dead: bool
    output_limit: bool
    cleanup_signals: tuple[str, ...]
    interrupted: bool = False


def group_exists(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # Absence is unproved; cleanup must not report success.


def stop_group(process, term_grace=TERM_GRACE, kill_grace=KILL_GRACE):
    """Only the new session's owned group; reap the direct child as well."""
    sent = []
    process.poll()
    for sig, grace in ((signal.SIGTERM, term_grace), (signal.SIGKILL, kill_grace)):
        if not group_exists(process.pid):
            break
        try:
            os.killpg(process.pid, sig)
            sent.append(sig.name)
        except ProcessLookupError:
            break
        except PermissionError:
            return False, tuple(sent)
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            process.poll()
            if not group_exists(process.pid):
                break
            time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))
    process.poll()
    return not group_exists(process.pid), tuple(sent)


def run_bounded(command, env, timeout, *, term_grace=TERM_GRACE, kill_grace=KILL_GRACE):
    """Capture bounded stdout in RAM, discard stderr, enforce an outer deadline.

    Pipe reads are nonblocking, so a child or descendant holding a pipe cannot
    defeat the deadline. Cleanup also runs after normal exit and interruption.
    Escaping this group is outside the reviewed child's permitted behavior.
    """
    output = bytearray()
    timed_out = output_limit = interrupted = False
    process = selector = None
    dead, sent = False, ()
    def record_interruption(signum, frame):
        # A child can signal us before Popen has returned its handle. Record
        # cancellation without unwinding construction; then own its cleanup.
        nonlocal interrupted
        interrupted = True
    old = {sig: signal.signal(sig, record_interruption) for sig in INTERRUPT_SIGNALS}
    try:
        if interrupted:
            return ProcessResult(None, b"", False, True, False, (), True)
        deadline = time.monotonic() + timeout
        process = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   start_new_session=True, close_fds=True)
        selector = selectors.DefaultSelector()
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            if interrupted:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            for key, _ in selector.select(min(0.05, remaining)):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                else:
                    if len(output) + len(chunk) > MAX_CAPTURE:
                        output_limit = True
                        break
                    output.extend(chunk)
            if output_limit or (process.poll() is not None and not selector.get_map()):
                break
    except KeyboardInterrupt:
        interrupted = True
    finally:
        if selector:
            selector.close()
        try:
            if process:
                dead, sent = stop_group(process, term_grace, kill_grace)
                process.stdout.close()
        finally:
            for sig, handler in old.items():
                signal.signal(sig, handler)
    return ProcessResult(process.returncode, bytes(output), timed_out, dead, output_limit, sent, interrupted)


def require_process(result):
    if result.timed_out or result.interrupted or not result.group_dead or result.output_limit or result.returncode != 0:
        raise Blocked("configuration_command_failed_or_incomplete")


def variables(service, runner=run_bounded):
    if service not in (BACKEND_SERVICE, MYSQL_SERVICE):
        raise Blocked("unknown_service")
    result = runner([str(RAILWAY), "variable", "list", "--project", PROJECT,
                     "--environment", ENVIRONMENT, "--service", service, "--json"],
                    {"HOME": "/Users/joey", "PATH": SAFE_PATH}, CLI_TIMEOUT)
    require_process(result)
    try:
        value = json.loads(result.stdout)
    except (ValueError, UnicodeError):
        raise Blocked("configuration_response_invalid") from None
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                               for k, v in value.items()):
        raise Blocked("configuration_response_invalid")
    return value


def read_regular(path, maximum):
    """Known files only at callers; reject symlink paths and nonregular input."""
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise Blocked("input_symlink_forbidden")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise Blocked("input_file_invalid")
        value = os.read(fd, maximum + 1)
        if len(value) > maximum:
            raise Blocked("input_file_invalid")
        return value
    finally:
        os.close(fd)


def fable_credentials():
    try:
        content = read_regular(FABLE_CREDENTIALS, 65536).decode("utf-8")
    except (OSError, UnicodeError):
        raise Blocked("known_credential_file_unavailable") from None
    found = {}
    for line in content.splitlines():
        match = re.fullmatch(r"\s*(?:export\s+)?(DB_USER|DB_PASSWORD)\s*=(.*)", line)
        if not match:
            continue
        key = match.group(1)
        # This fixed Fable source already uses grep -m1 for each key. Preserve
        # its first-definition precedence; later definitions are not fallback.
        if key in found:
            continue
        value = match.group(2).strip()
        if not value or "\x00" in value:
            raise Blocked("known_credential_fields_invalid")
        if value[0] in "\"'" or value[-1] in "\"'":
            if len(value) < 2 or value[0] not in "\"'" or value[-1] != value[0]:
                raise Blocked("known_credential_fields_invalid")
            value = value[1:-1]
        if not value.strip():
            raise Blocked("known_credential_fields_invalid")
        found[key] = value
    if set(found) != {"DB_USER", "DB_PASSWORD"} or found["DB_USER"] != "gmtmread":
        raise Blocked("known_readonly_credentials_required")
    return found


def configuration(backend, mysql, credentials):
    def required(mapping, key):
        value = mapping.get(key)
        if not isinstance(value, str) or not value.strip() or "${{" in value or "\x00" in value:
            raise Blocked("required_configuration_missing")
        return value
    pairs = (("AGENT_DB_HOST", "MYSQLHOST"), ("AGENT_DB_PORT", "MYSQLPORT"),
             ("AGENT_DB_USER", "MYSQLUSER"), ("AGENT_DB_PASSWORD", "MYSQLPASSWORD"),
             ("AGENT_DB_NAME", "MYSQLDATABASE"))
    values = {}
    for agent_key, mysql_key in pairs:
        agent_value = required(backend, agent_key)
        if agent_value != required(mysql, mysql_key):
            raise Blocked("agent_service_binding_mismatch")
        values[agent_key] = agent_value
    host = required(mysql, "RAILWAY_TCP_PROXY_DOMAIN")
    port = required(mysql, "RAILWAY_TCP_PROXY_PORT")
    if not re.fullmatch(r"[a-z0-9-]+\.proxy\.rlwy\.net", host):
        raise Blocked("existing_agent_public_proxy_required")
    if not re.fullmatch(r"[0-9]{1,5}", port) or not 1 <= int(port) <= 65535:
        raise Blocked("agent_proxy_port_invalid")
    if not re.fullmatch(r"[A-Za-z0-9_]+", values["AGENT_DB_NAME"]):
        raise Blocked("agent_database_name_invalid")
    if credentials.get("DB_USER") != "gmtmread":
        raise Blocked("known_readonly_credentials_required")
    password = required(credentials, "DB_PASSWORD")
    values.update(AGENT_DB_HOST=host, AGENT_DB_PORT=port, DB_HOST=GMTM_HOST,
                  DB_PORT="3306", DB_NAME="gmtm", DB_USER="gmtmread", DB_PASSWORD=password)
    return values


def output_path(raw, *, must_be_new):
    path = Path(raw)
    if not path.is_absolute() or any(part == ".." for part in path.parts):
        raise Blocked("output_must_be_absolute")
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise Blocked("output_symlink_forbidden")
    parent = path.parent
    if not parent.is_dir() or any((part / ".git").exists() for part in (parent, *parent.parents)):
        raise Blocked("output_must_be_outside_git")
    if must_be_new and path.exists():
        raise Blocked("output_must_be_exclusive")
    return path


def write_supervisor(directory, receipt):
    path = output_path(str(directory), must_be_new=False)
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.getuid():
            raise Blocked("child_output_permissions_invalid")
        target = os.open("supervisor.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=fd)
        with os.fdopen(target, "w") as stream:
            json.dump(receipt, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)


def observed_child(directory, expected_digest):
    try:
        receipt = json.loads(read_regular(directory / "receipt.json", 128 * 1024))
        hashes = receipt.get("source_hashes_before")
        actual = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
        return (receipt.get("status") == "observed" and receipt.get("complete") is True
                and receipt.get("all_connections_closed") is True
                and receipt.get("forbidden_attempts") == {}
                and isinstance(hashes, dict) and actual == expected_digest
                and hashes == receipt.get("source_hashes_after"))
    except (OSError, ValueError, TypeError, AttributeError, Blocked):
        return False


def _main(argv=None, *, runner=run_bounded):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-reviewed", action="store_true")
    parser.add_argument("--source-digest")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    execute = args.execute_reviewed
    directory = None
    try:
        if execute:
            if not args.output or not args.source_digest or not re.fullmatch(r"[a-f0-9]{64}", args.source_digest):
                raise Blocked("explicit_execution_arguments_required")
            directory = output_path(args.output, must_be_new=True)
        elif args.output or args.source_digest:
            raise Blocked("execution_arguments_require_explicit_flag")
        launcher_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        config = configuration(variables(BACKEND_SERVICE, runner), variables(MYSQL_SERVICE, runner),
                               fable_credentials())
        command = [str(PYTHON), "-I", "-B", str(READER)]
        if execute:
            command.extend(["--execute-reviewed", "--source-digest", args.source_digest,
                            "--output", str(directory)])
        env = {**config, "PATH": SAFE_PATH, "PYTHONDONTWRITEBYTECODE": "1"}
        result = runner(command, env, READER_TIMEOUT)
        if not execute:
            require_process(result)
            body = json.loads(result.stdout)
            if (not isinstance(body, dict) or body.get("mode") != "offline_preflight"
                    or body.get("configured") is not True or body.get("database_attempts") != 0
                    or body.get("connectivity_verified") is not False
                    or not isinstance(body.get("source_digest"), str)
                    or not re.fullmatch(r"[a-f0-9]{64}", body["source_digest"])):
                raise Blocked("reader_preflight_invalid")
            print(json.dumps({"mode": "offline_preflight", "configured": True,
                              "source_digest": body["source_digest"], "launcher_sha256": launcher_hash,
                              "agent_service_binding_verified": True, "database_attempts": 0,
                              "connectivity_verified": False, "owned_process_groups_dead": True}))
            return 0
        complete = (not result.timed_out and not result.interrupted and result.group_dead and not result.output_limit
                    and result.returncode == 0 and observed_child(directory, args.source_digest)
                    and hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == launcher_hash)
        summary = {"schema_version": 1, "status": "completed" if complete else "incomplete",
                   "complete": complete, "launcher_sha256": launcher_hash,
                   "reviewed_reader_source_digest": args.source_digest,
                   "reader_runtime_limit_seconds": READER_TIMEOUT,
                   "termination_grace_seconds": TERM_GRACE, "kill_grace_seconds": KILL_GRACE,
                   "timed_out": result.timed_out, "owned_process_group_dead": result.group_dead,
                   "interrupted": result.interrupted,
                   "output_limit_exceeded": result.output_limit, "reader_exit_code": result.returncode,
                   "cleanup_signals": list(result.cleanup_signals),
                   "finished_at": datetime.now(timezone.utc).isoformat(),
                   "agent_service_binding_verified": True, "secrets_written": False}
        # The parent does not create or reuse an output directory; only the
        # isolated child may have created it during its reviewed execution.
        if directory.exists():
            write_supervisor(directory, summary)
        else:
            summary.update(status="incomplete", complete=False)
        print(json.dumps({key: summary[key] for key in
                          ("status", "complete", "timed_out", "owned_process_group_dead")}))
        return 0 if summary["complete"] else 2
    except (Blocked, OSError, ValueError, TypeError, KeyboardInterrupt):
        print("Owner-profile launcher blocked; no command output or credential values retained.")
        return 2


def main(argv=None, *, runner=run_bounded):
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    old = {sig: signal.signal(sig, interrupted) for sig in INTERRUPT_SIGNALS}
    try:
        return _main(argv, runner=runner)
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    raise SystemExit(main())
