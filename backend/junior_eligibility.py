"""Junior pilot eligibility: pure decision plus an injectable read-only GMTM reader.

Eligible iff the GMTM user is on the explicit test allow-list, or the user has at
least one submission to the junior events and a date of birth that gives age
13..17 today. Unknown DOB, under 13 and 18+ are ineligible. Nothing here writes;
the decision never returns or stores the date of birth.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
import os
import time

JUNIOR_EVENT_IDS = (1305, 1314, 1317)
MIN_AGE, MAX_AGE = 13, 17
CACHE_SECONDS = 600


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def allowlist(env: Mapping[str, str]) -> frozenset[int]:
    ids = set()
    for part in env.get("SPARQ_TEST_ALLOWLIST", "").split(","):
        part = part.strip()
        if part.isascii() and part.isdecimal() and int(part) > 0:
            ids.add(int(part))
    return frozenset(ids)


def decide(user_id: int, *, allowed: frozenset[int], cohort_member: bool, dob, today: date) -> bool:
    """Pure decision. ``dob`` may be a date, datetime or None."""
    if type(user_id) is not int or user_id <= 0:
        return False
    if user_id in allowed:
        return True
    if not cohort_member or dob is None:
        return False
    if isinstance(dob, datetime):
        dob = dob.date()
    if not isinstance(dob, date) or dob > today:
        return False
    return MIN_AGE <= age_on(dob, today) <= MAX_AGE


def read_gmtm_facts(user_id: int) -> tuple[bool, object]:
    """Read-only GMTM lookup: (has junior-event submission, dob). SELECTs only."""
    from profile_api import _get_gmtm_db  # lazy: existing gmtmread connector pattern
    db = _get_gmtm_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT 1 AS hit FROM event_task_submissions s "
                "JOIN event_tasks t ON t.task_id = s.task_id "
                "WHERE s.user_id = %s AND t.event_id IN (%s, %s, %s) LIMIT 1",
                (user_id, *JUNIOR_EVENT_IDS),
            )
            member = c.fetchone() is not None
            c.execute("SELECT dob FROM users WHERE user_id = %s", (user_id,))
            row = c.fetchone()
        return member, (row or {}).get("dob")
    finally:
        db.close()


# Injectable for tests; production uses the read-only GMTM connector.
reader = read_gmtm_facts


def is_eligible(user_id: int, *, env: Mapping[str, str] | None = None, today: date | None = None) -> bool:
    env = os.environ if env is None else env
    allowed = allowlist(env)
    if user_id in allowed:
        return True  # no GMTM read needed for explicit testers
    member, dob = reader(user_id)
    return decide(user_id, allowed=allowed, cohort_member=member, dob=dob, today=today or date.today())


# ponytail: per-process cache; a multi-instance deploy re-checks per instance (still <= 10 min stale).
_cache: dict[int, tuple[bool, float]] = {}


def is_eligible_cached(user_id: int, *, now: float | None = None) -> bool:
    now = time.monotonic() if now is None else now
    hit = _cache.get(user_id)
    if hit is not None and now - hit[1] < CACHE_SECONDS:
        return hit[0]
    result = is_eligible(user_id)
    _cache[user_id] = (result, now)
    return result
