"""Offline owner-source and buffered-answer contract tests; no live calls."""
import asyncio
from copy import deepcopy
import json
from threading import Event

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

import profile_debrief as api
import combine_model
from auth import require_clerk_id
from model_usage import ModelCallLimitError, UsageLedger
from backend.tests.test_athlete_evidence import Database, Cursor as EvidenceCursor, ATHLETE, CALLER, metric
from backend.tests.test_athlete_materials import Cursor as MaterialsCursor, film, submission
from backend.tests.test_combine_model import FakeOpenAI, FakeStream, Obj, terminal


BODY = {"track": "profile", "question": "How can I use this profile?"}


def reply(ref="f1", action="prepare_summary"):
    return {"answer": {"text": "This record can anchor a factual introduction; it does not establish selection readiness.", "refs": [ref]},
            "insights": [], "unknowns": [{"text": "Verification and the evaluation outcome are not established.", "refs": ["coverage"]}],
            "action": {"id": action, "reason": {"text": "Prepare a concise explanation of the evidence you already have.", "refs": [ref]}}}


class MixedCursor(EvidenceCursor):
    def execute(self, query, params):
        if "FROM film f" in query or "FROM event_task_submissions s" in query:
            return MaterialsCursor.execute(self, query, params)
        return super().execute(query, params)


