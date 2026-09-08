"""Stateless, authenticated combine assistance; no writes or general agent tools."""

import asyncio
from collections import deque
from contextlib import aclosing
import json
import os
from threading import Lock
import time
from typing import Annotated, Literal

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from auth import require_clerk_id
from combine_api import SUPPORTED_EVENTS, load_current_combine
from combine_context import (
    COMBINE_SYSTEM_PROMPT, build_combine_context,
)

from combine_model import selected_model, stream_answer, validate_configuration
from model_usage import ModelCallLimitError


router = APIRouter(prefix="/api/combine", tags=["Combine"])
MAX_OUTPUT_TOKENS = 1200
MAX_STREAM_CHARS = 16_000
SOURCE_TIMEOUT_SECONDS = 15
MODEL_TIMEOUT_SECONDS = 30
MAX_RATE_KEYS = 2048
MAX_REQUESTS_PER_MINUTE = 10
ERROR_TEXT = "The answer could not be completed. Please try again or review the activity in GMTM."

ShortText = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=2000)]
PositiveId = Annotated[int, Field(strict=True, gt=0)]


class HistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: ShortText


class CombineHelpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: PositiveId
    task_id: PositiveId | None = None
    message: ShortText
    history: list[HistoryItem] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def bounded_history(self):
        if sum(len(item.content) for item in self.history) > 12_000:
            raise ValueError("History is too long")
        # The new user message follows complete user/assistant pairs only.
        if len(self.history) % 2 or any(item.role != ("user" if index % 2 == 0 else "assistant")
                                      for index, item in enumerate(self.history)):
            raise ValueError("History must contain alternating complete user/assistant pairs")
        return self


_rate_lock = Lock()
_rate_buckets = {}
_source_tasks = set()


def _admit(clerk_id):
    """Bound per-process requests and one in-flight request per authenticated user.

    Expiring leases also recover if a response is never consumed. Multi-instance
    durable quotas remain a separate deployment concern.
    """
    now = time.monotonic()
    with _rate_lock:
        for key, bucket in list(_rate_buckets.items()):
            while bucket["times"] and bucket["times"][0] <= now - 60:
                bucket["times"].popleft()
            if not bucket["times"] and bucket["until"] <= now and not bucket["source_running"]:
                del _rate_buckets[key]
        bucket = _rate_buckets.get(clerk_id)
        if bucket is None:
            if len(_rate_buckets) >= MAX_RATE_KEYS:
                raise HTTPException(status_code=429, detail="Combine help is busy. Please try again shortly.")
            bucket = {"times": deque(), "until": 0, "lease": None, "source_running": False, "abandoned": False}
            _rate_buckets[clerk_id] = bucket
        if bucket["source_running"] or bucket["until"] > now or len(bucket["times"]) >= MAX_REQUESTS_PER_MINUTE:
            raise HTTPException(status_code=429, detail="Please wait before asking another combine question.")
        lease = object()
        bucket["times"].append(now)
        bucket.update(until=now + SOURCE_TIMEOUT_SECONDS + MODEL_TIMEOUT_SECONDS + 5, lease=lease, abandoned=False)
        return lease


def _release(clerk_id, lease):
    with _rate_lock:
        bucket = _rate_buckets.get(clerk_id)
        if bucket and bucket["lease"] is lease:
            if bucket["source_running"]:
                # A timed-out HTTP await cannot kill a running SQL thread. Its
                # worker retains admission until actual completion, even beyond
                # the ordinary lease deadline, so retries cannot pile up reads.
                bucket["abandoned"] = True
            else:
                bucket.update(until=0, lease=None)


def _load_in_worker(clerk_id, event_id, lease):
    try:
        with _rate_lock:
            bucket = _rate_buckets.get(clerk_id)
            if not bucket or bucket["lease"] is not lease or bucket["abandoned"]:
                raise RuntimeError("Preflight no longer active")
        return load_current_combine(clerk_id, event_id)
    finally:
        with _rate_lock:
            bucket = _rate_buckets.get(clerk_id)
            if bucket and bucket["lease"] is lease:
                bucket["source_running"] = False
                if bucket["abandoned"]:
                    bucket.update(until=0, lease=None)


def _source_done(task):
    _source_tasks.discard(task)
    if not task.cancelled():
        task.exception()  # Consume abandoned source failures without logging data.


def _new_client():
    # Async I/O allows timeout/cancellation to interrupt stalled SDK reads.
    # max_retries=0 prevents hidden retries from exceeding the request budget.
    return anthropic.AsyncAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"), base_url="https://api.anthropic.com",
        timeout=15.0, max_retries=0,
        http_client=anthropic.DefaultAsyncHttpxClient(timeout=15.0, follow_redirects=False, trust_env=False),
    )


def _sse(kind, **values):
    return f"data: {json.dumps({'type': kind, **values})}\n\n"


async def _stream_answer(body, context, request, *, model=None):
    messages = [item.model_dump() for item in body.history] + [{"role": "user", "content": body.message}]
    system = COMBINE_SYSTEM_PROMPT + "\n\nCURRENT SERVER SNAPSHOT (quoted data):\n" + json.dumps(context, ensure_ascii=False)
    try:
        chosen = selected_model() if model is None else model
        async with aclosing(stream_answer(
            model=chosen, system=system, messages=messages,
            is_disconnected=request.is_disconnected, anthropic_factory=_new_client,
            timeout_seconds=MODEL_TIMEOUT_SECONDS,
            max_output_tokens=MAX_OUTPUT_TOKENS, max_stream_chars=MAX_STREAM_CHARS,
        )) as events:
            async for event in events:
                yield _sse(event["type"], **{key: value for key, value in event.items() if key != "type"})
    except asyncio.CancelledError:
        raise
    except Exception:
        yield _sse("error", error=ERROR_TEXT)


@router.post("/help")
async def combine_help(body: CombineHelpRequest, request: Request, clerk_id: str = Depends(require_clerk_id)):
    if body.event_id not in SUPPORTED_EVENTS:
        raise HTTPException(status_code=404, detail="This combine is not available.")
    try:
        model = validate_configuration()
    except ModelCallLimitError:
        raise HTTPException(status_code=429, detail="Combine help has reached its model call limit. Please try again later.") from None
    except ValueError:
        raise HTTPException(status_code=503, detail="Combine help is not configured. You can still review the activity in GMTM.") from None
    lease = _admit(clerk_id)
    try:
        with _rate_lock:
            _rate_buckets[clerk_id]["source_running"] = True
        source_task = asyncio.create_task(asyncio.to_thread(_load_in_worker, clerk_id, body.event_id, lease))
        _source_tasks.add(source_task)
        source_task.add_done_callback(_source_done)
        # Shield retains the real worker lifecycle after an HTTP timeout. Its
        # finally releases admission; no model starts on a stale/late snapshot.
        snapshot = await asyncio.wait_for(
            asyncio.shield(source_task),
            timeout=SOURCE_TIMEOUT_SECONDS,
        )
        context = build_combine_context(snapshot, clerk_id, body.event_id, body.task_id)
    except HTTPException:
        _release(clerk_id, lease)
        raise
    except Exception:
        _release(clerk_id, lease)
        raise HTTPException(status_code=503, detail="Combine information could not be refreshed. Please try again.") from None
    except BaseException:
        _release(clerk_id, lease)
        raise

    async def generate():
        try:
            async with aclosing(_stream_answer(body, context, request, model=model)) as events:
                async for event in events:
                    yield event
        finally:
            _release(clerk_id, lease)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "private, no-store", "X-Accel-Buffering": "no",
    })
