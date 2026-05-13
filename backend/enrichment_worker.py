"""
Enrichment Worker - runs after onboarding to research each college in parallel.
Uses raw anthropic SDK + asyncio.gather for true parallelism (no claude CLI required).
"""

import asyncio
import json
import os
import random
import re
from typing import Dict, List, Optional

import anthropic
import pymysql
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env"))
load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Path to the curated flag football programs seed file.
# Single source of truth for all college matching now that the product
# is narrowed to women's flag football only.
PROGRAMS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "flag_football_programs.json",
)


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
- Programs must actually have the athlete's EXACT sport (e.g. if sport is "Girls Basketball", only return women's basketball programs — NOT men's)
- If sport contains "Girls" or "Women's", every program must have an active women's program for that sport
- If sport contains "Boys" or "Men's", every program must have an active men's program for that sport
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


# US Census Bureau regional groupings — used for the "geography" preference filter.
_REGION_STATES = {
    "Southeast": {"AL", "AR", "FL", "GA", "KY", "LA", "MS", "NC", "SC", "TN", "VA", "WV"},
    "Northeast": {"CT", "DE", "DC", "MA", "MD", "ME", "NH", "NJ", "NY", "PA", "RI", "VT"},
    "Midwest":   {"IA", "IL", "IN", "KS", "MI", "MN", "MO", "ND", "NE", "OH", "SD", "WI"},
    "West":      {"AK", "AZ", "CA", "CO", "HI", "ID", "MT", "NM", "NV", "OK", "OR", "TX", "UT", "WA", "WY"},
}

# Per-division base fit score. Higher = more likely to recruit a given athlete
# (i.e. "Likely" tier). Lower = more selective ("Reach" tier).
# These numbers are intentionally bucketed — they live in the 65-95 range
# that the storage layer clamps to in profile_api._run_matching_thread.
_DIVISION_TIER_SCORE = {
    "NCAA D1": 72,   # Reach
    "NCAA D2": 80,   # Target
    "NCAA D3": 82,   # Target (no athletic scholarships)
    "NAIA":   86,    # Likely (scholarship-eligible but smaller)
    "NJCAA":  90,    # Likely (two-year pathway)
}


def _tier_label(fit_score: int) -> str:
    """Map a numeric fit_score to a Reach/Target/Likely label for narrative use."""
    if fit_score >= 85:
        return "Likely"
    if fit_score >= 78:
        return "Target"
    return "Reach"


