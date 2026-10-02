"""Junior colleges on the profile app: a sourced program list, why each fits, and a copy-only draft.

Program data: ``data/college_womens_flag_2026.json`` is built by
``scripts/build_college_data.py`` from ``sparq-demo/research/college-womens-flag-2026.json``
(verified 2026-10-01 from governing-body, conference or official athletics pages) plus
``college-coach-contacts-2026.json`` (coach, color and questionnaire fields, verified
2026-10-02) and US Census Gazetteer city points. Sources: ``*.sources.json`` beside it.
Two club teams are dropped (187 programs). Coach emails are stored but not served yet.
Contact rules below come from ``college-womens-flag-2026.md`` (same date) and keep
its source links. The NJCAA first-contact date was not verified, so it is not shown.

Rules for this module:
- Girls first: a list is built only when the stored GMTM gender is 1 (female).
- Matching is deterministic (home state, then neighbouring states, then region,
  with a mix of levels). No web search, no live research, no numeric fit score.
- The one model call per list build receives only position, grad year, state,
  the athlete's GMTM drill results and the stored program facts. Never a name, city or email.
- Saves and "I sent it" marks are per athlete and program; no email text is stored.
- Distances use stored lat/lon only (GMTM location, Census city points). No geocoding
  service is called at request time.
- Drafts reuse the shared outreach prompt (first name only). SPARQ never sends.

Inert on import. Outside effects go through module seams that tests replace:
``store`` (Agent DB), ``read_identity`` / ``read_athlete`` (read-only GMTM) and ``model_json`` (model).
``SCHEMA`` is prepared separately; the app never creates tables.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

import anthropic
from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, StrictBool

import auth
from auth import require_identity
import outreach_draft
from junior_eligibility import plausible_grad_year

log = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent / "data" / "college_womens_flag_2026.json"
MODEL = "claude-sonnet-4-6"
MAX_SHOWN = 12
FEMALE = 1
NOT_ELIGIBLE = ("College flag football is a women's sport at most schools today. "
                "Your profile, footage and results are here. "
                "If your GMTM profile gender is wrong, update it on GMTM.")

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS sparq_college_lists (
    clerk_id VARBINARY(255) PRIMARY KEY,
    gmtm_gender TINYINT NULL,
    gmtm_sport VARCHAR(100) NULL,
    inputs_key CHAR(64) NULL,
    programs JSON NULL,
    built_at DATETIME(6) NULL,
    updated_at DATETIME(6) NOT NULL
)""",
    """CREATE TABLE IF NOT EXISTS sparq_saved_colleges (
    clerk_id VARBINARY(255) NOT NULL,
    program_id VARCHAR(80) NOT NULL,
    saved_at DATETIME(6) NOT NULL,
    PRIMARY KEY (clerk_id, program_id)
)""",
    """CREATE TABLE IF NOT EXISTS sparq_sent_emails (
    clerk_id VARBINARY(255) NOT NULL,
    program_id VARCHAR(80) NOT NULL,
    sent_at DATETIME(6) NOT NULL,
    PRIMARY KEY (clerk_id, program_id)
)""",
)

LEVELS = {"NCAA-D1": "NCAA D1", "NCAA-D2": "NCAA D2", "NCAA-D3": "NCAA D3", "NAIA": "NAIA", "NJCAA": "NJCAA"}
BODY_ORDER = tuple(LEVELS)

# US Census divisions (neighbouring states) inside the four Census regions.
_DIVISIONS = {
    "Northeast": ("CT ME MA NH RI VT", "NJ NY PA"),
    "Midwest": ("IL IN MI OH WI", "IA KS MN MO NE ND SD"),
    "South": ("DE DC FL GA MD NC SC VA WV", "AL KY MS TN", "AR LA OK TX"),
    "West": ("AZ CO ID MT NV NM UT WY", "AK CA HI OR WA"),
}
DIVISION = {s: d for divisions in _DIVISIONS.values() for d in divisions for s in d.split()}
REGION = {s: r for r, divisions in _DIVISIONS.items() for d in divisions for s in d.split()}
_NAMES = ("Alabama AL,Alaska AK,Arizona AZ,Arkansas AR,California CA,Colorado CO,Connecticut CT,Delaware DE,"
          "District of Columbia DC,Florida FL,Georgia GA,Hawaii HI,Idaho ID,Illinois IL,Indiana IN,Iowa IA,"
          "Kansas KS,Kentucky KY,Louisiana LA,Maine ME,Maryland MD,Massachusetts MA,Michigan MI,Minnesota MN,"
          "Mississippi MS,Missouri MO,Montana MT,Nebraska NE,Nevada NV,New Hampshire NH,New Jersey NJ,"
          "New Mexico NM,New York NY,North Carolina NC,North Dakota ND,Ohio OH,Oklahoma OK,Oregon OR,"
          "Pennsylvania PA,Rhode Island RI,South Carolina SC,South Dakota SD,Tennessee TN,Texas TX,Utah UT,"
          "Vermont VT,Virginia VA,Washington WA,West Virginia WV,Wisconsin WI,Wyoming WY")
STATE_CODES = {name.lower(): code for name, code in (item.rsplit(" ", 1) for item in _NAMES.split(","))}

