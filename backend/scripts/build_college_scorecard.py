"""Join College Scorecard institution facts onto the college flag program list.

Usage: python3 -I backend/scripts/build_college_scorecard.py <Most-Recent-Cohorts-Institution.csv> [--check]

Input CSV: "Most Recent Institution-Level Data" from https://collegescorecard.ed.gov/data/
(bulk zip, no API key). Writes ``data/college_scorecard_2026.json`` keyed by the same
program id the app computes in ``college_programs.load_programs``.

Matching never guesses. A program matches one UNITID only when the Scorecard row is in the
same state, its LATITUDE/LONGITUDE is within MAX_MILES of our city point, and either
(a) the normalized name (or a Scorecard ALIAS) is equal and unique there, or
(b) the program id is in OVERRIDES (a hand-checked pair; the state and distance checks still apply).
Everything else is left unmatched and printed with the reason. ``--check`` prints the report only.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
PROGRAMS = BACKEND / "data" / "college_womens_flag_2026.json"
OUT = BACKEND / "data" / "college_scorecard_2026.json"
SOURCE = "https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_10152026.zip"
RELEASE = "College Scorecard Most Recent Institution-Level Data, October 15, 2026 update (Most-Recent-Cohorts-Institution_10152026.zip)"
MAX_MILES = 15.0

DALLAS = "Scorecard reports Dallas College as one institution; these facts cover all its campuses."
# program id -> (UNITID, note shown with the facts or None). Each pair checked by hand against the
# Scorecard row (name, city); the state and distance checks still apply. Reason in the comment.
OVERRIDES: dict[str, tuple[int, str | None]] = {
    "fairleigh-dickinson-university": (184603, None),  # FDU-Metropolitan Campus, Teaneck (D1 campus; Florham is D3)
    "barton-university": (197911, None),  # Barton College, Wilson NC (renamed)
    "batten-university": (234173, None),  # Virginia Wesleyan University (renamed Batten University)
    "cairn-university": (215114, None),  # Cairn University-Langhorne
    "hobart-and-william-smith-colleges": (191630, None),  # Hobart William Smith Colleges, Geneva NY
    "penn-state-schuylkill": (214810, None),  # Pennsylvania State University-Penn State Schuylkill
    "pennsylvania-state-university-harrisburg": (214713, None),  # Pennsylvania State University-Penn State Harrisburg
    "bethel-college": (154749, None),  # Bethel College-North Newton KS
    "brewton-parker-college": (139205, None),  # Brewton-Parker Christian University (renamed)
    "graceland-university": (153366, None),  # Graceland University-Lamoni
    "indiana-wesleyan-university": (151801, None),  # IWU-Marion (residential), not IWU-National & Global (online)
    "lindsey-wilson-college": (157216, None),  # Lindsey Wilson University (renamed)
    "ottawa-university-kansas": (155627, None),  # Ottawa University-Ottawa
    "ottawa-university-arizona": (464226, None),  # Ottawa University-Surprise
    "university-of-saint-francis": (152336, None),  # University of Saint Francis-Fort Wayne
    "rowan-college-of-south-jersey-cumberland": (184205, None),  # RCSJ-Cumberland Campus, Vineland
    "rowan-college-of-south-jersey-gloucester": (184791, None),  # RCSJ-Gloucester Campus, Sewell
    "wallace-state-community-college": (101295, None),  # George C Wallace State Community College-Hanceville
    **{f"dallas-college-{c}": (224615, DALLAS)
       for c in ("brookhaven", "cedar-valley", "eastfield", "mountain-view", "north-lake", "richland")},
}

CONTROL = {"1": "public", "2": "private nonprofit", "3": "private for-profit"}
LOCALE = {"1": "City", "2": "Suburb", "3": "Town", "4": "Rural"}
MISSING = {"", "NA", "NULL", "PrivacySuppressed"}


def program_id(school: str) -> str:
    # Same rule as college_programs.load_programs.
    return re.sub(r"[^a-z0-9]+", "-", school.lower()).strip("-")


def norm(name: str) -> str:
    n = name.lower().replace("&", " and ").replace("saint ", "st ").replace("st. ", "st ")
    n = re.sub(r"[^a-z0-9]+", " ", n)
    return re.sub(r"^the ", "", n).strip()


def miles(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(a))


def value(row, key, kind=float):
    v = row.get(key, "").strip()
    return None if v in MISSING else kind(float(v)) if kind is int else kind(v)


def facts(row) -> dict:
    control = row["CONTROL"].strip()
    locale = value(row, "LOCALE", int)
    return {
        "unitid": int(row["UNITID"]),
        "scorecard_name": row["INSTNM"],
        "scorecard_city": row["CITY"],
        "ownership": CONTROL.get(control),
        "undergrad_size": value(row, "UGDS", int),
        "admission_rate": value(row, "ADM_RATE"),
        # OPENADMP 1 = open admission (no admission rate). Stored, so "everyone who applies" is never a guess.
        "open_admission": row.get("OPENADMP", "").strip() == "1",
        "tuition_in_state": value(row, "TUITIONFEE_IN", int),
        "tuition_out_of_state": value(row, "TUITIONFEE_OUT", int),
        "avg_net_price": value(row, "NPT4_PUB" if control == "1" else "NPT4_PRIV", int),
        # ICLEVEL 1 = 4-year; 2 and 3 = 2-year and less.
        "grad_rate": value(row, "C150_4" if row["ICLEVEL"].strip() == "1" else "C150_L4"),
        "locale": LOCALE.get(str(locale)[0]) if locale else None,
        "scorecard_url": f"https://collegescorecard.ed.gov/school/?{int(row['UNITID'])}",
    }


def names(row) -> set[str]:
    aliases = "" if row.get("ALIAS", "").strip() in MISSING else row["ALIAS"]
    return {norm(row["INSTNM"])} | {norm(a) for a in re.split(r"[|,;]", aliases) if a.strip()}


def match(programs, rows):
    by_state: dict[str, list] = {}
    for row in rows:
        if value(row, "LATITUDE") is not None and value(row, "LONGITUDE") is not None:
            by_state.setdefault(row["STABBR"], []).append(row)
    matched, unmatched = {}, []
    for p in programs:
        pid, want = program_id(p["school"]), norm(p["school"])
        near = [(miles(p["lat"], p["lon"], float(r["LATITUDE"]), float(r["LONGITUDE"])), r)
                for r in by_state.get(p["state"], [])]
        if pid in OVERRIDES:
            unitid = OVERRIDES[pid][0]
            hit = [(d, r) for d, r in near if int(r["UNITID"]) == unitid]
            if not hit:
                unmatched.append((pid, f"override {unitid} not in {p['state']}"))
            elif hit[0][0] > MAX_MILES:
                unmatched.append((pid, f"override {unitid} is {hit[0][0]:.1f} mi away"))
            else:
                matched[pid] = (hit[0][0], hit[0][1])
            continue
        same = [(d, r) for d, r in near if want in names(r)]
        close = [(d, r) for d, r in same if d <= MAX_MILES]
        if len(close) == 1:
            matched[pid] = close[0]
        elif len(close) > 1:
            unmatched.append((pid, "ambiguous: " + "; ".join(f"{r['UNITID']} {r['INSTNM']} ({r['CITY']}, {d:.1f} mi)" for d, r in close)))
        elif same:
            d, r = min(same, key=lambda x: x[0])
            unmatched.append((pid, f"name match {r['UNITID']} {r['INSTNM']} ({r['CITY']}) is {d:.1f} mi away"))
        else:
            hints = sorted((d, r) for d, r in near if d <= MAX_MILES and set(want.split()) & set(norm(r["INSTNM"]).split()) - {"university", "college", "of", "community", "state", "and"})[:3]
            unmatched.append((pid, "no name match in state; nearby: " + ("; ".join(f"{r['UNITID']} {r['INSTNM']} ({r['CITY']}, {d:.1f} mi)" for d, r in hints) or "none")))
    return matched, unmatched


def main(argv):
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__)
    csv.field_size_limit(10**9)
    with open(argv[0], encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    programs = json.loads(PROGRAMS.read_text())
    matched, unmatched = match(programs, rows)
    print(f"matched {len(matched)} / {len(programs)}; unmatched {len(unmatched)}")
    for pid, why in unmatched:
        print(f"  UNMATCHED {pid}: {why}")
    seen: dict[int, list] = {}
    for pid, (_, r) in matched.items():
        seen.setdefault(int(r["UNITID"]), []).append(pid)
    for unitid, pids in seen.items():
        if len(pids) > 1:
            print(f"  SHARED UNITID {unitid}: {pids}")
    out = {pid: facts(r) | {"distance_miles": round(d, 1), "note": OVERRIDES.get(pid, (0, None))[1],
                                     "whole_system": OVERRIDES.get(pid, (0, None))[1] == DALLAS}
           for pid, (d, r) in sorted(matched.items())}
    fill = {k: sum(v[k] is not None for v in out.values()) for k in next(iter(out.values()), {})}
    print("fill:", json.dumps(fill))
    if "--check" not in argv:
        OUT.write_text(json.dumps({"source": SOURCE, "release": RELEASE, "retrieved_on": date.today().isoformat(),
                                   "programs": out}, indent=2) + "\n")
        print(f"wrote {OUT}")


if __name__ == "__main__":
    main(sys.argv[1:])
