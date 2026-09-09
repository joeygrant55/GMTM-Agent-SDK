"""Fixed metadata-only launcher behavior with synthetic Railway/child output."""
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys

import pytest
from backend.tests.test_prepare_athlete_workspace import inventory as inventory_fixture

PATH = Path(__file__).resolve().parents[1] / "scripts/run_workspace_schema_check.py"
spec = importlib.util.spec_from_file_location("workspace_check_launcher", PATH)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

MYSQL = {"MYSQLHOST": "mysql.railway.internal", "MYSQLPORT": "3306", "MYSQLUSER": "fixture",
         "MYSQLPASSWORD": "SECRET_CANARY", "MYSQLDATABASE": "railway",
         "RAILWAY_TCP_PROXY_DOMAIN": "fixture.proxy.rlwy.net", "RAILWAY_TCP_PROXY_PORT": "12345"}
BACKEND = {"AGENT_DB_" + suffix: MYSQL[key] for suffix, key in
           (("HOST", "MYSQLHOST"), ("PORT", "MYSQLPORT"), ("USER", "MYSQLUSER"), ("PASSWORD", "MYSQLPASSWORD"), ("NAME", "MYSQLDATABASE"))}
BACKEND.update(ANTHROPIC_API_KEY="PROVIDER_CANARY", DB_PASSWORD="GMTM_CANARY")


def result(value, **changes):
    fields = dict(returncode=0, stdout=json.dumps(value).encode(), timed_out=False, group_dead=True,
                  output_limit=False, cleanup_signals=(), interrupted=False)
    fields.update(changes)
    return launcher.owner.ProcessResult(**fields)


def schema_result(readiness="requires_create"):
    ready = readiness == "ready"
    return {"status": "schema_checked", "readiness": readiness, "workspace_contract_checked": ready,
            "select_attempts": 8 if ready else 5, "statement_attempts": 10 if ready else 7,
            "connected": True, "read_only_transaction_started": True, "rollback_completed": True,
            "connection_closed": True, "ddl_attempts": 0}


def fake_runner(calls, *, readiness="requires_create", child_changes=None, mismatch=False, inventory=False):
    def run(command, env, timeout):
        calls.append((command, env, timeout))
        if command[0] == str(launcher.owner.RAILWAY):
            assert command[1:3] == ["variable", "list"]
            assert command[command.index("--project") + 1] == launcher.owner.PROJECT
            assert command[command.index("--environment") + 1] == launcher.owner.ENVIRONMENT
            service = command[command.index("--service") + 1]
            if service == launcher.owner.BACKEND_SERVICE:
                return result({**BACKEND, **({"AGENT_DB_NAME": "other"} if mismatch else {})})
            assert service == launcher.owner.MYSQL_SERVICE
            return result(MYSQL)
        assert command[:5] == [str(launcher.owner.PYTHON), "-I", "-B", "-c", launcher.CHILD]
        assert ("--inventory" if inventory else "--check") in command and "--apply" not in command
        assert command[command.index("--expected-host") + 1] == "fixture.proxy.rlwy.net"
        assert command[command.index("--expected-database") + 1] == "railway"
        assert set(env) == {*BACKEND.keys() - {"ANTHROPIC_API_KEY", "DB_PASSWORD"}, "PATH", "PYTHONDONTWRITEBYTECODE"}
        assert env["AGENT_DB_HOST"] == "fixture.proxy.rlwy.net" and env["AGENT_DB_PORT"] == "12345"
        assert timeout == launcher.owner.READER_TIMEOUT
        return result(inventory_fixture() if inventory else schema_result(readiness), **(child_changes or {}))
    return run


def execute(tmp_path, runner, *, inventory=False):
    output = tmp_path / "receipt"
    code = launcher.main(["--inventory" if inventory else "--check", "--source-digest", launcher.source_state()[1], "--output", str(output)], runner=runner)
    return code, output, json.loads((output / "receipt.json").read_text())


def test_default_checks_current_binding_without_database_child(capsys):
    calls = []
    assert launcher.main([], runner=fake_runner(calls)) == 0
    assert len(calls) == 2
    value = json.loads(capsys.readouterr().out)
    assert value["status"] == "configuration_preflight" and value["database_child_started"] is False
    assert not any(text in json.dumps(value) for text in ("CANARY", "fixture.proxy", "MYSQLPASSWORD"))


