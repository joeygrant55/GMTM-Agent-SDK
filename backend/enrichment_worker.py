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


RESEARCHER_SYSTEM_PROMPT = """You are a college recruiting researcher.
Research the given college program and return ONLY a valid JSON object — no other text, no markdown.

Required JSON format:
{
  "coach_name": "head coach full name or null",
  "position_coach": "relevant position/sport coach name or null",
  "coaching_philosophy": "1-2 sentence summary",
  "position_needs_2026": "what positions/profiles they are targeting for 2026-2027",
  "recent_offer_activity": "summary of recent scholarship offer patterns for this sport",
  "camp_info": "upcoming camps, combines, or showcases, or null",
  "fit_summary": "2-3 specific sentences about why this program fits this athlete's stats, position, and goals"
}

Return ONLY the JSON object. No markdown, no code fences, no explanation.
"""

AI_MATCHING_SYSTEM = """You are a college recruiting analyst. Return ONLY a valid JSON array — no markdown, no explanation.

Each program object must have:
{
  "name": "Full University Name",
  "city": "City",
  "state": "ST",
  "division": "D1" or "D2" or "D3" or "NAIA",
  "fit_summary": "1-2 specific sentences about why this program fits this exact athlete",
  "fit_score": integer 70-95
}

Requirements:
- Programs must actually have the athlete's sport
- Mix of realistic reaches (2-3) and likely fits (5-7)
- Be specific — mention real program strengths, geographic fit, recruiting history
- Return 8-12 programs total as a JSON array only
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


async def ai_match_programs(athlete_profile: Dict) -> List[Dict]:
    """Use Claude + web_search to find programs actually recruiting this athlete's sport/position."""
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    sport = athlete_profile.get("sport") or athlete_profile.get("position") or "Basketball"
    position = athlete_profile.get("position") or ""
    state = athlete_profile.get("state") or ""
    class_year = athlete_profile.get("class_year") or "2026"
    goals = athlete_profile.get("recruiting_goals") or {}
    if isinstance(goals, str):
        try:
            goals = json.loads(goals)
        except Exception:
            goals = {}
    target_level = goals.get("targetLevel", "Open")
    geography = goals.get("geography", "Anywhere")

    stats = athlete_profile.get("maxpreps_stats") or {}
    stats_str = ", ".join(f"{k}: {v}" for k, v in stats.items()) if stats else "stats available in profile"

    user_prompt = (
        f"Find college {sport} programs that would realistically recruit this athlete:\n"
        f"- Sport: {sport}\n"
        f"- Position: {position}\n"
        f"- Class of: {class_year}\n"
        f"- From: {state}\n"
        f"- Key stats: {stats_str}\n"
        f"- Target division: {target_level}\n"
        f"- Geography preference: {geography}\n\n"
        f"Search for {sport} programs actively recruiting {position}s in the {class_year} class. "
        "Include programs where this athlete's stats would be competitive. "
        "Be specific about why each program fits. Return as JSON array only."
    )

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=AI_MATCHING_SYSTEM,
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": user_prompt}],
        )
        for block in response.content:
            if hasattr(block, "text"):
                m = re.search(r"\[.*\]", block.text, re.DOTALL)
                if m:
                    try:
                        programs = json.loads(m.group())
                        if isinstance(programs, list) and len(programs) > 0:
                            print(f"[Matching] AI found {len(programs)} programs for {sport} {position}")
                            return programs
                    except Exception:
                        pass
    except Exception as e:
        print(f"[Matching] AI match failed: {e}")
    return []


async def _research_one_college(
    client: anthropic.AsyncAnthropic,
    college: Dict,
    athlete_position: str,
    athlete_state: str,
    athlete_sport: str = "Basketball",
) -> Optional[Dict]:
    """Research a single college program using Anthropic web_search tool."""
    college_name = college["college_name"]
    division = college.get("division", "")
    city = college.get("college_city", "")
    state = college.get("college_state", "")

    user_prompt = (
        f"Research {college_name} ({division}, {city}, {state}) {athlete_sport} program. "
        f"I'm looking for information relevant to a {athlete_position} {athlete_sport} recruit from {athlete_state}, Class of 2026. "
        f"Find: head coach, {athlete_sport} position coach, coaching philosophy, 2026 recruiting needs for this position, "
        "recent scholarship offer activity, any upcoming camps or showcases, and why this program fits the athlete. "
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


async def enrich_college_targets(sparq_profile_id: int, athlete_position: str, athlete_state: str, athlete_sport: str = "Basketball"):
    """
    Background job: research each college using parallel async calls.
    Called fire-and-forget from profile_api after onboarding.
    """
    colleges = _get_college_targets(sparq_profile_id)
    if not colleges:
        print(f"[Enrichment] No college targets found for profile {sparq_profile_id}")
        return

    print(f"[Enrichment] Researching {len(colleges)} colleges for profile {sparq_profile_id} ({athlete_position} {athlete_sport} from {athlete_state})...")

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Run all college researchers in parallel
    tasks = [
        _research_one_college(client, college, athlete_position, athlete_state, athlete_sport)
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