# Only rules with a source in college-womens-flag-2026.md. Written for a reader aged 13-17.
_D1 = "https://web3.ncaa.org/lsdbi/reports/getReport/90008"
_D2 = "https://web3.ncaa.org/lsdbi/reports/getReport/90010"
_D3 = "https://web3.ncaa.org/lsdbi/reports/getReport/90011"
_NAIA = "https://play.mynaia.org/media/pzaf3rnz/naia_guide_college_bound_student.pdf"
# The .md links the CBSA guide over http; the same ncaa.org path is linked over https.
_ELIGIBILITY = ("To play an NCAA emerging sport like flag football, you register with the NCAA Eligibility Center.",
                "https://fs.ncaa.org/Docs/eligibility_center/Student_Resources/CBSA.pdf", "NCAA Guide for the College-Bound Student-Athlete")
CONTACT_RULES = {
    "NCAA-D1": [
        ("Coaches can't call, text or email you before June 15 after your sophomore year.", _D1, "NCAA Division I Manual 2026-27"),
        ("Coaches can't meet you in person off campus before August 1 of your junior year.", _D1, "NCAA Division I Manual 2026-27"),
        _ELIGIBILITY,
    ],
    "NCAA-D2": [
        ("Coaches can call, text and email you at any time.", _D2, "NCAA Division II Manual 2026-27"),
        ("Coaches can't meet you in person before June 15 before your junior year.", _D2, "NCAA Division II Manual 2026-27"),
        _ELIGIBILITY,
    ],
    "NCAA-D3": [
        ("Coaches can call, text and email you with no timing limit.", _D3, "NCAA Division III Manual 2026-27"),
        ("Coaches can meet you in person off campus only after your sophomore year is complete.", _D3, "NCAA Division III Manual 2026-27"),
    ],
    "NAIA": [
        ("The NAIA has few limits on contact between players and coaches.", _NAIA, "NAIA Guide for the College-Bound Student-Athlete"),
        ("You can try out at NAIA schools for no more than two days in your whole career.", _NAIA, "NAIA Guide for the College-Bound Student-Athlete"),
        ("To play in the NAIA, you register at PlayNAIA.org.", _NAIA, "NAIA Guide for the College-Bound Student-Athlete"),
    ],
    # NJCAA first-contact date: not verified (handbook did not render). Do not show one.
    "NJCAA": [("Check with the school.", None, None)],
}

# ── Map and distance (pure) ────────────────────────────────────────────────────
# Albers equal-area conic for the continental US (parallels 29.5/45.5, centre 37.5N 96W),
# fitted once to a 960x600 box. The bundled frontend/public/us-states.svg uses the same numbers.
MAP_W, MAP_H = 960, 600
_SCALE, _TX, _TY = 1261.4, 489.9, 322.1
_P1, _P2, _P0, _LON0 = (math.radians(v) for v in (29.5, 45.5, 37.5, -96.0))
_N = (math.sin(_P1) + math.sin(_P2)) / 2
_C = math.cos(_P1) ** 2 + 2 * _N * math.sin(_P1)
_R0 = math.sqrt(_C - 2 * _N * math.sin(_P0)) / _N


def project(lat: float, lon: float) -> tuple[float, float]:
    rho = math.sqrt(_C - 2 * _N * math.sin(math.radians(lat))) / _N
    theta = _N * (math.radians(lon) - _LON0)
    return _TX + _SCALE * rho * math.sin(theta), _TY + _SCALE * (rho * math.cos(theta) - _R0)


def continental(lat, lon) -> bool:
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (lat, lon)) \
        and 24 <= lat <= 50 and -125 <= lon <= -66


def map_point(lat, lon) -> Optional[dict]:
    """Percent position on the bundled map, or None outside the continental US."""
    if not continental(lat, lon):
        return None
    x, y = project(lat, lon)
    return {"x": round(100 * x / MAP_W, 2), "y": round(100 * y / MAP_H, 2)}


def miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle (haversine) distance in statute miles."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def about_miles(value: float) -> int:
    """'about N mi': nearest 5 under 100, nearest 10 above; never 0."""
    step = 5 if value < 100 else 10
    return max(step, int(round(value / step)) * step)


_programs: Optional[list[dict]] = None
_data_hash = ""
REQUIRED = ("school", "city", "state", "governing_body", "verified_on")


def load_programs(raw: bytes) -> list[dict]:
    """Parse and check every row; a bad file stops startup instead of showing a broken card."""
    rows = json.loads(raw)
    if not isinstance(rows, list) or not rows:
        raise ValueError("College program data must be a non-empty list.")
    ids = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip() for k in REQUIRED) \
                or row["governing_body"] not in LEVELS or not isinstance(row.get("source_urls"), list):
            raise ValueError(f"College program row {index} is missing a required field.")
        date.fromisoformat(row["verified_on"])
        if (row.get("lat") is not None or row.get("lon") is not None) and not continental(row.get("lat"), row.get("lon")):
            raise ValueError(f"College program row {index} has a bad location.")
        if row.get("primary_color") is not None and not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(row["primary_color"])):
            raise ValueError(f"College program row {index} has a bad color.")
        row["id"] = re.sub(r"[^a-z0-9]+", "-", row["school"].lower()).strip("-")
        if row["id"] in ids:
            raise ValueError(f"College program row {index} repeats a school.")
        ids.add(row["id"])
    return rows