@pytest.mark.parametrize("readiness", ["ready", "requires_create"])
def test_check_uses_agent_only_environment_and_private_receipt(tmp_path, capsys, readiness):
    calls = []
    code, output, receipt = execute(tmp_path, fake_runner(calls, readiness=readiness))
    assert code == 0 and len(calls) == 3 and receipt["status"] == "observed"
    assert receipt["schema"]["readiness"] == readiness
    assert receipt["schema_applied"] is False and receipt["athlete_rows_read"] is False and receipt["gmtm_accessed"] is False
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE((output / "receipt.json").stat().st_mode) == 0o600
    assert "CANARY" not in json.dumps(receipt) + capsys.readouterr().out


def test_wrong_binding_never_starts_database_child(tmp_path):
    calls = []
    code, _, receipt = execute(tmp_path, fake_runner(calls, mismatch=True))
    assert code == 1 and len(calls) == 2 and receipt["reason"] == "agent_service_binding_mismatch"
    assert receipt["database_child_started"] is False


def test_unreviewed_source_never_fetches_configuration(tmp_path):
    calls = []
    assert launcher.main(["--check", "--source-digest", "0" * 64, "--output", str(tmp_path / "unused")], runner=fake_runner(calls)) == 1
    assert not calls and not (tmp_path / "unused").exists()


@pytest.mark.parametrize("changes", [{"timed_out": True}, {"group_dead": False}, {"interrupted": True}, {"output_limit": True}, {"returncode": 1}, {"stdout": b"SECRET_CANARY not JSON"}])
def test_incomplete_or_invalid_child_is_not_success(tmp_path, capsys, changes):
    code, _, receipt = execute(tmp_path, fake_runner([], child_changes=changes))
    assert code == 1 and receipt["status"] == "blocked"
    assert "CANARY" not in json.dumps(receipt) + capsys.readouterr().out


def test_existing_receipt_cannot_be_overwritten(tmp_path):
    code, output, _ = execute(tmp_path, fake_runner([]))
    assert code == 0
    before = (output / "receipt.json").read_bytes()
    calls = []
    assert launcher.main(["--check", "--source-digest", launcher.source_state()[1], "--output", str(output)], runner=fake_runner(calls)) == 1
    assert not calls and (output / "receipt.json").read_bytes() == before


@pytest.mark.parametrize("change", [{"secret": "SECRET_CANARY"}, {"ddl_attempts": 1}, {"select_attempts": 9}, {"statement_attempts": 0}, {"rollback_completed": False}, {"connection_closed": 1}, {"read_only_transaction_started": False}, {"connected": False}, {"workspace_contract_checked": True}])
def test_schema_response_rejects_extra_fields_and_incomplete_safety_evidence(tmp_path, capsys, change):
    code, _, receipt = execute(tmp_path, fake_runner([], child_changes={"stdout": json.dumps({**schema_result(), **change}).encode()}))
    assert code == 1 and receipt["reason"] == "schema_check_response_invalid"
    assert "schema" not in receipt and "CANARY" not in json.dumps(receipt) + capsys.readouterr().out


def test_actual_isolated_child_bootstrap_preserves_argument_layout(tmp_path):
    # Default plan proves the exact bootstrap can import the sibling guard and
    # route arguments without requiring credentials or connecting to a service.
    child = subprocess.run([str(launcher.owner.PYTHON), "-I", "-B", "-c", launcher.CHILD, str(launcher.BACKEND),
                            str(launcher.BACKEND / "prepare_athlete_workspace.py")],
                           env={"PATH": launcher.owner.SAFE_PATH}, cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout)["status"] == "dry_run"


@pytest.mark.parametrize("change_at,expected_calls,reason", [(3, 2, "source_changed_before_check"), (4, 3, "source_changed_during_check")])
def test_source_changes_cannot_be_accepted(tmp_path, monkeypatch, change_at, expected_calls, reason):
    original = launcher.source_state()
    reads = 0
    def state():
        nonlocal reads
        reads += 1
        return ({**original[0], "unexpected.py": "0" * 64}, "1" * 64) if reads >= change_at else original
    monkeypatch.setattr(launcher, "source_state", state)
    calls = []
    code, _, receipt = execute(tmp_path, fake_runner(calls))
    assert code == 1 and len(calls) == expected_calls and receipt["reason"] == reason


