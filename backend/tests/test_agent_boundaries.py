"""Agent authorization/tool tests. conftest blocks dotenv, real DB and all network I/O."""

import copy
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import agent_api
from athlete_context import CURRENT_ATHLETE_TOOL, current_athlete_tool_result


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self.rows = []
        self.rowcount = 0
        self.lastrowid = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        q = " ".join(sql.split())
        store = self.db.store
        store["queries"].append((q, params))
        self.rows, self.rowcount = [], 0
        convs, messages = store["conversations"], store["messages"]
        if q.startswith("SELECT id FROM agent_conversations WHERE clerk_id"):
            assert "ORDER BY id ASC LIMIT 1" in q
            ids = sorted(k for k, v in convs.items() if v["clerk_id"] == params[0])
            self.rows = [{"id": ids[0]}] if ids else []
        elif q.startswith("SELECT clerk_id FROM agent_conversations WHERE id"):
            row = convs.get(params[0])
            self.rows = [{"clerk_id": row["clerk_id"]}] if row else []
        elif q.startswith("SELECT role, content FROM agent_messages"):
            assert "WHERE ac.id = %s AND ac.clerk_id = %s" in q
            cid, owner = params
            if convs.get(cid, {}).get("clerk_id") == owner:
                self.rows = [dict(role=m["role"], content=m["content"]) for m in reversed(messages) if m["conversation_id"] == cid][:20]
        elif q.startswith("INSERT IGNORE INTO agent_conversations"):
            if not any(c["clerk_id"] == params[0] for c in convs.values()):
                self.lastrowid = max(convs, default=0) + 1
                convs[self.lastrowid] = {"clerk_id": params[0]}
                self.rowcount = 1
        elif q.startswith("INSERT INTO agent_conversations"):
            if store.get("fail_fork"):
                raise RuntimeError("isolated schema constraint failure")
            owner, scenario, parent = params
            self.lastrowid = max(convs, default=0) + 1
            convs[self.lastrowid] = {"clerk_id": owner, "fork_scenario": scenario, "parent_id": parent}
            self.rowcount = 1
        elif q.startswith("INSERT INTO agent_messages") and "SELECT ac.id, %s, %s, NOW()" in q:
            assert "WHERE ac.id = %s AND ac.clerk_id = %s" in q
            role, content, cid, owner = params
            if convs.get(cid, {}).get("clerk_id") == owner:
                messages.append({"conversation_id": cid, "role": role, "content": content})
                self.rowcount = 1
        elif q.startswith("INSERT INTO agent_messages") and "SELECT %s, am.role" in q:
            assert "WHERE ac.id = %s AND ac.clerk_id = %s" in q
            if store.get("fail_copy"):
                raise RuntimeError("isolated copy failure")
            target, parent, owner = params
            if convs.get(parent, {}).get("clerk_id") == owner:
                copies = [dict(m, conversation_id=target) for m in messages if m["conversation_id"] == parent]
                messages.extend(copies)
                self.rowcount = len(copies)
        else:
            raise AssertionError(f"Unexpected SQL in isolated test: {q}")

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeDB:
    def __init__(self, store):
        self.store = store
        self.before = copy.deepcopy((store["conversations"], store["messages"]))
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.store["commits"] += 1

    def rollback(self):
        self.store["rollbacks"] += 1
        self.store["conversations"], self.store["messages"] = copy.deepcopy(self.before)

    def close(self):
        self.closed = True


def tool_response(name="get_current_athlete", arguments=None):
    return SimpleNamespace(stop_reason="tool_use", content=[SimpleNamespace(type="tool_use", id="tool-1", name=name, input={} if arguments is None else arguments)])


def text_response(text="Here is your next step."):
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


class FakeStream:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def __iter__(self):
        for block in self.response.content:
            yield SimpleNamespace(type="content_block_start", content_block=block)
            if block.type == "text":
                yield SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(type="text_delta", text=block.text))

    def get_final_message(self):
        return self.response