def programs() -> list[dict]:
    """The sourced list, loaded on first use (and checked at app startup)."""
    global _programs, _data_hash
    if _programs is None:
        raw = DATA_FILE.read_bytes()
        _programs, _data_hash = load_programs(raw), hashlib.sha256(raw).hexdigest()
    return _programs


def program(program_id: str) -> Optional[dict]:
    return next((p for p in programs() if p["id"] == program_id), None)


# ── Seams ──────────────────────────────────────────────────────────────────────

def read_identity(user_id: int) -> Optional[dict]:
    from workspace_bootstrap import _gmtm_identity  # lazy: read-only GMTM
    ident = _gmtm_identity(user_id)
    return None if ident is None else {"gender": ident.get("gender"), "sport": ident.get("sport")}


MAX_DRILLS = 8
_MS = "milliseconds"


def _drills(metric_items: list[dict], submitted: list[dict]) -> list[dict]:
    """Newest result per drill, height/weight left out, GMTM's stored milliseconds as seconds."""
    out, seen = [], set()
    for item in sorted(metric_items + submitted, key=lambda i: i.get("recorded_at") or "", reverse=True):
        name = item["label"]
        drill = re.sub(r"[^a-z0-9]", "", name.lower())
        if drill in ("height", "weight") or drill in seen:
            continue
        try:  # one bad drill is skipped; the others stay
            value, unit = float(item["value"]), str(item["unit"])
        except (KeyError, TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        seen.add(drill)
        if unit == _MS:
            value, unit = round(value / 1000, 2), "seconds"
        out.append({"name": name, "value": int(value) if value.is_integer() else value, "unit": unit})
    return out[:MAX_DRILLS]


def _origin(row: Optional[dict]) -> Optional[dict]:
    """The athlete's GMTM city point. GMTM lat/lng first, else the same city in the program data."""
    if not row:
        return None
    city = row.get("city").strip() if isinstance(row.get("city"), str) and row["city"].strip() else None
    state = state_code(row.get("state"))
    lat, lon = row.get("lat"), row.get("lng")
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        lat = lon = None
    if not continental(lat, lon) and city and state:
        hit = next((p for p in programs() if p["state"] == state and p["city"].lower() == city.lower() and p.get("lat") is not None), None)
        lat, lon = (hit["lat"], hit["lon"]) if hit else (None, None)
    if not continental(lat, lon):
        return None
    return {"city": city[:100] if city else None, "state": state, "lat": round(lat, 3), "lon": round(lon, 3)}


def read_athlete(user_id: int) -> dict:
    """Read-only GMTM: public drill results (existing evidence/materials readers) and city point."""
    import athlete_evidence as evidence  # lazy: read-only GMTM readers
    import athlete_materials as materials
    db = evidence._get_gmtm_db()
    try:
        metric_rows = evidence._metric_rows(db, user_id)
        submission_rows = materials._submission_rows(db, user_id)
        with db.cursor() as c:
            c.execute("SELECT u.user_id, l.lat, l.lng, l.city, l.province AS state FROM users u "
                      "LEFT JOIN locations l ON l.location_id = u.location_id WHERE u.user_id = %s LIMIT 2", (user_id,))
            rows = [r for r in c.fetchall() if r.get("user_id") == user_id]
    finally:
        db.close()
    metric_items = [i for i in map(evidence._measurement, metric_rows[:evidence.MAX_SOURCE_MEASUREMENTS]) if i]
    submitted = []
    for row in submission_rows[:materials.MAX_SOURCE_ROWS]:
        if materials._submission_scope(row, user_id):
            # Only results the athlete marked public can reach a draft to a coach.
            submitted += [{"label": i["title"], "value": i["result"]["value"], "unit": i["result"]["unit"],
                           "recorded_at": i["recorded_at"]} for i in materials._submission_items(row)[0] if i["can_include"]]
    return {"drills": _drills(metric_items, submitted), "origin": _origin(rows[0] if len(rows) == 1 else None)}


def model_json(system: str, user: str, max_tokens: int) -> Optional[dict]:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    client = anthropic.Anthropic(api_key=key, timeout=30.0, max_retries=1)
    response = client.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                      messages=[{"role": "user", "content": user}])
    return outreach_draft.parse_json_response("".join(b.text for b in response.content if hasattr(b, "text")))


