"""
Combine results for an athlete, built from real GMTM rows.

Source priority:
  1. `metrics` rows with `event_id` set (digital combines write these since 2026).
  2. Fallback: parse `event_task_submissions.payload` for events with submissions but no metrics.

Every result carries a trust tier and three ranks (in-event, all-time same drill, same-org).
Titles in GMTM are inconsistent per event ("Shuttle" vs "5-10-5 shuttle", "60 Yard" vs
"60 Yard Shuttle", a 20-yard dash stored as "20 Yard Shuttle"), so drills are canonicalized
here. `metrics.value` is a varchar(25) with junk ('.', '100' for a 40-time), so values are
parsed and range-checked.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from typing import Callable, Iterable, Optional

# ── Canonical drills ─────────────────────────────────────────────────────────
# titles: every GMTM `metrics.title` spelling seen for this drill.
# event_only_titles: aliases that are only trusted when the row has an event_id
#   ("20 Yard Shuttle" is what older USA Football templates called the 20-yard dash).
# lo/hi: sanity range; anything outside is dropped as data entry junk.
CANONICAL_DRILLS: dict[str, dict] = {
    "20-Yard Dash": dict(
        titles={"20 Yard Dash"}, event_only_titles={"20 Yard Shuttle"},
        unit="seconds", ideal="lower", lo=1.8, hi=6.0,
        task_titles={"20-yard dash"},
    ),
    "5-10-5 Shuttle": dict(
        titles={"5-10-5 shuttle", "5-10-5 Shuttle", "Shuttle"}, event_only_titles=set(),
        unit="seconds", ideal="lower", lo=3.0, hi=9.0,
        task_titles={"5-10-5 shuttle run", "5-10-5 shuttle"},
    ),
    "60-Yard Shuttle": dict(
        titles={"60 Yard Shuttle", "60 Yard"}, event_only_titles=set(),
        unit="seconds", ideal="lower", lo=8.0, hi=25.0,
        task_titles={"60-yard shuttle", "60 yard shuttle"},
    ),
    "Standing Broad Jump": dict(
        titles={"Broad Jump", "Standing Broad Jump"}, event_only_titles=set(),
        unit="inches", ideal="higher", lo=30.0, hi=160.0,
        task_titles={"standing broad jump", "broad jump"},
    ),
    "Max Push-Ups": dict(
        titles={"Push Ups", "Push ups"}, event_only_titles=set(),
        unit="repetitions", ideal="higher", lo=1.0, hi=400.0,
        task_titles={"max. push-ups", "max push-ups", "push-ups", "push ups"},
    ),
    "Max Sit-Ups": dict(
        titles={"Sit Ups", "Sit ups"}, event_only_titles=set(),
        unit="repetitions", ideal="higher", lo=1.0, hi=400.0,
        task_titles={"max. sit ups", "max. situps (copy)", "max sit-ups", "sit ups", "sit-ups"},
    ),
    "40-Yard Dash": dict(
        titles={"40 Yard Dash"}, event_only_titles=set(),
        unit="seconds", ideal="lower", lo=3.8, hi=8.0,
        task_titles={"40-yard dash", "40 yard dash"},
    ),
    "Vertical Jump": dict(
        titles={"Vertical Jump"}, event_only_titles=set(),
        unit="inches", ideal="higher", lo=8.0, hi=60.0,
        task_titles={"vertical jump"},
    ),
}

_TITLE_INDEX: dict[str, str] = {}
_EVENT_ONLY_INDEX: dict[str, str] = {}
_TASK_INDEX: dict[str, str] = {}
for _drill, _d in CANONICAL_DRILLS.items():
    for _t in _d["titles"]:
        _TITLE_INDEX[_t.lower()] = _drill
    for _t in _d["event_only_titles"]:
        _EVENT_ONLY_INDEX[_t.lower()] = _drill
    for _t in _d["task_titles"]:
        _TASK_INDEX[_t] = _drill

CDN = "https://cdn.gmtm.com/"


def canonical_drill(title: Optional[str], has_event: bool) -> Optional[str]:
    """Map a GMTM metrics.title to a canonical drill name, or None if not a tracked drill."""
    if not title:
        return None
    key = title.strip().lower()
    if key in _TITLE_INDEX:
        return _TITLE_INDEX[key]
    if has_event and key in _EVENT_ONLY_INDEX:
        return _EVENT_ONLY_INDEX[key]
    return None


def canonical_drill_from_task(task_title: Optional[str]) -> Optional[str]:
    if not task_title:
        return None
    return _TASK_INDEX.get(task_title.strip().lower())


def parse_value(raw, drill: str) -> Optional[float]:
    """Parse metrics.value (varchar) into a float inside the drill's sanity range."""
    if raw is None:
        return None
    try:
        v = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    d = CANONICAL_DRILLS[drill]
    if v < d["lo"] or v > d["hi"]:
        return None
    return v


