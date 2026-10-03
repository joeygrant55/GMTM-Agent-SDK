"""Phase 0a probe: run college research on named programs and print a JSON report. Writes nothing to any DB.

Usage: ANTHROPIC_API_KEY=... python backend/scripts/college_research_probe.py <program_id ...|--all> [--cap 2.00]
Prints one JSON line per program, then a summary line.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import anthropic  # noqa: E402

import college_programs  # noqa: E402
import college_research  # noqa: E402
import outreach_draft  # noqa: E402


def extract(system, user):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=90.0, max_retries=1)
    r = client.messages.create(model=college_programs.MODEL, max_tokens=4000, system=system,
                               messages=[{"role": "user", "content": user}])
    text = "".join(b.text for b in r.content if hasattr(b, "text"))
    return outreach_draft.parse_json_response(text), {"input_tokens": r.usage.input_tokens,
                                                      "output_tokens": r.usage.output_tokens}


def main(argv):
    cap = 2.0
    if "--cap" in argv:
        i = argv.index("--cap")
        try:
            cap, argv = float(argv[i + 1]), argv[:i] + argv[i + 2:]
        except (IndexError, ValueError):
            sys.exit("--cap needs a dollar amount, e.g. --cap 2.00")
    ids = argv
    if ids == ["--all"]:
        ids = sorted(p["id"] for p in college_programs.programs())  # fixed order, never saved-list priority
    by_id = {p["id"]: p for p in college_programs.programs()}
    missing = [pid for pid in ids if pid not in by_id]
    if missing:
        sys.exit(f"unknown program ids: {missing}")  # before any paid call
    spent, out = 0.0, []
    for pid in ids:
        if spent >= cap:
            out.append({"program_id": pid, "skipped": "cap"})
            continue
        result = college_research.research_program(by_id[pid], extract)
        spent += result.get("cost_usd", 0.0)  # early not_found results make no model call
        out.append(result)
        print(json.dumps(result), flush=True)  # one line per program, so a stop keeps what was done
    print(json.dumps({"spent_usd": round(spent, 4), "cap_usd": cap, "programs": len(out)}), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
