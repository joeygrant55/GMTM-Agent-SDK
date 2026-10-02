"""Build the junior college data file and the US map once, offline from the app.

Inputs (downloaded by hand; this script makes no network call):
  --research    sparq-demo/research (college-womens-flag-2026.json + college-coach-contacts-2026.json)
  --places      US Census 2024 Gazetteer places file (2024_Gaz_place_national.txt)
  --cousubs     US Census 2024 Gazetteer county subdivisions file (2024_Gaz_cousubs_national.txt)
  --states      us-atlas@3 states-10m.json (TopoJSON from the US Census cartographic boundary files)

Outputs:
  backend/data/college_womens_flag_2026.json          programs + coach/color fields + city lat/lon
  backend/data/college_womens_flag_2026.sources.json  where each added field came from, with dates
  frontend/public/us-states.svg                       continental US state outlines, same projection
                                                      as college_programs.map_point

Data hygiene (research 2026-10-02): Augsburg and Saint Vincent are dropped (their own
sites label the team a club). Albright gets "Starts spring 2027". Davenport's dead
davenportpanthers.com links move to dupanthers.com, the official site.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
import college_programs as cp  # noqa: E402  (pure projection helpers only)

DROP = {"Augsburg University", "Saint Vincent College"}
STARTS = {"Albright College": "Starts spring 2027"}
# Postal names with no Census place: the Census place or township the campus sits in (or next to).
ALIAS = {("University Center", "MI"): "Kochville", ("Gwynedd Valley", "PA"): "Lower Gwynedd",
         ("Immaculata", "PA"): "East Whiteland", ("Milligan", "TN"): "Elizabethton", ("Tanner", "AL"): "Athens"}
DOMAIN_FIX = {"Davenport University": ("davenportpanthers.com", "dupanthers.com")}
CONTACT_FIELDS = ("head_coach_name", "head_coach_title", "coach_email", "staff_page_url", "primary_color", "color_source_url")
LSAD = re.compile(r"\s+(city and borough|consolidated government \(balance\)|metro(?:politan)? government \(balance\)|"
                  r"unified government \(balance\)|urban county|city|town|village|cdp|borough|municipality|township|plantation|"
                  r"charter township|location|gore|grant|purchase|unorganized territory)$")


def key(name: str, gazetteer_name: bool = False) -> str:
    name = re.sub(r"\(balance\)", "", name.lower()).strip()
    name = LSAD.sub("", name) if gazetteer_name else name
    name = re.sub(r"-.* county$", "", name)  # "Macon-Bibb County" -> "macon"
    name = re.sub(r"^st\.?\s", "saint ", name).replace("ft. ", "fort ")
    return re.sub(r"[^a-z0-9]", "", name)


def gazetteer(path: Path) -> dict:
    out = {}
    with path.open(encoding="utf-8") as f:
        header = [h.strip() for h in f.readline().split("\t")]
        for line in f:
            row = dict(zip(header, (c.strip() for c in line.split("\t"))))
            k = (row["USPS"], key(row["NAME"], gazetteer_name=True))
            # Prefer an active, incorporated place over a CDP of the same name.
            rank = 0 if row.get("FUNCSTAT") == "A" else 1
            if k not in out or rank < out[k][0]:
                out[k] = (rank, float(row["INTPTLAT"]), float(row["INTPTLONG"]), row["NAME"])
    return out


def decode(topo: dict):
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        points = []
        for dx, dy in arc:
            x, y = x + dx, y + dy
            points.append((y * sy + ty, x * sx + tx))  # (lat, lon)
        arcs.append(points)
    return arcs


def simplify(points, tolerance):
    """Douglas-Peucker on projected points."""
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = (dx * dx + dy * dy) ** 0.5 or 1e-9
    far, index = 0.0, 0
    for i, (x, y) in enumerate(points[1:-1], 1):
        d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm
        if d > far:
            far, index = d, i
    if far <= tolerance:
        return [points[0], points[-1]]
    return simplify(points[:index + 1], tolerance)[:-1] + simplify(points[index:], tolerance)


def state_svg(topo: dict) -> str:
    arcs = decode(topo)
    skip = {"02", "15", "60", "66", "69", "72", "78"}  # continental US only
    paths = []
    for geometry in topo["objects"]["states"]["geometries"]:
        if geometry["id"] in skip:
            continue
        polygons = geometry["arcs"] if geometry["type"] == "MultiPolygon" else [geometry["arcs"]]
        d = []
        for polygon in polygons:
            for ring in polygon:
                points = []
                for i in ring:
                    arc = arcs[i] if i >= 0 else arcs[~i][::-1]
                    points += [cp.project(lat, lon) for lat, lon in (arc if not points else arc[1:])]
                half = len(points) // 2  # a closed ring has no chord: simplify two halves
                points = simplify(points[:half + 1], 0.6)[:-1] + simplify(points[half:], 0.6)
                if len(points) < 4:
                    continue
                d.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in points) + "Z")
        if d:
            paths.append(f'<path d="{"".join(d)}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {cp.MAP_W} {cp.MAP_H}">'
            '<g fill="#18242E" stroke="#2E4252" stroke-width="1" stroke-linejoin="round"><style>path{vector-effect:non-scaling-stroke}</style>'
            + "".join(paths) + "</g></svg>\n")


def main(argv=None):
    parser = argparse.ArgumentParser()
    for name in ("research", "places", "cousubs", "states"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    programs = json.loads((args.research / "college-womens-flag-2026.json").read_text())
    contacts = {r["school"]: r for r in json.loads((args.research / "college-coach-contacts-2026.json").read_text())}
    places, cousubs = gazetteer(args.places), gazetteer(args.cousubs)
    out, missing = [], []
    for p in programs:
        if p["school"] in DROP:
            continue
        c = contacts[p["school"]]
        row = dict(p)
        if p["school"] in DOMAIN_FIX:
            old, new = DOMAIN_FIX[p["school"]]
            row["program_url"] = (row.get("program_url") or "").replace(old, new) or None
            row["source_urls"] = [u for u in row["source_urls"] if old not in u]
        for field in CONTACT_FIELDS:
            row[field] = c.get(field)
        # The input questionnaire stays; the contacts research adds flag-only ones it found.
        row["questionnaire_url"] = p.get("questionnaire_url") or c.get("questionnaire_url")
        row["contacts_verified_on"] = c["verified_on"]
        row["contact_notes"] = c.get("notes")
        row["starts"] = STARTS.get(p["school"])
        city = key(ALIAS.get((p["city"], p["state"]), p["city"]))
        hit = places.get((p["state"], city)) or cousubs.get((p["state"], city))
        if hit:
            row["lat"], row["lon"] = round(hit[1], 4), round(hit[2], 4)
        else:
            row["lat"] = row["lon"] = None
            missing.append(f'{p["school"]} ({p["city"]}, {p["state"]})')
        out.append(row)
    data = ROOT / "backend" / "data"
    (data / "college_womens_flag_2026.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    (data / "college_womens_flag_2026.sources.json").write_text(json.dumps({
        "built_by": "backend/scripts/build_college_data.py",
        "programs": "sparq-demo/research/college-womens-flag-2026.json (verified 2026-10-01)",
        "coach_color_questionnaire": "sparq-demo/research/college-coach-contacts-2026.json (verified 2026-10-02; official athletics pages)",
        "city_lat_lon": "US Census Bureau 2024 Gazetteer Files: places, then county subdivisions "
                        "(https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/), internal point, downloaded 2026-10-02",
        "map": "us-atlas@3 states-10m.json (US Census cartographic boundaries, https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json), "
               "downloaded 2026-10-02, Albers equal-area (college_programs.project), simplified",
        "dropped": sorted(DROP), "starts": STARTS, "domain_fixed": {k: list(v) for k, v in DOMAIN_FIX.items()},
        "city_alias": {f"{c}, {st}": v for (c, st), v in ALIAS.items()}, "no_lat_lon": missing,
    }, indent=2) + "\n")
    (ROOT / "frontend" / "public" / "us-states.svg").write_text(state_svg(json.loads(args.states.read_text())))
    print(json.dumps({"programs": len(out), "no_lat_lon": missing}, indent=2))


if __name__ == "__main__":
    main()
