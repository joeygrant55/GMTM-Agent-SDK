"""
Enrichment Worker - runs after onboarding to research each college in parallel.
Uses raw anthropic SDK + asyncio.gather for true parallelism (no claude CLI required).
"""

import asyncio
import json
import os
import re
from typing import Dict, List, Optional

import anthropic
import pymysql
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env"))
load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def _get_agent_db():
    return pymysql.connect(
        host=os.environ.get("AGENT_DB_HOST", "localhost"),
        user=os.environ.get("AGENT_DB_USER", "root"),
        password=os.environ.get("AGENT_DB_PASSWORD", ""),
        database=os.environ.get("AGENT_DB_NAME", "railway"),
        port=int(os.environ.get("AGENT_DB_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor,
    )


def _get_college_targets(sparq_profile_id: int) -> List[Dict]:
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT id, college_name, college_city, college_state, division FROM college_targets WHERE sparq_profile_id = %s",
                (sparq_profile_id,),
            )
            return c.fetchall()
    finally:
        db.close()


def _store_research(college_target_id: int, research: Dict):
    """Write enriched fit_reasons back to college_targets."""
    db = _get_agent_db()
    try:
        reasons = []
        if research.get("fit_summary"):
            reasons.append(research["fit_summary"])
        if research.get("coach_name"):
            reasons.append(f"Head coach: {research['coach_name']}")
        if research.get("position_coach"):
            reasons.append(f"Position coach: {research['position_coach']}")
        if research.get("position_needs_2026"):
            reasons.append(f"2026 needs: {research['position_needs_2026']}")
        if research.get("recent_offer_activity"):
            reasons.append(research["recent_offer_activity"])

        with db.cursor() as c:
            c.execute(
                "UPDATE college_targets SET fit_reasons = %s WHERE id = %s",
                (json.dumps(reasons), college_target_id),
            )
        db.commit()
        print(f"[Enrichment] Stored research for college_target {college_target_id}")
    except Exception as e:
        print(f"[Enrichment] Warning: could not store research for college {college_target_id}: {e}")
    finally:
        db.close()


RESEARCHER_SYSTEM_PROMPT = """You are a college football recruiting researcher.
Research the given college program and return ONLY a valid JSON object — no other text, no markdown.

Required JSON format:
{
  "coach_name": "head coach full name or null",
  "position_coach": "relevant position coach name or null",
  "coaching_philosophy": "1-2 sentence summary",
  "position_needs_2026": "what positions/profiles they are targeting in the 2026 class",
  "recent_offer_activity": "summary of recent scholarship offer patterns",
  "camp_info": "upcoming camps or combines, or null",
  "fit_summary": "2-3 sentence explanation of why this program is a good fit for the athlete"
}

Return ONLY the JSON object. No markdown, no code fences, no explanation.
"""

WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
}


def _extract_json(text: str) -> Optional[Dict]:
    """Extract first valid JSON object from text."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try to find a JSON object in the text
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


async def _research_one_college(
    client: anthropic.AsyncAnthropic,
    college: Dict,
    athlete_position: str,
    athlete_state: str,
) -> Optional[Dict]:
    """Research a single college program using Anthropic web_search tool."""
    college_name = college["college_name"]
    division = college.get("division", "")
    city = college.get("college_city", "")
    state = college.get("college_state", "")

    user_prompt = (
        f"Research {college_name} ({division}, {city}, {state}) football program. "
        f"I'm looking for information relevant to a {athlete_position} recruit from {athlete_state}, Class of 2026. "
        "Find: head coach, position coach for this position, coaching philosophy, 2026 recruiting needs, "
        "recent offer activity, any upcoming camps, and why this program fits the athlete. "
        "Return your findings as JSON only."
    )

    try:
        # web_search_20260209 is fully server-side — single API call handles search + response
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=RESEARCHER_SYSTEM_PROMPT,
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": user_prompt}],
        )

        for block in response.content:
            if hasattr(block, "text"):
                result = _extract_json(block.text)
                if result:
                    return result

        print(f"[Enrichment] No valid JSON from researcher for {college_name}")

    except Exception as e:
        print(f"[Enrichment] Error researching {college_name}: {e}")

    return None


async def enrich_college_targets(sparq_profile_id: int, athlete_position: str, athlete_state: str):
    """
    Background job: research each college using parallel async calls.
    Called fire-and-forget from profile_api after onboarding.
    """
    colleges = _get_college_targets(sparq_profile_id)
    if not colleges:
        print(f"[Enrichment] No college targets found for profile {sparq_profile_id}")
        return

    print(f"[Enrichment] Researching {len(colleges)} colleges for profile {sparq_profile_id} ({athlete_position} from {athlete_state})...")

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Run all college researchers in parallel
    tasks = [
        _research_one_college(client, college, athlete_position, athlete_state)
        for college in colleges
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    stored = 0
    for college, result in zip(colleges, results):
        if isinstance(result, Exception):
            print(f"[Enrichment] Exception for {college['college_name']}: {result}")
            continue
        if result:
            _store_research(college["id"], result)
            stored += 1

    print(f"[Enrichment] Complete — enriched {stored}/{len(colleges)} colleges for profile {sparq_profile_id}")
    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute(
                "UPDATE sparq_profiles SET enrichment_complete = 1 WHERE id = %s",
                (sparq_profile_id,),
            )
        db.commit()
    finally:
        db.close()