class MySQLStore:
    """Agent DB access; each call opens and closes its own connection."""

    def _run(self, fn, write=False):
        from profile_api import _get_agent_db  # lazy
        db = _get_agent_db()
        try:
            with db.cursor() as c:
                result = fn(c)
            if write:
                db.commit()
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def profile(self, clerk_id):
        def read(c):
            c.execute("SELECT clerk_id, name, position, class_year, state, combine_metrics "
                      "FROM sparq_profiles WHERE clerk_id = %s LIMIT 2", (clerk_id,))
            rows = [r for r in c.fetchall() if r.get("clerk_id") == clerk_id]
            return rows[0] if len(rows) == 1 else None
        return self._run(read)

    def gmtm_user_id(self, clerk_id):
        def read(c):
            c.execute("SELECT user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2", (clerk_id,))
            rows = [r for r in c.fetchall() if r.get("clerk_id") == clerk_id]
            return int(rows[0]["user_id"]) if len(rows) == 1 else None
        return self._run(read)

    def load(self, clerk_id):
        def read(c):
            c.execute("SELECT gmtm_gender, gmtm_sport, inputs_key, programs FROM sparq_college_lists "
                      "WHERE clerk_id = %s", (clerk_id.encode(),))
            row = c.fetchone()
            if row and isinstance(row.get("programs"), (str, bytes)):
                row["programs"] = json.loads(row["programs"])
            return row
        return self._run(read)

    def save_identity(self, clerk_id, gender, sport):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self._run(lambda c: c.execute(
            "INSERT INTO sparq_college_lists (clerk_id, gmtm_gender, gmtm_sport, updated_at) VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE gmtm_gender = VALUES(gmtm_gender), gmtm_sport = VALUES(gmtm_sport), updated_at = VALUES(updated_at)",
            (clerk_id.encode(), gender, sport, now)), write=True)

    def save_list(self, clerk_id, inputs_key, items):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self._run(lambda c: c.execute(
            "UPDATE sparq_college_lists SET inputs_key = %s, programs = %s, built_at = %s, updated_at = %s WHERE clerk_id = %s",
            (inputs_key, json.dumps(items), now, now, clerk_id.encode())), write=True)

    def insert_draft(self, clerk_id, title, summary, payload, sources):
        def write(c):
            c.execute("INSERT INTO artifacts (clerk_id, type, state, agent_id, title, summary, payload, sources) "
                      "VALUES (%s, 'outreach_draft', 'ready_for_review', 'drafter', %s, %s, %s, %s)",
                      (clerk_id, title, summary, json.dumps(payload), json.dumps(sources)))
            return c.lastrowid
        return self._run(write, write=True)

    def latest_draft(self, clerk_id, program_id):
        def read(c):
            c.execute("SELECT id, clerk_id, payload, created_at FROM artifacts WHERE clerk_id = %s "
                      "AND type = 'outreach_draft' AND JSON_UNQUOTE(JSON_EXTRACT(payload, '$.program_id')) = %s "
                      "ORDER BY id DESC LIMIT 1", (clerk_id, program_id))
            row = c.fetchone()
            if not row or row.get("clerk_id") != clerk_id:
                return None
            payload = row["payload"]
            return {"id": row["id"], "payload": json.loads(payload) if isinstance(payload, (str, bytes)) else payload}
        return self._run(read)

    def marks(self, clerk_id):
        """{program_id: saved_at} and {program_id: sent_at} for one athlete."""
        def read(c):
            c.execute("SELECT program_id, saved_at FROM sparq_saved_colleges WHERE clerk_id = %s", (clerk_id.encode(),))
            saved = {r["program_id"]: r["saved_at"] for r in c.fetchall()}
            c.execute("SELECT program_id, sent_at FROM sparq_sent_emails WHERE clerk_id = %s", (clerk_id.encode(),))
            return saved, {r["program_id"]: r["sent_at"] for r in c.fetchall()}
        return self._run(read)

    def set_mark(self, table, clerk_id, program_id, on):
        """Idempotent: a repeat keeps the first timestamp; off deletes the row."""
        column = {"sparq_saved_colleges": "saved_at", "sparq_sent_emails": "sent_at"}[table]
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if on:
            sql, args = f"INSERT IGNORE INTO {table} (clerk_id, program_id, {column}) VALUES (%s, %s, %s)", (clerk_id.encode(), program_id, now)
        else:
            sql, args = f"DELETE FROM {table} WHERE clerk_id = %s AND program_id = %s", (clerk_id.encode(), program_id)
        self._run(lambda c: c.execute(sql, args), write=True)


store = MySQLStore()


# ── Pure logic ─────────────────────────────────────────────────────────────────

def state_code(value) -> Optional[str]:
    text = str(value or "").strip()
    code = text.upper() if len(text) == 2 else STATE_CODES.get(text.lower())
    return code if code in REGION else None


def rank(state: Optional[str], rows: Optional[list[dict]] = None) -> list[dict]:
    """Home state, then neighbouring states, then region, then the rest. Inside each
    tier, levels take turns (D1, D2, D3, NAIA, NJCAA) so every level can appear."""
    rows = programs() if rows is None else rows

    def tier(p):
        if not state:
            return 3
        if p["state"] == state:
            return 0
        return 1 if DIVISION.get(p["state"]) == DIVISION[state] else 2 if REGION.get(p["state"]) == REGION[state] else 3

    ranked = []
    for t in range(4):
        by_body = [sorted((p for p in rows if tier(p) == t and p["governing_body"] == body), key=lambda p: p["school"])
                   for body in BODY_ORDER]
        while any(by_body):
            ranked += [group.pop(0) for group in by_body if group]
    shown = ranked[:MAX_SHOWN]
    # Show every level: a missing level takes the last slot of a level shown more than once.
    for p in ranked[MAX_SHOWN:]:
        bodies = [q["governing_body"] for q in shown]
        if p["governing_body"] in bodies:
            continue
        spare = next((i for i in range(len(shown) - 1, -1, -1) if bodies.count(bodies[i]) > 1), None)
        if spare is None:
            break
        shown[spare] = p
    return shown


def https(url) -> Optional[str]:
    try:
        parts = urlsplit(url) if isinstance(url, str) else None
    except ValueError:
        return None
    return url if parts and parts.scheme == "https" and parts.hostname and not parts.username else None


def checked(value) -> str:
    day = date.fromisoformat(value)
    return f"{day:%b} {day.day}, {day.year}"