@pytest.fixture
def client(monkeypatch):
    store = {
        "conversations": {1: {"clerk_id": "user_alpha"}, 2: {"clerk_id": "user_beta"}, 10: {"clerk_id": "user_alpha", "parent_id": 1, "fork_scenario": "Hypothetical"}},
        "messages": [
            {"conversation_id": 1, "role": "assistant", "content": "Main context"},
            {"conversation_id": 2, "role": "assistant", "content": "Foreign private context"},
            {"conversation_id": 10, "role": "assistant", "content": "Hypothetical fork context"},
        ],
        "queries": [], "connections": [], "commits": 0, "rollbacks": 0,
        "profile_calls": [], "model_calls": [], "model_constructions": 0,
        "responses": [text_response()],
    }

    def db_factory():
        db = FakeDB(store)
        store["connections"].append(db)
        return db

    def profile_factory(subject):
        store["profile_calls"].append(subject)
        return {"name": "Synthetic Alpha", "source": "sparq_profile", "combine_results": []}

    def model_factory(**_):
        store["model_constructions"] += 1

        def create(**kwargs):
            store["model_calls"].append(copy.deepcopy(kwargs))
            return store["responses"].pop(0)

        return SimpleNamespace(messages=SimpleNamespace(create=create, stream=lambda **kw: FakeStream(create(**kw))))

    monkeypatch.setattr(agent_api, "_get_agent_db", db_factory)
    monkeypatch.setattr(agent_api, "_load_athlete_profile", profile_factory)
    monkeypatch.setattr(agent_api.anthropic, "Anthropic", model_factory)
    monkeypatch.setenv("DEMO_PROXY_SECRET", "isolated-demo-secret")
    monkeypatch.setattr(agent_api, "rate_limit", lambda *_a, **_k: True)
    app = FastAPI()
    app.include_router(agent_api.router)
    identity = {"subject": "user_alpha"}
    app.dependency_overrides[agent_api.require_identity] = lambda: identity["subject"]
    app.dependency_overrides[agent_api.optional_identity] = lambda: identity["subject"]
    with TestClient(app) as tc:
        tc.store, tc.identity = store, identity
        yield tc
    assert all(db.closed for db in store["connections"])


def stream_request(client, conversation_id=None, **extra):
    params = {"athlete_id": "user_alpha", "message": "What comes next?", **extra}
    if conversation_id is not None:
        params["conversation_id"] = conversation_id
    return client.get("/api/agent/stream", params=params)


def events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


@pytest.mark.parametrize("path", ["stream", "chat"])
@pytest.mark.parametrize("cid,status", [(2, 403), (999, 404)])
def test_explicit_foreign_or_missing_thread_stops_before_profile_and_model(client, path, cid, status):
    before = copy.deepcopy(client.store["messages"])
    if path == "stream":
        res = stream_request(client, cid)
    else:
        res = client.post("/api/agent/chat", json={"athlete_id": "user_alpha", "message": "Hi", "conversation_id": cid})
    assert res.status_code == status
    assert client.store["messages"] == before
    assert client.store["profile_calls"] == []
    assert client.store["model_constructions"] == 0
    assert all(not q.startswith("INSERT") for q, _ in client.store["queries"])


@pytest.mark.parametrize("value", [0, -1, False, 1.5, "", "abc", "²", pytest.param("9" * 5000, id="oversized")])
def test_invalid_explicit_thread_does_not_fall_back_to_default(client, value):
    res = client.post("/api/agent/chat", json={"athlete_id": "user_alpha", "message": "Hi", "conversation_id": value})
    assert res.status_code == 400
    assert client.store["queries"] == []
    assert client.store["model_constructions"] == 0


def test_forged_athlete_stops_before_any_data_access(client):
    res = stream_request(client, athlete_id="user_beta")
    assert res.status_code == 403
    assert client.store["queries"] == []
    assert client.store["profile_calls"] == []


def test_atomic_write_rechecks_owner_after_preflight(client):
    agent_api._require_conversation_owner("user_alpha", 1)
    client.store["conversations"][1]["clerk_id"] = "user_beta"
    before = copy.deepcopy(client.store["messages"])
    with pytest.raises(HTTPException) as exc:
        agent_api._save_message("user_alpha", "user", "Must not enter foreign history", 1)
    assert exc.value.status_code == 403
    assert client.store["messages"] == before
    assert client.store["rollbacks"] == 1


def test_default_history_excludes_newer_forks_and_other_athletes(client):
    assert agent_api._load_conversation("user_alpha") == [{"role": "assistant", "content": "Main context"}]


@pytest.mark.parametrize("path", ["stream", "chat"])
def test_owned_chat_uses_scoped_snapshot_and_preserves_web_search(client, path):
    client.store["responses"] = [tool_response(), text_response()]
    if path == "stream":
        res = stream_request(client)
        assert {"type": "session", "session_id": "1"} in events(res)
        assert events(res)[-1] == {"type": "done"}
    else:
        res = client.post("/api/agent/chat", json={"athlete_id": "user_alpha", "message": "What comes next?"})
        assert res.json()["session_id"] == "1"
    assert res.status_code == 200
    calls = client.store["model_calls"]
    assert len(calls) == 2
    assert calls[0]["messages"][0]["content"] == "Main context"
    assert "Hypothetical fork context" not in str(calls)
    assert "Foreign private context" not in str(calls)
    assert calls[0]["tools"][0] == {"type": "web_search_20250305", "name": "web_search"}
    result = json.loads(calls[1]["messages"][-1]["content"][0]["content"])
    assert result["profile"]["name"] == "Synthetic Alpha"
    assert client.store["profile_calls"] == ["user_alpha"]
    assert all(m["conversation_id"] == 1 for m in client.store["messages"][3:])


