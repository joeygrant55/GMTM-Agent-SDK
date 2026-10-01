"""Fresh-process composition and auth checks against the actual main.app.

These tests deliberately do not inherit conftest's fake SDKs or loaded routers.
Installed dependencies are real, while external effects are counted and blocked
before importing application code. They prove ASGI composition/lifespan and
failure boundaries, not a live GMTM sign-in, database schema, or deployed service.
"""

import json
from pathlib import Path
import subprocess
import sys


def _fresh_process(scenario):
    # Never inherit a developer's provider credentials, DB settings, proxies,
    # dotenv paths, or live evaluation allowance. This process owns only fakes.
    environment = {
        "PATH": "/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "ANTHROPIC_API_KEY": "synthetic-no-network",
        "OPENAI_API_KEY": "synthetic-no-network",
        "AGENT_DB_HOST": "127.0.0.1",
        "AGENT_DB_USER": "synthetic",
        "AGENT_DB_PASSWORD": "synthetic",
        "AGENT_DB_NAME": "synthetic",
        "DB_HOST": "127.0.0.1",
        "DB_USER": "synthetic",
        "DB_PASSWORD": "synthetic",
        "SHARE_TOKEN_SECRET": "synthetic-share-secret",
        "SENDGRID_API_KEY": "synthetic-no-network",
        "SPARQ_FROM_EMAIL": "sender@example.invalid",
        "FRONTEND_URL": "https://sparq-agent.test",
        "COMBINE_HELP_TEST_MODE": "1",
        "COMBINE_HELP_MAX_MODEL_CALLS": "1",
        "COMBINE_HELP_MAX_CONCURRENT_CALLS": "1",
    }
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(Path(__file__).resolve()), scenario],
        cwd=Path(__file__).resolve().parents[1], env=environment,
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    records = [line.removeprefix("STARTUP_PROBE ") for line in result.stdout.splitlines()
               if line.startswith("STARTUP_PROBE ")]
    assert len(records) == 1, result.stdout + result.stderr
    return json.loads(records[0])


def test_real_app_import_and_lifespan_have_zero_external_attempts():
    result = _fresh_process("composition")
    assert result["attempts"] == {}
    assert result["lifespan_completed"] is True
    assert result["guarded_lifespan_completed"] is True
    assert result["search_present"] is True


def test_real_registered_routes_fail_closed_before_external_work():
    result = _fresh_process("authentication")
    assert result["attempts"] == {}
    assert result["missing_bearer"] == [401] * 4
    assert result["missing_session_secret"] == [503] * 4


def test_real_registered_routes_reject_a_different_synthetic_owner():
    result = _fresh_process("ownership")
    assert result["attempts"] == {}
    assert result["statuses"] == {"recovery": 403, "combine": 409, "help": 409}
    assert result["synthetic_link_reads"] == 2
    assert result["synthetic_connections_closed"] == 2
    assert result["model_attempts"] == 0