NEWS_PATHS = ("/news/", "/releases/", "/blog/", "/general/")


def _iso(value) -> Optional[str]:
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()
    return None


def card(p: dict, reason: Optional[str] = None, origin: Optional[dict] = None, marks=({}, {})) -> dict:
    link = https(p.get("program_url"))
    # A homepage or news release is not a sport page: require "flag" and no news-style path.
    path = urlsplit(link).path.lower() if link else ""
    confirmed = bool(link) and "flag" in path and not any(part in path for part in NEWS_PATHS)
    return {
        "id": p["id"], "school": p["school"], "city": p["city"], "state": p["state"],
        "governing_body": p["governing_body"], "level": LEVELS[p["governing_body"]], "conference": p.get("conference"),
        "program_link": link if confirmed else None,
        "program_link_label": "Program page" if confirmed else "Program link not confirmed",
        "source_links": [] if confirmed else [u for u in map(https, p.get("source_urls") or []) if u],
        "questionnaire_link": https(p.get("questionnaire_url")),
        "source_checked": f"Source checked {checked(p['verified_on'])}",
        "notes": p.get("notes"), "reason": reason,
        "starts": p.get("starts"), "primary_color": p.get("primary_color"),
        # Coach names and emails stay in the data for the email-kit slice; not served yet.
        "map": map_point(p.get("lat"), p.get("lon")),
        "distance_mi": about_miles(miles((origin["lat"], origin["lon"]), (p["lat"], p["lon"])))
        if origin and continental(p.get("lat"), p.get("lon")) else None,
        "saved": p["id"] in marks[0], "sent_at": _iso(marks[1].get(p["id"])),
    }


def contact_rules(bodies) -> list[dict]:
    """Only the governing bodies given, in the order given (her list order)."""
    return [{"governing_body": b, "level": LEVELS[b],
             "rules": [{"text": t, "source_url": https(u), "source_label": l} for t, u, l in CONTACT_RULES[b]]}
            for b in dict.fromkeys(bodies) if b in LEVELS]


def athlete_facts(profile: dict, drills: Optional[list[dict]] = None) -> dict:
    """The only athlete facts a model sees for fit reasons. No name, city or contact.
    Drill results come from GMTM (read_athlete), not the old 40/shuttle/vertical profile copy."""
    return {
        "position": profile.get("position") or None,
        # Stale GMTM years (e.g. 2011) are omitted, so the model never sees them.
        "grad_year": plausible_grad_year(profile.get("class_year")),
        "state": state_code(profile.get("state")),
        "drill_results": list(drills or []),
    }


def program_facts(p: dict) -> dict:
    return {"id": p["id"], "school": p["school"], "state": p["state"],
            "level": LEVELS[p["governing_body"]], "conference": p.get("conference"), "notes": p.get("notes")}


REASON_SYSTEM = """You help a high-school flag football athlete (age 13-17) understand why some college women's flag football programs could fit her.

For each program, write exactly 2 short sentences. Be plain, encouraging and honest.
- Use only the facts given: the athlete's position, grad year, state and drill_results (her real combine drills, e.g. 20-Yard Dash, 5-10-5 Shuttle, Broad Jump), and each program's school, state, level, conference and notes.
- Never invent coaches, emails, rosters, scholarships, records, rankings or recruiting interest.
- Never say "verified" or "recruited". Do not promise anything.
- Name a drill only as it is given in drill_results, with its value and unit. Never add a drill, a comparison or a percentile.
- If drill_results is empty, talk about location, level and the program notes.
- If grad_year is null, never mention a grad year, class year or graduation year.

Respond with ONLY JSON: {"reasons": [{"id": "<program id>", "reason": "<2 sentences>"}]}"""
_BANNED = ("verified", "recruited", "scholarship", "ranked", "@", "http")


def explain(facts: dict, chosen: list[dict]) -> dict[str, str]:
    """One model call. Any failure gives no reasons; the list still shows."""
    user = json.dumps({"athlete": facts, "programs": [program_facts(p) for p in chosen]}, indent=2)
    try:
        parsed = model_json(REASON_SYSTEM, user, 2000)
    except Exception:
        return {}
    items = parsed.get("reasons") if isinstance(parsed, dict) else None
    ids = {p["id"] for p in chosen}
    reasons = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        pid, text = item.get("id"), item.get("reason")
        if pid in ids and isinstance(text, str) and 0 < len(text.strip()) <= 500 \
                and not any(word in text.lower() for word in _BANNED):
            reasons[pid] = text.strip()
    return reasons


# ── Routes (profile app; owner-checked; behind the junior gate + parent notice) ──

def _owner(clerk_id: str, caller: str) -> None:
    if clerk_id != caller:
        raise HTTPException(403, "Not authorized.")


def owner_id(clerk_id: str, caller_id: str = Depends(require_identity)) -> str:
    """Owner check as a dependency, so a wrong owner gets 403 before any body is read."""
    _owner(clerk_id, caller_id)
    return clerk_id