def test_owned_explicit_fork_reads_and_writes_only_that_thread(client):
    res = stream_request(client, 10)
    assert res.status_code == 200
    assert client.store["model_calls"][0]["messages"][0]["content"] == "Hypothetical fork context"
    assert all(m["conversation_id"] == 10 for m in client.store["messages"][3:])


def test_default_conversation_is_created_when_none_exists(client):
    client.store["conversations"] = {}
    client.store["messages"] = []
    res = stream_request(client)
    assert res.status_code == 200
    assert client.store["conversations"] == {1: {"clerk_id": "user_alpha"}}
    assert len(client.store["messages"]) == 2


@pytest.mark.parametrize("arguments", [{"sql": "SELECT email FROM users"}, {"athlete_id": "user_beta"}, {"user_id": 2}, {"profile": {"name": "Foreign"}}, None, [], ""])
def test_current_athlete_tool_rejects_every_argument(arguments):
    result = current_athlete_tool_result("get_current_athlete", arguments, {"name": "Synthetic Alpha"})
    assert "error" in result
    assert "profile" not in result


def test_sql_tool_and_schema_dump_are_removed():
    assert {t["name"] for t in agent_api.TOOLS} == {"web_search", "get_current_athlete"}
    assert CURRENT_ATHLETE_TOOL["input_schema"] == {"type": "object", "properties": {}, "additionalProperties": False}
    assert not hasattr(agent_api, "_run_read_only_query")
    assert "GMTM SCHEMA" not in agent_api.SYSTEM_PROMPT
    assert "query_database" not in agent_api.SYSTEM_PROMPT
    assert "error" in current_athlete_tool_result("query_database", {"sql": "SELECT 1"}, {"name": "Synthetic Alpha"})


def test_tool_returns_independent_snapshot_and_explicit_unavailable():
    profile = {"name": "Synthetic Alpha", "combine_results": [{"value": 4.6}]}
    result = current_athlete_tool_result("get_current_athlete", {}, profile)
    result["profile"]["combine_results"][0]["value"] = 9
    assert profile["combine_results"][0]["value"] == 4.6
    assert current_athlete_tool_result("get_current_athlete", {}, None)["available"] is False
    assert "profile" not in current_athlete_tool_result("get_current_athlete", {}, profile, is_demo=True)


def test_old_sql_tool_call_gets_error_without_database_execution(client):
    client.store["responses"] = [tool_response("query_database", {"sql": "SELECT email FROM users"}), text_response()]
    res = stream_request(client)
    assert res.status_code == 200
    result = client.store["model_calls"][1]["messages"][-1]["content"][0]
    assert result["is_error"] is True
    assert "error" in json.loads(result["content"])
    assert all("FROM users" not in q for q, _ in client.store["queries"])


def test_demo_never_loads_database_profile_or_history_even_with_numeric_athlete_id(client):
    client.identity["subject"] = None
    client.store["responses"] = [tool_response(), text_response()]
    before = copy.deepcopy(client.store["messages"])
    res = client.get("/api/agent/stream", params={"athlete_id": "2", "message": "Tell me about this athlete"}, headers={"X-Demo-Secret": "isolated-demo-secret"})
    assert res.status_code == 200
    assert client.store["queries"] == []
    assert client.store["profile_calls"] == []
    assert client.store["messages"] == before
    assert "Foreign private context" not in res.text
    result = json.loads(client.store["model_calls"][1]["messages"][-1]["content"][0]["content"])
    assert result["available"] is False
    assert "profile" not in result


def test_demo_rejects_saved_conversation_without_data_or_model_work(client):
    client.identity["subject"] = None
    res = client.get("/api/agent/stream", params={"athlete_id": "demo-test", "message": "Hi", "conversation_id": 1}, headers={"X-Demo-Secret": "isolated-demo-secret"})
    assert res.status_code == 400
    assert client.store["queries"] == []
    assert client.store["model_constructions"] == 0


@pytest.mark.parametrize("parent,status", [(2, 403), (999, 404)])
def test_fork_rejects_foreign_or_missing_parent_without_mutating(client, parent, status):
    before = copy.deepcopy(client.store["conversations"])
    res = client.post("/api/agent/fork", json={"athlete_id": "user_alpha", "scenario": "Switch sports", "parent_conversation_id": parent})
    assert res.status_code == status
    assert client.store["conversations"] == before
    assert all(not q.startswith(("INSERT", "ALTER")) for q, _ in client.store["queries"])


