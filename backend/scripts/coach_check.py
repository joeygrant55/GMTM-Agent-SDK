"""Coach contact check for all programs (or --only <id> ...). Local, read-only, no model call, no database.
Prints one JSON line per program, then a summary of buckets. Spec: docs/specs/coach-contact-refresh-2026-10-05.md.

Usage: python backend/scripts/coach_check.py [--only <id> ...] [--review]   (--review prints only rows to review)
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coach_check  # noqa: E402
import college_programs  # noqa: E402

REVIEW = {"different_person", "email_changed", "email_added"}


def main(argv):
    review = "--review" in argv
    argv = [a for a in argv if a != "--review"]
    programs = sorted(college_programs.programs(), key=lambda p: p["id"])
    if argv[:1] == ["--only"]:
        wanted = set(argv[1:])
        programs = [p for p in programs if p["id"] in wanted]
        if len(programs) != len(wanted):
            sys.exit("unknown program ids")
    elif argv:
        sys.exit(f"unexpected argument(s): {argv}")
    counts = collections.Counter()
    for p in programs:
        result = coach_check.check_program(p)
        counts[result["bucket"]] += 1
        if not review or result["bucket"] in REVIEW:
            print(json.dumps(result), flush=True)
    print(json.dumps({"programs": len(programs), "buckets": dict(counts)}), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
