"""Privacy-safe, bounded process accounting for combine model calls.

This is an operational estimate, not billing reconciliation or a durable quota.
Counters restart with the process and are not shared by multiple workers. Local
evaluations must set TEST_MODE=1 and explicit finite call/concurrency limits.
No prompt, account, request, provider response ID, or generated text is retained.
"""

from collections import deque
from copy import deepcopy
from decimal import Decimal
import os
from threading import Lock
import time


MODELS = {"gpt-5.6-luna": "openai", "claude-sonnet-4-6": "anthropic"}
MAX_RECORDS = 256
PRICING_AS_OF = "2026-09-07"
# Standard text prices per million tokens; cache counts are subsets of input.
# Sources: official Luna model page and Anthropic pricing, recorded in docs/research.
_PRICES = {
    "gpt-5.6-luna": (Decimal("0.20"), Decimal("0.02"), Decimal("1.20")),
    "claude-sonnet-4-6": (Decimal("3"), Decimal("0.30"), Decimal("15")),
}
_STATUSES = {"completed", "tool_use", "incomplete", "refused", "error", "cancelled",
             "disconnected", "output_limit", "timeout"}


class UsageConfigurationError(ValueError):
    pass


class ModelCallLimitError(RuntimeError):
    pass


def _finite_limit(env, name, maximum, default=None):
    raw = env.get(name)
    if raw is None:
        if default is not None:
            return default
        raise UsageConfigurationError("Explicit model limits are required")
    if not isinstance(raw, str) or not raw.isascii() or not raw.isdecimal() or len(raw) > 6:
        raise UsageConfigurationError("Invalid model limit")
    value = int(raw)
    if not 1 <= value <= maximum:
        raise UsageConfigurationError("Invalid model limit")
    return value


def _configuration(env):
    mode = env.get("COMBINE_HELP_TEST_MODE", "0")
    if mode not in ("0", "1"):
        raise UsageConfigurationError("Invalid model test mode")
    test_mode = mode == "1"
    calls = (_finite_limit(env, "COMBINE_HELP_MAX_MODEL_CALLS", 10_000)
             if test_mode or "COMBINE_HELP_MAX_MODEL_CALLS" in env else None)
    concurrency = _finite_limit(env, "COMBINE_HELP_MAX_CONCURRENT_CALLS", 16,
                                default=None if test_mode else 4)
    return test_mode, calls, concurrency


def _count(value):
    return value if type(value) is int and 0 <= value <= 1_000_000_000 else None


def _get(value, key, default=None):
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def normalize_usage(provider, usage):
    """Return only validated numeric usage; absence is never zero spend."""
    if usage is None:
        return None
    inputs, outputs = _count(_get(usage, "input_tokens")), _count(_get(usage, "output_tokens"))
    if inputs is None or outputs is None:
        return None
    if provider == "openai":
        cached = _count(_get(_get(usage, "input_tokens_details"), "cached_tokens"))
        reasoning = _count(_get(_get(usage, "output_tokens_details"), "reasoning_tokens"))
        created = 0
        if (cached is not None and cached > inputs) or (reasoning is not None and reasoning > outputs):
            return None
        uncached = inputs - cached if cached is not None else None
    elif provider == "anthropic":
        cached = _count(_get(usage, "cache_read_input_tokens"))
        created = _count(_get(usage, "cache_creation_input_tokens"))
        reasoning = _count(_get(_get(usage, "output_tokens_details"), "thinking_tokens"))
        if reasoning is not None and reasoning > outputs:
            return None
        # Anthropic's input_tokens excludes the separately reported cache tokens.
        # Optional None fields are unknown: retain known uncached/output usage
        # without inventing a total or a zero cache bill.
        uncached = inputs
        inputs = inputs + cached + created if cached is not None and created is not None else None
    else:
        return None
    return {"input_tokens": inputs, "uncached_input_tokens": uncached, "output_tokens": outputs,
            "total_tokens": inputs + outputs if inputs is not None else None,
            "cached_input_tokens": cached, "cache_creation_input_tokens": created,
            "reasoning_output_tokens": reasoning}


