"""Finite local, real-owner profile acceptance. Default preparation is offline.

Never deploys or edits configuration. Existing cloud credentials stay in RAM and
child environments. A fresh outside-Git directory owns source snapshots, a fixed
save budget and private before-state. --launch is explicit and single use.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

if __package__:
    from . import run_owner_profile_read as owner
    from .package_profile_candidate import SOURCES
else:
    import run_owner_profile_read as owner
    from package_profile_candidate import SOURCES

ROOT = Path(__file__).resolve().parents[2]
NODE = Path("/Users/joey/.nvm/versions/node/v24.13.0/bin/node")
VERCEL = NODE.with_name("vercel")
MODULES = Path("/Users/joey/GMTM-Agent-SDK/frontend/node_modules")
TEAM = "team_MWkBYZjV9ioig70uN2z1aXFe"
PROJECT = "prj_sJqoTAT5ncQV8fCDktWCM27I1mbD"
ISSUER_HOST = "fit-bonefish-6.clerk.accounts.dev"
EXTRA = (
    "backend/verification/profile_acceptance.py",
    "backend/scripts/run_profile_acceptance.py",
    "backend/scripts/run_owner_profile_read.py",
    "backend/scripts/read_owner_profile_evidence.py",
    "backend/scripts/package_profile_candidate.py",
    "backend/scripts/package_candidate.py",
)
EXCLUDED = {"node_modules", ".next", ".git", ".vercel", ".secrets", "secrets",
            "__pycache__", "tsconfig.tsbuildinfo", ".DS_Store", "next-env.d.ts"}


def write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def included(name):
    return (name not in EXCLUDED and not name.startswith(".env")
            and not name.endswith(("_env.json", ".pem", ".key", ".log"))
            and name not in {"env.yml", "env.yaml"})


def source_names(root):
    names = set(SOURCES) | set(EXTRA)
    for directory, dirs, files in os.walk(root / "frontend", followlinks=False):
        dirs[:] = sorted(name for name in dirs if included(name))
        for name in dirs + files:
            path = Path(directory) / name
            if included(name) and path.is_symlink():
                raise owner.Blocked("source_symlink_forbidden")
        names.update(str((Path(directory) / name).relative_to(root))
                     for name in files if included(name))
    return sorted(names)


def hashes(root, names):
    return {name: hashlib.sha256(owner.read_regular(root / name, 32 * 1024 * 1024)).hexdigest()
            for name in names}


def prepare(directory):
    directory = owner.output_path(str(directory), must_be_new=True)
    names = source_names(ROOT)
    manifest = hashes(ROOT, names)
    directory.mkdir(mode=0o700)
    snapshot = directory / "source"
    for name in names:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        data = owner.read_regular(ROOT / name, 32 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != manifest[name]:
            raise owner.Blocked("source_changed_during_preparation")
        target.write_bytes(data)
    (snapshot / "frontend/node_modules").symlink_to(MODULES, target_is_directory=True)
    write_new(directory / "source-manifest.json", manifest)
    write_new(directory / "prepared.json", {"file_count": len(names), "source": str(ROOT),
              "snapshot": str(snapshot), "configuration_read": False, "services_started": False})
    verify(directory)


def verify(directory):
    directory = owner.output_path(str(directory), must_be_new=False)
    if directory.stat().st_mode & 0o777 != 0o700 or directory.stat().st_uid != os.getuid():
        raise owner.Blocked("private_run_directory_required")
    manifest = json.loads(owner.read_regular(directory / "source-manifest.json", 1024 * 1024))
    if set(manifest) != set(source_names(ROOT)) or hashes(ROOT, manifest) != manifest:
        raise owner.Blocked("prepared_source_changed")
    if hashes(directory / "source", manifest) != manifest:
        raise owner.Blocked("snapshot_changed")
    dependency = directory / "source/frontend/node_modules"
    if not dependency.is_symlink() or dependency.resolve() != MODULES.resolve():
        raise owner.Blocked("dependency_path_changed")
    # Check additions too: a generated Next type declaration is safe, env files are not.
    for folder, dirs, files in os.walk(directory / "source", followlinks=False):
        dirs[:] = [name for name in dirs if name not in {"node_modules", ".next", "__pycache__"}]
        if any((Path(folder) / name).is_symlink() for name in dirs):
            raise owner.Blocked("snapshot_symlink_forbidden")
        for name in files:
            if name.startswith(".env") or name.endswith((".pem", ".key", "_env.json")):
                raise owner.Blocked("snapshot_secret_file_forbidden")
            path = Path(folder) / name
            relative = str(path.relative_to(directory / "source"))
            if path.is_symlink() or (relative not in manifest and relative not in {
                "frontend/next-env.d.ts", "frontend/tsconfig.tsbuildinfo"}):
                raise owner.Blocked("snapshot_unreviewed_file")


def vercel_api(path, runner=owner.run_bounded):
    result = runner([str(VERCEL), "api", path, "--method", "GET", "--raw"],
                    {"HOME": "/Users/joey", "PATH": str(NODE.parent) + ":/usr/bin:/bin"}, 30)
    owner.require_process(result)
    try:
        value = json.loads(result.stdout)
    except (ValueError, UnicodeError):
        raise owner.Blocked("clerk_configuration_response_invalid") from None
    if not isinstance(value, dict):
        raise owner.Blocked("clerk_configuration_response_invalid")
    return value


def clerk_settings(api=vercel_api):
    alias = api("/v4/aliases/sparq-agent.vercel.app?teamId=" + TEAM)
    if alias.get("projectId") != PROJECT or alias.get("alias") != "sparq-agent.vercel.app":
        raise owner.Blocked("frontend_identity_changed")
    records = api("/v10/projects/" + PROJECT + "/env?teamId=" + TEAM).get("envs", [])
    result = {}
    for key in ("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "CLERK_SECRET_KEY"):
        matches = [r for r in records if isinstance(r, dict) and r.get("key") == key
                   and "production" in r.get("target", []) and not r.get("gitBranch")]
        if len(matches) != 1 or not isinstance(matches[0].get("id"), str):
            raise owner.Blocked("clerk_configuration_ambiguous")
        value = api("/v1/projects/" + PROJECT + "/env/" + matches[0]["id"] + "?teamId=" + TEAM)
        if value.get("key") != key or not isinstance(value.get("value"), str):
            raise owner.Blocked("clerk_configuration_missing")
        result[key] = value["value"].strip()
    public = result["NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"]
    if not public.startswith("pk_test_") or not result["CLERK_SECRET_KEY"].startswith("sk_test_"):
        raise owner.Blocked("existing_development_clerk_required")
    encoded = public.split("_", 2)[2]
    try:
        decoded = base64.b64decode(encoded + "=" * (-len(encoded) % 4), validate=True).decode()
    except (ValueError, UnicodeError):
        raise owner.Blocked("clerk_issuer_invalid") from None
    if decoded != ISSUER_HOST + "$":
        raise owner.Blocked("clerk_issuer_mismatch")
    return result


def free_port(host):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def environments(config, clerk, frontend_port, backend_port, directory):
    origin = f"http://localhost:{frontend_port}"
    host = f"127.0.0.1:{backend_port}"
    base = {"HOME": "/Users/joey", "PATH": str(NODE.parent) + ":/usr/bin:/bin",
            "LANG": "en_US.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
    backend = {**base, **config, "AUTH_ENFORCED": "true",
               "CLERK_ISSUER": "https://" + ISSUER_HOST,
               "CLERK_AUTHORIZED_PARTIES": origin, "ALLOWED_ORIGINS": origin,
               "SHARE_TOKEN_SECRET": secrets.token_urlsafe(32),
               "COMBINE_HELP_TEST_MODE": "1", "COMBINE_HELP_MAX_MODEL_CALLS": "1",
               "COMBINE_HELP_MAX_CONCURRENT_CALLS": "1", "PROFILE_DEBRIEF_ENABLED": "false",
               "ACCEPTANCE_RUN_DIR": str(directory), "ACCEPTANCE_BACKEND_HOST": host}
    frontend = {**base, **clerk, "NEXT_PUBLIC_APP_SURFACE": "profile",
                "NEXT_PUBLIC_BACKEND_URL": "http://" + host, "NEXT_TELEMETRY_DISABLED": "1",
                "NEXT_PUBLIC_CLERK_SIGN_IN_URL": "/sign-in", "NEXT_PUBLIC_CLERK_SIGN_UP_URL": "/sign-up",
                "NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL": "/home/inbox"}
    return backend, frontend


CHILD = """
import os, uvicorn
from verification.profile_acceptance import create_acceptance_app
def settings(prefix):
    return {key: (int(os.environ[prefix+suffix]) if key == 'port' else os.environ[prefix+suffix])
            for key,suffix in [('host','HOST'),('port','PORT'),('user','USER'),
                               ('password','PASSWORD'),('database','NAME')]}
