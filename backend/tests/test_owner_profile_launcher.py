"""Launcher tests use synthetic values and local child processes only."""
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
from types import SimpleNamespace

import pytest

from scripts import run_owner_profile_read as launcher


MYSQL = {"MYSQLHOST": "mysql.railway.internal", "MYSQLPORT": "3306", "MYSQLUSER": "synthetic",
         "MYSQLPASSWORD": "synthetic-agent-secret", "MYSQLDATABASE": "railway",
         "RAILWAY_TCP_PROXY_DOMAIN": "synthetic.proxy.rlwy.net", "RAILWAY_TCP_PROXY_PORT": "12345"}
BACKEND = {"AGENT_DB_" + suffix: MYSQL[mysql_key] for suffix, mysql_key in
           (("HOST", "MYSQLHOST"), ("PORT", "MYSQLPORT"), ("USER", "MYSQLUSER"),
            ("PASSWORD", "MYSQLPASSWORD"), ("NAME", "MYSQLDATABASE"))}
BACKEND.update(DB_USER="root", DB_PASSWORD="must-never-use", DB_HOST="must-never-use")
CREDENTIALS = {"DB_USER": "gmtmread", "DB_PASSWORD": "synthetic-readonly-secret"}
HASHES = {"synthetic-source.py": "abc"}
DIGEST = hashlib.sha256(json.dumps(HASHES, sort_keys=True).encode()).hexdigest()


def success(body):
    return launcher.ProcessResult(0, json.dumps(body).encode(), False, True, False, ())


def fake_runner(monkeypatch, *, execute=False, result=None, child_receipt=None):
    calls = []
    monkeypatch.setattr(launcher, "fable_credentials", lambda: dict(CREDENTIALS))
    def run(command, env, timeout):
        calls.append((command, env, timeout))
        if command[0] == str(launcher.RAILWAY):
            assert command[1:3] == ["variable", "list"]
            assert command[command.index("--project") + 1] == launcher.PROJECT
            assert command[command.index("--environment") + 1] == launcher.ENVIRONMENT
            assert env == {"HOME": "/Users/joey", "PATH": launcher.SAFE_PATH}
            service = command[command.index("--service") + 1]
            return success(BACKEND if service == launcher.BACKEND_SERVICE else MYSQL)
        assert command[:4] == [str(launcher.PYTHON), "-I", "-B", str(launcher.READER)]
        assert timeout == 105.0
        assert set(env) == {"DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
                            "AGENT_DB_HOST", "AGENT_DB_PORT", "AGENT_DB_NAME", "AGENT_DB_USER",
                            "AGENT_DB_PASSWORD", "PATH", "PYTHONDONTWRITEBYTECODE"}
        assert env["DB_PASSWORD"] == CREDENTIALS["DB_PASSWORD"]
        if execute:
            assert command[4] == "--execute-reviewed"
            output = Path(command[command.index("--output") + 1])
            output.mkdir(mode=0o700)
            receipt = child_receipt if child_receipt is not None else {
                "status": "observed", "complete": True, "all_connections_closed": True,
                "forbidden_attempts": {}, "source_hashes_before": HASHES, "source_hashes_after": HASHES}
            (output / "receipt.json").write_text(json.dumps(receipt))
            return result if result else success({"private": "synthetic-child-secret"})
        assert len(command) == 4
        return success({"mode": "offline_preflight", "configured": True,
                        "source_digest": DIGEST, "database_attempts": 0, "connectivity_verified": False,
                        "ignored_secret": "synthetic-child-secret"})
    return run, calls


def test_default_is_only_preflight_with_minimal_pinned_environment(monkeypatch, capsys):
    run, calls = fake_runner(monkeypatch)
    assert launcher.main([], runner=run) == 0
    output = capsys.readouterr().out
    body = json.loads(output)
    assert body["database_attempts"] == 0 and body["connectivity_verified"] is False
    assert body["source_digest"] == DIGEST and body["owned_process_groups_dead"] is True
    assert len(calls) == 3 and "synthetic-" not in output
    env = calls[-1][1]
    assert env["DB_HOST"] == launcher.GMTM_HOST and env["DB_USER"] == "gmtmread"
    assert env["DB_NAME"] == "gmtm" and env["DB_PORT"] == "3306"
    assert env["AGENT_DB_HOST"] == MYSQL["RAILWAY_TCP_PROXY_DOMAIN"]


@pytest.mark.parametrize("key", ["AGENT_DB_HOST", "AGENT_DB_PORT", "AGENT_DB_USER", "AGENT_DB_PASSWORD", "AGENT_DB_NAME"])
def test_every_backend_agent_binding_must_match_known_mysql_service(key):
    backend = dict(BACKEND, **{key: "mismatch"})
    with pytest.raises(launcher.Blocked, match="agent_service_binding_mismatch"):
        launcher.configuration(backend, MYSQL, CREDENTIALS)