def test_child_failure_retains_only_bounded_diagnostics(tmp_path, capsys):
    failure = {"status": "failed", "stage": "athlete_link_preflight", "reason": "existing_athlete_link_subject_type_required",
               "connected": True, "rollback_completed": True, "connection_closed": True, "ddl_attempts": 0,
               "select_attempts": 3, "statement_attempts": 5, "error": {"mysql_code": 1045, "type": "SECRET_CANARY"},
               "raw_metadata": "SECRET_CANARY", "password": "SECRET_CANARY",
               "required_link_columns": {"id": False, "user_id": True, "clerk_id": True}}
    code, _, receipt = execute(tmp_path, fake_runner([], child_changes={"returncode": 1, "stdout": json.dumps(failure).encode()}))
    assert code == 1 and receipt["reason"] == "metadata_check_failed"
    assert receipt["schema_failure"]["stage"] == "athlete_link_preflight" and receipt["schema_failure"]["mysql_code"] == 1045
    assert receipt["schema_failure"]["required_link_columns"] == {"id": False, "user_id": True, "clerk_id": True}
    assert "CANARY" not in json.dumps(receipt) + capsys.readouterr().out


def test_unknown_failure_strings_and_counts_are_not_echoed():
    safe = launcher.failure_summary({"status": "failed", "stage": "SECRET_CANARY", "reason": "SECRET_CANARY",
                                    "ddl_attempts": 1, "select_attempts": 900, "connection_closed": "SECRET_CANARY",
                                    "error": {"mysql_code": "SECRET_CANARY"}})
    assert safe == {"stage": "unknown"}


def test_inventory_reuses_exact_binding_private_receipt_and_finite_child(tmp_path, capsys):
    calls = []
    code, output, receipt = execute(tmp_path, fake_runner(calls, inventory=True), inventory=True)
    assert code == 0 and len(calls) == 3 and receipt["status"] == "observed"
    assert receipt["inventory"]["tables"]["athlete_workspaces"]["exists"] is False
    assert receipt["inventory"]["select_attempts"] == 7 and receipt["inventory"]["statement_attempts"] == 9
    assert receipt["inventory"]["server_version"] == "8.4.6"
    assert stat.S_IMODE((output / "receipt.json").stat().st_mode) == 0o600
    assert "CANARY" not in json.dumps(receipt) + capsys.readouterr().out


@pytest.mark.parametrize("defect", ["extra", "raw_default", "incomplete", "budget", "server_version", "table_scope"])
def test_inventory_child_output_is_strictly_validated_before_retention(tmp_path, capsys, defect):
    value = inventory_fixture()
    if defect == "extra": value["secret"] = "SECRET_CANARY"
    elif defect == "raw_default": value["tables"]["athlete_profiles"]["columns"][0]["default_class"] = "SECRET_CANARY"
    elif defect == "incomplete": value["rollback_completed"] = False
    elif defect == "budget": value["select_attempts"] = 8
    elif defect == "server_version": value["server_version"] = "SECRET_CANARY"
    else: value["tables"]["SECRET_CANARY"] = {}
    code, _, receipt = execute(tmp_path, fake_runner([], inventory=True, child_changes={"stdout": json.dumps(value).encode()}), inventory=True)
    assert code == 1 and receipt["reason"] == "schema_inventory_response_invalid" and "inventory" not in receipt
    assert "CANARY" not in json.dumps(receipt) + capsys.readouterr().out


def test_inventory_source_review_and_exclusive_modes_precede_configuration(tmp_path):
    calls = []
    assert launcher.main(["--inventory", "--source-digest", "0" * 64, "--output", str(tmp_path / "unused")], runner=fake_runner(calls, inventory=True)) == 1
    assert not calls and not (tmp_path / "unused").exists()
    with pytest.raises(SystemExit) as caught: launcher.main(["--inventory", "--check"], runner=fake_runner(calls))
    assert caught.value.code == 2 and not calls
