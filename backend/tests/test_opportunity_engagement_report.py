"""Synthetic exported interactions only; no collector, services or identity access."""
import json

import pytest

import opportunity_engagement_report as report

START = "2026-09-10T00:00:00Z"
END = "2026-09-24T00:00:00Z"
PERIOD = "adult-flag-september"


def event(number=1, **changes):
    return {"schema": 1, "at": "2026-09-10T12:00:00Z", "catalog_revision": "a" * 64,
            "opportunity_id": "synthetic-tournament-2026", "kind": "card_visible",
            "event_id": f"00000000-0000-4000-8000-{number:012x}", "cohort": "pilot",
            "account": "b" * 64, "measurement_period": PERIOD, "destination_kind": "event_page", **changes}


def line(row):
    return report.PREFIX + json.dumps(row) + "\n"


def build(rows, **changes):
    return report.build_report((line(row) for row in rows),
                               **{"start": START, "end": END, "measurement_period": PERIOD, **changes})


def test_retry_dedup_repeated_actions_overlap_rates_and_private_accounts():
    rows = [event(), event(at="2026-09-10T12:01:00Z"), event(2, kind="details_opened"),
            event(3, kind="outbound_activated"), event(4, kind="outbound_activated"),
            event(5, account="c" * 64), event(6, account="c" * 64, kind="details_opened"),
            event(7, account="d" * 64, kind="outbound_activated"),
            event(8, account="e" * 64, kind="details_opened")]
    result = build(rows)
    assert result["status"] == "ok"
    item = result["opportunities"][0]
    assert item["viewed_accounts"] == 2
    assert item["details_accounts"] == 3
    assert item["outbound_accounts"] == 2
    assert item["actions"]["outbound_activated"] == 3
    assert item["details_with_view_accounts"] == 2
    assert item["outbound_with_view_accounts"] == 1
    assert item["outbound_with_details_accounts"] == 1
    assert item["details_without_view_accounts"] == 1
    assert item["outbound_without_view_accounts"] == 1
    assert item["rates"]["view_to_details"] == {"numerator": 2, "denominator": 2, "rate": 1.0}
    assert item["rates"]["view_to_outbound"] == {"numerator": 1, "denominator": 2, "rate": 0.5}
    assert item["rates"]["details_to_outbound"] == {"numerator": 1, "denominator": 3, "rate": 1 / 3}
    assert result["coverage"]["validated_records"] == 9
    assert result["coverage"]["duplicate_records"] == 1
    assert result["coverage"]["included_records"] == 8
    assert result["totals"]["unique_accounts"] == 4
    encoded = json.dumps(result)
    assert all(account not in encoded for account in ("b" * 64, "c" * 64, "d" * 64, "e" * 64))
    assert all(row["event_id"] not in encoded for row in rows)


@pytest.mark.parametrize("change", [{"kind": "details_opened"}, {"opportunity_id": "different-event"},
                                    {"catalog_revision": "f" * 64}, {"destination_kind": "contact_page"}])
def test_conflicting_retry_invalidates_whole_report_without_partial_counts(change):
    result = build([event(), event(**change)])
    assert result == {"schema": 1, "status": "invalid", "error": "conflicting_duplicate", "line": 2}
    assert "opportunities" not in result


def test_dedupe_key_keeps_distinct_accounts_cohorts_and_periods_separate():
    rows = [event(), event(account="c" * 64), event(cohort="internal"), event(cohort="fixture"),
            event(measurement_period="next-period")]
    result = build(rows)
    assert result["coverage"]["duplicate_records"] == 0
    assert result["coverage"]["excluded_deduplicated_records"] == {"cohort": 2, "measurement_period": 1, "window": 0}
    assert result["opportunities"][0]["viewed_accounts"] == 2
    assert build(rows, cohort="internal")["totals"]["unique_accounts"] == 1


def test_retry_earliest_server_time_is_order_independent_and_end_is_exclusive():
    rows = [event(at="2026-09-09T23:59:59Z"), event(at=START), event(2, at=END), event(3, at=START)]
    first, reversed_result = build(rows), build(reversed(rows))
    assert first == reversed_result
    assert first["coverage"]["included_records"] == 1
    assert first["coverage"]["excluded_deduplicated_records"]["window"] == 2
    assert first["opportunities"][0]["first_observed_at"] == START


def test_multiple_catalogs_do_not_reset_account_counts_and_destinations_stay_separate():
    rows = [event(), event(2, catalog_revision="f" * 64),
            event(3, opportunity_id="second-event", kind="outbound_activated"),
            event(4, destination_kind="contact_page", kind="outbound_activated")]
    result = build(rows)
    assert result["totals"]["unique_accounts"] == 1
    assert result["totals"]["opportunity_groups"] == 3
    assert result["catalog_revisions"] == ["a" * 64, "f" * 64]
    main = next(item for item in result["opportunities"] if item["opportunity_id"] == "synthetic-tournament-2026" and item["destination_kind"] == "event_page")
    assert main["viewed_accounts"] == 1
    assert main["actions"]["card_visible"] == 2
    assert main["rates"]["view_to_outbound"]["numerator"] == 0