def test_fork_requires_existing_parent(client):
    client.store["conversations"] = {}
    res = client.post("/api/agent/fork", json={"athlete_id": "user_alpha", "scenario": "Switch sports"})
    assert res.status_code == 404
    assert client.store["conversations"] == {}


def test_fork_copies_default_parent_with_one_commit_and_no_schema_changes(client):
    res = client.post("/api/agent/fork", json={"athlete_id": "user_alpha", "scenario": "Switch sports"})
    assert res.status_code == 200
    cid = int(res.json()["session_id"])
    assert client.store["conversations"][cid]["parent_id"] == 1
    assert [m["content"] for m in client.store["messages"] if m["conversation_id"] == cid] == ["Main context"]
    assert client.store["commits"] == 1
    assert any("FOR UPDATE" in q for q, _ in client.store["queries"])
    assert all(not q.startswith("ALTER") for q, _ in client.store["queries"])


@pytest.mark.parametrize("failure", ["fail_fork", "fail_copy"])
def test_fork_storage_failure_rolls_back_and_returns_real_http_error(client, failure):
    client.store[failure] = True
    before = copy.deepcopy((client.store["conversations"], client.store["messages"]))
    res = client.post("/api/agent/fork", json={"athlete_id": "user_alpha", "scenario": "Switch sports", "parent_conversation_id": 1})
    assert res.status_code == 503
    assert "unavailable" in res.json()["detail"]
    assert (client.store["conversations"], client.store["messages"]) == before
    assert client.store["commits"] == 0
    assert client.store["rollbacks"] == 1


def test_conversation_storage_failure_stops_before_profile_and_model(client, monkeypatch):
    def unavailable():
        raise ConnectionError("isolated failure")
    monkeypatch.setattr(agent_api, "_get_agent_db", unavailable)
    res = stream_request(client, 1)
    assert res.status_code == 503
    assert client.store["profile_calls"] == []
    assert client.store["model_constructions"] == 0


def test_assistant_save_failure_emits_stream_error_not_success(client, monkeypatch):
    original_save = agent_api._save_message

    def save(subject, role, content, conversation_id=None):
        if role == "assistant":
            raise HTTPException(status_code=503, detail="Your reply could not be saved.")
        return original_save(subject, role, content, conversation_id)

    monkeypatch.setattr(agent_api, "_save_message", save)
    res = stream_request(client, 1)
    assert res.status_code == 200  # headers were already sent before the model reply
    assert events(res)[-1] == {"type": "error", "error": "Your reply could not be saved."}
    assert not any(event["type"] == "done" for event in events(res))
    assert len(client.store["messages"]) == 4  # only the user's request was saved


def test_provider_failure_after_text_emits_generic_error_not_done(client, monkeypatch):
    class BrokenStream(FakeStream):
        def __iter__(self):
            yield from super().__iter__()
            raise RuntimeError("private provider failure detail")

    monkeypatch.setattr(agent_api.anthropic, "Anthropic", lambda **_: SimpleNamespace(
        messages=SimpleNamespace(stream=lambda **_: BrokenStream(text_response("Partial reply")))
    ))
    res = stream_request(client, 1)
    assert any(event["type"] == "text" for event in events(res))
    assert events(res)[-1]["type"] == "error"
    assert "private provider failure detail" not in res.text
    assert not any(event["type"] == "done" for event in events(res))
    assert len(client.store["messages"]) == 4


def test_ownership_change_during_generation_rejects_assistant_write(client, monkeypatch):
    original_save = agent_api._save_message

    def save(subject, role, content, conversation_id=None):
        if role == "assistant":
            client.store["conversations"][conversation_id]["clerk_id"] = "user_beta"
        return original_save(subject, role, content, conversation_id)

    monkeypatch.setattr(agent_api, "_save_message", save)
    res = stream_request(client, 1)
    assert events(res)[-1]["type"] == "error"
    assert not any(event["type"] == "done" for event in events(res))
    assert len(client.store["messages"]) == 4
    assert client.store["messages"][-1]["role"] == "user"


def test_numeric_athlete_identity_does_not_bypass_owner_mapping(monkeypatch):
    queries, gmtm_calls = [], []

    class EmptyAgentDB:
        def cursor(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, sql, params):
            queries.append((sql, params))

        def fetchone(self):
            return None

        def close(self):
            pass

    def forbidden_gmtm():
        gmtm_calls.append(True)
        raise AssertionError("No mapping means no GMTM lookup")

    monkeypatch.setattr(agent_api, "_get_agent_db", EmptyAgentDB)
    monkeypatch.setattr(agent_api, "_get_gmtm_db", forbidden_gmtm)
    assert agent_api._load_athlete_profile("4521") is None
    assert gmtm_calls == []
    assert any("athlete_profiles WHERE clerk_id" in sql and params == ("4521",) for sql, params in queries)
