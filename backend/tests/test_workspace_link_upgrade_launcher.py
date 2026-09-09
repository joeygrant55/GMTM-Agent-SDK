"""Finite upgrade dispatch and receipt behavior with no real services."""
from copy import deepcopy
import json
import stat

import pytest

from backend.scripts import run_workspace_link_upgrade as launch


FINGERPRINT = "a" * 64
SUCCESS = {"status": "ready", "ddl_is_atomic": False,
           "attempted_statements": launch.OPERATIONS, "completed_statements": launch.OPERATIONS,
           "observations": [{"state": "needs_id_and_workspace", "fingerprint": FINGERPRINT},
                            {"state": "needs_workspace", "fingerprint": "b" * 64},
                            {"state": "ready", "fingerprint": "c" * 64}],
           "ddl_outcome_uncertain": False, "ddl_connection_closed": True}


@pytest.fixture
def stub(monkeypatch):
    calls, configurations = [], []
    config = {"AGENT_DB_HOST": "centerbeam.proxy.rlwy.net", "AGENT_DB_PORT": "15014", "AGENT_DB_NAME": "railway",
              "AGENT_DB_USER": "synthetic_user", "AGENT_DB_PASSWORD": "SECRET_CONFIG_CANARY"}
    def configuration(runner):
        configurations.append(True)
        return dict(config)
    monkeypatch.setattr(launch.check, "agent_configuration", configuration)
    def runner(command, environ, timeout):
        calls.append((command, environ, timeout))
        return launch.owner.ProcessResult(0, json.dumps(SUCCESS).encode(), False, True, False, ())
    return calls, configurations, runner


def arguments(tmp_path):
    return ["--apply", "--source-digest", launch.source_state()[1], "--schema-fingerprint", FINGERPRINT,
            "--output", str(tmp_path / "exclusive-upgrade")]


def test_default_has_no_configuration_or_child(stub, capsys):
    calls, configurations, runner = stub
    assert launch.main([], runner=runner) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "offline_upgrade_plan"
    assert calls == configurations == []


def test_explicit_apply_uses_fixed_child_private_receipt_and_agent_only_environment(stub, tmp_path, capsys):
    calls, configurations, runner = stub
    args = arguments(tmp_path)
    assert launch.main(args, runner=runner) == 0
    command, env, timeout = calls[0]
    assert command[:4] == [str(launch.owner.PYTHON), "-I", "-B", "-c"]
    assert str(launch.SCRIPT) in command and "--apply" in command and "--allow-live" in command
    assert command[-2:] == ["--expected-fingerprint", FINGERPRINT]
    assert set(env) == {"AGENT_DB_HOST", "AGENT_DB_PORT", "AGENT_DB_NAME", "AGENT_DB_USER", "AGENT_DB_PASSWORD", "PATH", "PYTHONDONTWRITEBYTECODE"}
    assert len(calls) == len(configurations) == 1 and timeout == launch.owner.READER_TIMEOUT
    directory = tmp_path / "exclusive-upgrade"
    receipt = directory / "receipt.json"
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    assert "SECRET_CONFIG_CANARY" not in capsys.readouterr().out + receipt.read_text()


@pytest.mark.parametrize("index,value", [(2, "wrong"), (4, "wrong"), (4, "b" * 63)])
def test_bad_source_or_schema_rejected_before_configuration(stub, tmp_path, index, value):
    calls, configurations, runner = stub
    args = arguments(tmp_path); args[index] = value
    assert launch.main(args, runner=runner) == 1
    assert calls == configurations == []


def test_existing_receipt_directory_rejected_without_retry(stub, tmp_path):
    calls, configurations, runner = stub
    (tmp_path / "exclusive-upgrade").mkdir()
    assert launch.main(arguments(tmp_path), runner=runner) == 1
    assert calls == configurations == []


@pytest.mark.parametrize("change", [{"ddl_outcome_uncertain": True}, {"ddl_connection_closed": False},
    {"completed_statements": []}, {"observations": []}, {"attempted_statements": ["delete_anything"]},
    {"ddl_is_atomic": True}])
def test_incomplete_or_invalid_success_is_never_accepted(change):
    with pytest.raises(launch.owner.Blocked):
        launch.safe_result({**deepcopy(SUCCESS), **change})


def test_arbitrary_error_fields_never_retained():
    value = launch.safe_result({**deepcopy(SUCCESS), "status": "failed", "error": "SECRET_DRIVER_CANARY",
                                "stage": "SECRET_STAGE_CANARY", "reason": "SECRET_REASON_CANARY"})
    assert "CANARY" not in json.dumps(value)


def test_failed_metadata_cleanup_evidence_is_retained_without_raw_error():
    failure = {"connected": True, "read_only_transaction_started": True, "rollback_completed": True,
               "connection_closed": False, "select_attempts": 7, "statement_attempts": 9, "ddl_attempts": 0}
    value = launch.safe_result({**deepcopy(SUCCESS), "status": "failed", "inventory_attempts": 2,
                                "metadata_failure": failure, "error": "SECRET"})
    assert value["metadata_failure"] == failure and value["inventory_attempts"] == 2
    assert "SECRET" not in json.dumps(value)
    for invalid in ({**failure, "sql": "secret"}, {**failure, "select_attempts": 8}, {**failure, "connection_closed": 1}):
        with pytest.raises(launch.owner.Blocked):
            launch.safe_result({**deepcopy(SUCCESS), "status": "failed", "metadata_failure": invalid})


@pytest.mark.parametrize("failure", ["timeout", "interrupted", "alive", "overflow", "partial"])
def test_failed_child_is_not_retried_or_reported_ready(stub, tmp_path, failure):
    calls, _, _ = stub
    def runner(command, env, timeout):
        calls.append(command)
        value = {**SUCCESS, "status": "failed", "ddl_outcome_uncertain": True,
                 "completed_statements": ["add_link_id"], "stage": "create_athlete_workspaces"}
        return launch.owner.ProcessResult(1, json.dumps(value).encode(), failure == "timeout", failure != "alive",
                                          failure == "overflow", (), failure == "interrupted")
    assert launch.main(arguments(tmp_path), runner=runner) == 1
    assert len(calls) == 1
    report = json.loads((tmp_path / "exclusive-upgrade" / "receipt.json").read_text())
    assert report["status"] == "blocked" and "reconcile" in report["reason"]
    if failure == "partial":
        assert report["upgrade"]["completed_statements"] == ["add_link_id"]


def test_source_drift_after_child_requires_reconciliation(stub, tmp_path, monkeypatch):
    _, _, runner = stub
    args = arguments(tmp_path)
    original = launch.source_state
    count = 0
    def state():
        nonlocal count
        count += 1
        hashes, digest = original()
        return ({**hashes, "drift": "f" * 64} if count == 3 else hashes), digest
    monkeypatch.setattr(launch, "source_state", state)
    assert launch.main(args, runner=runner) == 1
    report = json.loads((tmp_path / "exclusive-upgrade" / "receipt.json").read_text())
    assert report["status"] == "blocked" and report["reason"] == "source_changed_during_upgrade_reconcile_server"
