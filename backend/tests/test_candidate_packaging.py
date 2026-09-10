"""Candidate source packaging and launcher checks, without a container engine."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from types import SimpleNamespace

import pytest
import start_candidate
import start_profile_candidate

ROOT = Path(__file__).resolve().parents[2]

def _load_packager(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"backend/scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


packager = _load_packager("package_candidate")
profile_packager = _load_packager("package_profile_candidate")


@pytest.fixture(params=["combine", "profile"])
def candidate(request):
    if request.param == "profile":
        return SimpleNamespace(surface="profile", packager=profile_packager, launcher=start_profile_candidate,
                               entry="profile_candidate_app", dockerfile="Dockerfile.profile-candidate",
                               launcher_name="start_profile_candidate.py", kind="profile_candidate_source_context")
    return SimpleNamespace(surface="combine", packager=packager, launcher=start_candidate,
                           entry="candidate_app", dockerfile="Dockerfile.candidate",
                           launcher_name="start_candidate.py", kind="candidate_source_context")


@pytest.mark.parametrize("value", ["", "0", "65536", " 8000", "8000;echo nope", "８０００", "abc", "-1"])
def test_invalid_port_never_reaches_exec(value, candidate):
    with pytest.raises(ValueError, match="PORT"):
        candidate.launcher.command({"PORT": value})


def test_launcher_fixes_candidate_surface_and_runtime_options(monkeypatch, candidate):
    launcher = candidate.launcher
    calls = []
    monkeypatch.setattr(launcher.sys, "argv", [candidate.launcher_name])
    monkeypatch.setenv("PORT", "8091")
    monkeypatch.setenv("UVICORN_WORKERS", "8")
    monkeypatch.setenv("UVICORN_RELOAD", "true")
    monkeypatch.setenv("UVICORN_ENV_FILE", "/synthetic-only/.env")
    monkeypatch.setenv("UVICORN_APP", "main:app")
    monkeypatch.setenv("SPARQ_CANDIDATE_SURFACE", "unexpected")
    monkeypatch.setenv("AGENT_DB_NAME", "synthetic-agent")
    monkeypatch.setattr(launcher.os, "execve", lambda exe, args, env: calls.append((exe, args, env)))
    launcher.main()
    exe, command, environment = calls[0]
    assert exe == sys.executable
    assert command[command.index("--port") + 1] == "8091"
    assert command[command.index("--workers") + 1] == "1"
    assert command[command.index("--app-dir") + 1] == str(ROOT / "backend")
    assert command[3] == f"{candidate.entry}:app" and "main:app" not in command
    assert {"--no-access-log", "--no-proxy-headers", "--lifespan"} <= set(command)
    assert not {"--reload", "--env-file"} & set(command)
    assert not any(key.startswith("UVICORN_") for key in environment)
    assert environment["AGENT_DB_NAME"] == "synthetic-agent"
    # Parse the real installed CLI without starting a server or loading env files.
    from uvicorn.main import main as uvicorn_cli
    for key in tuple(launcher.os.environ):
        if key.startswith("UVICORN_"):
            monkeypatch.delenv(key)
    with uvicorn_cli.make_context("uvicorn", command[3:]) as context:
        assert context.params["reload"] is False
        assert context.params["env_file"] is None
        assert context.params["workers"] == 1


def test_launcher_rejects_extra_arguments_before_execution(monkeypatch, candidate):
    monkeypatch.setattr(candidate.launcher.sys, "argv", [candidate.launcher_name, "--reload"])
    monkeypatch.setattr(candidate.launcher.os, "execve", lambda *_: pytest.fail("must not execute"))
    with pytest.raises(SystemExit, match="options are fixed"):
        candidate.launcher.main()


def fake_root(tmp_path, candidate):
    root = tmp_path / "source"
    for name in candidate.packager.SOURCES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    for name in (".env", "backend/.env.local", "backend/private.key", "backend/tests/private.json", "backend/main.py",
                 "backend/scripts/prepare_agent_schema.py", "backend/enrichment_worker.py"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("SYNTHETIC-SECRET-SENTINEL-DO-NOT-PACK")
    return root


def test_package_is_exact_deterministic_and_excludes_unrelated_files(tmp_path, candidate):
    packager = candidate.packager
    root = fake_root(tmp_path, candidate)
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
    assert report["kind"] == candidate.kind
    assert report["built"] is False and report["deployed"] is False
    assert "no container engine, Linux installation or image digest has been verified" in report["limits"]
    assert json.loads(a.with_suffix(".manifest.json").read_text()) == report
    with pytest.raises(ValueError, match="new"):
        packager.package(root, a)


@pytest.mark.parametrize("problem", ["symlink", "missing", "inside", "manifest", "output_symlink", "manifest_symlink"])
def test_invalid_package_source_or_output_fails_without_partial_archive(tmp_path, problem, candidate):
    packager = candidate.packager
    root = fake_root(tmp_path, candidate)
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


def test_context_and_docker_recipe_match_packager_allowlist(candidate):
    packager = candidate.packager
    # This evaluates the intentionally constrained exact-path grammar only, not
    # a substitute Docker engine or a general dockerignore pattern matcher.
    lines = [s.strip() for s in (ROOT / f"{candidate.dockerfile}.dockerignore").read_text().splitlines() if s.strip() and not s.startswith("#")]
    assert lines[0] == "**"
    assert lines[lines.index("!backend/") + 1] == "backend/**"
    inclusions = [s for s in lines[1:] if s != "backend/**"]
    allowed = {s[1:] for s in inclusions if not s.endswith("/")}
    assert allowed == set(packager.SOURCES)
    assert all(s.startswith("!") and not any(c in s for c in "*?[") for s in inclusions)
    dockerfile = (ROOT / candidate.dockerfile).read_text()
    copied = set()
    for line in dockerfile.splitlines():
        if line.startswith("COPY "):
            copied.update(line.split()[1:-1])
    assert copied == set(packager.SOURCES) - {candidate.dockerfile, f"{candidate.dockerfile}.dockerignore"}
    assert "USER 10001:10001" in dockerfile
    assert f'ENTRYPOINT ["python", "/app/backend/{candidate.launcher_name}"]' in dockerfile
    assert "COPY backend/ ./backend/" not in dockerfile


def test_packaged_source_import_and_lifespan_are_self_contained_and_inert(tmp_path, candidate):
    packager = candidate.packager
    root = fake_root(tmp_path, candidate)
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
import asyncio,importlib,json,os,socket,sys,threading
from pathlib import Path
from unittest.mock import patch
attempts=[]
def deny(name):
 def block(*a,**k): attempts.append(name);raise AssertionError(name)
 return block
def audit(event,args):
 if event == 'socket.getaddrinfo' or (event == 'socket.connect' and args[0].family in (socket.AF_INET,socket.AF_INET6)):
  deny('network')()
 if event == 'open' and isinstance(args[0],(str,bytes)) and os.path.basename(os.fsdecode(args[0])).startswith('.env'):
  deny('dotenv-file')()
 if event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn','os.fork'):
  deny('process')()
sys.addaudithook(audit)
import anthropic,openai,pymysql,dotenv,httpx
socket.socket.connect=deny('network')
socket.getaddrinfo=socket.gethostbyname=socket.gethostbyname_ex=deny('dns')
pymysql.connect=deny('database')
pymysql.connections.Connection.connect=deny('database')
anthropic.Anthropic=anthropic.AsyncAnthropic=deny('anthropic')
openai.OpenAI=openai.AsyncOpenAI=deny('openai')
dotenv.load_dotenv=dotenv.dotenv_values=deny('dotenv')
threading.Thread.start=deny('thread')
sys.path.insert(0,sys.argv[1])
entry=importlib.import_module(sys.argv[2])
surface=sys.argv[3]
app=entry.app
assert not any(name in sys.modules for name in ('main','agent_api','artifacts_api','reports_api','search_api','enrichment_worker'))
profile_modules=('profile_candidate_app','athlete_evidence','athlete_materials','athlete_workspace','athlete_opportunities','opportunity_catalog','profile_debrief','profile_pathways','source_scope')
if surface == 'profile':
 assert all(name in sys.modules for name in profile_modules)
 assert all(Path(sys.modules[name].__file__).parent == Path(sys.argv[1]) for name in profile_modules)
 assert sys.modules['profile_debrief']._ledger_state is None
else:
 assert not any(name in sys.modules for name in profile_modules)
import model_usage
assert model_usage._ledger is None
expected={
 ('GET','/api/profile/by-clerk/{clerk_id}'),('GET','/api/claims/{token}'),
 ('POST','/api/claims/{token}/redeem'),('GET','/health'),
}
if surface == 'profile':
 expected.update({('GET','/api/athlete/evidence'),('GET','/api/athlete/materials'),
                  ('POST','/api/athlete/debrief'),('POST','/api/athlete/opportunities'),('GET','/api/athlete/workspace'),('PATCH','/api/athlete/workspace')})
else:
 expected.update({('GET','/api/combine/current'),('POST','/api/combine/help')})
assert {(method,route.path) for route in app.routes for method in route.methods} == expected
async def run():
 loop=asyncio.get_running_loop()
 # Block all new task scheduling during startup/shutdown. Normal HTTP middleware
 # uses task groups, so request execution below runs after these guards restore.
 with patch.object(loop,'create_task',deny('background_task')),patch.object(asyncio,'create_task',deny('background_task')):
  async with app.router.lifespan_context(app):
   assert app.state.candidate_configuration is not None
   assert model_usage._ledger is None
 assert app.state.candidate_configuration is None
 async with app.router.lifespan_context(app):
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://fixture.invalid') as client:
   response=await client.get('/health')
   assert response.status_code==200,response.text
   assert response.json()['configuration_ready'] is True
   assert response.json()['surface']==surface+'_candidate'
   assert all(response.json()[key] is False for key in ('connectivity_verified','schema_verified','provider_delivery_verified'))
   denied=[('GET','/docs'),('GET','/openapi.json'),('POST','/api/profile/connect'),
           ('POST','/api/claims/mint'),('GET','/api/reports/public/token')]
   if surface == 'profile':
    assert response.json()['debrief_enabled'] is False
    assert response.json()['debrief_provider_configured'] is False
    assert response.headers['cache-control']=='private, no-store'
    denied.extend([('GET','/api/combine/current'),('POST','/api/combine/help'),
                   ('POST','/api/athlete/workspace'),('DELETE','/api/athlete/workspace')])
    for method,path,body in [('GET','/api/athlete/evidence',None),('GET','/api/athlete/materials',None),
                             ('GET','/api/athlete/workspace',None),('PATCH','/api/athlete/workspace',{}),
                             ('POST','/api/athlete/debrief',{'track':'profile','question':'What can I use?'})]:
     protected=await client.request(method,path,json=body)
     assert protected.status_code==401,(path,protected.text)
     assert protected.headers['cache-control']=='private, no-store'
   else:
    denied.extend([('GET','/api/athlete/evidence'),('GET','/api/athlete/materials'),
                   ('POST','/api/athlete/debrief'),('GET','/api/athlete/workspace'),('PATCH','/api/athlete/workspace')])
   for method,path in denied:
    blocked=await client.request(method,path)
    assert blocked.status_code in (404,405),(path,blocked.text)
   assert model_usage._ledger is None
   if surface == 'profile':
    assert sys.modules['profile_debrief']._ledger_state is None
 assert app.state.candidate_configuration is None
asyncio.run(run())
assert attempts==[],attempts
print(json.dumps({'attempts':attempts,'surface':surface+'_candidate','configuration_ready':True}))
'''
    env = {
        "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "AUTH_ENFORCED": "true",
        "CLERK_ISSUER": "https://clerk.example.invalid", "CLERK_AUTHORIZED_PARTIES": "http://127.0.0.1:3218", "ALLOWED_ORIGINS": "http://127.0.0.1:3218",
        "DB_HOST": "db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com", "DB_USER": "gmtmread", "DB_PASSWORD": "synthetic-only",
        "AGENT_DB_HOST": "127.0.0.1", "AGENT_DB_PORT": "3307", "AGENT_DB_NAME": "sparq_fixture", "AGENT_DB_USER": "fixture", "AGENT_DB_PASSWORD": "synthetic-only",
        "SHARE_TOKEN_SECRET": "synthetic-only", "COMBINE_HELP_MAX_MODEL_CALLS": "2", "COMBINE_HELP_MAX_CONCURRENT_CALLS": "1",
    }
    result = subprocess.run([sys.executable, "-I", "-c", script, str(extracted / "backend"), candidate.entry, candidate.surface], env=env, cwd=extracted, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["attempts"] == []


def test_separate_profile_packaging_preserves_the_original_combine_source_set():
    original_combine = {
        "Dockerfile.candidate", "Dockerfile.candidate.dockerignore",
        "backend/requirements-candidate.txt", "backend/constraints-candidate.txt",
        "backend/auth.py", "backend/candidate_app.py", "backend/claims_api.py",
        "backend/combine_api.py", "backend/combine_context.py", "backend/combine_help_api.py",
        "backend/combine_model.py", "backend/combine_requirements.py", "backend/combine_results.py",
        "backend/model_usage.py", "backend/profile_api.py", "backend/workspace_bootstrap.py",
        "backend/start_candidate.py",
    }
    assert set(packager.SOURCES) == original_combine
    assert set(profile_packager.SOURCES) - original_combine == {
        "Dockerfile.profile-candidate", "Dockerfile.profile-candidate.dockerignore",
        "backend/profile_candidate_app.py", "backend/athlete_evidence.py", "backend/athlete_materials.py",
        "backend/athlete_workspace.py", "backend/profile_debrief.py", "backend/profile_pathways.py",
        "backend/source_scope.py", "backend/start_profile_candidate.py",
        "backend/athlete_opportunities.py", "backend/opportunity_catalog.py",
    }
    assert original_combine - set(profile_packager.SOURCES) == {
        "Dockerfile.candidate", "Dockerfile.candidate.dockerignore", "backend/start_candidate.py",
    }
