"""Bounded combine-only provider adapters; no implicit routing or fallback."""

import asyncio
from copy import deepcopy
import os

import openai

from model_usage import MODELS, get_usage_ledger


DEFAULT_MODEL = "claude-sonnet-4-6"
ERROR_TEXT = "The answer could not be completed. Please try again or review the activity in GMTM."


def selected_model():
    model = os.getenv("COMBINE_HELP_MODEL", DEFAULT_MODEL)
    if model not in MODELS:
        raise ValueError("Combine model is not allowed")
    return model


def validate_configuration():
    model = selected_model()
    key_name = "OPENAI_API_KEY" if model == "gpt-5.6-luna" else "ANTHROPIC_API_KEY"
    if not os.getenv(key_name, "").strip():
        raise ValueError("Combine provider is not configured")
    get_usage_ledger().check_available()
    return model


def _new_openai_client():
    return openai.AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"), base_url="https://api.openai.com/v1",
        timeout=15.0, max_retries=0,
        http_client=openai.DefaultAsyncHttpxClient(timeout=15.0, follow_redirects=False, trust_env=False),
    )


def _get(value, key, default=None):
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def _completed_luna_response(response):
    if _get(response, "status") != "completed":
        return False
    output = _get(response, "output")
    if not isinstance(output, list) or not output:
        return False
    texts = []
    for item in output:
        kind = _get(item, "type")
        if kind == "reasoning":
            continue
        if kind != "message" or _get(item, "role") != "assistant" or _get(item, "status") != "completed":
            return False
        content = _get(item, "content")
        if not isinstance(content, list):
            return False
        for part in content:
            if _get(part, "type") != "output_text" or not isinstance(_get(part, "text"), str):
                return False
            texts.append(_get(part, "text"))
    return bool("".join(texts).strip())


def _completed_sonnet_response(response):
    if (_get(response, "type") != "message" or _get(response, "role") != "assistant"
            or _get(response, "stop_reason") != "end_turn" or _get(response, "stop_details") is not None):
        return False
    content = _get(response, "content")
    if not isinstance(content, list) or not content:
        return False
    texts = []
    for block in content:
        if _get(block, "type") != "text" or not isinstance(_get(block, "text"), str):
            return False
        texts.append(_get(block, "text"))
    return bool("".join(texts).strip())


