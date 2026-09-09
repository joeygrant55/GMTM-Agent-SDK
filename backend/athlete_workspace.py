"""Private authored workspace, separate from canonical GMTM profile data.

Import performs no I/O, schema preparation or model work. GET reads only Agent
storage. Mutations lock the exact owner link and use both link and row versions.
Only explicitly changing a featured film checks the existing GMTM projection.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import re

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from auth import require_clerk_id
from combine_api import _get_agent_db, _get_gmtm_db
from athlete_evidence import PRIVATE_HEADERS
from source_scope import owner_scope


MAX_BODY_BYTES = 98304
MAX_VERSION = 2_147_483_647
MAX_RECENT = 20
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_FILM = re.compile(r"film-([1-9][0-9]{0,15})\Z")
_METRIC = re.compile(r"metric-([1-9][0-9]{0,15})\Z")
_SUBMISSION = re.compile(r"submission-([1-9][0-9]{0,15})-[0-9a-f]{16}\Z")
_KINDS = {"goal_saved", "goal_removed", "featured_saved", "featured_removed", "draft_saved", "draft_removed"}
_FIELDS = {"goal", "featured_source_id", "draft"}
_COLUMNS = "clerk_id, athlete_link_id, gmtm_user_id, version, payload, created_at, updated_at"


class WorkspaceError(Exception):
    def __init__(self, status, code, detail):
        self.status, self.code, self.detail = status, code, detail
        super().__init__(code)


def _invalid():
    return WorkspaceError(400, "workspace_invalid", "The saved-work request is invalid.")


def _unavailable():
    return WorkspaceError(503, "workspace_unavailable", "Your saved work is unavailable. Keep your current text and try again.")


def _link_changed():
    return WorkspaceError(409, "workspace_link_changed", "Your athlete connection changed or needs review. Reload your saved work before making changes.")


def _conflict():
    return WorkspaceError(409, "workspace_conflict", "Your saved work changed elsewhere. Keep your current text and load the saved version before trying again.")


def _positive(value):
    return type(value) is int and 0 < value <= 9_007_199_254_740_991


def _text(value, maximum, *, nonempty=False):
    if (not isinstance(value, str) or len(value) > maximum or _CONTROL.search(value)
            or any(0xD800 <= ord(char) <= 0xDFFF for char in value)
            or (nonempty and not value.strip())):
        raise _invalid()
    return value


def _source_id(value, matchers):
    if not isinstance(value, str):
        raise _invalid()
    match = next((found for matcher in matchers if (found := matcher.fullmatch(value))), None)
    if match is None or not _positive(int(match[1])):
        raise _invalid()
    return value


def _ids(value, maximum, matchers):
    if not isinstance(value, list) or len(value) > maximum:
        raise _invalid()
    result = [_source_id(item, matchers) for item in value]
    if len(set(result)) != len(result):
        raise _invalid()
    return result


def _goal(value):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"text", "destination", "timeframe"}:
        raise _invalid()
    return {"text": _text(value["text"], 600, nonempty=True),
            "destination": None if value["destination"] is None else _text(value["destination"], 200),
            "timeframe": None if value["timeframe"] is None else _text(value["timeframe"], 100)}


def _draft(value):
    if value is None:
        return None
    keys = {"kind", "text", "goal", "destination", "selected_evidence_ids", "selected_material_ids", "inputs_changed"}
    if (not isinstance(value, dict) or set(value) != keys or value["kind"] not in ("summary", "introduction")
            or type(value["inputs_changed"]) is not bool):
        raise _invalid()
    return {"kind": value["kind"], "text": _text(value["text"], 20000),
            "goal": _text(value["goal"], 600), "destination": _text(value["destination"], 200),
            "selected_evidence_ids": _ids(value["selected_evidence_ids"], 20, (_METRIC,)),
            "selected_material_ids": _ids(value["selected_material_ids"], 30, (_FILM, _SUBMISSION)),
            "inputs_changed": value["inputs_changed"]}


def _changes(value):
    if not isinstance(value, dict) or not value or not set(value) <= _FIELDS:
        raise _invalid()
    result = {}
    for key, item in value.items():
        result[key] = (_goal(item) if key == "goal" else _draft(item) if key == "draft"
                       else None if item is None else _source_id(item, (_FILM,)))
    return result


def _pairs(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise _invalid()
        output[key] = value
    return output


def _json(value):
    if not isinstance(value, (str, bytes)) or len(value.encode("utf-8") if isinstance(value, str) else value) > MAX_BODY_BYTES:
        raise _invalid()
    try:
        return json.loads(value, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(_invalid()))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise _invalid() from None


def _request(value):
    if not isinstance(value, dict) or set(value) != {"link_revision", "expected_version", "changes"}:
        raise _invalid()
    revision, version = value["link_revision"], value["expected_version"]
    if (not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{64}", revision)
            or type(version) is not int or not 0 <= version < MAX_VERSION):
        raise _invalid()
    return revision, version, _changes(value["changes"])


def _owner(cursor, clerk_id, *, lock=False):
    if (not isinstance(clerk_id, str) or not clerk_id or len(clerk_id.encode("utf-8")) > 255):
        raise _link_changed()
    suffix = " FOR UPDATE" if lock else ""
    cursor.execute("SELECT id, user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2" + suffix, (clerk_id,))
    rows = cursor.fetchall()
    if not rows:
        raise WorkspaceError(409, "workspace_unlinked", "Connect your athlete profile to save your work.")
    if (len(rows) != 1 or not isinstance(rows[0], dict) or rows[0].get("clerk_id") != clerk_id
            or not _positive(rows[0].get("id")) or not _positive(rows[0].get("user_id"))):
        raise _link_changed()
    row = rows[0]
    cursor.execute("SELECT id, user_id, clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 2" + suffix, (row["user_id"],))
    reverse = cursor.fetchall()
    if len(reverse) != 1 or reverse[0] != row:
        raise _link_changed()
    return row


def _revision(owner):
    # A comparison token, not an authorization credential. Including the link row
    # ID invalidates a tab after removal/recreation of an otherwise identical pair.
    raw = json.dumps([owner["clerk_id"], owner["id"], owner["user_id"]], separators=(",", ":"))
    return hashlib.sha256(("sparq-workspace-v1:" + raw).encode()).hexdigest()


def _time(value):
    if not isinstance(value, datetime):
        raise _unavailable()
    return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.astimezone(timezone.utc).isoformat()


def _state(cursor, owner, *, lock=False):
    cursor.execute(f"SELECT {_COLUMNS} FROM athlete_workspaces WHERE clerk_id = %s LIMIT 2" + (" FOR UPDATE" if lock else ""),
                   (owner["clerk_id"].encode("utf-8"),))
    rows = cursor.fetchall()
    empty = {"state": "ready", "link_revision": _revision(owner), "version": 0,
             "owner_scope": owner_scope(owner["clerk_id"], owner["user_id"]),
             "goal": None, "featured_source_id": None, "draft": None, "recent_work": [], "updated_at": None}
    if not rows:
        return empty
    if len(rows) != 1 or not isinstance(rows[0], dict):
        raise _unavailable()
    row = rows[0]
    if (row.get("clerk_id") != owner["clerk_id"].encode("utf-8") or row.get("athlete_link_id") != owner["id"]
            or type(row.get("athlete_link_id")) is not int or row.get("gmtm_user_id") != owner["user_id"]
            or type(row.get("gmtm_user_id")) is not int):
        raise _link_changed()
    if type(row.get("version")) is not int or not 1 <= row["version"] <= MAX_VERSION:
        raise _unavailable()
    try:
        payload = _json(row["payload"])
        if not isinstance(payload, dict) or set(payload) != _FIELDS | {"recent_work"}:
            raise _invalid()
        content = _changes({key: payload[key] for key in _FIELDS})
        recent = payload["recent_work"]
        if not isinstance(recent, list) or len(recent) > MAX_RECENT:
            raise _invalid()
        seen = set()
        for event in recent:
            if (not isinstance(event, dict) or set(event) != {"id", "kind", "at"}
                    or not isinstance(event["id"], str) or not re.fullmatch(r"[1-9][0-9]*:[a-z_]+", event["id"])
                    or event["id"] in seen or event["kind"] not in _KINDS
                    or not isinstance(event["at"], str) or len(event["at"]) > 40
                    or datetime.fromisoformat(event["at"]).utcoffset().total_seconds() != 0):
                raise _invalid()
            seen.add(event["id"])
    except (WorkspaceError, KeyError, TypeError, ValueError, AttributeError):
        raise _unavailable() from None
    return {**empty, **content, "version": row["version"], "recent_work": recent, "updated_at": _time(row.get("updated_at"))}


def _close(db):
    if db is not None:
        try:
            db.close()
        except Exception:
            raise _unavailable() from None


def _read_owned_workspace(clerk_id):
    db = None
    try:
        db = _get_agent_db()
        with db.cursor() as cursor:
            owner = _owner(cursor, clerk_id)
            return _state(cursor, owner), owner
    except WorkspaceError:
        raise
    except Exception:
        raise _unavailable() from None
    finally:
        _close(db)


def read_workspace(clerk_id):
    return _read_owned_workspace(clerk_id)[0]


def _check_feature(athlete_id, source_id):
    import athlete_materials as materials
    db = None
    try:
        db = _get_gmtm_db()
        films = [("submission", materials._submitted_film_rows(db, athlete_id)),
                 ("direct", materials._direct_film_rows(db, athlete_id)),
                 ("career", materials._career_film_rows(db, athlete_id))]
        items, _ = materials._project([], films, athlete_id)
        if not any(item["id"] == source_id and item["can_include"] and item["availability"] == "unchecked"
                   and item["source_url"] for item in items):
            raise WorkspaceError(400, "workspace_invalid", "Choose an available public clip from your profile.")
    except WorkspaceError:
        raise
    except Exception:
        raise WorkspaceError(503, "workspace_unavailable", "That clip could not be checked. Your saved work has not changed.") from None
    finally:
        _close(db)


def save_workspace(clerk_id, value):
    revision, expected, changes = _request(value)
    # Source validation does not hold an Agent transaction open. The second
    # owner resolution and link_revision comparison protect a concurrent relink.
    if changes.get("featured_source_id") is not None:
        initial, initial_owner = _read_owned_workspace(clerk_id)
        if initial["link_revision"] != revision:
            raise _link_changed()
        if initial["version"] != expected:
            raise _conflict()
        if changes["featured_source_id"] != initial["featured_source_id"]:
            _check_feature(initial_owner["user_id"], changes["featured_source_id"])
    db, started, committed = None, False, False
    try:
        db = _get_agent_db()
        with db.cursor() as cursor:
            cursor.execute("SET SESSION innodb_lock_wait_timeout = 3")
        db.begin()
        started = True
        with db.cursor() as cursor:
            owner = _owner(cursor, clerk_id, lock=True)
            if _revision(owner) != revision:
                raise _link_changed()
            current = _state(cursor, owner, lock=True)
            if current["version"] != expected:
                raise _conflict()
            changed = {key: item for key, item in changes.items() if current[key] != item}
            if not changed:
                db.rollback()
                started = False
                return current
            version = expected + 1
            now = datetime.now(timezone.utc)
            recent = []
            names = {"goal": "goal", "featured_source_id": "featured", "draft": "draft"}
            for key in ("goal", "featured_source_id", "draft"):
                if key in changed:
                    kind = names[key] + ("_removed" if changed[key] is None else "_saved")
                    recent.append({"id": f"{version}:{kind}", "kind": kind, "at": now.isoformat()})
            payload = {key: changed.get(key, current[key]) for key in _FIELDS}
            payload["recent_work"] = (recent + current["recent_work"])[:MAX_RECENT]
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            if len(encoded.encode()) > MAX_BODY_BYTES:
                raise _invalid()
            stamp, subject = now.replace(tzinfo=None), clerk_id.encode("utf-8")
            if expected == 0:
                cursor.execute("INSERT INTO athlete_workspaces (clerk_id, athlete_link_id, gmtm_user_id, version, payload, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                               (subject, owner["id"], owner["user_id"], version, encoded, stamp, stamp))
            else:
                cursor.execute("UPDATE athlete_workspaces SET version = %s, payload = %s, updated_at = %s WHERE clerk_id = %s AND athlete_link_id = %s AND gmtm_user_id = %s AND version = %s",
                               (version, encoded, stamp, subject, owner["id"], owner["user_id"], expected))
            if cursor.rowcount != 1:
                raise _conflict()
        db.commit()
        committed = True
        return {"state": "ready", "link_revision": revision, "version": version,
                "owner_scope": owner_scope(clerk_id, owner["user_id"]),
                **payload, "updated_at": now.isoformat()}
    except WorkspaceError:
        raise
    except Exception as exc:
        if getattr(exc, "args", ()) and type(exc.args[0]) is int and exc.args[0] in (1062, 1205, 1213):
            raise _conflict() from None
        raise _unavailable() from None
    finally:
        try:
            if db is not None and started and not committed:
                db.rollback()
        except Exception:
            raise _unavailable() from None
        finally:
            _close(db)


def _response(call):
    try:
        return JSONResponse(call(), headers=PRIVATE_HEADERS)
    except WorkspaceError as exc:
        return JSONResponse({"detail": exc.detail, "code": exc.code}, status_code=exc.status, headers=PRIVATE_HEADERS)


def current_athlete_workspace(request: Request, caller_clerk_id: str = Depends(require_clerk_id)):
    return _response(lambda: (_ for _ in ()).throw(_invalid()) if request.query_params else read_workspace(caller_clerk_id))


async def update_athlete_workspace(request: Request, caller_clerk_id: str = Depends(require_clerk_id)):
    async def body():
        data = bytearray()
        async for part in request.stream():
            data.extend(part)
            if len(data) > MAX_BODY_BYTES:
                raise _invalid()
        return bytes(data)
    try:
        if request.query_params or request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise _invalid()
        value = _json(await asyncio.wait_for(body(), timeout=10))
        _request(value)
    except (WorkspaceError, asyncio.TimeoutError, ValueError):
        return _response(lambda: (_ for _ in ()).throw(_invalid()))
    return await run_in_threadpool(lambda: _response(lambda: save_workspace(caller_clerk_id, value)))
