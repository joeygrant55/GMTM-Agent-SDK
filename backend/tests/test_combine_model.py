"""Actual adapter protocol tests with synthetic streams; no real model calls."""

import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace as Obj

from fastapi import HTTPException
import pytest

import combine_help_api as help_api
import combine_model as model
import model_usage


def terminal(*, status="completed", text="Review your highlight footage in GMTM.", usage=True, output=None):
    return Obj(type="response.completed", response=Obj(status=status,
        output=output if output is not None else [Obj(type="message", role="assistant", status="completed",
                                                     content=[Obj(type="output_text", text=text)])],
        usage=Obj(input_tokens=1000, output_tokens=100,
                  input_tokens_details=Obj(cached_tokens=200),
                  output_tokens_details=Obj(reasoning_tokens=20)) if usage else None))


class FakeStream:
    def __init__(self, events, *, stall=False, error=False):
        self.events, self.stall, self.error = events, stall, error
        self.closed = self.cancelled = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        self.closed = True

    async def __aiter__(self):
        for event in self.events:
            await asyncio.sleep(0)
            yield event
        if self.stall:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise
        if self.error:
            raise RuntimeError("PRIVATE_PROVIDER_ERROR")


class FakeOpenAI:
    def __init__(self, stream):
        self.responses, self.stream, self.calls, self.closed = self, stream, [], False

    async def create(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        return self.stream

    async def close(self):
        self.closed = True


async def connected():
    return False


def run(monkeypatch, events=None, *, stall=False, error=False, **kwargs):
    events = ([Obj(type="response.output_text.delta", delta="Review your highlight footage in GMTM."), terminal()]
              if events is None else events)
    client = FakeOpenAI(FakeStream(events, stall=stall, error=error))
    monkeypatch.setattr(model, "_new_openai_client", lambda: client)
    async def consume():
        return [event async for event in model.stream_answer(
            model="gpt-5.6-luna", system="Authoritative public requirements; no selection status.",
            messages=[{"role": "user", "content": "What do I submit here?"}],
            is_disconnected=connected, **kwargs)]
    return asyncio.run(consume()), client


def test_luna_uses_one_no_store_low_reasoning_no_tools_call_and_accounts_actual_usage(monkeypatch):
    result, client = run(monkeypatch)
    assert result[-1] == {"type": "done"}
    assert len(client.calls) == 1 and client.closed and client.stream.closed
    request = client.calls[0]
    assert request == {"model": "gpt-5.6-luna", "instructions": "Authoritative public requirements; no selection status.",
                       "input": [{"role": "user", "content": "What do I submit here?"}], "stream": True,
                       "store": False, "reasoning": {"effort": "low"}, "max_output_tokens": 1200}
    record = model_usage.get_usage_snapshot()["calls"][0]
    assert record["status"] == "completed" and record["usage"]["total_tokens"] == 1100
    assert record["usage"]["reasoning_output_tokens"] == 20
    assert record["estimated_cost_usd"] == pytest.approx(0.000284)


@pytest.mark.parametrize("ending", [
    [], [Obj(type="error", message="PRIVATE_PROVIDER_ERROR")],
    [Obj(type="response.refusal.delta", delta="PRIVATE_REFUSAL")],
    [terminal(status="incomplete")], [terminal(text="")],
    [terminal(output=[Obj(type="function_call", name="query_database")])],
    [terminal(output=[Obj(type="message", role="assistant", status="completed", content=[Obj(type="refusal", refusal="PRIVATE")])])],
    [Obj(type="response.output_item.added", item=Obj(type="web_search_call"))],
])
def test_partial_or_refused_tool_or_missing_completion_never_emits_done(monkeypatch, ending):
    result, client = run(monkeypatch, [Obj(type="response.output_text.delta", delta="Partial"), *ending])
    assert result[-1] == {"type": "error", "error": model.ERROR_TEXT}
    assert all(event["type"] != "done" for event in result)
    assert "PRIVATE" not in json.dumps(result)
    assert len(client.calls) == 1 and client.closed and client.stream.closed
    assert model_usage.get_usage_snapshot()["in_flight_calls"] == 0


def test_incomplete_terminal_captures_known_usage_without_success(monkeypatch):
    end = terminal(status="incomplete")
    end.type = "response.incomplete"
    result, _ = run(monkeypatch, [Obj(type="response.output_text.delta", delta="Partial"), end])
    assert result[-1]["type"] == "error"
    record = model_usage.get_usage_snapshot()["calls"][0]
    assert record["status"] == "incomplete" and record["usage"]["output_tokens"] == 100


def test_provider_failure_after_partial_output_keeps_usage_unknown(monkeypatch):
    result, _ = run(monkeypatch, [Obj(type="response.output_text.delta", delta="Partial")], error=True)
    assert result[-1]["type"] == "error"
    record = model_usage.get_usage_snapshot()["calls"][0]
    assert record["status"] == "error" and record["usage"] is None and record["estimated_cost_usd"] is None


def test_timeout_interrupts_provider_and_settles_unknown_usage(monkeypatch):
    result, client = run(monkeypatch, [Obj(type="response.output_text.delta", delta="Partial")], stall=True, timeout_seconds=0.01)
    assert result[-1]["type"] == "error" and client.closed and client.stream.closed and client.stream.cancelled
    record = model_usage.get_usage_snapshot()["calls"][0]
    assert record["status"] == "timeout" and record["usage"] is None


def test_cancelled_consumer_closes_resources_and_does_not_refund_call(monkeypatch):
    stream = FakeStream([Obj(type="response.output_text.delta", delta="Partial")], stall=True)
    client = FakeOpenAI(stream)
    monkeypatch.setattr(model, "_new_openai_client", lambda: client)
    async def consume():
        async for _ in model.stream_answer(model="gpt-5.6-luna", system="Source", messages=[{"role": "user", "content": "Help"}],
                                           is_disconnected=connected):
            pass
    async def cancel():
        task = asyncio.create_task(consume())
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(cancel())
    snap = model_usage.get_usage_snapshot()
    assert client.closed and stream.closed and snap["attempted_calls"] == 1 and snap["in_flight_calls"] == 0
    assert snap["calls"][0]["status"] == "cancelled" and snap["calls"][0]["usage"] is None


def test_disconnect_after_text_stops_and_settles(monkeypatch):
    client = FakeOpenAI(FakeStream([Obj(type="response.output_text.delta", delta="Partial"), terminal()]))
    monkeypatch.setattr(model, "_new_openai_client", lambda: client)
    checks = iter([False, False, True])
    async def disconnected():
        return next(checks)
    async def consume():
        return [event async for event in model.stream_answer(model="gpt-5.6-luna", system="Source",
             messages=[{"role": "user", "content": "Help"}], is_disconnected=disconnected)]
    assert asyncio.run(consume()) == [{"type": "text", "text": "Partial"}]
    assert client.closed and client.stream.closed
    assert model_usage.get_usage_snapshot()["calls"][0]["status"] == "disconnected"


def test_closing_actual_response_after_first_chunk_closes_provider_before_releasing_lease(monkeypatch):
    from backend.tests.test_combine_help import snapshot, CALLER, EVENT
    monkeypatch.setenv("COMBINE_HELP_MODEL", "gpt-5.6-luna")
    monkeypatch.setattr(help_api, "load_current_combine", lambda *_: snapshot())
    client = FakeOpenAI(FakeStream([Obj(type="response.output_text.delta", delta="Partial")], stall=True))
    monkeypatch.setattr(model, "_new_openai_client", lambda: client)
    help_api._rate_buckets.clear()
    async def consume_one():
        response = await help_api.combine_help(help_api.CombineHelpRequest(event_id=EVENT, message="Help"),
                                               Obj(is_disconnected=connected), CALLER)
        first = await anext(response.body_iterator)
        assert "Partial" in first and model_usage.get_usage_snapshot()["in_flight_calls"] == 1
        await response.body_iterator.aclose()
        assert client.closed and client.stream.closed
        assert model_usage.get_usage_snapshot()["in_flight_calls"] == 0
        assert help_api._rate_buckets[CALLER]["lease"] is None
    asyncio.run(consume_one())
    assert model_usage.get_usage_snapshot()["calls"][0]["status"] == "cancelled"


def test_output_cap_and_process_call_cap_apply_without_fallback(monkeypatch):
    monkeypatch.setenv("COMBINE_HELP_TEST_MODE", "1")
    monkeypatch.setenv("COMBINE_HELP_MAX_MODEL_CALLS", "1")
    monkeypatch.setenv("COMBINE_HELP_MAX_CONCURRENT_CALLS", "1")
    result, client = run(monkeypatch, max_stream_chars=4)
    assert result == [{"type": "error", "error": model.ERROR_TEXT}]
    assert model_usage.get_usage_snapshot()["calls"][0]["status"] == "output_limit"
    result, second_client = run(monkeypatch)
    assert result == [{"type": "error", "error": model.ERROR_TEXT}]
    assert len(client.calls) == 1 and second_client.calls == []
    assert model_usage.get_usage_snapshot()["attempted_calls"] == 1


@pytest.mark.parametrize("changes", [
    {"COMBINE_HELP_MODEL": "unsupported"},
    {"COMBINE_HELP_MODEL": "gpt-5.6-luna", "OPENAI_API_KEY": ""},
    {"COMBINE_HELP_TEST_MODE": "1"},
])
def test_model_config_rejected_before_source_or_sdk(monkeypatch, changes):
    for key, value in changes.items():
        monkeypatch.setenv(key, value)
    def no_source(*_):
        raise AssertionError("Source must not be loaded")
    monkeypatch.setattr(help_api, "load_current_combine", no_source)
    async def request():
        return await help_api.combine_help(help_api.CombineHelpRequest(event_id=1318, message="Help"), Obj(), "caller")
    with pytest.raises(HTTPException) as error:
        asyncio.run(request())
    assert error.value.status_code == 503


def test_provider_factories_pin_endpoints_no_redirect_proxy_or_retry(monkeypatch):
    seen = {}
    for name, module, factory, expected in (
        ("openai", model.openai, model._new_openai_client, "https://api.openai.com/v1"),
        ("anthropic", help_api.anthropic, help_api._new_client, "https://api.anthropic.com"),
    ):
        monkeypatch.setattr(module, "DefaultAsyncHttpxClient", lambda **kwargs: seen.update(http=kwargs) or Obj())
        monkeypatch.setattr(module, "AsyncOpenAI" if name == "openai" else "AsyncAnthropic", lambda **kwargs: seen.update(sdk=kwargs) or Obj())
        factory()
        assert seen["http"] == {"timeout": 15.0, "follow_redirects": False, "trust_env": False}
        assert seen["sdk"]["base_url"] == expected
        assert seen["sdk"]["max_retries"] == 0 and seen["sdk"]["timeout"] == 15.0
