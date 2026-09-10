"""Reviewed public source records, never athlete data or generated recommendations.

Records expire and are rechecked before use. Import does not fetch or call AI.
"""

CHECKED = "2026-09-10T16:30:06Z"
EXPIRES = "2026-09-17T16:30:06Z"
DIGITAL = "https://www.usafootball.com/national-team/digital-combine"
CONTACT = "https://usafootball.com/national-team"
GMTM_COMBINE = "https://gmtm.com/virtuals/1318/2027-u-s-flag-national-team-adult-digital-combine-2"

# Field-by-field evidence and excluded stale/test sources:
# docs/research/athlete-opportunities-2026-09-10.md. Review expiry is SPARQ's
# internal freshness policy; it is never presented as an organizer's deadline.
RECORDS = (
    {
        "id": "usaf-adult-digital-combine-2-2027", "title": "Adult Flag Digital Combine 2",
        "organization": "USA Football", "kind": "assessment", "format": "remote",
        "categories": ["men", "women"], "status": "check_details",
        "summary": "Review the published evaluation window and requirements. Already participating? Use the official details without starting another submission.",
        "valid_until": EXPIRES, "opens_at": None,
        # Conservative internal withdrawal, not a claim about the missing timezone.
        "closes_at": "2026-09-21T00:00:00Z",
        "facts": [
            {"key": "dates", "label": "Published window", "value": "Aug 10–Sep 21, 2026. The linked adult combine names the 2027 cycle. Cutoff time and timezone are not published.", "source_ids": ["schedule", "entry"]},
            {"key": "location", "label": "Location", "value": "Remote participation across the United States.", "source_ids": ["schedule"]},
            {"key": "cost", "label": "Published cost", "value": "Combine registration: free. Required Adult Athlete ID: $39.50.", "source_ids": ["schedule"]},
            {"key": "eligibility", "label": "Requirements", "value": "Age 18+ by December 31, 2027 and a valid Athlete ID. Confirm the applicable cycle and your eligibility with USA Football.", "source_ids": ["schedule"]},
            {"key": "contact", "label": "Contact", "value": None, "source_ids": []},
        ],
        "action": {"kind": "open_source", "label": "View official details", "href": DIGITAL,
                   "recipient": None, "purpose": None, "source_ids": ["schedule"]},
        "sources": [
            {"id": "schedule", "title": "USA Football digital combines — schedule and requirements", "url": DIGITAL, "checked_at": CHECKED, "expires_at": EXPIRES},
            {"id": "entry", "title": "Official adult combine link on GMTM", "url": GMTM_COMBINE, "checked_at": CHECKED, "expires_at": EXPIRES},
        ],
    },
    {
        "id": "usaf-high-performance-inquiry", "title": "Ask about your next evaluation",
        "organization": "USA Football High Performance", "kind": "contact", "format": "remote",
        "categories": ["men", "women"], "status": "published_route",
        "summary": "Prepare a focused question for the publicly listed High Performance department about upcoming adult evaluations and requirements.",
        "valid_until": EXPIRES, "opens_at": None, "closes_at": None,
        "facts": [
            {"key": "dates", "label": "Dates", "value": None, "source_ids": []},
            {"key": "location", "label": "Location", "value": None, "source_ids": []},
            {"key": "cost", "label": "Cost", "value": None, "source_ids": []},
            {"key": "eligibility", "label": "Requirements", "value": None, "source_ids": []},
            {"key": "contact", "label": "Public program contact", "value": "teamusa@usafootball.com — High Performance department. No named recipient or response time is published.", "source_ids": ["contact"]},
        ],
        "action": {"kind": "prepare_introduction", "label": "Prepare introduction", "href": CONTACT,
                   "recipient": "USA Football High Performance",
                   "purpose": "Could you clarify the next adult flag evaluation dates, any in-person opportunities, and the requirements for the applicable national-team cycle?",
                   "source_ids": ["contact"]},
        "sources": [{"id": "contact", "title": "USA Football national team — High Performance contact", "url": CONTACT, "checked_at": CHECKED, "expires_at": EXPIRES}],
    },
)
