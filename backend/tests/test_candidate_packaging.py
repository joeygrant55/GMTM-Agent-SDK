"""Candidate source packaging and launcher checks, without a container engine."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest
import start_candidate

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("package_candidate", ROOT / "backend/scripts/package_candidate.py")
packager = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packager)


@pytest.mark.parametrize("value", ["", "0", "65536", " 8000", "8000;echo nope", "８０００", "abc", "-1"])
def test_invalid_port_never_reaches_exec(value):
    with pytest.raises(ValueError, match="PORT"):
        start_candidate.command({"PORT": value})


def test_launcher_fixes_candidate_surface_and_runtime_options(monkeypatch):
    calls = []
    monkeypatch.setattr(start_candidate.sys, "argv", ["start_candidate.py"])
    monkeypatch.setenv("PORT", "8091")
    monkeypatch.setenv("UVICORN_WORKERS", "8")
    monkeypatch.setenv("UVICORN_RELOAD", "true")
    monkeypatch.setenv("UVICORN_ENV_FILE", "/synthetic-only/.env")
    monkeypatch.setenv("AGENT_DB_NAME", "synthetic-agent")
    monkeypatch.setattr(start_candidate.os, "execve", lambda exe, args, env: calls.append((exe, args, env)))
    start_candidate.main()
    exe, command, environment = calls[0]
    assert exe == sys.executable
    assert command[command.index("--port") + 1] == "8091"
    assert command[command.index("--workers") + 1] == "1"
    assert command[command.index("--app-dir") + 1] == str(ROOT / "backend")
    assert "candidate_app:app" in command and "main:app" not in command
    assert {"--no-access-log", "--no-proxy-headers", "--lifespan"} <= set(command)
    assert not {"--reload", "--env-file"} & set(command)
    assert not any(key.startswith("UVICORN_") for key in environment)
    assert environment["AGENT_DB_NAME"] == "synthetic-agent"
    # Parse the real installed CLI without starting a server or loading env files.
    from uvicorn.main import main as uvicorn_cli
    for key in tuple(start_candidate.os.environ):
        if key.startswith("UVICORN_"):
            monkeypatch.delenv(key)
    with uvicorn_cli.make_context("uvicorn", command[3:]) as context:
        assert context.params["reload"] is False
        assert context.params["env_file"] is None
        assert context.params["workers"] == 1


def test_launcher_rejects_extra_arguments_before_execution(monkeypatch):
    monkeypatch.setattr(start_candidate.sys, "argv", ["start_candidate.py", "--reload"])
    monkeypatch.setattr(start_candidate.os, "execve", lambda *_: pytest.fail("must not execute"))
    with pytest.raises(SystemExit, match="options are fixed"):
        start_candidate.main()


def fake_root(tmp_path):
    root = tmp_path / "source"
    for name in packager.SOURCES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    for name in (".env", "backend/.env.local", "backend/private.key", "backend/tests/private.json", "backend/main.py"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("SYNTHETIC-SECRET-SENTINEL-DO-NOT-PACK")
    return root


def test_package_is_exact_deterministic_and_excludes_unrelated_files(tmp_path):
    root = fake_root(tmp_path)
    a, b = tmp_path / "one.tar", tmp_path / "two.tar"
    report = packager.package(root, a)
    packager.package(root, b)
    assert a.read_bytes() == b.read_bytes()
    assert b"SYNTHETIC-SECRET-SENTINEL" not in a.read_bytes()
    with tarfile.open(a) as archive:
        assert archive.getnames() == list(packager.SOURCES)
        assert all(member.isfile() and member.mode == 0o644 and member.uid == 0 for member in archive.getmembers())
        for name in packager.SOURCES:
            assert archive.extractfile(name).read() == (root / name).read_bytes()
    assert report["archive_sha256"] == hashlib.sha256(a.read_bytes()).hexdigest()
    assert report["built"] is False and report["deployed"] is False
    assert json.loads(a.with_suffix(".manifest.json").read_text()) == report
    with pytest.raises(ValueError, match="new"):
        packager.package(root, a)


@pytest.mark.parametrize("problem", ["symlink", "missing", "inside", "manifest", "output_symlink", "manifest_symlink"])
def test_invalid_package_source_or_output_fails_without_partial_archive(tmp_path, problem):
    root = fake_root(tmp_path)
    output = tmp_path / "candidate.tar"
    target = root / "backend/auth.py"
    if problem in ("missing", "symlink"):
        target.unlink()
        if problem == "symlink":
            target.symlink_to(root / "backend/private.key")
    elif problem == "inside":
        output = root / "candidate.tar"
    elif problem == "manifest":
        output.with_suffix(".manifest.json").write_text("preserve")
    elif problem == "output_symlink":
        output.symlink_to(tmp_path / "unexpected.tar")
    elif problem == "manifest_symlink":
        output.with_suffix(".manifest.json").symlink_to(tmp_path / "unexpected.json")
    with pytest.raises((ValueError, FileNotFoundError)):
        packager.package(root, output)
    assert not output.exists()
    assert not (tmp_path / "unexpected.tar").exists()
    assert not (tmp_path / "unexpected.json").exists()
    if problem == "manifest":
        assert output.with_suffix(".manifest.json").read_text() == "preserve"


def test_context_and_docker_recipe_match_packager_allowlist():
    # This evaluates the intentionally constrained exact-path grammar only, not
    # a substitute Docker engine or a general dockerignore pattern matcher.
    lines = [s.strip() for s in (ROOT / "Dockerfile.candidate.dockerignore").read_text().splitlines() if s.strip() and not s.startswith("#")]
    assert lines[0] == "**"
    assert lines[lines.index("!backend/") + 1] == "backend/**"
    inclusions = [s for s in lines[1:] if s != "backend/**"]
    allowed = {s[1:] for s in inclusions if not s.endswith("/")}
    assert allowed == set(packager.SOURCES)
    assert all(s.startswith("!") and not any(c in s for c in "*?[") for s in inclusions)
    dockerfile = (ROOT / "Dockerfile.candidate").read_text()
    copied = set()
    for line in dockerfile.splitlines():
        if line.startswith("COPY "):
            copied.update(line.split()[1:-1])
    assert copied == set(packager.SOURCES) - {"Dockerfile.candidate", "Dockerfile.candidate.dockerignore"}
    assert "USER 10001:10001" in dockerfile
    assert 'ENTRYPOINT ["python", "/app/backend/start_candidate.py"]' in dockerfile
    assert "COPY backend/ ./backend/" not in dockerfile


def test_packaged_source_import_and_lifespan_are_self_contained_and_inert(tmp_path):
    root = fake_root(tmp_path)
    archive = tmp_path / "candidate.tar"
    packager.package(root, archive)
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    with tarfile.open(archive) as stream:
        # Extract only our just-verified exact regular source entries.
        for member in stream.getmembers():
            target = extracted / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(stream.extractfile(member).read())
    script = r'''
import asyncio,json,os,socket,sys,threading
from pathlib import Path
import anthropic,openai,pymysql,dotenv,httpx
attempts=[]
def deny(name):
 def block(*a,**k): attempts.append(name);raise AssertionError(name)
 return block
socket.socket.connect=deny('network')
socket.getaddrinfo=socket.gethostbyname=socket.gethostbyname_ex=deny('dns')
pymysql.connect=deny('database')
anthropic.Anthropic=anthropic.AsyncAnthropic=deny('anthropic')
openai.OpenAI=openai.AsyncOpenAI=deny('openai')
dotenv.load_dotenv=dotenv.dotenv_values=deny('dotenv')
threading.Thread.start=deny('thread')
sys.path.insert(0,sys.argv[1])
import candidate_app
assert 'main' not in sys.modules
async def run():
 asyncio.create_task=deny('background_task')
 async with candidate_app.app.router.lifespan_context(candidate_app.app):
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=candidate_app.app),base_url='http://fixture.invalid') as client:
   response=await client.get('/health')
   assert response.status_code==200,response.text
   assert response.json()['configuration_ready'] is True
   assert response.json()['connectivity_verified'] is False
asyncio.run(run())
assert attempts==[],attempts
print(json.dumps({'attempts':attempts,'surface':'combine_candidate','configuration_ready':True}))
'''
    env = {
        "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "AUTH_ENFORCED": "true",
        "CLERK_ISSUER": "https://clerk.example.invalid", "CLERK_AUTHORIZED_PARTIES": "http://127.0.0.1:3218", "ALLOWED_ORIGINS": "http://127.0.0.1:3218",
        "DB_HOST": "db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com", "DB_USER": "gmtmread", "DB_PASSWORD": "synthetic-only",
        "AGENT_DB_HOST": "127.0.0.1", "AGENT_DB_PORT": "3307", "AGENT_DB_NAME": "sparq_fixture", "AGENT_DB_USER": "fixture", "AGENT_DB_PASSWORD": "synthetic-only",
        "SHARE_TOKEN_SECRET": "synthetic-only", "COMBINE_HELP_MAX_MODEL_CALLS": "2", "COMBINE_HELP_MAX_CONCURRENT_CALLS": "1",
    }
    result = subprocess.run([sys.executable, "-I", "-c", script, str(extracted / "backend")], env=env, cwd=extracted, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["attempts"] == []
