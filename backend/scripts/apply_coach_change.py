"""Apply ONE reviewed coach change to the data file and the research file (after Fable review against the source
page, and before a reviewed commit + deploy). Never run from a check automatically.

Usage: python backend/scripts/apply_coach_change.py <program_id> --name "A; B" [--email x@school.edu | --no-email]
       --checked YYYY-MM-DD [--research /path/college-coach-contacts-2026.json]
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data" / "college_womens_flag_2026.json"
RESEARCH = ROOT.parent / "research" / "college-coach-contacts-2026.json"
EMAIL = re.compile(r"[A-Za-z0-9._+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+")


def slug(school: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", school.lower()).strip("-")  # same id rule as college_programs.programs()


def apply(program_id, name, email, checked, data_path=DATA, research_path=RESEARCH, title=None):
    if email is not None and not EMAIL.fullmatch(email):
        raise ValueError("email must be one plain address")
    date.fromisoformat(checked)
    if not name.strip() or len(name) > 160:
        raise ValueError("name required, at most 160 characters")
    data = json.loads(data_path.read_text())
    row = next((r for r in data if slug(r["school"]) == program_id), None)
    if row is None:
        raise ValueError("unknown program id")
    if email is not None:
        sys.path.insert(0, str(ROOT / "backend"))
        import college_programs as cp
        if not cp.coach_email({**row, "coach_email": email}):  # personal or shared-domain addresses are never stored
            raise ValueError("email must be on the school's own domain or the program/staff page host")
    research = json.loads(research_path.read_text())
    rows = research if isinstance(research, list) else research.get("programs", [])
    match = [r for r in rows if r.get("school") == row["school"]]
    if len(match) != 1:
        raise ValueError(f"research file has {len(match)} rows for {row['school']}")
    for target in (row, match[0]):
        target["head_coach_name"], target["coach_email"] = name.strip(), email
        if title is not None:
            target["head_coach_title"] = title.strip()[:120]
    row["contacts_verified_on"], match[0]["verified_on"] = checked, checked
    # Each file keeps its own format (data: indent 2; research: indent 1) so a diff shows only the change.
    data_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    research_path.write_text(json.dumps(research, indent=1))  # its own format: indent 1, ASCII, no final newline
    return row["school"]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("program_id")
    ap.add_argument("--name", required=True)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--email")
    group.add_argument("--no-email", action="store_true")
    ap.add_argument("--checked", required=True)
    ap.add_argument("--title")
    ap.add_argument("--research", type=Path, default=RESEARCH)
    args = ap.parse_args(argv)
    school = apply(args.program_id, args.name, None if args.no_email else args.email, args.checked,
                   research_path=args.research, title=args.title)
    print(f"updated {school}")


if __name__ == "__main__":
    main(sys.argv[1:])
