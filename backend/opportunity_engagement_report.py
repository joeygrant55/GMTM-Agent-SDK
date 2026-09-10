"""Offline aggregate report from a bounded engagement-log export; imports are inert.

No database, provider or network access. Input is streamed, with only bounded,
validated occurrence metadata retained for order-independent retry deduplication.
Account pseudonyms never appear in results, including invalid-input errors.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import re
import sys

PREFIX = "SPARQ_OPPORTUNITY_ENGAGEMENT "
KINDS = ("card_visible", "details_opened", "outbound_activated")
COHORTS = ("fixture", "internal", "pilot")
DESTINATIONS = ("event_page", "program_page", "contact_page")
MAX_LINES = 100_000
MAX_BYTES = 32 * 1024 * 1024
MAX_LINE_BYTES = 8192
FIELDS = {"schema", "at", "catalog_revision", "opportunity_id", "kind", "event_id",
          "cohort", "account", "measurement_period", "destination_kind"}
_HEX = re.compile(r"[a-f0-9]{64}\Z")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_UUID4 = re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)\Z")


class InvalidReport(ValueError):
    """Only fixed error codes; never interpolate input or exception text."""


def _date(value, *, record=False):
    if (not isinstance(value, str) or not _UTC.fullmatch(value)
            or record and not value.endswith("Z")):
        raise InvalidReport("invalid_utc_time")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise InvalidReport("invalid_utc_time") from None


def _stamp(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug(value):
    return isinstance(value, str) and 1 <= len(value) <= 64 and bool(_SLUG.fullmatch(value))


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidReport("duplicate_json_key")
        result[key] = value
    return result


def _constant(_value):
    raise InvalidReport("invalid_json_constant")


def _record(payload):
    try:
        row = json.loads(payload, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, RecursionError):
        raise InvalidReport("invalid_prefixed_record") from None
    if (not isinstance(row, dict) or set(row) != FIELDS
            or type(row["schema"]) is not int or row["schema"] != 1
            or not isinstance(row["catalog_revision"], str) or not _HEX.fullmatch(row["catalog_revision"])
            or not isinstance(row["account"], str) or not _HEX.fullmatch(row["account"])
            or not isinstance(row["event_id"], str) or not _UUID4.fullmatch(row["event_id"])
            or not _slug(row["opportunity_id"]) or not _slug(row["measurement_period"])
            or row["kind"] not in KINDS or row["cohort"] not in COHORTS
            or row["destination_kind"] not in DESTINATIONS):
        raise InvalidReport("invalid_prefixed_record")
    row["at"] = _date(row["at"], record=True)
    return row


def _rate(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "rate": numerator / denominator if denominator else None}


def _aggregate(key, rows):
    sets = {kind: {row["account"] for row in rows if row["kind"] == kind} for kind in KINDS}
    viewed, details, outbound = (sets[kind] for kind in KINDS)
    vd, vo, do = len(viewed & details), len(viewed & outbound), len(details & outbound)
    return {"opportunity_id": key[0], "destination_kind": key[1],
            "catalog_revisions": sorted({row["catalog_revision"] for row in rows}),
            "first_observed_at": _stamp(min(row["at"] for row in rows)),
            "last_observed_at": _stamp(max(row["at"] for row in rows)),
            "unique_accounts": len(viewed | details | outbound),
            "viewed_accounts": len(viewed), "details_accounts": len(details), "outbound_accounts": len(outbound),
            "details_with_view_accounts": vd, "outbound_with_view_accounts": vo,
            "outbound_with_details_accounts": do,
            "details_without_view_accounts": len(details - viewed),
            "outbound_without_view_accounts": len(outbound - viewed),
            "actions": {kind: sum(row["kind"] == kind for row in rows) for kind in KINDS},
            "rates": {"view_to_details": _rate(vd, len(viewed)),
                      "view_to_outbound": _rate(vo, len(viewed)),
                      "details_to_outbound": _rate(do, len(details))}}


def build_report(lines, *, start, end, measurement_period, cohort="pilot",
                 max_lines=MAX_LINES, max_bytes=MAX_BYTES):
    """Report selected [start, end) server acceptance times, never whole-population demand.

    Every prefixed record is validated, including excluded cohorts/windows. Retry
    identity is (cohort, measurement period, account, event UUID). All fields other
    than server time must agree. Earliest observed acceptance wins across retries,
    including when retries straddle a window boundary; export order cannot matter.
    """
    line_number = 0
    try:
        start_at, end_at = _date(start), _date(end)
        if start_at >= end_at:
            raise InvalidReport("invalid_window")
        if not _slug(measurement_period) or cohort not in COHORTS:
            raise InvalidReport("invalid_report_scope")
        if (type(max_lines) is not int or not 1 <= max_lines <= MAX_LINES
                or type(max_bytes) is not int or not 1 <= max_bytes <= MAX_BYTES):
            raise InvalidReport("invalid_report_bounds")
        occurrences, counts = {}, Counter()
        for line_number, line in enumerate(lines, 1):
            if line_number > max_lines:
                raise InvalidReport("line_limit")
            if not isinstance(line, (str, bytes)):
                raise InvalidReport("invalid_input_type")
            if len(line) > MAX_LINE_BYTES:
                raise InvalidReport("line_bytes_limit")
            try:
                raw = line.encode("utf-8", "strict") if isinstance(line, str) else line
                line = raw.decode("utf-8", "strict")
            except UnicodeError:
                raise InvalidReport("invalid_input_encoding") from None
            if len(raw) > MAX_LINE_BYTES:
                raise InvalidReport("line_bytes_limit")
            counts["input_bytes"] += len(raw)
            if counts["input_bytes"] > max_bytes:
                raise InvalidReport("byte_limit")
            if not line.startswith(PREFIX):
                counts["unrelated_lines"] += 1
                continue
            row = _record(line[len(PREFIX):])
            counts["validated_records"] += 1
            key = tuple(row[field] for field in ("cohort", "measurement_period", "account", "event_id"))
            previous = occurrences.get(key)
            if previous is not None:
                if any(previous[field] != row[field] for field in FIELDS - {"at"}):
                    raise InvalidReport("conflicting_duplicate")
                previous["at"] = min(previous["at"], row["at"])
                counts["duplicate_records"] += 1
            else:
                occurrences[key] = row
        excluded = {"cohort": 0, "measurement_period": 0, "window": 0}
        selected, groups = [], {}
        for row in occurrences.values():
            reason = ("cohort" if row["cohort"] != cohort else
                      "measurement_period" if row["measurement_period"] != measurement_period else
                      "window" if not start_at <= row["at"] < end_at else None)
            if reason:
                excluded[reason] += 1
                continue
            selected.append(row)
            groups.setdefault((row["opportunity_id"], row["destination_kind"]), []).append(row)
        return {"schema": 1, "status": "ok" if selected else "no_data",
                "window": {"start": _stamp(start_at), "end_exclusive": _stamp(end_at)},
                "measurement_period": measurement_period, "cohort": cohort,
                "coverage": {"capture_completeness": "not_established",
                             "input_lines": line_number, "input_bytes": counts["input_bytes"],
                             "unrelated_lines": counts["unrelated_lines"],
                             "validated_records": counts["validated_records"],
                             "duplicate_records": counts["duplicate_records"],
                             "deduplicated_records": len(occurrences), "included_records": len(selected),
                             "excluded_deduplicated_records": excluded,
                             "first_observed_at": _stamp(min(row["at"] for row in selected)) if selected else None,
                             "last_observed_at": _stamp(max(row["at"] for row in selected)) if selected else None},
                "catalog_revisions": sorted({row["catalog_revision"] for row in selected}),
                "totals": {"unique_accounts": len({row["account"] for row in selected}),
                           "opportunity_groups": len(groups),
                           "actions": {kind: sum(row["kind"] == kind for row in selected) for kind in KINDS}},
                "opportunities": [_aggregate(key, groups[key]) for key in sorted(groups)],
                "limitations": [
                    "Only valid prefixed records in this supplied export are measured; complete capture, retention and delivery are not established.",
                    "Counts describe signed-in accounts, not verified athletes, people or teams. Fixture and internal cohorts are excluded from the default pilot report.",
                    "Outbound activation does not establish destination arrival, registration, payment, selection or revenue.",
                    "Rates are same-window account overlaps, not action order or causation. Missing views remain missing; zero captured actions do not establish zero interest.",
                    "Action counts deduplicate retry IDs, not repeated intentional actions. Unique audience is deduplicated again across opportunities.",
                    "Retries use their earliest server acceptance in this export. Missing earlier export records can change window attribution; source refreshes do not reset audience counts."]}
    except InvalidReport as exc:
        return {"schema": 1, "status": "invalid", "error": str(exc), "line": line_number or None}
    except (OSError, UnicodeError):
        return {"schema": 1, "status": "invalid", "error": "input_unavailable", "line": line_number or None}


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise InvalidReport("invalid_arguments")


def _input_lines(paths):
    for path in paths:
        if path == "-":
            stream = getattr(sys.stdin, "buffer", sys.stdin)
            while line := stream.readline(MAX_LINE_BYTES + 1):
                yield line
        else:
            with open(path, "rb") as stream:
                while line := stream.readline(MAX_LINE_BYTES + 1):
                    yield line


def main(argv=None):
    parser = _Parser(add_help=False)
    parser.add_argument("inputs", nargs="*")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--measurement-period")
    parser.add_argument("--cohort", default="pilot")
    parser.add_argument("--help", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.help:
            result = {"usage": "opportunity_engagement_report.py LOG... --start UTC --end UTC --measurement-period SLUG [--cohort pilot|internal|fixture]",
                      "input": "Local UTF-8 log exports, or - for stdin. End is exclusive; no complete-capture claim."}
        elif not args.inputs or args.inputs.count("-") > 1:
            raise InvalidReport("invalid_arguments")
        else:
            result = build_report(_input_lines(args.inputs), start=args.start, end=args.end,
                                  measurement_period=args.measurement_period, cohort=args.cohort)
    except InvalidReport:
        result = {"schema": 1, "status": "invalid", "error": "invalid_arguments", "line": None}
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 2 if result.get("status") == "invalid" else 0


if __name__ == "__main__":
    raise SystemExit(main())