def estimate_cost(model, usage):
    if (usage is None or usage["input_tokens"] is None or usage["cached_input_tokens"] is None
            or usage["cache_creation_input_tokens"] != 0):
        # No cache writes are requested here. An unexpected write needs its TTL
        # to price accurately; never silently treat it as a free/base-rate write.
        return None
    input_rate, cache_rate, output_rate = _PRICES[model]
    cached = usage["cached_input_tokens"]
    amount = ((usage["input_tokens"] - cached) * input_rate + cached * cache_rate
              + usage["output_tokens"] * output_rate) / Decimal(1_000_000)
    # Reasoning is already included in output_tokens; do not charge it twice.
    return float(amount)


class UsageLedger:
    def __init__(self, *, test_mode=False, max_calls=None, max_concurrent=4):
        if type(max_concurrent) is not int or not 1 <= max_concurrent <= 16:
            raise UsageConfigurationError("Invalid model concurrency")
        if max_calls is not None and (type(max_calls) is not int or not 1 <= max_calls <= 10_000):
            raise UsageConfigurationError("Invalid model call limit")
        if test_mode and max_calls is None:
            raise UsageConfigurationError("Explicit model limits are required")
        self.test_mode, self.max_calls, self.max_concurrent = test_mode, max_calls, max_concurrent
        self._lock, self._records = Lock(), deque(maxlen=MAX_RECORDS)
        self._attempted, self._in_flight, self._rejected = 0, 0, 0

    def check_available(self):
        with self._lock:
            if (self.max_calls is not None and self._attempted >= self.max_calls) or self._in_flight >= self.max_concurrent:
                raise ModelCallLimitError("Model call limit reached")

    def reserve(self, model):
        if model not in MODELS:
            raise UsageConfigurationError("Model is not allowed")
        with self._lock:
            if (self.max_calls is not None and self._attempted >= self.max_calls) or self._in_flight >= self.max_concurrent:
                self._rejected += 1
                raise ModelCallLimitError("Model call limit reached")
            self._attempted += 1
            self._in_flight += 1
            record = {"provider": MODELS[model], "model": model, "status": "in_flight",
                      "duration_ms": None, "usage": None, "estimated_cost_usd": None}
            self._records.append(record)
            return _Attempt(self, record)

    def snapshot(self):
        with self._lock:
            return {"scope": "process_only", "test_mode": self.test_mode,
                    "max_calls": self.max_calls, "max_concurrent": self.max_concurrent,
                    "attempted_calls": self._attempted, "in_flight_calls": self._in_flight,
                    "rejected_calls": self._rejected, "retained_calls": len(self._records),
                    "pricing_as_of": PRICING_AS_OF, "calls": deepcopy(list(self._records))}


class _Attempt:
    def __init__(self, ledger, record):
        self.ledger, self.record, self.started = ledger, record, time.monotonic()
        self.finished = False

    def finish(self, status, raw_usage=None):
        with self.ledger._lock:
            if self.finished:
                return
            self.finished = True
            usage = normalize_usage(self.record["provider"], raw_usage)
            self.record.update(status=status if status in _STATUSES else "error",
                               duration_ms=round(max(0, time.monotonic() - self.started) * 1000, 2),
                               usage=usage, estimated_cost_usd=estimate_cost(self.record["model"], usage))
            self.ledger._in_flight -= 1


_ledger = None
_ledger_lock = Lock()


def get_usage_ledger():
    """Freeze limits on first use; changing environment cannot reset the budget."""
    global _ledger
    with _ledger_lock:
        if _ledger is None:
            test_mode, calls, concurrent = _configuration(os.environ)
            _ledger = UsageLedger(test_mode=test_mode, max_calls=calls, max_concurrent=concurrent)
        return _ledger


def get_usage_snapshot():
    return get_usage_ledger().snapshot()
