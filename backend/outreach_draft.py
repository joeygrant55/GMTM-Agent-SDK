"""Outreach draft prompt shared by the legacy artifacts route and the junior colleges route.

No SendGrid, database or model import: the profile (junior) app imports this module
without pulling artifacts_api or email_sender into its process.
"""
from __future__ import annotations

import json
import re
from typing import Optional

DRAFT_OUTREACH_SYSTEM = """You draft a high-quality cold outreach email from a high-school athlete to a college coach.

You will be given the athlete's full profile and the target college's research data. Use both — every email should reference at least one specific detail about the program (recent recruiting, depth chart, position need) and at least one specific stat the athlete has.

Respond with ONLY valid JSON in this exact shape — no preamble, no code fences, no commentary:
{
  "to_name": "Coach <Last Name>",
  "to_email": "<email or empty string if unknown>",
  "school": "<full school name>",
  "subject": "<short, specific subject line — class year + position + the hook>",
  "body": "<150-220 word email body — opens with a specific personal observation about the program, states 1-2 measurable stats, offers one clear next step the coach can take on their own time (film review or the recruiting questionnaire). Sign with the athlete's first name only.>",
  "personalization_notes": ["<3-5 short bullets describing the specific things you used from the program and the athlete to personalize this draft>"]
}

Rules:
- Never invent coach names, emails, or facts. If the position coach name isn't provided, address the head coach. If no email is available, return "" for to_email.
- Body must be one block of plain text with \\n\\n between paragraphs.
- Avoid clichés (\"I am writing to express my interest…\"). Open with a real observation.
- Stay under 220 words in the body.
- The athlete may be a minor. Never ask for a phone call, video call, campus visit or meeting.
- Include one plain sentence that the athlete understands coaches may not be able to reply yet because of recruiting contact rules.
- You only receive the athlete's first name. Never invent a last name, school name, email, phone number or address.
"""


PROFILE_KEYS = ("sport", "position", "class_year", "state", "gpa", "combine_metrics", "stats", "season")


def prompt_profile(profile: dict) -> dict:
    """Minimum needed to write the email: first name only; no last name, school,
    contacts, address, exact birth date or free-text goals reach the model."""
    first_name = (str(profile.get("name") or "").split() or [""])[0]
    return {"first_name": first_name or None, **{key: profile.get(key) for key in PROFILE_KEYS}}


def user_message(profile: dict, college: dict, coach_name: str, coach_email: str) -> str:
    return (
        "ATHLETE PROFILE\n"
        f"{json.dumps(prompt_profile(profile), default=str, indent=2)}\n\n"
        "TARGET PROGRAM\n"
        f"{json.dumps(college, default=str, indent=2)}\n\n"
        "ADDRESSEE\n"
        f"Coach name (if provided, use it; otherwise pick the most appropriate coach from the research): {coach_name or '(none)'}\n"
        f"Coach email (if known): {coach_email or '(none)'}\n"
    )


def strip_code_fences(text: str) -> str:
    if not text:
        return text
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    return text


def parse_json_response(text: str) -> Optional[dict]:
    text = strip_code_fences(text)
    try:
        return json.loads(text)
    except Exception:
        # Last-resort recovery — find the outermost JSON object.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
    return None