def _load_flag_football_programs() -> List[Dict]:
    """Read the curated women's flag football program list from disk."""
    try:
        with open(PROGRAMS_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
        programs = payload.get("programs") or []
        if not isinstance(programs, list):
            print(f"[Matching] Programs file is malformed at {PROGRAMS_FILE}")
            return []
        return programs
    except FileNotFoundError:
        print(f"[Matching] Programs file not found at {PROGRAMS_FILE}")
        return []
    except Exception as e:
        print(f"[Matching] Failed to load programs file: {e}")
        return []


def _program_is_eligible_for_class_year(program: Dict, class_year: Optional[int]) -> bool:
    """A program is eligible if the athlete's class year can plausibly compete there.

    - active programs: always eligible
    - announced_2026_27: eligible for athletes graduating HS in 2026 or later
    - announced_2027_28: eligible for athletes graduating HS in 2027 or later
    - if class year is unknown, accept active programs only (safest default)
    """
    status = program.get("status") or "active"
    if status == "active":
        return True
    if class_year is None:
        return False
    try:
        cy = int(class_year)
    except (TypeError, ValueError):
        return False
    if status == "announced_2026_27":
        return cy >= 2026
    if status == "announced_2027_28":
        return cy >= 2027
    return False


def ai_match_programs_sync(athlete_profile: Dict) -> List[Dict]:
    """Match a flag football athlete to real college programs from the curated seed.

    This function REPLACES the previous Claude-hallucinated matcher. It is
    deterministic — schools come from data/flag_football_programs.json, not
    from a language model. The fit_summary written here is a short template
    label; the rich per-row narrative (coach names, recruiting needs, fit
    reasoning) is produced downstream by enrich_college_targets, which is
    grounded by web_search.

    Returns 12-15 programs in the dict shape expected by
    profile_api._run_matching_thread: name, city, state, division, fit_score,
    fit_summary.
    """
    programs = _load_flag_football_programs()
    if not programs:
        print("[Matching] No programs loaded — returning empty list")
        return []

    class_year_raw = athlete_profile.get("class_year")
    try:
        class_year = int(class_year_raw) if class_year_raw is not None else None
    except (TypeError, ValueError):
        class_year = None

    athlete_state = (athlete_profile.get("state") or "").strip().upper()

    goals = athlete_profile.get("recruiting_goals") or {}
    if isinstance(goals, str):
        try:
            goals = json.loads(goals)
        except Exception:
            goals = {}
    geography_pref = (goals.get("geography") or "Anywhere").strip()
    target_level = (goals.get("targetLevel") or "Open").strip()

    eligible = [p for p in programs if _program_is_eligible_for_class_year(p, class_year)]
    print(f"[Matching] {len(eligible)}/{len(programs)} programs eligible for class {class_year}")

    # Score every eligible program.
    scored: List[Dict] = []
    for prog in eligible:
        base = _DIVISION_TIER_SCORE.get(prog.get("division", ""), 78)

        # Geography bonus: in-state +4, same region +2, otherwise 0.
        geo_bonus = 0
        prog_state = (prog.get("state") or "").strip().upper()
        if geography_pref == "In-state" and prog_state and prog_state == athlete_state:
            geo_bonus = 4
        elif geography_pref in _REGION_STATES and prog_state in _REGION_STATES[geography_pref]:
            geo_bonus = 2

        fit_score = max(65, min(95, base + geo_bonus))
        tier = _tier_label(fit_score)

        # Deterministic short summary — enrichment will overwrite this with
        # a researched narrative for each row that's stored in college_targets.
        conf = prog.get("conference") or "Independent"
        location = ", ".join([x for x in [prog.get("city"), prog.get("state")] if x])
        fit_summary = (
            f"{tier} — {prog.get('division')} women's flag football program "
            f"({conf}) in {location}."
        )

        scored.append({
            "name": prog.get("name") or "Unknown",
            "city": prog.get("city") or "",
            "state": prog_state,
            "division": prog.get("division") or "NAIA",
            "conference": conf,
            "fit_score": fit_score,
            "fit_summary": fit_summary,
            "tier": tier,
            "status": prog.get("status") or "active",
        })

    # If the athlete picked an explicit target level, bias the selection toward
    # programs that match (without excluding others — flag football is small).
    level_map = {
        "D1 Power": ["NCAA D1"],
        "D1 Mid-Major": ["NCAA D1"],
        "D2": ["NCAA D2"],
        "D3": ["NCAA D3"],
    }
    preferred_divs = level_map.get(target_level)
    if preferred_divs:
        for row in scored:
            if row["division"] in preferred_divs:
                row["fit_score"] = min(95, row["fit_score"] + 3)

    # Pick a mix across tiers so the athlete sees a real spread.
    # Sort within each tier by fit_score desc.
    by_tier: Dict[str, List[Dict]] = {"Reach": [], "Target": [], "Likely": []}
    for row in scored:
        by_tier[row["tier"]].append(row)
    for tier in by_tier:
        by_tier[tier].sort(key=lambda r: r["fit_score"], reverse=True)

    # Target shape: 3 Reach, 6 Target, 5 Likely — total ~14.
    selected: List[Dict] = []
    selected.extend(by_tier["Reach"][:3])
    selected.extend(by_tier["Target"][:6])
    selected.extend(by_tier["Likely"][:5])

    # If a tier was thin, backfill from any other tier so we still hand back
    # a useful list. Cap at 15.
    if len(selected) < 12:
        remaining = [r for r in scored if r not in selected]
        remaining.sort(key=lambda r: r["fit_score"], reverse=True)
        selected.extend(remaining[: 15 - len(selected)])

    # Light shuffle inside the final list so the athlete doesn't always see
    # programs in the exact same order across re-runs.
    random.shuffle(selected)

    print(f"[Matching] Returning {len(selected)} flag football programs")
    return selected


def _legacy_ai_match_programs_sync(athlete_profile: Dict) -> List[Dict]:
    """DEPRECATED: AI-hallucinated multi-sport matcher.

    Preserved for reference only. The product is now narrowed to women's
    flag football and uses ai_match_programs_sync (above), which loads from
    data/flag_football_programs.json. Do not call this function.
    """
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    sport = athlete_profile.get("sport") or athlete_profile.get("position") or "Basketball"
    position = athlete_profile.get("position") or sport
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
    stats_str = ", ".join(f"{k}: {v}" for k, v in stats.items()) if stats else "no stats provided"

    user_prompt = (
        f"Generate a college target list for this athlete:\n"
        f"- Sport: {sport}, Position: {position}\n"
        f"- Class of {class_year}, from {state}\n"
        f"- Stats: {stats_str}\n"
        f"- Target division: {target_level}, Geography: {geography}\n\n"
        f"Return 8-12 realistic college {sport} programs that would recruit this athlete. "
        "Mix 2-3 reach schools with 5-7 realistic fits. "
        "For each, explain specifically why they fit this athlete's stats and goals. "
        "Return ONLY a JSON array."
    )

    try:
        print(f"[Matching] Calling Claude for {sport} {position} from {state}...")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=AI_MATCHING_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        full_text = "".join(b.text for b in response.content if hasattr(b, "text"))
        print(f"[Matching] Response ({len(full_text)} chars): {full_text[:200]}")

        for pattern in [r"\[\s*\{.*?\}\s*\]", r"\[.*?\]"]:
            m = re.search(pattern, full_text, re.DOTALL)
            if m:
                try:
                    programs = json.loads(m.group())
                    if isinstance(programs, list) and programs:
                        print(f"[Matching] Found {len(programs)} programs")
                        return programs
                except Exception:
                    pass
        # direct parse
        try:
            parsed = json.loads(full_text.strip())
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        print(f"[Matching] Could not parse JSON from response")
    except Exception as e:
        print(f"[Matching] Claude call failed: {e}")
    return []


async def ai_match_programs(athlete_profile: Dict) -> List[Dict]:
    """Async wrapper — runs sync Claude call in thread pool."""
    loop = asyncio.get_event_loop()
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, ai_match_programs_sync, athlete_profile)


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
        f"IMPORTANT: The athlete plays {athlete_sport}. If this is 'Girls Basketball' or 'Women's Basketball', research the WOMEN'S program only. "
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