def better(a: float, b: float, ideal: str) -> float:
    return min(a, b) if ideal == "lower" else max(a, b)


def percentile_better_than(value: float, pool: Iterable[float], ideal: str) -> Optional[float]:
    """Share of the pool this value beats, 0..100. None if the pool is empty."""
    pool = list(pool)
    if not pool:
        return None
    if ideal == "lower":
        beaten = sum(1 for p in pool if p > value)
    else:
        beaten = sum(1 for p in pool if p < value)
    return round(100.0 * beaten / len(pool), 1)


def rank_in(value: float, pool: Iterable[float], ideal: str) -> int:
    """1-based rank of value in pool (pool should include the value itself)."""
    pool = list(pool)
    if ideal == "lower":
        return 1 + sum(1 for p in pool if p < value)
    return 1 + sum(1 for p in pool if p > value)


@dataclass
class CombineResult:
    event_id: int
    event_name: str
    organization: Optional[str]
    drill: str
    value: float
    unit: str
    ideal: str
    video_uri: Optional[str]
    submitted_on: Optional[str]
    trust_tier: str
    rank_in_event: Optional[int]
    event_pool_size: Optional[int]
    pct_flag_all_time: Optional[float]
    pool_size_all_time: Optional[int]
    pct_same_org: Optional[float]
    pool_size_same_org: Optional[int]
    source: str  # "metrics" | "submission"


# ── Tiny in-process TTL cache (pools are the expensive part) ────────────────
_CACHE: dict[str, tuple[float, object]] = {}
_TTL = 600.0


def _cached(key: str, fn: Callable[[], object]):
    now = time.time()
    hit = _CACHE.get(key)
    if hit and hit[0] > now:
        return hit[1]
    val = fn()
    _CACHE[key] = (now + _TTL, val)
    return val


def clear_cache() -> None:
    _CACHE.clear()


# ── DB access ────────────────────────────────────────────────────────────────
def _fetch_athlete_event_metrics(cur, user_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT m.event_id, e.name AS event_name, o.name AS organization, e.organization_id,
               m.title, m.value, m.unit, m.created_on, m.in_person_event_id
        FROM metrics m
        JOIN events e ON e.event_id = m.event_id
        LEFT JOIN organizations o ON o.organization_id = e.organization_id
        WHERE m.user_id = %s AND m.event_id IS NOT NULL
        """,
        (user_id,),
    )
    return list(cur.fetchall())


def _fetch_athlete_submissions(cur, user_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT t.event_id, e.name AS event_name, o.name AS organization, e.organization_id,
               t.title AS task_title, s.payload, s.video_uri, s.created_on
        FROM event_task_submissions s
        JOIN event_tasks t ON t.task_id = s.task_id
        JOIN events e ON e.event_id = t.event_id
        LEFT JOIN organizations o ON o.organization_id = e.organization_id
        WHERE s.user_id = %s AND t.type = 2
        """,
        (user_id,),
    )
    return list(cur.fetchall())


def _best_per_user_in_event(cur, event_id: int, drill: str) -> dict[int, float]:
    d = CANONICAL_DRILLS[drill]
    titles = list(d["titles"] | d["event_only_titles"])
    ph = ",".join(["%s"] * len(titles))
    cur.execute(
        f"SELECT user_id, value FROM metrics WHERE event_id = %s AND title IN ({ph})",
        (event_id, *titles),
    )
    return _best_map(cur.fetchall(), drill)


def _best_per_user_all_time(cur, drill: str) -> dict[int, float]:
    d = CANONICAL_DRILLS[drill]
    titles = list(d["titles"])  # aliases are event-only; excluded from the global pool
    ph = ",".join(["%s"] * len(titles))
    cur.execute(
        f"SELECT user_id, value FROM metrics WHERE title IN ({ph}) AND is_current = 1",
        tuple(titles),
    )
    return _best_map(cur.fetchall(), drill)


