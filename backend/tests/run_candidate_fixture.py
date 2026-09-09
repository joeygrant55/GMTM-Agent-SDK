"""Bounded loopback fixture server for an explicitly chosen candidate ASGI app.

This executable scrubs its environment, blocks real services, and accepts fixture
control only on stdin. It creates no HTTP fixture routes. JWT/claim tokens are
synthetic IPC values; never persist stdout. No actual GMTM submission is made.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sys
import threading
import time
from types import SimpleNamespace


def main():
    raw = {name: os.environ.get(name) for name in (
        "SPARQ_FIXTURE_FRONTEND_PORT", "SPARQ_FIXTURE_BACKEND_PORT", "SPARQ_FIXTURE_RECEIPT",
        "SPARQ_FIXTURE_SURFACE")}
    surface = raw["SPARQ_FIXTURE_SURFACE"] or "combine"
    if surface not in ("combine", "profile"):
        raise ValueError("Fixture surface must be combine or profile")
    def port(name):
        value = raw[name]
        if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or not 1024 <= int(value) <= 65535:
            raise ValueError("Explicit non-privileged fixture port required")
        return int(value)
    frontend_port, backend_port = port("SPARQ_FIXTURE_FRONTEND_PORT"), port("SPARQ_FIXTURE_BACKEND_PORT")
    if frontend_port == backend_port:
        raise ValueError("Fixture frontend and backend ports must differ")
    receipt = Path(raw["SPARQ_FIXTURE_RECEIPT"] or "").resolve()
    if not raw["SPARQ_FIXTURE_RECEIPT"] or receipt.suffix != ".json" or receipt.exists() or not receipt.parent.is_dir():
        raise ValueError("A new JSON receipt in an existing artifact directory is required")
    origin = f"http://127.0.0.1:{frontend_port}"
    # Do not inherit provider keys, proxies, DB settings, or existing test budgets.
    os.environ.clear()
    os.environ.update({
        "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
        "AUTH_ENFORCED": "true", "CLERK_ISSUER": "https://clerk.example.invalid",
        "CLERK_AUTHORIZED_PARTIES": origin, "ALLOWED_ORIGINS": origin,
        "DB_HOST": "db2-dev.ckmlts6umure.us-east-1.rds.amazonaws.com",
        "DB_USER": "gmtmread", "DB_PASSWORD": "synthetic-source-not-a-credential",
        "AGENT_DB_HOST": "127.0.0.1", "AGENT_DB_PORT": "3307", "AGENT_DB_USER": "synthetic",
        "AGENT_DB_PASSWORD": "synthetic-agent-not-a-credential", "AGENT_DB_NAME": "sparq_candidate_fixture",
        "SHARE_TOKEN_SECRET": "synthetic-candidate-share-not-a-credential",
        "ANTHROPIC_API_KEY": "synthetic-provider-never-used", "COMBINE_HELP_MODEL": "claude-sonnet-4-6",
        "COMBINE_HELP_TEST_MODE": "1", "COMBINE_HELP_MAX_MODEL_CALLS": "8",
        "COMBINE_HELP_MAX_CONCURRENT_CALLS": "1",
        "PROFILE_DEBRIEF_ENABLED": "true" if surface == "profile" else "false",
        "PROFILE_DEBRIEF_MODEL": "claude-sonnet-4-6", "PROFILE_DEBRIEF_MAX_MODEL_CALLS": "4",
        "PROFILE_DEBRIEF_MAX_CONCURRENT_CALLS": "1",
    })
    attempts, requests, commands = Counter(), Counter(), Counter()
    counts = {"synthetic_help_calls": 0, "synthetic_debrief_calls": 0}
    def blocked(name):
        def stop(*args, **kwargs):
            attempts[name] += 1
            raise AssertionError(f"Fixture blocked {name}")
        return stop
    def audit(event, args):
        if event == "socket.getaddrinfo":
            if args[0] not in ("127.0.0.1", b"127.0.0.1") or args[1] != backend_port:
                blocked("network.dns")()
        elif event == "socket.connect" and args[0].family in (socket.AF_INET, socket.AF_INET6):
            blocked("network.outbound")()
        elif event == "socket.bind" and args[0].family in (socket.AF_INET, socket.AF_INET6):
            if args[1] != ("127.0.0.1", backend_port):
                blocked("network.bind")()
        elif event in ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.fork"):
            blocked("process.start")()
        elif event == "open" and isinstance(args[0], (str, bytes)):
            if os.path.basename(os.fsdecode(args[0])).startswith(".env"):
                blocked("dotenv.file")()
    sys.addaudithook(audit)

    import anthropic
    import dotenv
    import dotenv.main
    import httpx
    import jwt
    import openai
    import pymysql
    # This IPv4-only fixture does not need urllib3's import-time IPv6 bind
    # capability probe. Prevent that probe, then restore Python's capability
    # flag before application imports. All bind/outbound audit guards remain.
    native_has_ipv6 = socket.has_ipv6
    try:
        socket.has_ipv6 = False
        import requests as http_requests
    finally:
        socket.has_ipv6 = native_has_ipv6
    import smtplib
    import urllib.request
    import uvicorn
    from cryptography.hazmat.primitives.asymmetric import rsa
    from fastapi import HTTPException
    for module in (dotenv, dotenv.main):
        module.load_dotenv = module.dotenv_values = blocked("dotenv.load")
    pymysql.connect = pymysql.connections.Connection.connect = blocked("database.mysql")
    try:
        import mysql.connector
        mysql.connector.connect = blocked("database.mysql_connector")
    except ModuleNotFoundError:
        pass
    for module, names in ((anthropic, ("Anthropic", "AsyncAnthropic")), (openai, ("OpenAI", "AsyncOpenAI"))):
        for name in names:
            setattr(module, name, blocked(f"provider.{module.__name__}"))
    http_requests.sessions.Session.send = blocked("network.requests")
    httpx.HTTPTransport.handle_request = blocked("network.httpx")
    async def no_async_http(*args, **kwargs):
        blocked("network.httpx_async")()
    httpx.AsyncHTTPTransport.handle_async_request = no_async_http
    urllib.request.urlopen = blocked("network.urllib")
    smtplib.SMTP = smtplib.SMTP_SSL = blocked("email.smtp")

    original_thread_start = threading.Thread.start
    def thread_start(thread, *args, **kwargs):
        target = getattr(thread, "_target", None)
        module = getattr(target, "__module__", "")
        if not (module in ("concurrent.futures.thread", "asyncio.base_events")
                or type(thread).__module__.startswith("anyio.")):
            blocked("worker.thread")()
        return original_thread_start(thread, *args, **kwargs)
    threading.Thread.start = thread_start

    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend.parent))
    sys.path.insert(0, str(backend))
    import auth
    import candidate_app
    import claims_api
    import combine_api
    import combine_help_api
    import email_sender
    import model_usage
    import profile_api
    import workspace_bootstrap
    from backend.tests.test_claims import _FakeDB as ClaimDB
    from backend.tests.test_combine_requirements import (
        ATHLETE, CALLER, PUBLIC, FakeDB as CombineDB, definition_rows, submission_for,
    )
    assert "main" not in sys.modules
    email_sender.send_outreach_email = blocked("email.send")
    profile_api._run_matching_thread = blocked("worker.matching")

    mutex = threading.RLock()
    claims = {"claims": {}, "athlete_profiles": {}, "users": {ATHLETE}, "open_writes": 0,
              "connections": [], "named_locks": {}, "row_locks": {}, "failures": {}, "mutex": mutex}
    workspaces, shared_connections = {}, []
    source = {"profiles": [], "claims": [], "events": [deepcopy(item["event"]) for item in PUBLIC["events"]],
              "tasks": definition_rows(1317) + definition_rows(1318), "submissions": [], "queries": [], "connections": []}
    workspace_fail = {"enabled": False}

    class AgentDB:
        """Only recovery reads and creation-only workspace writes are accepted."""
        def __init__(self):
            self.rows, self.pending, self.closed, self.rowcount = [], {}, False, 0
            shared_connections.append(self)
        def cursor(self): return self
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, sql, params):
            normalized = " ".join(sql.split())
            self.rows, self.rowcount = [], 0
            with mutex:
                if normalized.startswith("SELECT user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s"):
                    self.rows = [{"user_id": uid, "clerk_id": owner} for uid, owner in claims["athlete_profiles"].items() if owner == params[0]][:2]
                elif normalized.startswith("SELECT user_id, clerk_id FROM athlete_profiles WHERE user_id = %s"):
                    self.rows = [{"user_id": uid, "clerk_id": owner} for uid, owner in claims["athlete_profiles"].items() if uid == params[0]][:2]
                elif normalized.startswith("SELECT id, clerk_id FROM sparq_profiles WHERE clerk_id = %s"):
                    row = workspaces.get(params[0])
                    self.rows = [deepcopy(row)] if row else []
                elif normalized.startswith("INSERT INTO sparq_profiles"):
                    assert normalized.split("ON DUPLICATE KEY UPDATE", 1)[1].replace(" ", "") == "id=id"
                    if workspace_fail["enabled"]:
                        raise RuntimeError("Synthetic optional bootstrap failure")
                    clerk, name, position, school, year, city, region, metrics = params
                    if clerk not in workspaces:
                        self.pending[clerk] = {"id": 501, "clerk_id": clerk, "name": name,
                            "position": position, "school": school, "class_year": year,
                            "city": city, "state": region, "combine_metrics": json.loads(metrics) if metrics else {},
                            "enrichment_complete": 0}
                        self.rowcount = 1
                else:
                    blocked("fixture.unexpected_agent_query")()
        def fetchone(self): return deepcopy(self.rows[0]) if self.rows else None
        def fetchall(self): return deepcopy(self.rows)
        def commit(self):
            with mutex:
                workspaces.update(deepcopy(self.pending))
                self.pending.clear()
        def close(self):
            self.pending.clear()
            self.closed = True

    class IdentityDB:
        def __init__(self):
            self.rows, self.closed = [], False
            shared_connections.append(self)
        def cursor(self): return self
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, sql, params):
            normalized = " ".join(sql.split())
            assert normalized.startswith("SELECT")
            if normalized.startswith("SELECT first_name FROM users"):
                self.rows = [{"first_name": "Ava"}] if params == (ATHLETE,) else []
            elif normalized.startswith("SELECT name FROM events"):
                self.rows = [{"name": row["name"]} for row in source["events"] if row["event_id"] == params[0]]
            elif "FROM users u LEFT JOIN locations" in normalized and params == (ATHLETE,):
                self.rows = [{"user_id": ATHLETE, "first_name": "Ava", "last_name": "Fixture", "graduation_year": 2027,
                              "gender": 0, "city": "Austin", "state": "TX"}]
            elif "FROM career c" in normalized and params == (ATHLETE,):
                self.rows = [{"position": "WR", "school": "Fixture High", "sport": "Flag Football"}]
            elif "FROM metrics" in normalized and params == (ATHLETE,):
                self.rows = [{"title": "Height", "value": "70"}, {"title": "Weight", "value": "150"}]
            else:
                blocked("fixture.unexpected_gmtm_query")()
        def fetchone(self): return deepcopy(self.rows[0]) if self.rows else None
        def fetchall(self): return deepcopy(self.rows)
        def close(self): self.closed = True

    def combine_connection(kind):
        with mutex:
            source["profiles"] = [{"user_id": uid, "clerk_id": owner} for uid, owner in claims["athlete_profiles"].items()]
            source["claims"] = list(claims["claims"].values())
            db = CombineDB(source, kind)
            source["connections"].append(db)
            return db
    claims_api._get_agent_db = lambda: ClaimDB(claims)
    claims_api._get_gmtm_db = IdentityDB
    profile_api._get_agent_db = AgentDB
    profile_api._get_gmtm_db = IdentityDB
    workspace_bootstrap.get_combine_results = lambda user_id, factory: []
    combine_api._get_agent_db = lambda: combine_connection("agent")
    combine_api._get_gmtm_db = lambda: combine_connection("gmtm")

    if surface == "profile":
        import athlete_evidence
        import athlete_materials

        class EvidenceAgentDB(AgentDB):
            """Use the shared claim link, but permit only the two owner reads."""
            def execute(self, sql, params):
                normalized = " ".join(sql.split())
                allowed = {
                    "SELECT user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2": (CALLER,),
                    "SELECT user_id, clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 2": (ATHLETE,),
                }
                if normalized not in allowed or params != allowed[normalized]:
                    blocked("fixture.unexpected_evidence_agent_query")()
                return super().execute(sql, params)

            def commit(self):
                blocked("fixture.evidence_agent_write")()

        class EvidenceDB(IdentityDB):
            """Read-only synthetic identity and one explicitly unit-bearing fact."""
            def execute(self, sql, params):
                normalized = " ".join(sql.split())
                if not normalized.startswith("SELECT ") or ";" in normalized:
                    blocked("fixture.unexpected_evidence_source_query")()
                if ("FROM users u LEFT JOIN locations" in normalized
                        and "WHERE u.user_id = %s LIMIT 2" in normalized and params == (ATHLETE,)):
                    self.rows = [{"user_id": ATHLETE, "first_name": "Ava", "last_name": "Fixture",
                                  "graduation_year": 2027, "city": "Austin", "state": "TX"}]
                elif ("FROM career c" in normalized and params == (ATHLETE,)
                      and "c.is_primary = 1 AND c.visibility >= 0" in normalized
                      and "c.approved = 1 OR c.suggested_by IS NULL" in normalized
                      and normalized.endswith("ORDER BY c.career_id DESC LIMIT 2")):
                    self.rows = [{"user_id": ATHLETE, "career_id": 31, "is_primary": 1,
                                  "visibility": 1, "approved": 0, "suggested_by": None,
                                  "position": "WR", "school": "Fixture High", "sport": "Flag Football"}]
                elif ("FROM metrics m" in normalized and params == (ATHLETE, 101)
                      and "WHERE m.user_id = %s AND m.is_current = 1 AND m.visibility = 2" in normalized
                      and "m.user_approved = 0 AND m.suggested_by IS NULL" in normalized
                      and "e.published = 1 AND e.`public` = 1 AND e.visibility = 2" in normalized
                      and "e.invite_only = 0 AND e.product_id IS NULL" in normalized
                      and "m.event_id IS NULL OR e.event_id IS NOT NULL" in normalized
                      and normalized.endswith("ORDER BY m.created_on DESC, m.metric_id DESC LIMIT %s")):
                    self.rows = [{"metric_id": 401, "user_id": ATHLETE, "title": "40 Yard Dash",
                                  "value": "4.75", "unit": "seconds", "created_on": datetime(2026, 9, 1, 12, 30),
                                  "is_current": 1, "visibility": 2, "user_approved": 0, "suggested_by": None,
                                  "event_id": None, "public_event_id": None, "event_name": None,
                                  "event_published": None, "event_public": None, "event_visibility": None,
                                  "event_invite_only": None, "event_product_id": None}]
                else:
                    blocked("fixture.unexpected_evidence_source_query")()

        athlete_evidence._get_agent_db = EvidenceAgentDB
        athlete_evidence._get_gmtm_db = EvidenceDB

        public_event = dict(joined_event_id=1318, event_name="Fixture digital combine",
                            event_visibility=2, event_published=1, event_public=1,
                            event_invite_only=0, event_networks_only=0, event_product_id=None)

        def material_submission(identifier, task_id, title, value, visibility):
            payload = json.dumps({"questions": {"metric:" + title: {
                "type": "metric", "key": "metric:" + title,
                "value": {"value": value, "unit": "inches"}},
                "essay:Personal contact": {"type": "essay", "value": "synthetic-excluded-contact"}}})
            return dict(user_id=ATHLETE, task_submission_id=identifier, task_id=task_id,
                        created_on=datetime(2026, 9, 2, 10, 0), visibility=visibility,
                        payload=payload, payload_bytes=len(payload.encode()),
                        joined_task_id=task_id, event_id=1318, task_title="Fixture assessment",
                        task_visibility=2, **public_event)

        def material_film(identifier, visibility):
            return dict(user_id=ATHLETE, film_id=identifier, direct_user_id=ATHLETE,
                        career_id=None, joined_career_id=None, career_user_id=None,
                        task_submission_id=None, title="Fixture highlight reel",
                        service="gmtm", thumbnail_uri="videos/film/thumbnails/fixture-703.png",
                        published_on=datetime(2026, 9, 3, 11, 0), visibility=visibility,
                        approved=0, suggested_by=None, suggested_by_org_id=None,
                        processed=0, dead_link=0, challenge_id=None, film_event_id=0,
                        in_person_event_id=None, joined_event_id=None, event_name=None,
                        event_visibility=None, event_published=None, event_public=None,
                        event_invite_only=None, event_networks_only=None, event_product_id=None)

        class MaterialsDB(IdentityDB):
            """Independent source snapshots, including a private result and film."""
            def execute(self, sql, params):
                normalized = " ".join(sql.split())
                if (not normalized.startswith("SELECT ") or ";" in normalized
                        or params != (ATHLETE, 51) or not normalized.endswith("LIMIT %s")):
                    blocked("fixture.unexpected_materials_source_query")()
                if ("FROM event_task_submissions s" in normalized
                        and "WHERE s.user_id = %s" in normalized and "NOT EXISTS" in normalized
                        and "OCTET_LENGTH(s.payload) <= 65536" in normalized):
                    self.rows = [material_submission(701, 801, "Vertical Jump", 28.5, 2),
                                 material_submission(702, 802, "Broad Jump", 94, 0)]
                elif "FROM film f" in normalized and "WHERE s.user_id = %s" in normalized:
                    self.rows = []
                elif ("FROM film f" in normalized and "WHERE f.user_id = %s" in normalized
                      and "f.task_submission_id IS NULL" in normalized and "f.challenge_id IS NULL" in normalized):
                    private = material_film(704, 0)
                    private["title"] = "Fixture private practice"
                    private["published_on"] = datetime(2026, 9, 2, 11, 0)
                    self.rows = [material_film(703, 2), private]
                elif ("FROM film f" in normalized and "WHERE c.user_id = %s" in normalized
                      and "f.user_id IS NULL" in normalized and "f.task_submission_id IS NULL" in normalized):
                    self.rows = []
                else:
                    blocked("fixture.unexpected_materials_source_query")()

        athlete_materials._get_agent_db = EvidenceAgentDB
        athlete_materials._get_gmtm_db = MaterialsDB

        import profile_debrief

        class DebriefDB(EvidenceDB):
            def execute(self, sql, params):
                if "FROM event_task_submissions s" in sql or "FROM film f" in sql:
                    return MaterialsDB.execute(self, sql, params)
                return super().execute(sql, params)

        profile_debrief._get_agent_db = EvidenceAgentDB
        profile_debrief._get_gmtm_db = DebriefDB

        async def synthetic_debrief(**kwargs):
            assert kwargs["model"] == "claude-sonnet-4-6"
            assert kwargs["usage_ledger"] is not None
            assert all(db.closed for db in shared_connections)
            # Provider fixture sees only the actual minimized context. It does
            # not bypass ownership/source reads, admission or JSON validation.
            encoded = json.dumps({"system": kwargs["system"], "messages": kwargs["messages"]})
            for excluded in ("Ava Fixture", "Fixture High", "Austin", "synthetic-excluded-contact",
                             "Fixture private practice", "Fixture highlight reel", "gmtm.com/film", CALLER):
                assert excluded not in encoded
            counts["synthetic_debrief_calls"] += 1
            result = {
                "answer": {"text": "Your recorded result can anchor a factual profile summary. Timing conditions and comparison standards are not confirmed here.", "refs": ["f1", "coverage"]},
                "insights": [{"text": "Use the recorded measurement with its source, then explain what opportunity you are working toward.", "refs": ["f1"]}],
                "unknowns": [{"text": "This view does not establish whether a scout reviewed or selected you.", "refs": ["coverage"]}],
                "action": {"id": "prepare_summary", "reason": {"text": "Prepare a summary using the evidence you choose and your own goal.", "refs": ["f1"]}},
            }
            yield {"type": "text", "text": json.dumps(result)}
            yield {"type": "done"}

        profile_debrief.stream_answer = synthetic_debrief

    async def synthetic_answer(**kwargs):
        assert kwargs["model"] == "claude-sonnet-4-6"
        assert "CURRENT SERVER SNAPSHOT" in kwargs["system"]
        if await kwargs["is_disconnected"]():
            return
        counts["synthetic_help_calls"] += 1
        yield {"type": "text", "text": "Open GMTM to finish this activity. Submission is for review, not selection."}
        yield {"type": "done"}
    combine_help_api.stream_answer = synthetic_answer
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    auth._jwks_issuer = os.environ["CLERK_ISSUER"]
    auth._jwks_client = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=key.public_key()))
    token = jwt.encode({"sub": CALLER, "iss": os.environ["CLERK_ISSUER"], "azp": origin,
                        "exp": int(time.time()) + 1800}, key, algorithm="RS256")
    secret = os.environ["SHARE_TOKEN_SECRET"].encode()
    claim_tokens = {event: claims_api.mint_token(ATHLETE, event, secret, exp=int(time.time()) + 1800) for event in (1318, 999)}

    def reset(*, linked=True, workspace=True, submitted=0, workspace_failure=False):
        if type(linked) is not bool or type(workspace) is not bool or type(workspace_failure) is not bool or type(submitted) is not int or submitted not in (0, 1):
            raise ValueError("Invalid reset shape")
        with mutex:
            claims["claims"] = {claims_api.token_hash(value): {
                "id": index, "user_id": ATHLETE, "event_id": event,
                "expires_at": datetime.now(timezone.utc), "opened_at": None,
                "claimed_at": "synthetic-saved" if linked else None, "clerk_id": CALLER if linked else None,
            } for index, (event, value) in enumerate(claim_tokens.items(), 1)}
            claims["athlete_profiles"] = {ATHLETE: CALLER} if linked else {}
            workspaces.clear()
            if workspace:
                workspaces[CALLER] = {"id": 501, "clerk_id": CALLER, "name": "Ava Fixture", "enrichment_complete": 0}
            workspace_fail["enabled"] = workspace_failure
            submit(submitted)
    def submit(submitted):
        if type(submitted) is not int or submitted not in (0, 1):
            raise ValueError("Invalid submission fixture count")
        with mutex:
            adult_task = next(task for task in source["tasks"] if task["event_id"] == 1318)
            source["submissions"] = [submission_for(adult_task, sid=401, user_id=ATHLETE)] if submitted else []
    reset()

    def emit(record):
        # Protocol tokens go to the controlling Node process only, never receipt.
        print("CANDIDATE_FIXTURE " + json.dumps(record, sort_keys=True), flush=True)

    class CountRequests:
        def __init__(self, app): self.app = app
        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                return await self.app(scope, receive, send)
            try:
                await self.app(scope, receive, send)
            finally:
                route = scope.get("route")
                path = getattr(route, "path", "unregistered")
                # Only source route templates are retained; no raw URL, query,
                # header, JWT, claim token, payload, or athlete data is logged.
                requests[f'{scope["method"]} {path}'] += 1

    app = candidate_app.app if surface == "combine" else candidate_app.create_app(surface="profile")
    expected = ({path for _, path, _ in candidate_app.BUSINESS_ROUTES} | {"/health"}
                if surface == "combine" else {
                    "/health", "/api/athlete/evidence", "/api/athlete/materials", "/api/profile/by-clerk/{clerk_id}",
                    "/api/athlete/debrief",
                    "/api/claims/{token}", "/api/claims/{token}/redeem",
                })
    assert set(app.openapi()["paths"]) == expected
    server = uvicorn.Server(uvicorn.Config(CountRequests(app), host="127.0.0.1", port=backend_port,
                                           loop="asyncio", http="h11", access_log=False,
                                           log_level="error", timeout_graceful_shutdown=5))
    def command_line():
        line = sys.stdin.readline()
        if not line:
            server.should_exit = True
            return
        identifier = None
        try:
            command = json.loads(line)
            identifier = command.get("id")
            if not (isinstance(identifier, (str, int)) and not isinstance(identifier, bool)
                    and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", str(identifier))):
                raise ValueError("Invalid command id")
            operation = command.get("op")
            if operation == "reset" and set(command) <= {"id", "op", "linked", "workspace", "submitted", "workspace_failure"}:
                reset(**{key: value for key, value in command.items() if key not in ("id", "op")})
            elif operation == "submit" and set(command) == {"id", "op", "submitted"}:
                submit(command["submitted"])
            elif operation == "stop" and set(command) == {"id", "op"}:
                server.should_exit = True
            else:
                raise ValueError("Unsupported fixture command")
            commands[operation] += 1
            emit({"event": "command", "id": identifier, "ok": True})
        except Exception:
            commands["invalid"] += 1
            emit({"event": "command", "id": identifier if isinstance(identifier, int) else None, "ok": False,
                  "reason": "invalid_fixture_command"})

    async def serve():
        loop = asyncio.get_running_loop()
        loop.add_reader(sys.stdin.fileno(), command_line)
        deadline = loop.call_later(900, setattr, server, "should_exit", True)
        task = asyncio.create_task(server.serve())
        try:
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("Fixture server did not start")
                await asyncio.sleep(0.01)
            emit({"event": "ready", "surface": surface, "token": token, "claim_token": claim_tokens[1318],
                  "old_claim_token": claim_tokens[999], "clerk_id": CALLER, "athlete_id": ATHLETE,
                  "adult_task_id": next(task["task_id"] for task in source["tasks"] if task["event_id"] == 1318)})
            await task
        finally:
            deadline.cancel()
            loop.remove_reader(sys.stdin.fileno())

    exit_status = "stopped"
    try:
        asyncio.run(serve())
    except BaseException:
        exit_status = "failed"
        raise
    finally:
        all_connections = claims["connections"] + source["connections"] + shared_connections
        report = {
            "kind": "synthetic_actual_candidate_asgi", "status": exit_status, "surface": surface,
            "requests_by_route_template": dict(requests), "fixture_commands": dict(commands),
            "forbidden_attempts": dict(attempts), **counts,
            "real_provider_attempts": model_usage.get_usage_snapshot()["attempted_calls"],
            "real_debrief_provider_attempts": (profile_debrief._ledger_state[1].snapshot()["attempted_calls"]
                                               if surface == "profile" and profile_debrief._ledger_state else 0),
            "all_synthetic_connections_closed": all(db.closed for db in all_connections),
            "fixture_connection_count": len(all_connections),
            "live_clerk_verified": False, "live_database_verified": False,
            "real_gmtm_submission_verified": False, "production_changed": False,
            "limits": "Loopback transport, locally signed JWT/JWKS, fake database interfaces and provider output; no live integration claim.",
            "source_hashes": {name: hashlib.sha256((backend/name).read_bytes()).hexdigest() for name in (
                "candidate_app.py", "claims_api.py", "workspace_bootstrap.py", "profile_api.py", "combine_api.py",
                "combine_help_api.py", "tests/run_candidate_fixture.py",
                *(("athlete_evidence.py", "athlete_materials.py", "profile_debrief.py", "profile_pathways.py", "combine_model.py") if surface == "profile" else ()))},
        }
        descriptor = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")


if __name__ == "__main__":
    main()