def _run_probe(scenario):
    import collections
    import os
    import socket
    import threading

    attempts = collections.Counter()

    def block(name):
        def blocked(*args, **kwargs):
            attempts[name] += 1
            raise AssertionError(f"Forbidden external attempt: {name}")
        return blocked

    def audit(event, args):
        if event == "socket.getaddrinfo":
            block("dns")()
        if event == "socket.connect" and args[0].family in (socket.AF_INET, socket.AF_INET6):
            block("network")()
        if event in ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.fork"):
            block("process.start")()
        if event == "open" and isinstance(args[0], (str, bytes)):
            name = os.path.basename(os.fsdecode(args[0]))
            if name == ".env" or name.startswith(".env."):
                block("dotenv_file")()

    # The audit hook is installed even before importing installed dependencies.
    # AF_UNIX socketpairs used by the in-process ASGI transport remain available.
    sys.addaudithook(audit)

    import anthropic
    import asyncio
    import dotenv
    import dotenv.main
    import httpx
    import openai
    import pymysql
    import requests
    import smtplib
    import urllib.request

    for module in (dotenv, dotenv.main):
        module.load_dotenv = block("dotenv.load_dotenv")
        module.dotenv_values = block("dotenv.dotenv_values")
    pymysql.connect = block("pymysql.connect")
    pymysql.connections.Connection.connect = block("pymysql.Connection.connect")
    try:
        import mysql.connector
        import mysql.connector.connection
    except ModuleNotFoundError as exc:
        if exc.name not in ("mysql", "mysql.connector"):
            raise
    else:
        mysql.connector.connect = block("mysql.connector.connect")
        mysql.connector.connection.MySQLConnection.connect = block("mysql.MySQLConnection.connect")
        if hasattr(mysql.connector, "CMySQLConnection"):
            mysql.connector.CMySQLConnection.connect = block("mysql.CMySQLConnection.connect")
    for module, names in (
        (anthropic, ("Anthropic", "AsyncAnthropic", "Client", "AsyncClient",
                     "AnthropicBedrock", "AsyncAnthropicBedrock", "AnthropicVertex", "AsyncAnthropicVertex")),
        (openai, ("OpenAI", "AsyncOpenAI", "Client", "AsyncClient", "AzureOpenAI", "AsyncAzureOpenAI")),
    ):
        for name in names:
            if hasattr(module, name):
                setattr(module, name, block(f"provider.{module.__name__}.{name}"))
    requests.sessions.Session.send = block("requests.send")
    httpx.HTTPTransport.handle_request = block("httpx.network_transport")

    async def no_async_transport(*args, **kwargs):
        block("httpx.async_network_transport")()

    httpx.AsyncHTTPTransport.handle_async_request = no_async_transport
    urllib.request.urlopen = block("urllib.urlopen")
    smtplib.SMTP = block("email.SMTP")
    smtplib.SMTP_SSL = block("email.SMTP_SSL")
    original_thread_start = threading.Thread.start
    threading.Thread.start = block("import.thread_start")
    original_create_task = asyncio.create_task
    original_loop_create_task = asyncio.BaseEventLoop.create_task
    asyncio.create_task = block("import.asyncio_task")
    asyncio.BaseEventLoop.create_task = block("import.loop_task")

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    # Guard the project's actual mail transport before routers capture its alias.
    import email_sender
    email_sender.send_outreach_email = block("email.send_outreach_email")

    import main
    # This worker is imported lazily by workspace bootstrap and historically
    # loaded dotenv when first used, beyond the primary router import graph.
    import enrichment_worker

    # A swallowed connection/import error is a failure, even if main.app exists.
    assert dict(attempts) == {}, f"Import attempted external effects: {dict(attempts)}"
    asyncio.create_task = original_create_task
    asyncio.BaseEventLoop.create_task = original_loop_create_task

    async def guarded_lifespan():
        # asyncio.run has created its own task already. Guard application task
        # creation specifically during the real composed startup and shutdown.
        loop = asyncio.get_running_loop()
        loop_create_task = loop.create_task
        asyncio.create_task = block("lifespan.asyncio_task")
        loop.create_task = block("lifespan.loop_task")
        threading.Thread.start = block("lifespan.thread_start")
        try:
            async with main.app.router.lifespan_context(main.app):
                assert dict(attempts) == {}, f"Startup attempted external effects: {dict(attempts)}"
            assert dict(attempts) == {}, f"Shutdown attempted external effects: {dict(attempts)}"
        finally:
            asyncio.create_task = original_create_task
            loop.create_task = loop_create_task
            threading.Thread.start = original_thread_start

    asyncio.run(guarded_lifespan())

    def asgi_thread_start(thread, *args, **kwargs):
        # TestClient needs an AnyIO portal, synchronous dependency workers, and
        # asyncio.to_thread for combine reads. Permit those transport workers;
        # an application-owned matching/background thread remains a violation.
        target = getattr(thread, "_target", None)
        module = getattr(target, "__module__", "")
        name = getattr(target, "__name__", "")
        transport_worker = (
            (module == "anyio.from_thread" and name == "run_blocking_portal")
            or (type(thread).__module__ == "anyio._backends._asyncio"
                and type(thread).__name__ == "WorkerThread")
            or (module == "concurrent.futures.thread" and name == "_worker")
            or (module == "asyncio.base_events" and name == "_do_shutdown")
        )
        if not transport_worker:
            block("application.thread_start")()
        return original_thread_start(thread, *args, **kwargs)

    threading.Thread.start = asgi_thread_start

    from fastapi.testclient import TestClient

    expected = {
        "/api/combine/current": "get",
        "/api/combine/help": "post",
        "/api/profile/by-owner/{clerk_id}": "get",
        "/gmtm-entry/exchange": "post",
        "/api/workspace/inbox/{clerk_id}": "get",
        "/api/agent/chat": "post",
        "/api/reports/{user_id}": "get",
        "/api/search": "get",
        "/api/athlete/{user_id}": "get",
    }
    # New FastAPI versions lazily compose included routers; inspect the actual
    # OpenAPI schema and exercise ASGI requests instead of counting app.routes.
    schema = main.app.openapi()
    for path, method in expected.items():
        assert method in schema["paths"].get(path, {}), f"Missing registered route: {method} {path}"
    assert dict(attempts) == {}, f"Composition attempted external effects: {dict(attempts)}"

    result = {"scenario": scenario, "search_present": True, "guarded_lifespan_completed": True}
    with TestClient(main.app) as client:
        assert dict(attempts) == {}, f"Lifespan attempted external effects: {dict(attempts)}"
        assert client.get("/").status_code == 200
        health = client.get("/health")
        assert health.status_code == 200
        if scenario == "composition":
            assert health.json()["checks"]["auth"]["gmtm_sign_in_configured"] is False
        elif scenario == "authentication":
            routes = [
                ("GET", "/api/combine/current?event_id=1318", {}),
                ("POST", "/api/combine/help", {"json": {"event_id": 1318, "message": "Help me finish"}}),
                ("GET", "/api/profile/by-owner/synthetic-owner", {}),
                ("GET", "/api/search", {}),
            ]
            result["missing_bearer"] = []
            result["missing_session_secret"] = []
            for method, path, kwargs in routes:
                response = client.request(method, path, **kwargs)
                result["missing_bearer"].append(response.status_code)
                assert response.status_code == 401 and "bearer" in response.json()["detail"]
                response = client.request(method, path, headers={"Authorization": "Bearer synthetic-token"}, **kwargs)
                result["missing_session_secret"].append(response.status_code)
                assert response.status_code == 503 and "SPARQ sign-in" in response.json()["detail"]
                assert dict(attempts) == {}, f"Authentication reached external work: {dict(attempts)}"
        elif scenario == "ownership":
            result.update(_probe_ownership(client, block))
        else:
            raise AssertionError(f"Unknown probe: {scenario}")
        assert dict(attempts) == {}, f"Requests attempted external effects: {dict(attempts)}"
    assert dict(attempts) == {}, f"Shutdown attempted external effects: {dict(attempts)}"
    result.update(attempts=dict(attempts), lifespan_completed=True)
    print("STARTUP_PROBE " + json.dumps(result, sort_keys=True))