def _identity(clerk_id: str, refresh: bool) -> dict:
    row = store.load(clerk_id) or {}
    # Anyone not yet eligible is re-read from GMTM, so a gender fix there shows up here.
    if refresh or row.get("gmtm_gender") != FEMALE:
        user_id = store.gmtm_user_id(clerk_id)
        ident = read_identity(user_id) if user_id else None
        if ident:
            try:
                gender = int(ident.get("gender"))
            except (TypeError, ValueError):
                gender = None
            sport = str(ident.get("sport") or "")[:100] or None
            store.save_identity(clerk_id, gender, sport)
            row = {**row, "gmtm_gender": gender, "gmtm_sport": sport}
    return row


def _athlete(clerk_id: str) -> Optional[dict]:
    """GMTM drills and city point, or None when GMTM cannot be read right now."""
    user_id = store.gmtm_user_id(clerk_id)
    if not user_id:
        return None
    try:
        return read_athlete(user_id)
    except Exception as error:
        log.warning("college_programs: GMTM athlete read failed (%s)", type(error).__name__)  # class only, never values
        return None


def _marks(clerk_id: str):
    """Saves and sent marks; empty if the store fails (e.g. the new tables are not created yet)."""
    try:
        return store.marks(clerk_id)
    except Exception as error:
        log.warning("college_programs: marks read failed (%s)", type(error).__name__)  # class only, never values
        return {}, {}


def _not_eligible() -> dict:
    return {"eligible": False, "notice": NOT_ELIGIBLE, "built": False, "programs": [], "contact_rules": [],
            "origin": None, "saved_count": 0, "sent_count": 0}


def _origin_view(athlete: Optional[dict]) -> Optional[dict]:
    origin = (athlete or {}).get("origin")
    return {"city": origin["city"], "state": origin["state"], "map": map_point(origin["lat"], origin["lon"])} if origin else None


def _cards(items, athlete: Optional[dict], marks) -> list[dict]:
    origin = (athlete or {}).get("origin")
    cards = [card(p, r, origin, marks) for p, r in items if p]
    # Closest first when the athlete's city is known; ties and unknowns keep the ranked order.
    return sorted(cards, key=lambda c: (c["distance_mi"] is None, c["distance_mi"] or 0))


def _listing(saved, athlete: Optional[dict], marks) -> dict:
    items = [(program(i.get("id")), i.get("reason")) for i in saved or [] if isinstance(i, dict)]
    cards = _cards(items[:MAX_SHOWN], athlete, marks)
    return {"eligible": True, "notice": None, "built": saved is not None, "programs": cards,
            "contact_rules": contact_rules(c["governing_body"] for c in cards), "origin": _origin_view(athlete),
            "saved_count": sum(1 for pid in marks[0] if program(pid)), "sent_count": sum(1 for pid in marks[1] if program(pid))}


def _inputs_key(facts: dict, chosen: list[dict]) -> str:
    return hashlib.sha256(json.dumps([facts, [p["id"] for p in chosen], _data_hash], sort_keys=True, default=str).encode()).hexdigest()


def _current_programs(clerk_id: str, row: dict, athlete: Optional[dict]):
    """The saved list only if it was built from today's facts (e.g. not a since-dropped 2011
    grad year, or older drill results). Otherwise None: the athlete sees "not built" and rebuilds."""
    saved = row.get("programs")
    profile = store.profile(clerk_id) if saved is not None else None
    if profile is None:
        return None
    if athlete is None:
        # ponytail: GMTM unreadable right now, so drills are unknown; keep showing the saved list
        # (its reasons were written from plausible facts) instead of a false "not built".
        return saved
    facts = athlete_facts(profile, athlete["drills"])
    return saved if row.get("inputs_key") == _inputs_key(facts, rank(facts["state"])) else None


def list_colleges(clerk_id: str, caller_id: str = Depends(require_identity)):
    _owner(clerk_id, caller_id)
    row = _identity(clerk_id, refresh=False)
    if row.get("gmtm_gender") != FEMALE:
        return _not_eligible()
    athlete = _athlete(clerk_id)
    return _listing(_current_programs(clerk_id, row, athlete), athlete, _marks(clerk_id))


BUILDS_PER_HOUR, DRAFTS_PER_HOUR, MARKS_PER_HOUR = 5, 10, 200
TOO_MANY = "You've done this a lot in the last hour. Take a break and try again later."


def _limit(kind: str, clerk_id: str, calls: int) -> None:
    # ponytail: per-process memory (auth.rate_limit); one replica in the pilot. Shared store if it scales out.
    if not auth.rate_limit(f"colleges:{kind}:{clerk_id}", calls, 3600):
        raise HTTPException(429, TOO_MANY)


def build_colleges(clerk_id: str, caller_id: str = Depends(require_identity)):
    _owner(clerk_id, caller_id)
    _limit("build", clerk_id, BUILDS_PER_HOUR)
    row = _identity(clerk_id, refresh=True)
    if row.get("gmtm_gender") != FEMALE:
        return _not_eligible()
    profile = store.profile(clerk_id)
    if profile is None:
        raise HTTPException(404, "Your profile is not ready yet. Open SPARQ from GMTM again.")
    athlete = _athlete(clerk_id)
    # GMTM down: build without drills; the key differs, so the next build after GMTM is back redoes the reasons.
    facts = athlete_facts(profile, (athlete or {}).get("drills"))
    chosen = rank(facts["state"])
    key = _inputs_key(facts, chosen)
    saved = row.get("programs")
    marks = _marks(clerk_id)
    # Cache per athlete: same inputs (and data file) means no new model call. A missing reason is final.
    if row.get("inputs_key") == key and saved:
        return _listing(saved, athlete, marks)
    reasons = explain(facts, chosen)
    items = [{"id": p["id"], "reason": reasons.get(p["id"])} for p in chosen]
    store.save_list(clerk_id, key, items)
    return _listing(items, athlete, marks)


