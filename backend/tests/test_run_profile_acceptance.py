"""Offline checks for the finite real-profile launcher; no cloud or services."""
import base64
import json
from pathlib import Path

import pytest

from scripts import run_profile_acceptance as launch


def api_fixture(*, duplicate=False, wrong_project=False, wrong_issuer=False):
    public = "pk_test_" + base64.b64encode(
        (("wrong.clerk.accounts.dev" if wrong_issuer else launch.ISSUER_HOST) + "$").encode()).decode().rstrip("=")
    values = {"public": ("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", public),
              "secret": ("CLERK_SECRET_KEY", "sk_test_synthetic")}
    calls = []
    def api(path):
        calls.append(path)
        if path.startswith("/v4/aliases/"):
            return {"projectId": "wrong" if wrong_project else launch.PROJECT, "alias": "sparq-agent.vercel.app"}
        if path.startswith("/v10/"):
            envs = [{"key": key, "id": id, "target": ["production"]} for id,(key,_) in values.items()]
            return {"envs": envs + ([envs[0]] if duplicate else [])}
        id = path.split("/env/")[1].split("?")[0]
        key, value = values[id]
        return {"key": key, "value": "  " + value + "\n"}
    return api,calls


def test_clerk_reads_only_bound_pair_and_normalizes_tokens():
    api,calls = api_fixture()
    result = launch.clerk_settings(api)
    assert set(result) == {"NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "CLERK_SECRET_KEY"}
    assert result["CLERK_SECRET_KEY"] == "sk_test_synthetic"
    assert len(calls) == 4


@pytest.mark.parametrize("option", ["duplicate", "wrong_project", "wrong_issuer"])
def test_clerk_binding_ambiguity_or_wrong_issuer_blocks(option):
    api,_ = api_fixture(**{option: True})
    with pytest.raises(launch.owner.Blocked):
        launch.clerk_settings(api)


def test_child_environments_exclude_inherited_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "never-forward")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "never-forward")
    config = {"DB_PASSWORD": " exact password ", "AGENT_DB_PASSWORD": " exact agent "}
    backend,frontend = launch.environments(config, {"CLERK_SECRET_KEY": "synthetic"}, 4567, 4568, tmp_path)
    assert backend["DB_PASSWORD"] == " exact password "
    assert backend["AGENT_DB_PASSWORD"] == " exact agent "
    assert backend["AUTH_ENFORCED"] == "true"
    assert backend["CLERK_AUTHORIZED_PARTIES"] == backend["ALLOWED_ORIGINS"] == "http://localhost:4567"
    assert backend["PROFILE_DEBRIEF_ENABLED"] == "false"
    assert frontend["NEXT_PUBLIC_APP_SURFACE"] == "profile"
    assert frontend["NEXT_PUBLIC_BACKEND_URL"] == "http://127.0.0.1:4568"
    assert "CLERK_SECRET_KEY" not in backend
    assert "DB_PASSWORD" not in frontend
    for env in (backend,frontend):
        assert "OPENAI_API_KEY" not in env and "ANTHROPIC_API_KEY" not in env


def test_readonly_flag_reaches_child_and_is_reported(monkeypatch, tmp_path):
    backend,_ = launch.environments({}, {}, 4567, 4568, tmp_path, read_only=True)
    assert backend["ACCEPTANCE_READ_ONLY"] == "1"
    calls=[]
    monkeypatch.setattr(launch, "launch", lambda path, seconds, **kwargs: calls.append((path,seconds,kwargs)) or 0)
    assert launch.main(["--run-dir",str(tmp_path),"--launch","--read-only"])==0
    assert calls==[(tmp_path,600,{"read_only":True})]


def test_default_never_launches_or_reads_configuration(monkeypatch, tmp_path, capsys):
    prepared = []
    monkeypatch.setattr(launch, "prepare", lambda path: prepared.append(path))
    def forbidden(*a, **kw):
        pytest.fail("offline mode attempted network or launch")
    monkeypatch.setattr(launch, "launch", forbidden)
    monkeypatch.setattr(launch.owner, "variables", forbidden)
    monkeypatch.setattr(launch, "clerk_settings", forbidden)
    assert launch.main(["--run-dir", str(tmp_path / "run")]) == 0
    assert prepared == [tmp_path / "run"]
    assert json.loads(capsys.readouterr().out)["services_started"] is False


