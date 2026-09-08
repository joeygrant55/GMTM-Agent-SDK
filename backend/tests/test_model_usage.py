"""Offline accounting tests: no provider, source or identity data is needed."""

from concurrent.futures import ThreadPoolExecutor
import json

import pytest

import model_usage as usage


@pytest.mark.parametrize("values", [
    {"COMBINE_HELP_TEST_MODE": "true"},
    {"COMBINE_HELP_TEST_MODE": "1"},
    {"COMBINE_HELP_TEST_MODE": "1", "COMBINE_HELP_MAX_MODEL_CALLS": "24"},
    {"COMBINE_HELP_MAX_MODEL_CALLS": "0"},
    {"COMBINE_HELP_MAX_MODEL_CALLS": "-1"},
    {"COMBINE_HELP_MAX_MODEL_CALLS": "unlimited"},
    {"COMBINE_HELP_MAX_MODEL_CALLS": "²"},
    {"COMBINE_HELP_MAX_MODEL_CALLS": "9" * 5000},
    {"COMBINE_HELP_MAX_CONCURRENT_CALLS": "17"},
])
def test_invalid_limits_fail_closed(values):
    with pytest.raises(usage.UsageConfigurationError):
        usage._configuration(values)


def test_test_limits_are_explicit_and_frozen_despite_model_switch(monkeypatch):
    monkeypatch.setenv("COMBINE_HELP_TEST_MODE", "1")
    monkeypatch.setenv("COMBINE_HELP_MAX_MODEL_CALLS", "2")
    monkeypatch.setenv("COMBINE_HELP_MAX_CONCURRENT_CALLS", "1")
    ledger = usage.get_usage_ledger()
    ledger.reserve("gpt-5.6-luna").finish("completed")
    monkeypatch.setenv("COMBINE_HELP_MAX_MODEL_CALLS", "999")
    monkeypatch.setenv("COMBINE_HELP_MODEL", "claude-sonnet-4-6")
    assert usage.get_usage_ledger() is ledger
    ledger.reserve("claude-sonnet-4-6").finish("error")
    with pytest.raises(usage.ModelCallLimitError):
        ledger.reserve("gpt-5.6-luna")
    assert ledger.snapshot()["attempted_calls"] == 2
    assert ledger.snapshot()["max_calls"] == 2


def test_concurrent_reservations_are_atomic_and_settle_only_once():
    ledger = usage.UsageLedger(test_mode=True, max_calls=3, max_concurrent=2)
    def reserve(_):
        try:
            return ledger.reserve("gpt-5.6-luna")
        except usage.ModelCallLimitError:
            return None
    with ThreadPoolExecutor(max_workers=8) as workers:
        attempts = [attempt for attempt in workers.map(reserve, range(8)) if attempt]
    assert len(attempts) == 2
    assert ledger.snapshot()["in_flight_calls"] == 2
    for attempt in attempts:
        attempt.finish("cancelled")
        attempt.finish("completed", {"input_tokens": 0, "output_tokens": 0})
    ledger.reserve("gpt-5.6-luna").finish("error")
    with pytest.raises(usage.ModelCallLimitError):
        ledger.reserve("gpt-5.6-luna")
    snap = ledger.snapshot()
    assert snap["attempted_calls"] == 3 and snap["in_flight_calls"] == 0
    assert [item["status"] for item in snap["calls"]] == ["cancelled", "cancelled", "error"]
    assert all(item["usage"] is None and item["estimated_cost_usd"] is None for item in snap["calls"])


def test_openai_cache_and_reasoning_are_subtotals_not_additional_tokens():
    raw = {"input_tokens": 1000, "output_tokens": 200,
           "input_tokens_details": {"cached_tokens": 100},
           "output_tokens_details": {"reasoning_tokens": 150}, "private_prompt": "PRIVATE"}
    normalized = usage.normalize_usage("openai", raw)
    assert normalized == {"input_tokens": 1000, "uncached_input_tokens": 900, "output_tokens": 200, "total_tokens": 1200,
                          "cached_input_tokens": 100, "cache_creation_input_tokens": 0,
                          "reasoning_output_tokens": 150}
    assert usage.estimate_cost("gpt-5.6-luna", normalized) == pytest.approx(0.000422)


def test_anthropic_cache_counts_separate_from_uncached_input():
    normalized = usage.normalize_usage("anthropic", {"input_tokens": 100, "output_tokens": 20,
                                                     "cache_read_input_tokens": 50, "cache_creation_input_tokens": 0})
    assert normalized["input_tokens"] == 150 and normalized["total_tokens"] == 170
    assert usage.estimate_cost("claude-sonnet-4-6", normalized) == pytest.approx(0.000615)
    normalized = usage.normalize_usage("anthropic", {"input_tokens": 100, "output_tokens": 20,
                                                     "cache_creation_input_tokens": 50})
    assert usage.estimate_cost("claude-sonnet-4-6", normalized) is None  # TTL unavailable.


def test_optional_anthropic_details_preserve_known_counts_without_inventing_cache_totals():
    normalized = usage.normalize_usage("anthropic", {"input_tokens": 100, "output_tokens": 20,
        "cache_read_input_tokens": None, "cache_creation_input_tokens": None,
        "output_tokens_details": {"thinking_tokens": 5}})
    assert normalized["uncached_input_tokens"] == 100 and normalized["output_tokens"] == 20
    assert normalized["reasoning_output_tokens"] == 5
    assert normalized["input_tokens"] is None and normalized["total_tokens"] is None
    assert normalized["cached_input_tokens"] is None and normalized["cache_creation_input_tokens"] is None
    assert usage.estimate_cost("claude-sonnet-4-6", normalized) is None


@pytest.mark.parametrize("raw", [None, {}, {"input_tokens": True, "output_tokens": 10},
    {"input_tokens": -1, "output_tokens": 10}, {"input_tokens": 1},
    {"input_tokens": 1, "output_tokens": 10, "input_tokens_details": {"cached_tokens": 2}},
    {"input_tokens": 1, "output_tokens": 10, "output_tokens_details": {"reasoning_tokens": 11}}])
def test_missing_or_inconsistent_provider_usage_is_unknown(raw):
    assert usage.normalize_usage("openai", raw) is None


def test_ledger_is_bounded_numeric_only_and_snapshot_is_detached():
    ledger = usage.UsageLedger()
    for _ in range(usage.MAX_RECORDS + 2):
        ledger.reserve("gpt-5.6-luna").finish("error", {"input_tokens": 10, "output_tokens": 1,
                                                       "response_id": "PRIVATE_ID", "text": "PRIVATE"})
    snap = ledger.snapshot()
    assert snap["attempted_calls"] == usage.MAX_RECORDS + 2
    assert len(snap["calls"]) == usage.MAX_RECORDS
    assert "PRIVATE" not in json.dumps(snap)
    snap["calls"][0]["usage"]["input_tokens"] = 999
    assert ledger.snapshot()["calls"][0]["usage"]["input_tokens"] == 10