def _best_per_user_same_org(cur, organization_name: str, drill: str) -> dict[int, float]:
    d = CANONICAL_DRILLS[drill]
    titles = list(d["titles"] | d["event_only_titles"])
    ph = ",".join(["%s"] * len(titles))
    cur.execute(
        f"""
        SELECT m.user_id, m.value
        FROM metrics m JOIN events e ON e.event_id = m.event_id
        JOIN organizations o ON o.organization_id = e.organization_id
        WHERE o.name = %s AND m.title IN ({ph})
        """,
        (organization_name, *titles),
    )
    return _best_map(cur.fetchall(), drill)


def _best_map(rows, drill: str) -> dict[int, float]:
    ideal = CANONICAL_DRILLS[drill]["ideal"]
    best: dict[int, float] = {}
    for r in rows:
        uid, raw = (r["user_id"], r["value"]) if isinstance(r, dict) else (r[0], r[1])
        v = parse_value(raw, drill)
        if v is None:
            continue
        best[uid] = v if uid not in best else better(best[uid], v, ideal)
    return best


def _videos_by_drill(subs: list[dict], event_id: int) -> dict[str, tuple[Optional[str], Optional[str]]]:
    """drill -> (video_uri, submitted_on) from submission rows for one event."""
    out: dict[str, tuple[Optional[str], Optional[str]]] = {}
    for s in subs:
        if s["event_id"] != event_id:
            continue
        drill = canonical_drill_from_task(s.get("task_title"))
        if not drill:
            continue
        uri = s.get("video_uri")
        if not uri:
            try:
                qs = json.loads(s["payload"]).get("questions", {}) if s.get("payload") else {}
                for k, q in (qs.items() if isinstance(qs, dict) else []):
                    if str(k).startswith("video:") and isinstance(q, dict):
                        uri = (q.get("value") or {}).get("value")
                        if uri:
                            break
            except Exception:
                uri = None
        ts = s.get("created_on")
        out[drill] = (f"{CDN}{uri}" if uri and not str(uri).startswith("http") else uri,
                      ts.isoformat() if hasattr(ts, "isoformat") else (str(ts) if ts else None))
    return out


def _values_from_submissions(subs: list[dict], event_id: int) -> dict[str, float]:
    """Fallback: drill -> best value parsed from submission payload 'metric:*' entries."""
    out: dict[str, float] = {}
    for s in subs:
        if s["event_id"] != event_id or not s.get("payload"):
            continue
        drill = canonical_drill_from_task(s.get("task_title"))
        if not drill:
            continue
        try:
            qs = json.loads(s["payload"]).get("questions", {})
        except Exception:
            continue
        for k, q in (qs.items() if isinstance(qs, dict) else []):
            if not str(k).startswith("metric:") or not isinstance(q, dict):
                continue
            raw = (q.get("value") or {}).get("value")
            v = parse_value(raw, drill)
            if v is None:
                continue
            out[drill] = v if drill not in out else better(out[drill], v, CANONICAL_DRILLS[drill]["ideal"])
    return out


