"""Finite-ledger, owner-2 acceptance boundary; never deployed or started on import.

The parent owns process deadlines/source freezing. This module restricts actual
current app auth, routes and SQL, and keeps a private pre-save workspace receipt.
"""
from __future__ import annotations

import asyncio
from contextvars import ContextVar
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from threading import RLock
from types import SimpleNamespace

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

import auth
import candidate_app
import junior_entry
import athlete_workspace as workspace
from scripts.read_owner_profile_evidence import reviewed_query_specs, normalized

CAPS = {"personal_requests": 40, "patch_attempts": 3, "selects": 500, "connections": 160}
CONTEXT = ContextVar("profile_acceptance_owner", default=None)
LINK_FORWARD = "SELECT id, user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2"
LINK_REVERSE = "SELECT id, user_id, clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 2"
PAIR_FORWARD = "SELECT user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2"
PAIR_REVERSE = "SELECT user_id, clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 2"
PROFILE_SQL = "SELECT id, clerk_id FROM sparq_profiles WHERE clerk_id = %s LIMIT 2"
WORKSPACE_SQL = f"SELECT {workspace._COLUMNS} FROM athlete_workspaces WHERE clerk_id = %s LIMIT 2"
INSERT_SQL = "INSERT INTO athlete_workspaces (clerk_id, athlete_link_id, gmtm_user_id, version, payload, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)"
UPDATE_SQL = "UPDATE athlete_workspaces SET version = %s, payload = %s, updated_at = %s WHERE clerk_id = %s AND athlete_link_id = %s AND gmtm_user_id = %s AND version = %s"


def _raw_connect(settings):
    import pymysql
    return pymysql.connect(**settings, cursorclass=pymysql.cursors.DictCursor,
                           autocommit=True, connect_timeout=5, read_timeout=10, write_timeout=10)