def saved_colleges(clerk_id: str, caller_id: str = Depends(require_identity)):
    """Everything Home needs for the journey: list built, how many found, saved programs, sent count."""
    _owner(clerk_id, caller_id)
    row = _identity(clerk_id, refresh=False)
    if row.get("gmtm_gender") != FEMALE:
        return {**_not_eligible(), "found": 0, "saved": []}
    athlete = _athlete(clerk_id)
    marks = _marks(clerk_id)
    current = _current_programs(clerk_id, row, athlete)
    saved = sorted(((program(pid), at) for pid, at in marks[0].items() if program(pid)), key=lambda x: x[1], reverse=True)
    return {"eligible": True, "notice": None, "built": current is not None,
            "found": len([i for i in current or [] if isinstance(i, dict) and program(i.get("id"))][:MAX_SHOWN]),
            "saved": [card(p, None, (athlete or {}).get("origin"), marks) for p, _ in saved],
            "saved_count": len(saved), "sent_count": sum(1 for pid in marks[1] if program(pid)),
            "origin": _origin_view(athlete)}


class SaveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    saved: StrictBool


class SentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sent: StrictBool


def _listed_program(clerk_id: str, program_id: str, turning_on: bool) -> dict:
    """Turning a mark ON needs the program in her current built list (409 not built, 404 not listed).
    Turning it off is always allowed, so a mark from an older list can still be cleared."""
    row, p = _eligible_program(clerk_id, program_id)
    if turning_on:
        current = _current_programs(clerk_id, row, _athlete(clerk_id))
        if current is None:
            raise HTTPException(409, "Find your colleges first.")
        if p["id"] not in {i.get("id") for i in current if isinstance(i, dict)}:
            raise HTTPException(404, "This college is not in your list.")
    return p


def save_college(program_id: str, body: SaveBody, clerk_id: str = Depends(owner_id)):
    """Heart on or off. Idempotent; saving twice keeps the first time."""
    _limit("mark", clerk_id, MARKS_PER_HOUR)
    p = _listed_program(clerk_id, program_id, body.saved)
    store.set_mark("sparq_saved_colleges", clerk_id, p["id"], body.saved)
    return {"program_id": p["id"], "saved": body.saved}