def test_direct_outbound_and_empty_exports_do_not_fabricate_exposure():
    result = build([event(kind="outbound_activated")])
    item = result["opportunities"][0]
    assert item["outbound_without_view_accounts"] == 1
    assert item["rates"]["view_to_outbound"] == {"numerator": 0, "denominator": 0, "rate": None}
    assert item["rates"]["details_to_outbound"]["rate"] is None
    assert result["coverage"]["capture_completeness"] == "not_established"
    empty = build([])
    assert empty["status"] == "no_data"
    assert empty["coverage"]["first_observed_at"] is None
    assert empty["totals"]["unique_accounts"] == 0 and empty["opportunities"] == []
    assert build([event(cohort="internal")])["status"] == "no_data"


@pytest.mark.parametrize("change", [
    {"schema": True}, {"schema": 2}, {"schema": 1.0}, {"at": "2026-02-30T00:00:00Z"},
    {"at": "2026-09-10T12:00:00+00:00"}, {"at": "2026-09-10T12:00:00"},
    {"at": "2026-09-10T12:00:00-04:00"}, {"at": "2026-09-10T12:00:00.1234567Z"},
    {"catalog_revision": "A" * 64}, {"account": "b" * 63}, {"account": []},
    {"event_id": "00000000-0000-1000-8000-000000000001"},
    {"event_id": "00000000-0000-4000-7000-000000000001"},
    {"event_id": "00000000-0000-4000-8000-00000000000A"},
    {"opportunity_id": "UPPER"}, {"opportunity_id": "a" * 65}, {"opportunity_id": "a--b"},
    {"kind": "registration"}, {"kind": {}}, {"cohort": "external"},
    {"measurement_period": "has space"}, {"destination_kind": "email"},
    {"extra": "private input must not be echoed"},
])
def test_strict_record_schema_and_redacted_errors(change):
    result = build([event(), event(2, **change)])
    assert result["status"] == "invalid"
    assert set(result) == {"schema", "status", "error", "line"}
    assert "private input" not in json.dumps(result)


@pytest.mark.parametrize("payload", ["{bad secret", "[]", "null", '{"schema":1,"schema":1}',
                                    '{"schema":NaN}', '{"schema":Infinity}'])
def test_malformed_prefixed_json_is_invalid_even_for_unselected_cohorts(payload):
    result = report.build_report([line(event(cohort="internal")), report.PREFIX + payload],
                                 start=START, end=END, measurement_period=PERIOD)
    assert result["status"] == "invalid" and result["line"] == 2
    assert payload not in json.dumps(result)


def test_missing_field_rejected_and_conflicts_in_excluded_data_are_not_hidden():
    missing = event()
    del missing["destination_kind"]
    assert build([missing])["status"] == "invalid"
    assert build([event(cohort="fixture"), event(cohort="fixture", kind="details_opened")])["error"] == "conflicting_duplicate"


@pytest.mark.parametrize("changes", [{"start": END}, {"end": START}, {"end": "2026-09-09T00:00:00Z"},
                                     {"start": "2026-09-10"}, {"start": "2026-09-10T00:00:00-04:00"},
                                     {"measurement_period": ""}, {"cohort": "all"}, {"max_lines": True},
                                     {"max_lines": report.MAX_LINES + 1}, {"max_bytes": 0}])
def test_invalid_scope_or_bounds_do_not_consume_input(changes):
    def forbidden():
        raise AssertionError("Invalid report configuration must not read input")
        yield
    result = report.build_report(forbidden(), **{"start": START, "end": END, "measurement_period": PERIOD, **changes})
    assert result["status"] == "invalid" and result["line"] is None


def test_timezone_normalization_unrelated_lines_and_all_input_bounds():
    args = {"start": START, "end": END, "measurement_period": PERIOD}
    lines = ["unrelated private text\n", line(event()).encode()]
    result = report.build_report(lines, **args)
    assert result["coverage"]["unrelated_lines"] == 1
    assert "unrelated private text" not in json.dumps(result)
    assert build([event()], start="2026-09-10T00:00:00+00:00")["window"]["start"] == START
    assert report.build_report(lines, **args, max_lines=1)["error"] == "line_limit"
    assert report.build_report(lines, **args, max_bytes=1)["error"] == "byte_limit"
    assert report.build_report(["x" * (report.MAX_LINE_BYTES + 1)], **args)["error"] == "line_bytes_limit"
    assert report.build_report([b"\xff"], **args)["error"] == "invalid_input_encoding"
    assert report.build_report([42], **args)["error"] == "invalid_input_type"


def test_cli_reads_exports_and_returns_only_json(tmp_path, capsys):
    first, second = tmp_path / "first.log", tmp_path / "second.log"
    first.write_text(line(event()), encoding="utf-8")
    second.write_text(line(event(at="2026-09-10T12:01:00Z")), encoding="utf-8")
    args = [str(first), str(second), "--start", START, "--end", END, "--measurement-period", PERIOD]
    assert report.main(args) == 0
    captured = capsys.readouterr()
    value = json.loads(captured.out)
    assert captured.err == "" and value["coverage"]["duplicate_records"] == 1
    assert str(first) not in captured.out
    assert report.main(["--unknown-secret-argument"]) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out)["error"] == "invalid_arguments" and captured.err == ""
    assert "unknown-secret" not in captured.out
    first.unlink()
    assert report.main(args) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out)["error"] == "input_unavailable"
    assert str(first) not in captured.out