def _probe_ownership(client, block):
    """Use actual SPARQ session validation and routes with an invented local secret.

    The session store is supplied locally; this is not a real GMTM sign-in.
    Only the Agent DB interface is synthetic. GMTM and model interfaces remain
    guarded, and the application's real ownership checks must stop before them.
    """
    import os
    import time
    from types import SimpleNamespace

    import combine_api
    import junior_entry
    import jwt
    import model_usage

    secret = "synthetic-sparq-session-secret-32-bytes!"
    os.environ.update({"SPARQ_ENTRY_SECRET": "synthetic", "SPARQ_HANDOFF_SECRET": "synthetic",
                       "GMTM_API_URL": "https://gmtm-api.example.invalid", "SPARQ_SESSION_SECRET": secret,
                       "SPARQ_TEST_ALLOWLIST": "910001"})
    now = int(time.time())
    junior_entry.store = SimpleNamespace(
        session_jti=lambda sub: "synthetic-jti" if sub == "synthetic-owner" else None,
        latest_entry=lambda sub: {"user_id": 910001} if sub == "synthetic-owner" else None)
    token = jwt.encode({"sub": "synthetic-owner", "jti": "synthetic-jti", "gsh": "0" * 64, "aud": "legacy",
                        "iat": now, "exp": now + 120}, secret, algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    reads, closed = [], []

    class ConflictingLink:
        def cursor(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql, params):
            assert "SELECT user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2" in sql
            assert params == ("synthetic-owner",)
            reads.append((sql, params))

        def fetchall(self):
            return [{"user_id": 910001, "clerk_id": "a-different-synthetic-owner"}]

        def close(self):
            closed.append(True)

    combine_api._get_agent_db = ConflictingLink
    combine_api._get_gmtm_db = block("GMTM.source")
    recovery = client.get("/api/profile/by-owner/a-different-synthetic-owner", headers=headers)
    assert recovery.status_code == 403 and recovery.json()["detail"] == "Not authorized."
    status = client.get("/api/combine/current?event_id=1318", headers=headers)
    help_response = client.post("/api/combine/help", headers=headers,
                                json={"event_id": 1318, "message": "What remains?"})
    for response in (status, help_response):
        assert response.status_code == 409 and "athlete link needs review" in response.json()["detail"]
    return {
        "statuses": {"recovery": recovery.status_code, "combine": status.status_code, "help": help_response.status_code},
        "synthetic_link_reads": len(reads),
        "synthetic_connections_closed": len(closed),
        "model_attempts": model_usage.get_usage_snapshot()["attempted_calls"],
    }


if __name__ == "__main__":
    _run_probe(sys.argv[1])