@pytest.mark.parametrize("key,value", [("RAILWAY_TCP_PROXY_DOMAIN", "other.example"),
    ("RAILWAY_TCP_PROXY_DOMAIN", ""), ("RAILWAY_TCP_PROXY_PORT", "0"),
    ("RAILWAY_TCP_PROXY_PORT", "65536"), ("MYSQLPASSWORD", "")])
def test_no_proxy_or_credentials_fallback(key, value):
    with pytest.raises(launcher.Blocked):
        launcher.configuration(BACKEND, dict(MYSQL, **{key: value}), CREDENTIALS)


@pytest.mark.parametrize("text,valid", [
    ("DB_USER=gmtmread\nDB_PASSWORD='literal$(never-run)#value'\nOTHER=ignored", True),
    (' export DB_USER="gmtmread"\nDB_PASSWORD=literal\\nvalue', True),
    ("DB_USER=root\nDB_PASSWORD=value", False),
    ("DB_USER=gmtmread\nDB_PASSWORD=value\nDB_PASSWORD=duplicate", True),
    ("DB_USER=gmtmread\nDB_PASSWORD='unclosed", False),
    ("DB_USER=gmtmread\nDB_PASSWORD=''", False),
    ("DB_USER=gmtmread", False)])
def test_literal_two_field_known_file_parse_only(monkeypatch, tmp_path, text, valid):
    path = tmp_path / "known.env"
    path.write_text(text)
    monkeypatch.setattr(launcher, "FABLE_CREDENTIALS", path)
    if valid:
        result = launcher.fable_credentials()
        assert set(result) == {"DB_USER", "DB_PASSWORD"}
        assert result["DB_USER"] == "gmtmread"
    else:
        with pytest.raises(launcher.Blocked):
            launcher.fable_credentials()


@pytest.mark.parametrize("text,valid", [
    ("DB_USER=gmtmread\nDB_PASSWORD=first-password\nDB_USER=other", True),
    ("DB_USER=other\nDB_PASSWORD=first-password\nDB_USER=gmtmread", False),
    ("DB_USER=gmtmread\nDB_PASSWORD=first-password\nDB_PASSWORD=other-password", True),
    ("DB_USER=gmtmread\nDB_PASSWORD=''\nDB_PASSWORD=first-password", False)])
def test_fixed_fable_file_uses_first_definition_without_fallback(monkeypatch, tmp_path, text, valid):
    path = tmp_path / "known.env"
    path.write_text(text)
    monkeypatch.setattr(launcher, "FABLE_CREDENTIALS", path)
    if valid:
        assert launcher.fable_credentials() == {"DB_USER": "gmtmread", "DB_PASSWORD": "first-password"}
    else:
        with pytest.raises(launcher.Blocked):
            launcher.fable_credentials()


def test_credential_symlink_is_not_read(monkeypatch, tmp_path):
    target = tmp_path / "target"
    target.write_text("DB_USER=gmtmread\nDB_PASSWORD=value")
    path = tmp_path / "link"
    path.symlink_to(target)
    monkeypatch.setattr(launcher, "FABLE_CREDENTIALS", path)
    with pytest.raises(launcher.Blocked, match="symlink"):
        launcher.fable_credentials()


@pytest.mark.parametrize("arguments", [["--output", "/private/tmp/unused"],
    ["--source-digest", DIGEST], ["--execute-reviewed"],
    ["--execute-reviewed", "--source-digest", "bad", "--output", "/private/tmp/unused"]])
def test_partial_execution_flags_block_before_even_configuration(arguments, capsys):
    def forbidden(*args):
        pytest.fail("No command may execute")
    assert launcher.main(arguments, runner=forbidden) == 2
    assert "blocked" in capsys.readouterr().out


@pytest.mark.parametrize("outcome", ["complete", "timeout", "descendant_alive", "child_incomplete", "interrupted"])
def test_supervisor_private_receipt_cannot_promote_incomplete_run(monkeypatch, tmp_path, capsys, outcome):
    directory = tmp_path.resolve() / "new-output"
    result = launcher.ProcessResult(0, b"synthetic-child-secret", outcome == "timeout",
                                    outcome != "descendant_alive", False, (), outcome == "interrupted")
    bad_receipt = {"status": "blocked", "complete": True} if outcome == "child_incomplete" else None
    run, _ = fake_runner(monkeypatch, execute=True, result=result, child_receipt=bad_receipt)
    code = launcher.main(["--execute-reviewed", "--source-digest", DIGEST,
                          "--output", str(directory)], runner=run)
    receipt = json.loads((directory / "supervisor.json").read_text())
    assert code == (0 if outcome == "complete" else 2)
    assert receipt["complete"] is (outcome == "complete")
    assert (directory / "supervisor.json").stat().st_mode & 0o777 == 0o600
    assert directory.stat().st_mode & 0o777 == 0o700
    assert "synthetic-" not in json.dumps(receipt) + capsys.readouterr().out