app = create_acceptance_app(agent_settings=settings('AGENT_DB_'),gmtm_settings=settings('DB_'),
    frontend_origin=os.environ['ALLOWED_ORIGINS'],backend_host=os.environ['ACCEPTANCE_BACKEND_HOST'],
    run_dir=os.environ['ACCEPTANCE_RUN_DIR'])
uvicorn.run(app,host='127.0.0.1',port=int(os.environ['ACCEPTANCE_BACKEND_HOST'].split(':')[1]),
            workers=1,access_log=False,log_level='critical',proxy_headers=False)
"""


def launch(directory, seconds):
    verify(directory)
    if not 60 <= seconds <= 900:
        raise owner.Blocked("duration_outside_60_to_900_seconds")
    write_new(directory / "launch-reserved.json", {"single_use": True, "seconds": seconds})
    children = []
    interrupted = False
    status = "configuration"
    frontend_port = backend_port = None
    def stop(signum, frame):
        nonlocal interrupted
        interrupted = True
    previous = {sig: signal.signal(sig, stop) for sig in owner.INTERRUPT_SIGNALS}
    try:
        config = owner.configuration(owner.variables(owner.BACKEND_SERVICE),
                                     owner.variables(owner.MYSQL_SERVICE), owner.fable_credentials())
        clerk = clerk_settings()
        verify(directory)
        if interrupted:
            raise owner.Blocked("launch_interrupted")
        frontend_port, backend_port = free_port("127.0.0.1"), free_port("127.0.0.1")
        if frontend_port == backend_port:
            raise owner.Blocked("ports_collided")
        backend_env, frontend_env = environments(config, clerk, frontend_port, backend_port, directory)
        deadline = time.monotonic() + seconds
        for name, command, env, cwd in (
            ("backend", [str(owner.PYTHON), "-c", CHILD], backend_env, directory / "source/backend"),
            ("frontend", [str(NODE), str(MODULES / "next/dist/bin/next"), "dev", "-H", "localhost", "-p", str(frontend_port)],
             frontend_env, directory / "source/frontend"),
        ):
            if interrupted:
                raise owner.Blocked("launch_interrupted")
            process = subprocess.Popen(command, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       start_new_session=True, close_fds=True)
            children.append((name, process))
        write_new(directory / "processes.json", {"groups": {name: p.pid for name,p in children},
                  "frontend_port": frontend_port, "backend_port": backend_port})
        status = "starting"
        ready = False
        while time.monotonic() < deadline and not interrupted and not (directory / "STOP").exists():
            if any(p.poll() is not None for _,p in children):
                status = "child_exited"
                break
            if not ready:
                try:
                    with urlopen(f"http://127.0.0.1:{backend_port}/health", timeout=1) as response:
                        health = json.loads(response.read(16384))
                    if response.status != 200 or not isinstance(health, dict):
                        raise ValueError("health")
                    with urlopen(f"http://localhost:{frontend_port}/sign-in", timeout=3) as response:
                        frontend_ok = response.status == 200
                    if frontend_ok:
                        ready = True
                        status = "ready"
                        receipt = {"url": f"http://localhost:{frontend_port}/home/inbox",
                                   "frontend_port": frontend_port, "backend_port": backend_port,
                                   "expires_unix": time.time() + max(0, deadline-time.monotonic()),
                                   "real_account_verified": False}
                        write_new(directory / "ready.json", receipt)
                        print(json.dumps(receipt), flush=True)
                except Exception:
                    pass
            time.sleep(0.25 if ready else 0.5)
        if interrupted:
            status = "interrupted"
        elif (directory / "STOP").exists():
            status = "stopped_by_operator"
        elif time.monotonic() >= deadline:
            status = "expired"
    except Exception:
        status = "blocked_" + status
    finally:
        cleanup = {}
        for name, process in reversed(children):
            dead, sent = owner.stop_group(process, term_grace=5, kill_grace=3)
            cleanup[name] = {"group": process.pid, "group_dead": dead,
                             "exit_code": process.returncode, "signals": list(sent)}
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        try:
            verify(directory)
            source_unchanged = True
        except Exception:
            source_unchanged = False
        write_new(directory / "supervisor.json", {"status": status, "children": cleanup,
                  "frontend_port": frontend_port, "backend_port": backend_port,
                  "source_unchanged": source_unchanged})
        print(json.dumps({"status": status, "groups_dead": all(x["group_dead"] for x in cleanup.values())}), flush=True)
    return 0 if status in {"stopped_by_operator", "expired"} and all(x["group_dead"] for x in cleanup.values()) else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--launch", action="store_true")
    parser.add_argument("--seconds", default=600, type=int)
    args = parser.parse_args(argv)
    try:
        if args.launch:
            return launch(args.run_dir, args.seconds)
        if args.check:
            verify(args.run_dir)
        else:
            prepare(args.run_dir)
        print(json.dumps({"offline": True, "verified": True, "services_started": False}))
        return 0
    except Exception:
        print(json.dumps({"blocked": True, "configuration_not_printed": True}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