QUESTIONNAIRE = "[QUESTIONNAIRE_LINK]"
# Junior path only; the legacy prompt in outreach_draft is unchanged. The shared
# user message (first name only, program facts, no addressee) is still used.
JUNIOR_DRAFT_SYSTEM = f"""You draft a short first email from a high-school flag football athlete (age 13-17) to a college women's flag football program.

Respond with ONLY valid JSON, no preamble or code fences:
{{"subject": "<short subject: grad year (only if given) + position + flag football>", "body": "<100-180 words, plain text, \\n\\n between paragraphs>"}}

Rules:
- Start the body with "Hello Coach," and never name a coach. You do not know any coach's name.
- Use only the facts given: the athlete's first name, sport, position, grad year, state and combine metrics, and the program's school, state, level, conference and notes.
- If class_year is null, never mention a grad year, class year or graduation year in the subject or body.
- Never write an email address, a phone number, a web link, a social media handle or a film link.
- Never ask for a phone call, video call, campus visit or meeting.
- Include one plain sentence that the athlete understands coaches may not be able to reply yet because of recruiting contact rules.
- If recruit_questionnaire is "available", say the athlete will fill out the program's recruit questionnaire and put the exact text {QUESTIONNAIRE} on its own line where the link goes. Otherwise do not mention a questionnaire.
- Never invent scholarships, records, rankings, rosters or recruiting interest. Never say "verified" or "recruited".
- Sign with the athlete's first name only."""
_PHONE = re.compile(r"\(?\b\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
_NAMED_COACH = re.compile(r"\bCoach [A-Z][a-z]")
_GRAD_YEAR = re.compile(r"(?i)\b(?:class of|grad(?:uate|uating|uation)?(?: year| in)?)\s*(?:[a-z]+\s+)?['\u2018\u2019]?\d{2,4}\b"
                        r"|\b(?:19|20)\d{2}\s*grad|['\u2018\u2019]\d{2}\b")
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


def year_is_clean(text: str, grad_year, facts_text: str) -> bool:
    """A draft may name only the known grad year or a year in the program facts.
    With no known grad year it may not mention a class/grad year in any form."""
    allowed = set(_YEAR.findall(facts_text)) | ({str(grad_year)} if grad_year else set())
    if any(year not in allowed for year in _YEAR.findall(text)):
        return False
    return grad_year is not None or not _GRAD_YEAR.search(text)


def draft_is_clean(text: str) -> bool:
    """Reject a model draft with an invented contact, link or coach name."""
    return "@" not in text and "http" not in text.lower() and "www." not in text.lower() \
        and not _PHONE.search(text) and not _NAMED_COACH.search(text)


def _eligible_program(clerk_id: str, program_id: str) -> tuple[dict, dict]:
    row = _identity(clerk_id, refresh=False)
    if row.get("gmtm_gender") != FEMALE:
        raise HTTPException(403, NOT_ELIGIBLE)
    p = program(program_id)
    if p is None:
        raise HTTPException(404, "Program not found.")
    return row, p


def college_detail(clerk_id: str, program_id: str, caller_id: str = Depends(require_identity)):
    _owner(clerk_id, caller_id)
    row, p = _eligible_program(clerk_id, program_id)
    athlete = _athlete(clerk_id)
    reason = next((i.get("reason") for i in _current_programs(clerk_id, row, athlete) or [] if isinstance(i, dict) and i.get("id") == p["id"]), None)
    return {"program": card(p, reason, (athlete or {}).get("origin"), _marks(clerk_id)),
            "contact_rules": contact_rules([p["governing_body"]])}


def _draft_view(draft) -> dict:
    if not draft:
        return {"draft": None}
    payload = draft["payload"] if isinstance(draft["payload"], dict) else {}
    return {"draft": {"id": draft["id"], "to_email": "", "school": payload.get("school"),
                      "subject": payload.get("subject") or "", "body": payload.get("body") or ""}}


def _college_facts(p: dict) -> dict:
    return {"college_name": p["school"], "state": p["state"], "division": LEVELS[p["governing_body"]],
            "conference": p.get("conference"), "notes": p.get("notes"),
            "recruit_questionnaire": "available" if https(p.get("questionnaire_url")) else "not available"}


def get_outreach_draft(clerk_id: str, program_id: str, caller_id: str = Depends(require_identity)):
    _owner(clerk_id, caller_id)
    _, p = _eligible_program(clerk_id, program_id)
    draft = store.latest_draft(clerk_id, p["id"])
    payload = draft["payload"] if draft and isinstance(draft.get("payload"), dict) else {}
    profile = store.profile(clerk_id) if draft else None
    grad_year = athlete_facts(profile)["grad_year"] if profile else None
    # An older draft written with a stale year (e.g. "Class of 2011") is not shown again.
    if draft and not year_is_clean(f"{payload.get('subject') or ''}\n{payload.get('body') or ''}", grad_year,
                                   json.dumps(_college_facts(p), default=str)):
        return {"draft": None}
    return _draft_view(draft)


def create_outreach_draft(clerk_id: str, program_id: str, caller_id: str = Depends(require_identity)):
    _owner(clerk_id, caller_id)
    row, p = _eligible_program(clerk_id, program_id)
    profile = store.profile(clerk_id)
    if profile is None:
        raise HTTPException(404, "Your profile is not ready yet. Open SPARQ from GMTM again.")
    facts = athlete_facts(profile, (_athlete(clerk_id) or {}).get("drills"))
    sport = row.get("gmtm_sport")
    # GMTM's generic "All Sports" says nothing; the draft is about flag football anyway.
    sport = None if not sport or str(sport).strip().casefold() == "all sports" else sport
    athlete = {"name": profile.get("name"), "sport": sport, "position": facts["position"],
               "class_year": facts["grad_year"], "state": facts["state"], "combine_metrics": facts["drill_results"]}
    questionnaire = https(p.get("questionnaire_url"))
    college = _college_facts(p)
    _limit("draft", clerk_id, DRAFTS_PER_HOUR)
    # The data has no coach names or addresses: To stays empty and no coach is named.
    try:
        parsed = model_json(JUNIOR_DRAFT_SYSTEM, outreach_draft.user_message(athlete, college, "", ""), 2048)
    except Exception:
        parsed = None
    subject = parsed.get("subject") if isinstance(parsed, dict) else None
    body = parsed.get("body") if isinstance(parsed, dict) else None
    if not isinstance(body, str) or not body.strip() or not isinstance(subject, str) or not draft_is_clean(subject + "\n" + body) \
            or not year_is_clean(subject + "\n" + body, facts["grad_year"], json.dumps(college, default=str)):
        raise HTTPException(502, "We could not write a draft right now. Try again.")
    # The real questionnaire link is added here, never written by the model.
    body = body.replace(QUESTIONNAIRE, questionnaire) if questionnaire else body.replace(QUESTIONNAIRE, "")
    payload = {"to_name": "Head coach", "to_email": "", "school": p["school"],
               "subject": subject.strip()[:200], "body": body.strip()[:4000], "program_id": p["id"]}
    sources = [{"label": f"{p['school']} program facts ({card(p)['source_checked']})",
                "url": card(p)["program_link"] or next(iter(card(p)["source_links"]), None)}]
    artifact_id = store.insert_draft(clerk_id, f"Outreach draft: {p['school']}", payload["subject"] or p["school"], payload, sources)
    return _draft_view({"id": artifact_id, "payload": payload})


def mark_sent(program_id: str, body: SentBody, clerk_id: str = Depends(owner_id)):
    """"I sent it" for one program: a timestamp only, never the email text. Needs a SPARQ draft first."""
    _limit("mark", clerk_id, MARKS_PER_HOUR)
    p = _listed_program(clerk_id, program_id, body.sent)
    if body.sent and not store.latest_draft(clerk_id, p["id"]):
        raise HTTPException(409, "Write a draft for this college first.")
    store.set_mark("sparq_sent_emails", clerk_id, p["id"], body.sent)
    return {"program_id": p["id"], "sent_at": _iso(_marks(clerk_id)[1].get(p["id"]))}