def test_configuration_errors_never_echo_captured_output_or_values(monkeypatch, capsys):
    def failed(*args):
        return launcher.ProcessResult(1, b"synthetic-private-secret", False, True, False, ())
    assert launcher.main([], runner=failed) == 2
    assert "synthetic-private" not in capsys.readouterr().out


def test_output_rejects_existing_directory_git_and_symlinks(tmp_path):
    base = tmp_path.resolve()
    (base / ".git").mkdir()
    with pytest.raises(launcher.Blocked, match="outside_git"):
        launcher.output_path(str(base / "new"), must_be_new=True)
    (base / ".git").rmdir()
    with pytest.raises(launcher.Blocked, match="exclusive"):
        launcher.output_path(str(base), must_be_new=True)
    link = base / "alias"
    link.symlink_to(base)
    with pytest.raises(launcher.Blocked, match="symlink"):
        launcher.output_path(str(link / "new"), must_be_new=True)


def test_real_offline_process_deadline_kills_term_ignoring_child():
    before = time.monotonic()
    result = launcher.run_bounded([sys.executable, "-I", "-B", "-c",
        "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)"],
        {"PATH": launcher.SAFE_PATH}, 0.15, term_grace=0.1, kill_grace=1)
    assert result.timed_out and result.group_dead
    assert "SIGKILL" in result.cleanup_signals and time.monotonic() - before < 3


def test_real_offline_descendant_keeping_pipe_open_is_terminated(tmp_path):
    # Parent reaps its child on TERM, so group-dead proof does not depend on the
    # host's timing for reaping an orphan zombie. Both hold the stdout pipe.
    script = """import os, signal, time
child = os.fork()
if child == 0:
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    time.sleep(30)
else:
    def finish(*args):
        os.waitpid(child, 0)
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, finish)
    print(child, flush=True)
    time.sleep(30)
"""
    result = launcher.run_bounded([sys.executable, "-I", "-B", "-c", script],
                                  {"PATH": launcher.SAFE_PATH}, 0.25,
                                  term_grace=1, kill_grace=1)
    assert result.timed_out and result.group_dead
    child = int(result.stdout.strip())
    with pytest.raises(ProcessLookupError):
        os.kill(child, 0)


def test_real_offline_normal_child_exit_is_reaped():
    result = launcher.run_bounded([sys.executable, "-I", "-B", "-c", "print('safe')"],
                                  {"PATH": launcher.SAFE_PATH}, 2)
    assert result.returncode == 0 and result.group_dead and result.stdout == b"safe\n"
    assert not result.timed_out and result.cleanup_signals == ()


@pytest.mark.parametrize("interruption", launcher.INTERRUPT_SIGNALS)
def test_real_parent_interruption_cleans_owned_child_and_records_incomplete(monkeypatch, tmp_path, capsys, interruption):
    fake, calls = fake_runner(monkeypatch)
    directory = tmp_path.resolve() / "interrupted"
    previous = signal.getsignal(interruption)
    def run(command, env, timeout):
        if command[0] == str(launcher.RAILWAY):
            return fake(command, env, timeout)
        directory.mkdir(mode=0o700)
        script = ("import os,signal,time; print('synthetic-private-secret',flush=True); "
                  f"os.kill(os.getppid(),{int(interruption)}); time.sleep(30)")
        return launcher.run_bounded([sys.executable, "-I", "-B", "-c", script],
                                   {"PATH": launcher.SAFE_PATH}, 2, term_grace=0.1, kill_grace=1)
    assert launcher.main(["--execute-reviewed", "--source-digest", DIGEST,
                          "--output", str(directory)], runner=run) == 2
    receipt = json.loads((directory / "supervisor.json").read_text())
    assert receipt["interrupted"] is True and receipt["complete"] is False
    assert receipt["owned_process_group_dead"] is True
    assert "synthetic-private" not in json.dumps(receipt) + capsys.readouterr().out
    assert signal.getsignal(interruption) == previous


def test_real_offline_output_capture_is_bounded(monkeypatch):
    monkeypatch.setattr(launcher, "MAX_CAPTURE", 128)
    result = launcher.run_bounded([sys.executable, "-I", "-B", "-c", "print('x'*1000)"],
                                  {"PATH": launcher.SAFE_PATH}, 2)
    assert result.output_limit and result.group_dead and len(result.stdout) <= 128


def test_permission_denied_is_not_group_dead_proof(monkeypatch):
    def denied(*args):
        raise PermissionError
    monkeypatch.setattr(launcher.os, "killpg", denied)
    assert launcher.stop_group(SimpleNamespace(pid=999, poll=lambda: None)) == (False, ())


def test_configuration_cancellation_prevents_any_next_phase(capsys):
    calls = []
    def cancelled(*args):
        calls.append(args)
        return launcher.ProcessResult(0, b"synthetic-secret", False, True, False, (), True)
    assert launcher.main([], runner=cancelled) == 2
    assert len(calls) == 1 and "synthetic-secret" not in capsys.readouterr().out