@pytest.mark.parametrize("seconds", [0,59,901,999999])
def test_bad_duration_stops_before_configuration(monkeypatch, tmp_path, seconds):
    monkeypatch.setattr(launch, "verify", lambda path: None)
    monkeypatch.setattr(launch.owner, "variables", lambda *a: pytest.fail("network"))
    with pytest.raises(launch.owner.Blocked):
        launch.launch(tmp_path, seconds)
    assert not (tmp_path / "launch-reserved.json").exists()


def test_launch_reservation_cannot_replay(monkeypatch, tmp_path):
    monkeypatch.setattr(launch, "verify", lambda path: None)
    launch.write_new(tmp_path / "launch-reserved.json", {"single_use": True})
    monkeypatch.setattr(launch.owner, "variables", lambda *a: pytest.fail("network"))
    with pytest.raises(FileExistsError):
        launch.launch(tmp_path, 60)


def test_snapshot_rejects_injected_code_and_keeps_preparation_offline(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    (root / "frontend").mkdir(parents=True)
    (root / "frontend/next.config.js").write_text("module.exports = {}")
    modules = tmp_path / "modules"
    modules.mkdir()
    monkeypatch.setattr(launch, "ROOT", root)
    monkeypatch.setattr(launch, "MODULES", modules)
    monkeypatch.setattr(launch, "source_names", lambda root: ["frontend/next.config.js"])
    monkeypatch.setattr(launch.owner, "variables", lambda *a: pytest.fail("network"))
    directory = tmp_path / "run"
    launch.prepare(directory)
    launch.verify(directory)
    (directory / "source/sitecustomize.py").write_text("raise RuntimeError('not reviewed')")
    with pytest.raises(launch.owner.Blocked, match="snapshot_unreviewed_file"):
        launch.verify(directory)


def test_config_failure_has_receipt_without_values(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(launch, "verify", lambda path: None)
    def fail(*a):
        raise RuntimeError("secret-canary")
    monkeypatch.setattr(launch.owner, "variables", fail)
    assert launch.launch(tmp_path, 60) == 2
    receipt = (tmp_path / "supervisor.json").read_text()
    assert json.loads(receipt)["status"] == "blocked_configuration"
    assert "secret-canary" not in receipt + capsys.readouterr().out


def test_second_child_start_failure_cleans_first_owned_group(monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.setattr(launch, "verify", lambda path: None)
    monkeypatch.setattr(launch.owner, "variables", lambda *a: {})
    monkeypatch.setattr(launch.owner, "fable_credentials", lambda: {})
    monkeypatch.setattr(launch.owner, "configuration", lambda *a: {})
    monkeypatch.setattr(launch, "clerk_settings", lambda: {})
    ports = iter([4541,4542])
    monkeypatch.setattr(launch, "free_port", lambda host: next(ports))
    calls, stopped = [], []
    child = SimpleNamespace(pid=123456,returncode=None)
    def popen(*a, **kw):
        calls.append(kw)
        if len(calls) == 2:
            raise OSError("synthetic second child failure")
        return child
    def stop(process, **kw):
        stopped.append(process)
        process.returncode = -15
        return True,("SIGTERM",)
    monkeypatch.setattr(launch.subprocess, "Popen", popen)
    monkeypatch.setattr(launch.owner, "stop_group", stop)
    assert launch.launch(tmp_path, 60) == 2
    assert stopped == [child]
    assert all(call["start_new_session"] and call["close_fds"] for call in calls)
    receipt = json.loads((tmp_path / "supervisor.json").read_text())
    assert receipt["children"]["backend"]["group_dead"]


@pytest.mark.parametrize("name", [".env.local", "node_modules", "secret.pem", "private.key", "backend_env.json", "env.yaml"])
def test_excludes_secret_and_generated_paths(name):
    assert not launch.included(name)