class Ledger:
    def __init__(self, run_dir, *, read_only=False):
        path = Path(run_dir)
        if (not path.is_absolute() or ".." in path.parts or any(p.is_symlink() for p in (path, *path.parents))
                or not path.is_dir() or any((p / ".git").exists() for p in (path, *path.parents))
                or stat.S_IMODE(path.stat().st_mode) != 0o700 or path.stat().st_uid != os.getuid()):
            raise ValueError("Acceptance directory must be private and outside Git")
        self.path, self.lock = path, RLock()
        self.caps = {**CAPS, "patch_attempts": 0 if read_only else CAPS["patch_attempts"]}
        self.fd = os.open(path / "acceptance-ledger.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        self.data = {"status": "prepared", "athlete_id": 2, "caps": dict(self.caps), "attempts": dict.fromkeys(self.caps, 0),
                     "connections_opened": 0, "connections_closed": 0, "commits_attempted": 0,
                     "commits_acknowledged": 0, "denials": {}, "outcomes": {}, "before_state_saved": False,
                     "errors": {}, "writes_closed": False, "provider_calls": 0, "gmtm_writes": 0}
        self.owner, self.baseline, self.version, self.closed = None, None, None, False
        self.flush()

    def flush(self):
        data = (json.dumps(self.data, sort_keys=True, indent=2) + "\n").encode()
        os.lseek(self.fd, 0, os.SEEK_SET)
        while data:
            n = os.write(self.fd, data)
            if n <= 0: raise OSError("Ledger write failed")
            data = data[n:]
        os.ftruncate(self.fd, os.lseek(self.fd, 0, os.SEEK_CUR))
        os.fsync(self.fd)

    def deny(self, reason, status=403):
        with self.lock:
            self.data["denials"][reason] = self.data["denials"].get(reason, 0) + 1
            self.flush()
        raise HTTPException(status, "The local acceptance boundary blocked this request.")

    def reserve(self, key):
        with self.lock:
            if self.closed or self.data["attempts"][key] >= self.caps[key]: self.deny("budget_" + key, 429)
            self.data["attempts"][key] += 1
            self.flush()

    def add(self, key):
        with self.lock:
            self.data[key] += 1
            self.flush()

    def error(self, stage, exc):
        kind = type(exc).__name__
        if kind not in ("HTTPException", "WorkspaceError", "OperationalError", "InterfaceError", "IntegrityError",
                        "ProgrammingError", "TimeoutError", "OSError", "ValueError", "RuntimeError"):
            kind = "other"
        code = exc.args[0] if exc.args and type(exc.args[0]) is int and 0 <= exc.args[0] <= 65535 else None
        key = stage + ":" + kind + (":" + str(code) if code is not None else "")
        with self.lock:
            self.data["errors"][key] = self.data["errors"].get(key, 0) + 1
            self.flush()

    def pin(self, owner):
        with self.lock:
            if owner["user_id"] != 2 or (self.owner is not None and self.owner != owner): self.deny("owner_changed", 409)
            self.owner = dict(owner)
            self.data["owner_verified"] = True
            self.flush()

    def remember(self, value, ctx, *, patch=False):
        with self.lock:
            if (not isinstance(value, dict) or value.get("state") != "ready"
                    or value.get("link_revision") != workspace._revision(ctx.owner)
                    or value.get("owner_scope") != workspace.owner_scope(ctx.clerk, 2)
                    or type(value.get("version")) is not int or not 0 <= value["version"] <= workspace.MAX_VERSION):
                self.deny("workspace_response_scope", 503)
            if patch:
                if value["version"] not in (ctx.expected_version, ctx.expected_version + 1): self.deny("workspace_version", 503)
                self.version = value["version"]
            elif self.baseline is None:
                data = (json.dumps({"athlete_id": 2, "workspace": value}, sort_keys=True) + "\n").encode()
                fd = os.open(self.path / "private-workspace-before.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                self.baseline, self.version = value, value["version"]
                self.data["before_state_saved"] = True
            self.flush()

    def close(self):
        with self.lock:
            if not self.closed:
                self.data["status"] = "stopped"
                self.flush()
                os.close(self.fd)
                self.closed = True


class GuardCursor:
    def __init__(self, db, raw): self.db, self.raw, self.query = db, raw, None
    def __enter__(self): return self
    def __exit__(self, *_): self.raw.close()
    def close(self): self.raw.close()
    @property
    def rowcount(self): return self.raw.rowcount

    def execute(self, sql, params=None):
        db, ctx, key = self.db, self.db.ctx, normalized(sql)
        if CONTEXT.get() is not ctx or db.closed: db.ledger.deny("connection_context")
        if db.kind == "gmtm":
            spec = db.sources.get(key)
            if not ctx.owner or spec is None or params != spec[0]: db.ledger.deny("gmtm_sql_scope")
        else:
            allowed = {LINK_FORWARD: (ctx.clerk,), LINK_REVERSE: (2,), PAIR_FORWARD: (ctx.clerk,), PAIR_REVERSE: (2,)}
            if ctx.owner:
                allowed.update({PROFILE_SQL: (ctx.clerk,), WORKSPACE_SQL: (ctx.clerk.encode(),)})
            if db.transaction:
                allowed.update({LINK_FORWARD + " FOR UPDATE": (ctx.clerk,), LINK_REVERSE + " FOR UPDATE": (2,),
                                WORKSPACE_SQL + " FOR UPDATE": (ctx.clerk.encode(),)})
            if key in allowed:
                if params != allowed[key]: db.ledger.deny("agent_sql_owner")
            elif key == "SET SESSION innodb_lock_wait_timeout = 3":
                if ctx.method != "PATCH" or not ctx.owner or params is not None: db.ledger.deny("agent_sql_scope")
            elif key in (INSERT_SQL, UPDATE_SQL):
                if (ctx.method != "PATCH" or not ctx.owner or not db.transaction or ctx.write_attempts
                        or not db.locked_owner or not db.locked_workspace or not isinstance(params, tuple) or len(params) != 7):
                    db.ledger.deny("workspace_write_scope")
                if key == INSERT_SQL:
                    subject, link, athlete, version, payload, created, updated = params
                    expected = 0
                else:
                    version, payload, updated, subject, link, athlete, expected = params
                if (subject != ctx.clerk.encode() or type(link) is not int or link != ctx.owner["id"]
                        or type(athlete) is not int or athlete != 2 or type(expected) is not int
                        or expected != ctx.expected_version or type(version) is not int or version != expected + 1):
                    db.ledger.deny("workspace_write_owner")
                workspace._json(payload)
                ctx.write_attempts += 1
                db.written = True
            else:
                db.ledger.deny("agent_sql_scope")
        if key.startswith("SELECT "): db.ledger.reserve("selects")
        self.query = key
        try:
            return self.raw.execute(sql, params)
        except Exception as exc:
            db.ledger.error(db.kind + ("_select" if key.startswith("SELECT ") else "_statement"), exc)
            raise

    def _rows(self, rows):
        db, ctx = self.db, self.db.ctx
        if not isinstance(rows, (list, tuple)) or self.query is None: db.ledger.deny("invalid_rows")
        source_params = db.sources[self.query][0] if db.kind == "gmtm" else ()
        cap = (source_params[1] if len(source_params) == 2 else 2) if db.kind == "gmtm" else 2
        if len(rows) > cap: db.ledger.deny("row_limit")
        for row in rows:
            if not isinstance(row, dict): db.ledger.deny("invalid_rows")
            if db.kind == "gmtm":
                owner_column = db.sources[self.query][1]
                if type(row.get(owner_column)) is not int or row[owner_column] != 2: db.ledger.deny("foreign_source_row")
                for field in ("user_id", "direct_user_id", "career_user_id", "submission_user_id"):
                    if row.get(field) is not None and (type(row[field]) is not int or row[field] != 2): db.ledger.deny("foreign_source_row")
            elif "FROM athlete_profiles" in self.query:
                if row.get("clerk_id") != ctx.clerk or type(row.get("user_id")) is not int or row["user_id"] != 2:
                    db.ledger.deny("foreign_link_row", 409)
                if self.query.startswith("SELECT id,") and (not workspace._positive(row.get("id")) or (ctx.owner and row["id"] != ctx.owner["id"])):
                    db.ledger.deny("changed_link_row", 409)
            elif "FROM athlete_workspaces" in self.query:
                if (row.get("clerk_id") != ctx.clerk.encode() or row.get("gmtm_user_id") != 2
                        or type(row.get("gmtm_user_id")) is not int or row.get("athlete_link_id") != ctx.owner["id"]):
                    db.ledger.deny("foreign_workspace_row", 409)
            elif row.get("clerk_id") != ctx.clerk: db.ledger.deny("foreign_profile_row", 409)
        if self.query == LINK_REVERSE + " FOR UPDATE" and len(rows) == 1: db.locked_owner = True
        if self.query == WORKSPACE_SQL + " FOR UPDATE": db.locked_workspace = True
        return rows

    def fetchall(self): return self._rows(self.raw.fetchall())
    def fetchone(self):
        value = self.raw.fetchone()
        return self._rows([value])[0] if value is not None else None


class GuardConnection:
    def __init__(self, raw, kind, ledger, ctx, sources):
        self.raw, self.kind, self.ledger, self.ctx, self.sources = raw, kind, ledger, ctx, sources
        self.closed = self.transaction = self.written = self.locked_owner = self.locked_workspace = False
        self.readonly = kind == "gmtm" or ctx.method != "PATCH" or ctx.owner is None
        self.ledger.add("connections_opened")
        try:
            if self.readonly:
                with raw.cursor() as cursor: cursor.execute("START TRANSACTION READ ONLY")
        except BaseException:
            self.close()
            raise
    def cursor(self): return GuardCursor(self, self.raw.cursor())
    def begin(self):
        if self.readonly or self.ctx.method != "PATCH" or self.transaction: self.ledger.deny("transaction_scope")
        self.raw.begin()
        self.transaction = True
    def commit(self):
        if not self.transaction or not self.written: self.ledger.deny("commit_scope")
        self.ledger.add("commits_attempted")
        try:
            self.raw.commit()
        except Exception as exc:
            self.ledger.error("agent_commit", exc)
            raise
        self.transaction = False
        self.ledger.add("commits_acknowledged")
    def rollback(self):
        self.raw.rollback()
        self.transaction = False
    def close(self):
        if self.closed: return
        try:
            if self.readonly or self.transaction: self.raw.rollback()
        finally:
            self.raw.close()
            self.closed = True
            self.ledger.add("connections_closed")


def _settings(settings, prefix):
    if not isinstance(settings, dict) or set(settings) != {"host", "port", "user", "password", "database"}:
        raise ValueError("Explicit database settings required")
    expected = {"host": os.environ.get(prefix + "HOST"), "port": int(os.environ.get(prefix + "PORT", "3306")),
                "user": os.environ.get(prefix + "USER"), "password": os.environ.get(prefix + "PASSWORD"),
                "database": os.environ.get(prefix + "NAME", "gmtm")}
    if settings != expected or type(settings["port"]) is not int: raise ValueError("Database settings disagree with process configuration")
    return dict(settings)


def create_acceptance_app(*, agent_settings, gmtm_settings, frontend_origin, backend_host, run_dir, read_only: bool = False):
    if type(read_only) is not bool: raise ValueError("Acceptance read_only must be a boolean")
    # Profile has no Clerk (rev 3): the owner authenticates with a SPARQ session token,
    # so GMTM entry (incl. SPARQ_SESSION_SECRET) must be fully configured.
    config = candidate_app.validate_configuration(os.environ, "profile")
    try:
        entry = junior_entry.entry_configuration(os.environ)
    except ValueError:
        entry = None
    if (entry is None or config.origins != (frontend_origin,)
            or not re.fullmatch(r"http://localhost:[0-9]{1,5}", frontend_origin)
            or not re.fullmatch(r"(?:127\.0\.0\.1|localhost):[0-9]{1,5}", backend_host)
            or os.environ.get("PROFILE_DEBRIEF_ENABLED") != "false"
            or any(os.environ.get(key) for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"))):
        raise ValueError("Acceptance authentication/origin/provider configuration is not pinned")
    agent_settings, gmtm_settings = _settings(agent_settings, "AGENT_DB_"), _settings(gmtm_settings, "DB_")
    if not re.fullmatch(r"[a-z0-9-]+\.proxy\.rlwy\.net", agent_settings["host"]): raise ValueError("Existing Agent proxy required")
    sources = {**reviewed_query_specs("profile"), **reviewed_query_specs("materials")}
    ledger = Ledger(run_dir, read_only=read_only)
    inner = candidate_app.create_app(surface="profile")
    patches = []

    def connection(kind):
        ctx = CONTEXT.get()
        if ctx is None or (kind == "gmtm" and ctx.owner is None): ledger.deny("missing_owner_context")
        ledger.reserve("connections")
        raw = _raw_connect(agent_settings if kind == "agent" else gmtm_settings)
        db = GuardConnection(raw, kind, ledger, ctx, sources)
        ctx.connections.append(db)
        return db

    async def verified_subject():
        ctx = CONTEXT.get()
        if ctx is None or ctx.owner is None: ledger.deny("missing_verified_subject")
        return ctx.clerk
    inner.dependency_overrides[auth.require_clerk_id] = verified_subject

    def resolve_owner():
        db = connection("agent")
        try:
            with db.cursor() as cursor: owner = workspace._owner(cursor, CONTEXT.get().clerk)
            ledger.pin(owner)
            return owner
        finally: db.close()

    def install():
        import athlete_evidence, athlete_materials, athlete_opportunities, combine_api, profile_api, claims_api, profile_debrief, profile_owner
        for module in (athlete_evidence, athlete_materials, athlete_opportunities, workspace, combine_api, profile_api, claims_api, profile_debrief, profile_owner):
            for name, kind in (("_get_agent_db", "agent"), ("_get_gmtm_db", "gmtm")):
                if hasattr(module, name):
                    patches.append((module, name, getattr(module, name)))
                    setattr(module, name, lambda kind=kind: connection(kind))

    def route(path, method):
        if read_only and method == "PATCH": return None
        if path == "/health" and method == "GET": return "health"
        if path in ("/api/athlete/evidence", "/api/athlete/materials") and method == "GET": return path.rsplit("/", 1)[1]
        if path == "/api/athlete/opportunities" and method == "POST": return "opportunities"
        if path == "/api/athlete/workspace" and method in ("GET", "PATCH"): return "workspace_" + method.lower()
        if re.fullmatch(r"/api/profile/by-clerk/[A-Za-z0-9_-]{1,255}", path) and method == "GET": return "profile_link"
        return None

    class AcceptanceApp:
        async def __call__(self, scope, receive, send):
            if scope["type"] == "lifespan":
                install()
                try: await inner(scope, receive, send)
                finally:
                    for module, name, previous in reversed(patches): setattr(module, name, previous)
                    patches.clear()
                    ledger.close()
                return
            if scope["type"] != "http":
                await send({"type": "websocket.close", "code": 1008})
                return
            ctx, marker, response_started, stage = None, None, False, "http_boundary"
            headers = {}
            duplicate = False
            for key, value in scope.get("headers", []):
                key, value = key.lower().decode("latin1"), value.decode("latin1")
                if key in headers and key in ("host", "origin", "authorization"): duplicate = True
                headers[key] = value
            cors = {"Access-Control-Allow-Origin": frontend_origin, "Access-Control-Allow-Credentials": "true",
                    "Vary": "Origin, Authorization", "Cache-Control": "private, no-store"} if headers.get("origin") == frontend_origin else {"Cache-Control": "private, no-store"}
            try:
                path, method = scope["path"], scope["method"]
                desired = headers.get("access-control-request-method") if method == "OPTIONS" else method
                name = route(path, desired)
                if duplicate or headers.get("host") != backend_host or scope.get("query_string") or name is None:
                    ledger.deny("http_boundary")
                if name != "health" and headers.get("origin") != frontend_origin: ledger.deny("origin")
                if method == "OPTIONS":
                    if any(x.strip().lower() not in ("authorization", "content-type") for x in headers.get("access-control-request-headers", "").split(",") if x.strip()): ledger.deny("cors_headers")
                    await Response(status_code=204, headers={**cors, "Access-Control-Allow-Methods": desired,
                                                          "Access-Control-Allow-Headers": "Authorization, Content-Type"})(scope, receive, send)
                    return
                if name == "health":
                    await inner(scope, receive, send)
                    return
                if config.signature != candidate_app._signature(os.environ): ledger.deny("configuration_drift", 503)
                stage = "authentication"
                clerk = await junior_entry.require_identity(headers.get("authorization"))
                if name == "profile_link" and path.rsplit("/", 1)[1] != clerk: ledger.deny("profile_subject")
                ledger.reserve("personal_requests")
                if method == "PATCH": ledger.reserve("patch_attempts")
                ctx = SimpleNamespace(clerk=clerk, method=method, owner=None, connections=[], expected_version=None, write_attempts=0)
                marker = CONTEXT.set(ctx)
                stage = "owner_link"
                ctx.owner = await run_in_threadpool(resolve_owner)
                inner_receive = receive
                if method == "PATCH":
                    stage = "patch_input"
                    async def read_body():
                        data = bytearray()
                        while True:
                            message = await receive()
                            if message["type"] != "http.request": ledger.deny("request_disconnected", 400)
                            data.extend(message.get("body", b""))
                            if len(data) > workspace.MAX_BODY_BYTES: ledger.deny("body_limit", 400)
                            if not message.get("more_body"): return bytes(data)
                    body = await asyncio.wait_for(read_body(), 10)
                    revision, expected, _ = workspace._request(workspace._json(body))
                    with ledger.lock:
                        if (ledger.baseline is None or ledger.data["writes_closed"] or expected != ledger.version
                                or revision != workspace._revision(ctx.owner)): ledger.deny("save_requires_current_baseline", 409)
                    ctx.expected_version = expected
                    consumed = False
                    async def replay():
                        nonlocal consumed
                        if not consumed:
                            consumed = True
                            return {"type": "http.request", "body": body, "more_body": False}
                        return await receive()
                    inner_receive = replay
                messages, body_parts, status = [], bytearray(), None
                async def capture(message):
                    nonlocal status
                    messages.append(message)
                    if message["type"] == "http.response.start": status = message["status"]
                    if message["type"] == "http.response.body":
                        body_parts.extend(message.get("body", b""))
                        if len(body_parts) > 512 * 1024: ledger.deny("response_limit", 503)
                stage = "application_route"
                await inner(scope, inner_receive, capture)
                if name.startswith("workspace_") and status == 200:
                    stage = "workspace_receipt"
                    ledger.remember(json.loads(body_parts), ctx, patch=method == "PATCH")
                with ledger.lock:
                    if method == "PATCH" and status != 200: ledger.data["writes_closed"] = True
                    key = name + ":" + str(status)
                    ledger.data["outcomes"][key] = ledger.data["outcomes"].get(key, 0) + 1
                    ledger.flush()
                for message in messages:
                    response_started = True
                    await send(message)
            except Exception as exc:
                ledger.error(stage, exc)
                if ctx is not None and ctx.method == "PATCH" and ctx.expected_version is not None:
                    with ledger.lock:
                        ledger.data["writes_closed"] = True
                        ledger.flush()
                if not response_started:
                    await JSONResponse({"detail": "The local acceptance request could not be completed."},
                                       status_code=exc.status_code if isinstance(exc, HTTPException) else 503, headers=cors)(scope, receive, send)
            finally:
                if ctx is not None:
                    for db in ctx.connections:
                        if not db.closed:
                            try: db.close()
                            except Exception: pass
                if marker is not None: CONTEXT.reset(marker)

    result = AcceptanceApp()
    result.ledger, result.inner = ledger, inner
    return result