def _validate_request(model, system, messages, max_output_tokens, max_stream_chars, timeout_seconds):
    if model not in MODELS or not isinstance(system, str) or not 1 <= len(system) <= 40_000:
        raise ValueError("Invalid combine model request")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 13:
        raise ValueError("Invalid combine model history")
    for item in messages:
        if not isinstance(item, dict) or set(item) != {"role", "content"} or item["role"] not in ("user", "assistant"):
            raise ValueError("Invalid combine model history")
        if not isinstance(item["content"], str) or not 1 <= len(item["content"]) <= 2000:
            raise ValueError("Invalid combine model history")
    if sum(len(item["content"]) for item in messages) > 14_000:
        raise ValueError("Invalid combine model history")
    for value, maximum in ((max_output_tokens, 1200), (max_stream_chars, 16_000)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError("Invalid combine model bound")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not 0 < timeout_seconds <= 30:
        raise ValueError("Invalid combine model timeout")


async def stream_answer(*, model, system, messages, is_disconnected,
                        anthropic_factory=None, timeout_seconds=30,
                        max_output_tokens=1200, max_stream_chars=16_000,
                        usage_ledger=None):
    """Yield text/done/error dictionaries from the preloaded system snapshot.

    Each question makes exactly one provider request with no tools or fallback.
    Luna uses store=False and low reasoning. Every actual call is atomically
    reserved and settled even on cancellation.
    """
    client = None
    try:
        _validate_request(model, system, messages, max_output_tokens, max_stream_chars, timeout_seconds)
        messages = deepcopy(messages)
        ledger = get_usage_ledger() if usage_ledger is None else usage_ledger
        emitted_chars = 0
        async with asyncio.timeout(timeout_seconds) as deadline:
            if await is_disconnected():
                return
            attempt = ledger.reserve(model)
            status, usage = "cancelled", None
            try:
                if client is None:
                    client = _new_openai_client() if model == "gpt-5.6-luna" else anthropic_factory()
                turn_text = []
                if model == "gpt-5.6-luna":
                    stream = await client.responses.create(
                        model=model, instructions=system, input=messages, stream=True,
                        store=False, reasoning={"effort": "low"}, max_output_tokens=max_output_tokens,
                    )
                    terminal = None
                    async with stream:
                        async for event in stream:
                            if await is_disconnected():
                                status = "disconnected"
                                return
                            kind = _get(event, "type")
                            if kind == "response.output_text.delta":
                                delta = _get(event, "delta")
                                if not isinstance(delta, str):
                                    raise ValueError("Invalid model delta")
                                emitted_chars += len(delta)
                                if emitted_chars > max_stream_chars:
                                    status = "output_limit"
                                    raise ValueError("Output bound reached")
                                turn_text.append(delta)
                                if delta:
                                    yield {"type": "text", "text": delta}
                            elif kind in ("response.completed", "response.incomplete", "response.failed"):
                                terminal = _get(event, "response")
                                usage = _get(terminal, "usage")
                                if kind != "response.completed":
                                    status = "incomplete" if kind == "response.incomplete" else "error"
                                    raise ValueError("Incomplete model answer")
                                break
                            elif kind in ("response.refusal.delta", "response.refusal.done"):
                                status = "refused"
                                raise ValueError("Model refused")
                            elif kind == "error":
                                raise ValueError("Provider stream failed")
                            elif kind in ("response.output_item.added", "response.output_item.done"):
                                if _get(_get(event, "item"), "type") not in ("message", "reasoning"):
                                    raise ValueError("Unexpected model tool")
                    if not _completed_luna_response(terminal) or not "".join(turn_text).strip():
                        status = "incomplete"
                        raise ValueError("Invalid completed answer")
                    status = "completed"
                else:
                    message_stopped = False
                    async with client.messages.stream(
                        model=model, max_tokens=max_output_tokens, system=system, messages=messages,
                    ) as stream:
                        async for event in stream:
                            if await is_disconnected():
                                status = "disconnected"
                                return
                            kind = _get(event, "type")
                            if kind == "content_block_start":
                                if _get(_get(event, "content_block"), "type") != "text":
                                    status = "incomplete"
                                    raise ValueError("Unexpected model content")
                            elif kind == "content_block_delta":
                                delta = _get(event, "delta")
                                text = _get(delta, "text")
                                if _get(delta, "type") != "text_delta" or not isinstance(text, str):
                                    status = "incomplete"
                                    raise ValueError("Unexpected model delta")
                                emitted_chars += len(text)
                                if emitted_chars > max_stream_chars:
                                    status = "output_limit"
                                    raise ValueError("Output bound reached")
                                turn_text.append(text)
                                if text:
                                    yield {"type": "text", "text": text}
                            elif kind == "message_stop":
                                message_stopped = True
                                # The SDK attaches the final message here. Keep
                                # known usage even if later stream cleanup fails.
                                usage = _get(_get(event, "message"), "usage")
                        final = await stream.get_final_message()
                    usage = _get(final, "usage") or usage
                    if not message_stopped or not _completed_sonnet_response(final) or not "".join(turn_text).strip():
                        status = ("refused" if _get(final, "stop_reason") == "refusal"
                                  or _get(_get(final, "stop_details"), "type") == "refusal" else "incomplete")
                        raise ValueError("Incomplete model answer")
                    status = "completed"
            except asyncio.CancelledError:
                status = "timeout" if deadline.expired() else "cancelled"
                raise
            except Exception:
                if status == "cancelled":
                    status = "error"
                raise
            finally:
                attempt.finish(status, usage)
            yield {"type": "done"}
    except asyncio.CancelledError:
        raise
    except Exception:
        yield {"type": "error", "error": ERROR_TEXT}
    finally:
        if client is not None:
            try:
                await asyncio.wait_for(client.close(), timeout=1)
            except (Exception, asyncio.CancelledError):
                pass
