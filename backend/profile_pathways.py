"""Reviewed public pathway facts, not a live opportunity search or eligibility check.

No network, model, database or environment access. A reviewer must refresh the
facts and review dates together; extending the date alone is not a review.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone


CHECKED_AT = "2026-09-08T22:51:00Z"
EXPIRES_AT = datetime(2026, 10, 8, 22, 51, tzinfo=timezone.utc)


class PathwayExpired(ValueError):
    """Official facts need a new source review before national-team advice."""


_REFERENCES = (
    {
        "id": "o1", "kind": "official", "label": "USA Football digital-combine process",
        "detail": (
            "USA Football describes the digital combine as a route for submitting measurements and film "
            "for evaluation. Submission does not guarantee an invitation. Its published FAQ requires an "
            "Athlete ID for consideration. This page does not establish whether this athlete was reviewed, "
            "selected, invited, or holds a current Athlete ID. A complete 2027 selection schedule is not confirmed."
        ),
        "href": "https://www.usafootball.com/national-team/digital-combine", "checked_at": CHECKED_AT,
    },
    {
        "id": "o2", "kind": "official", "label": "USA Football official support",
        "detail": (
            "USA Football publishes general support and Help Desk routes on its contact page. "
            "An athlete can ask where dates for their adult combine cycle are published and how invitations "
            "are communicated. This is a general support route, not a recruiting introduction or a promise of review."
        ),
        "href": "https://www.usafootball.com/contact-us", "checked_at": CHECKED_AT,
    },
    {
        "id": "o3", "kind": "official", "label": "USA Football development resources",
        "detail": (
            "USA Football's app page describes drills, training resources and alerts. The athlete can choose "
            "a skill to work on using those resources. These are development resources, not individual "
            "selection benchmarks or a diagnosis of this athlete's film."
        ),
        "href": "https://usafootball.com/resources/app", "checked_at": CHECKED_AT,
    },
    {
        "id": "o4", "kind": "official", "label": "Adult Talent ID pathway — dates need confirmation",
        "detail": (
            "USA Football describes adult Talent ID Camps as an instruction and evaluation pathway. "
            "All dated camps visible at the September 8 review were in the past. No upcoming adult camp "
            "or 2027 Trials date was verified. Do not recommend registration for a past camp or treat "
            "junior and invitation-only events as open adult opportunities."
        ),
        "href": "https://usafootball.com/national-team/adult-talent-id-camp", "checked_at": CHECKED_AT,
    },
)

_LOCAL_ACTIONS = (
    {"id": "prepare_summary", "kind": "prepare_summary", "label": "Prepare my profile summary",
     "href": None, "source_ref": None},
    {"id": "prepare_introduction", "kind": "prepare_introduction", "label": "Prepare an introduction",
     "href": None, "source_ref": None},
)
_OFFICIAL_ACTIONS = (
    {"id": "usaf_support", "kind": "open_source", "label": "Check the official support route",
     "href": "https://www.usafootball.com/contact-us", "source_ref": "o2"},
    {"id": "usaf_development", "kind": "open_source", "label": "Explore USA Football development resources",
     "href": "https://usafootball.com/resources/app", "source_ref": "o3"},
)


def pathway_bundle(track: str, now: datetime | None = None) -> dict:
    if track not in ("national_team", "profile", "outreach"):
        raise ValueError("Unsupported debrief track")
    if track != "national_team":
        return {"references": [], "actions": deepcopy(list(_LOCAL_ACTIONS))}
    current = now if now is not None else datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("Source review clock must include a timezone")
    if current >= EXPIRES_AT or current < datetime.fromisoformat(CHECKED_AT.replace("Z", "+00:00")):
        raise PathwayExpired("USA Football sources need a fresh review. You can still ask about your profile or prepare an introduction.")
    return {"references": deepcopy(list(_REFERENCES)),
            "actions": deepcopy([*_LOCAL_ACTIONS, *_OFFICIAL_ACTIONS])}