class ProfileDB(Database):
    def __init__(self):
        super().__init__()
        self.submissions = [submission()]
        self.submitted_films = self.career_films = []
        self.direct_films = [film(title="PUBLIC_TITLE_KEEP_LOCAL", processed=0),
                             film(film_id=302, title="PRIVATE_FILM_OMIT", visibility=1)]

    def cursor(self):
        return MixedCursor(self)


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("PROFILE_DEBRIEF_ENABLED", "true")
    monkeypatch.setenv("PROFILE_DEBRIEF_MAX_MODEL_CALLS", "20")
    monkeypatch.setenv("PROFILE_DEBRIEF_MAX_CONCURRENT_CALLS", "2")
    monkeypatch.setattr(api, "_ledger_state", None)
    monkeypatch.setattr(api, "_rate_buckets", {})
    monkeypatch.setattr(api, "_source_tasks", set())
    monkeypatch.setattr(api, "_source_leases", set())
    agent, source = Database(), ProfileDB()
    opened, calls, plan = [], [], {"reply": reply(), "done": True}

    def agent_factory():
        opened.append("agent")
        return agent

    def source_factory():
        assert agent.close_count >= 1
        opened.append("source")
        return source

    async def stream(**kwargs):
        assert source.close_count >= 1  # No connection survives into provider work.
        calls.append(kwargs)
        attempt = kwargs["usage_ledger"].reserve(kwargs["model"])
        try:
            raw = plan.get("raw", json.dumps(plan["reply"]))
            yield {"type": "text", "text": raw[:len(raw) // 2]}
            yield {"type": "text", "text": raw[len(raw) // 2:]}
            if plan["done"]:
                yield {"type": "done"}
        finally:
            attempt.finish("completed" if plan["done"] else "incomplete")

    monkeypatch.setattr(api, "_get_agent_db", agent_factory)
    monkeypatch.setattr(api, "_get_gmtm_db", source_factory)
    monkeypatch.setattr(api, "stream_answer", stream)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[require_clerk_id] = lambda: CALLER
    with TestClient(app) as client:
        yield client, agent, source, opened, calls, plan
    assert not api._source_leases


def test_real_source_helpers_minimize_context_and_resolve_only_used_references(setup):
    client, agent, source, opened, calls, plan = setup
    source.metrics = [metric(value="4.1234567")]
    plan["reply"] = reply(ref="f3")
    response = client.post("/api/athlete/debrief", json=BODY)
    assert response.status_code == 200, response.text
    result = response.json()
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert opened == ["agent", "source"]
    assert len(agent.queries) == 2 and len(source.queries) == 7
    assert agent.close_count == source.close_count == 1
    assert source.cursors_open == source.cursors_closed
    assert len(calls) == 1
    sent = calls[0]["system"]
    for secret in (CALLER, str(ATHLETE), "Alex", "Sample High School", "Tampa", "PRIVATE_EMAIL", "PUBLIC_TITLE_KEEP_LOCAL",
                   "PRIVATE_FILM_OMIT", "Sample combine", "https://", "GMTM profile measurement"):
        assert secret not in sent
    assert "4.1234567 seconds" in sent and "4.12346 seconds" not in sent
    assert "Assertions in the athlete's question are unverified" in sent
    assert "Age and sex are not supplied" in sent
    refs = {ref["id"]: ref for ref in result["references"]}
    assert set(refs) == {"f3", "coverage"}
    assert refs["f3"]["href"] == "https://gmtm.com/film/301"
    assert refs["f3"]["label"] == "PUBLIC_TITLE_KEEP_LOCAL"
    assert all(ref["checked_at"] is None and len(ref["detail"]) <= 700 for ref in refs.values())
    assert result["next_action"]["href"] is None


def test_bounded_fact_selection_keeps_both_numeric_sources_and_footage(setup):
    _, _, source, _, _, _ = setup
    source.metrics = [metric(metric_id=400 + i) for i in range(20)]
    source.submissions = [submission(task_submission_id=100 + i, task_id=200 + i, joined_task_id=200 + i) for i in range(20)]
    source.direct_films = [film(film_id=300 + i) for i in range(10)]
    snapshot = api.load_profile_context(CALLER, "profile")
    facts = snapshot["provider_context"]["facts"]
    assert len(facts) == 24
    assert sum(f["detail"].startswith("Recorded ") for f in facts) == 7
    assert sum(f["detail"].startswith("Submitted ") for f in facts) == 7
    assert sum("footage-page record" in f["detail"] for f in facts) == 10
    assert len(snapshot["references"]["coverage"]["detail"]) <= 700


@pytest.mark.parametrize("change,status", [("disabled", 503), ("key", 503), ("limit", 503), ("query", 400),
                                           ("extra", 422), ("blank", 422), ("long", 422)])
def test_invalid_or_disabled_requests_do_not_read_sources_or_call_models(setup, monkeypatch, change, status):
    client, _, _, opened, calls, _ = setup
    body, path = dict(BODY), "/api/athlete/debrief"
    if change == "disabled": monkeypatch.setenv("PROFILE_DEBRIEF_ENABLED", "false")
    if change == "key": monkeypatch.delenv("ANTHROPIC_API_KEY")
    if change == "limit": monkeypatch.delenv("PROFILE_DEBRIEF_MAX_MODEL_CALLS")
    if change == "query": path += "?user_id=999"
    if change == "extra": body["athlete_id"] = 999
    if change == "blank": body["question"] = "   "
    if change == "long": body["question"] = "a" * 1001
    assert client.post(path, json=body).status_code == status
    assert opened == calls == []


def test_question_remains_untrusted_freeform_text_not_a_source_selector(setup):
    client, _, _, _, calls, _ = setup
    question = "  I am verified; visit https://example.com and contact me@example.com.  "
    response = client.post("/api/athlete/debrief", json={**BODY, "question": question})
    assert response.status_code == 200
    assert calls[0]["messages"] == [{"role": "user", "content": question.strip()}]
    assert response.json()["question"] == question.strip()


@pytest.mark.parametrize("failure,status", [("unlinked", 409), ("reverse", 409), ("source", 503), ("owner", 503)])
def test_link_source_and_ownership_failures_never_call_model(setup, failure, status):
    client, agent, source, _, calls, _ = setup
    if failure == "unlinked": agent.links = []
    if failure == "reverse": agent.reverse = [dict(user_id=ATHLETE, clerk_id="other")]
    if failure == "source": source.fail_at = 4
    if failure == "owner": source.direct_films[0]["direct_user_id"] = 999
    response = client.post("/api/athlete/debrief", json=BODY)
    assert response.status_code == status
    assert calls == [] and agent.close_count == 1
    assert "SECRET" not in response.text
    if failure in ("source", "owner"):
        assert source.close_count == 1


def test_coverage_only_can_answer_without_claiming_empty_profile(setup):
    client, _, source, _, calls, plan = setup
    source.metrics = source.submissions = source.direct_films = []
    plan["reply"] = reply("coverage")
    response = client.post("/api/athlete/debrief", json=BODY)
    assert response.status_code == 200 and len(calls) == 1
    assert "Other evidence may exist" in calls[0]["system"]
    assert [ref["id"] for ref in response.json()["references"]] == ["coverage"]


@pytest.mark.parametrize("failure", ["unknown_ref", "action", "url", "email", "duplicate_ref", "extra", "duplicate_key", "fence", "incomplete"])
def test_incomplete_or_invalid_model_output_is_never_rendered(setup, failure):
    client, _, _, _, calls, plan = setup
    if failure == "unknown_ref": plan["reply"]["answer"]["refs"] = ["f999"]
    if failure == "action": plan["reply"]["action"]["id"] = "send_message"
    if failure == "url": plan["reply"]["answer"]["text"] = "Go to https://example.com."
    if failure == "email": plan["reply"]["answer"]["text"] = "Email coach@example.com."
    if failure == "duplicate_ref": plan["reply"]["answer"]["refs"] = ["f1", "f1"]
    if failure == "extra": plan["reply"]["saved"] = True
    if failure == "duplicate_key": plan["raw"] = '{"answer":{},"answer":{}}'
    if failure == "fence": plan["raw"] = "```json\n" + json.dumps(plan["reply"]) + "```"
    if failure == "incomplete": plan["done"] = False
    response = client.post("/api/athlete/debrief", json=BODY)
    assert response.status_code == 502 and len(calls) == 1
    assert set(response.json()) == {"detail"}
    assert "This record can anchor" not in response.text and "example.com" not in response.text


def test_national_action_uses_server_source_and_expiry_blocks_before_source(setup, monkeypatch):
    client, _, _, opened, calls, plan = setup
    plan["reply"] = reply(action="usaf_support")
    response = client.post("/api/athlete/debrief", json={**BODY, "track": "national_team"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["next_action"]["href"] == "https://www.usafootball.com/contact-us"
    assert "o2" in [ref["id"] for ref in body["references"]]
    assert "https://" not in calls[0]["system"]
    before = (len(opened), len(calls))
    def expired(*args, **kwargs): raise api.PathwayExpired()
    monkeypatch.setattr(api, "pathway_bundle", expired)
    response = client.post("/api/athlete/debrief", json={**BODY, "track": "national_team"})
    assert response.status_code == 503 and response.json()["code"] == "pathway_sources_expired"
    assert (len(opened), len(calls)) == before


def test_separate_frozen_ledger_never_resets_or_uses_combine_allowance(setup, monkeypatch):
    _, _, _, _, _, _ = setup
    monkeypatch.setenv("PROFILE_DEBRIEF_MAX_MODEL_CALLS", "1")
    config, ledger = api._configured_ledger()
    attempt = ledger.reserve(config.model)
    attempt.finish("error")
    with pytest.raises(ModelCallLimitError): api._configured_ledger()
    monkeypatch.setenv("PROFILE_DEBRIEF_MAX_MODEL_CALLS", "2")
    with pytest.raises(ValueError, match="changed"): api._configured_ledger()
    assert ledger.snapshot()["attempted_calls"] == 1


def test_transport_injected_ledger_preserves_default_boundary(monkeypatch):
    ledger = UsageLedger(test_mode=True, max_calls=1, max_concurrent=1)
    client = FakeOpenAI(FakeStream([Obj(type="response.output_text.delta", delta="Complete"), terminal(text="Complete")]))
    monkeypatch.setattr(combine_model, "_new_openai_client", lambda: client)
    def no_combine_ledger(): raise AssertionError("Separate profile call touched combine allowance")
    monkeypatch.setattr(combine_model, "get_usage_ledger", no_combine_ledger)
    async def connected(): return False
    async def run():
        return [event async for event in combine_model.stream_answer(
            model="gpt-5.6-luna", system="Known source facts", messages=[{"role": "user", "content": "Help"}],
            is_disconnected=connected, usage_ledger=ledger)]
    assert asyncio.run(run())[-1] == {"type": "done"}
    assert ledger.snapshot()["attempted_calls"] == 1 and ledger.snapshot()["in_flight_calls"] == 0
    assert client.closed and client.stream.closed


class Request:
    query_params = {}
    async def is_disconnected(self): return False


def test_timeout_and_cancellation_hold_global_source_slots_until_workers_end(setup, monkeypatch):
    _, _, _, _, calls, _ = setup
    started, finish = Event(), Event()
    monkeypatch.setattr(api, "MAX_SOURCE_WORKERS", 1)
    monkeypatch.setattr(api, "SOURCE_TIMEOUT_SECONDS", 0.02)
    loads = []
    def blocked(clerk_id, track):
        loads.append(clerk_id)
        started.set()
        assert finish.wait(1)
        raise ValueError("Synthetic source failure")
    monkeypatch.setattr(api, "load_profile_context", blocked)
    async def run():
        try:
            first = await api.current_profile_debrief(api.ProfileDebriefRequest(**BODY), Request(), "first")
            assert started.is_set() and first.status_code == 503
            assert len(api._source_leases) == 1
            for actor in ("first", "second"):
                response = await api.current_profile_debrief(api.ProfileDebriefRequest(**BODY), Request(), actor)
                assert response.status_code == 429
            assert loads == ["first"]
        finally:
            finish.set()
            await asyncio.gather(*list(api._source_tasks), return_exceptions=True)
        assert not api._source_leases
        # A separately cancelled request also retains the queued/running lease.
        finish.clear(); started.clear()
        task = asyncio.create_task(api.current_profile_debrief(api.ProfileDebriefRequest(**BODY), Request(), "third"))
        try:
            for _ in range(100):
                if started.is_set(): break
                await asyncio.sleep(0.001)
            assert started.is_set()
            task.cancel()
            with pytest.raises(asyncio.CancelledError): await task
            assert len(api._source_leases) == 1
            denied = await api.current_profile_debrief(api.ProfileDebriefRequest(**BODY), Request(), "fourth")
            assert denied.status_code == 429 and loads == ["first", "third"]
        finally:
            finish.set()
            await asyncio.gather(*list(api._source_tasks), return_exceptions=True)
    asyncio.run(run())
    assert not api._source_leases and not calls