def get_combine_results(user_id: int, connect: Callable[[], object]) -> list[dict]:
    """
    Build the athlete's combine results. `connect` returns a pymysql connection with DictCursor
    to the GMTM database (read-only). Returns a list of CombineResult dicts, newest event first.
    """
    db = connect()
    try:
        with db.cursor() as cur:
            rows = _fetch_athlete_event_metrics(cur, user_id)
            subs = _fetch_athlete_submissions(cur, user_id)

            # 1. metrics rows → best per (event, drill)
            per_event: dict[int, dict] = {}
            for r in rows:
                drill = canonical_drill(r["title"], has_event=True)
                if not drill:
                    continue
                v = parse_value(r["value"], drill)
                if v is None:
                    continue
                ev = per_event.setdefault(r["event_id"], dict(meta=r, drills={}, source="metrics"))
                cur_v = ev["drills"].get(drill)
                ev["drills"][drill] = v if cur_v is None else better(cur_v, v, CANONICAL_DRILLS[drill]["ideal"])

            # 2. fallback: events with submissions but no metrics rows
            sub_events = {s["event_id"]: s for s in subs}
            for ev_id, s in sub_events.items():
                if ev_id in per_event:
                    continue
                vals = _values_from_submissions(subs, ev_id)
                if vals:
                    per_event[ev_id] = dict(meta=s, drills=vals, source="submission")

            results: list[CombineResult] = []
            for ev_id, ev in per_event.items():
                meta = ev["meta"]
                org = meta.get("organization")
                videos = _videos_by_drill(subs, ev_id)
                trust = "Official In-Person" if meta.get("in_person_event_id") else "Remote App-Captured"
                for drill, v in ev["drills"].items():
                    d = CANONICAL_DRILLS[drill]
                    ev_pool = _cached(f"ev:{ev_id}:{drill}", lambda: _best_per_user_in_event(cur, ev_id, drill))
                    all_pool = _cached(f"all:{drill}", lambda: _best_per_user_all_time(cur, drill))
                    org_pool = (_cached(f"org:{org}:{drill}", lambda: _best_per_user_same_org(cur, org, drill))
                                if org else {})
                    # The event pool comes from metrics rows; a submission-sourced value is not in it.
                    ev_vals = list(ev_pool.values())
                    if user_id not in ev_pool:
                        ev_vals.append(v)
                    video_uri, sub_on = videos.get(drill, (None, None))
                    ts = meta.get("created_on")
                    results.append(CombineResult(
                        event_id=ev_id,
                        event_name=meta.get("event_name") or f"Event {ev_id}",
                        organization=org,
                        drill=drill,
                        value=v,
                        unit=d["unit"],
                        ideal=d["ideal"],
                        video_uri=video_uri,
                        submitted_on=sub_on or (ts.isoformat() if hasattr(ts, "isoformat") else (str(ts) if ts else None)),
                        trust_tier=trust,
                        rank_in_event=rank_in(v, ev_vals, d["ideal"]),
                        event_pool_size=len(ev_vals),
                        pct_flag_all_time=percentile_better_than(v, all_pool.values(), d["ideal"]),
                        pool_size_all_time=len(all_pool) or None,
                        pct_same_org=percentile_better_than(v, org_pool.values(), d["ideal"]) if org_pool else None,
                        pool_size_same_org=len(org_pool) or None,
                        source=ev["source"],
                    ))
    finally:
        try:
            db.close()
        except Exception:
            pass

    results.sort(key=lambda r: (r.event_id, r.drill), reverse=True)
    return [asdict(r) for r in results]


def format_for_prompt(results: list[dict], max_events: int = 2) -> str:
    """One line per drill for the CURRENT ATHLETE PROFILE block, newest `max_events` events only.
    Empty string if none. The dashboard shows the full history; the prompt only needs the recent ones."""
    if not results:
        return ""
    keep_events = []
    for r in results:  # results arrive newest event first
        if r["event_id"] not in keep_events:
            keep_events.append(r["event_id"])
        if len(keep_events) >= max_events:
            break
    shown = [r for r in results if r["event_id"] in keep_events]
    older = len({r["event_id"] for r in results}) - len(keep_events)
    lines = []
    for r in shown:
        unit = "s" if r["unit"] == "seconds" else ('"' if r["unit"] == "inches" else " reps")
        bits = [f"{r['drill']} {r['value']:g}{unit}"]
        if r.get("rank_in_event") and r.get("event_pool_size"):
            bits.append(f"{r['rank_in_event']} of {r['event_pool_size']} in {r['event_name']}")
        if r.get("pct_flag_all_time") is not None and r.get("pool_size_all_time"):
            bits.append(f"beats {r['pct_flag_all_time']:g}% of {r['pool_size_all_time']} GMTM athletes on this drill")
        if r.get("pct_same_org") is not None and r.get("pool_size_same_org") and r.get("organization"):
            bits.append(f"beats {r['pct_same_org']:g}% of {r['pool_size_same_org']} {r['organization']} athletes")
        bits.append(r["trust_tier"].lower())
        if r.get("video_uri"):
            bits.append("video on file")
        lines.append("  - " + ", ".join(bits))
    tail = f"\n  (+{older} older combine{'s' if older != 1 else ''} on record; use query_database for those)" if older > 0 else ""
    return "\n  Combine results (cite the trust tier when advising the athlete to share a number):\n" + "\n".join(lines) + tail
