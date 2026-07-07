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

AI_MATCHING_SYSTEM = """You are a college recruiting analyst. Use web_search to find real college programs for this athlete. NEVER invent programs — every entry must be a real school you verified through web_search results.

After gathering candidates, return ONLY a valid JSON array — no markdown, no explanation.

Each program object must have:
{
  "name": "Full University Name",
  "city": "City",
  "state": "ST",
  "division": "D1" or "D2" or "D3" or "NAIA",
  "fit_summary": "1-2 specific sentences about why this program fits this exact athlete",
  "fit_score": integer 70-95,
  "source_url": "the URL of a web_search result that confirms this school currently fields a team in the athlete's exact sport"
}

Hard requirements (drop any candidate that fails these — do not include it):
- The program MUST have an active team in the athlete's EXACT sport AND gender (e.g. if sport is "Girls Basketball", only Women's Basketball programs; never Men's).
- source_url MUST come from your web_search results and reference the school's athletics site, an NCAA/conference roster page, or another authoritative source confirming the team exists.
- If you cannot find 8-12 programs that meet these requirements, return fewer — better to return 5 verified programs than 12 with guesses.

Process:
1. Run web_search queries combining the athlete's sport, gender, target division, and geography preferences (e.g. "D2 women's basketball programs in Northeast", "NAIA football schools recruiting class of 2027").
2. From the results, pick real schools and verify each currently fields a team in the athlete's exact sport.
3. Mix realistic reaches (2-3) with likely fits (5-7). Be specific about why each fits.
4. Return ONLY the JSON array.
"""

WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
}

FLAG_RANKING_SYSTEM = """You are a college recruiting analyst for women's flag football.

You will be given (a) an athlete profile and (b) the COMPLETE list of real women's college
flag football programs from SPARQ's curated database. Every program in the list is real and
verified — you must NOT add, rename, or invent any program not in the list.

Select the 8-12 best fits for this athlete and return ONLY a valid JSON array — no markdown,
no explanation. Each entry must use the program's exact "name" from the list and have:
{
  "name": "<exact name from the provided list>",
  "fit_summary": "1-2 specific sentences on why this program fits this athlete",
  "fit_score": integer 70-95
}

Selection guidance:
- Mix 2-3 reaches (higher-level or more established programs) with 5-7 realistic fits.
- Weight geography preference, target level (NAIA programs are established with championship
  history and 12 scholarships/team; NCAA programs are brand-new and actively hunting for
  founding rosters — often the best opportunity), and 'announced' programs recruiting
  founding classes for upcoming seasons.
- Return ONLY the JSON array."""


def _match_flag_programs_sync(athlete_profile: Dict, client) -> List[Dict]:
    """Bounded matching for flag football: rank from the curated flag_programs table.

    No web_search, no invented schools — the candidate universe is the real program list,
    so hallucination is structurally impossible. source_url comes from the table.
    """
    from flag_programs_api import load_flag_programs

    programs = load_flag_programs()
    if not programs:
        print("[Matching] flag_programs table empty — falling back to web-search matching")
        return []

    by_name = {p["name"]: p for p in programs}
    catalog = "\n".join(
        f"- {p['name']} | {p['org']} | {p.get('conference') or 'conference TBD'} | "
        f"{p.get('state') or '??'} | {p['status']}"
        + (f" (first season {p['first_varsity_season']})" if p.get("first_varsity_season") else "")
        for p in programs
    )

    goals = athlete_profile.get("recruiting_goals") or {}
    if isinstance(goals, str):
        try:
            goals = json.loads(goals)
        except Exception:
            goals = {}
    stats = athlete_profile.get("maxpreps_stats") or {}
    stats_str = ", ".join(f"{k}: {v}" for k, v in stats.items()) if stats else "no stats provided"

    user_prompt = (
        f"ATHLETE\n"
        f"- Sport: {athlete_profile.get('sport')}, Position: {athlete_profile.get('position')}\n"
        f"- Class of {athlete_profile.get('class_year') or 'unknown'}, from {athlete_profile.get('state') or 'unknown'}\n"
        f"- Stats: {stats_str}\n"
        f"- Target level: {goals.get('targetLevel', 'Open')}, Geography: {goals.get('geography', 'Anywhere')}\n\n"
        f"PROGRAM LIST (the complete universe — select only from these)\n{catalog}\n\n"
        f"Select the 8-12 best fits and return ONLY the JSON array."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=FLAG_RANKING_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
        timeout=60.0,
    )
    full_text = "".join(b.text for b in response.content if hasattr(b, "text"))

    picks: List[Dict] = []
    m = re.search(r"\[.*\]", full_text, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group())
            if isinstance(parsed, list):
                picks = parsed
        except Exception:
            pass

    matched: List[Dict] = []
    dropped = 0
    for pick in picks:
        if not isinstance(pick, dict):
            continue
        program = by_name.get(pick.get("name"))
        if not program:
            dropped += 1  # model named something outside the universe — discard
            continue
        matched.append({
            "name": program["name"],
            "city": program.get("city") or "",
            "state": program.get("state") or "",
            "division": program["org"],
            "fit_summary": pick.get("fit_summary") or "",
            "fit_score": pick.get("fit_score") or 75,
            "source_url": program.get("source_url") or "",
        })
    print(f"[Matching] Flag bounded match: {len(matched)} programs from curated table (dropped {dropped} out-of-universe picks)")
    return matched


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


def _is_plausible_url(s: object) -> bool:
    """Reject hallucinated source_urls — must be an http(s) URL with a plausible TLD."""
    if not isinstance(s, str):
        return False
    s = s.strip()
    return bool(re.match(r"^https?://[^\s]+\.[a-z]{2,}", s, re.IGNORECASE))


def ai_match_programs_sync(athlete_profile: Dict) -> List[Dict]:
    """Use Claude WITH web_search to find real college programs from web sources.

    Replaces the prior pure-training-data approach which fabricated programs from Claude's
    memory. Now each program must include a source_url that came from a web_search result —
    candidates without a plausible URL are dropped before insertion.
    """
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    sport = athlete_profile.get("sport") or athlete_profile.get("position") or "Basketball"

    # Flag football (the focus market) matches against the curated flag_programs table —
    # a bounded universe with zero hallucination risk. Other sports use web-search matching.
    if "flag" in str(sport).lower():
        try:
            matched = _match_flag_programs_sync(athlete_profile, client)
            if matched:
                return matched
        except Exception as e:
            print(f"[Matching] Flag bounded match failed ({e}) — falling back to web search")
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
        f"Find real college {sport} programs that recruit this athlete:\n"
        f"- Sport: {sport}, Position: {position}\n"
        f"- Class of {class_year}, from {state}\n"
        f"- Stats: {stats_str}\n"
        f"- Target division: {target_level}, Geography: {geography}\n\n"
        f"Use web_search to find 8-12 verified {sport} programs. Each MUST include a source_url "
        f"from your search results confirming the school currently fields a team in this sport. "
        f"Drop any school you cannot verify. Mix 2-3 reaches with 5-7 realistic fits. "
        f"Return ONLY a JSON array."
    )

    try:
        print(f"[Matching] Calling Claude (web_search) for {sport} {position} from {state}...")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            system=AI_MATCHING_SYSTEM,
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": user_prompt}],
        )
        full_text = "".join(b.text for b in response.content if hasattr(b, "text"))
        print(f"[Matching] Response ({len(full_text)} chars): {full_text[:200]}")

        programs: List[Dict] = []
        for pattern in [r"\[\s*\{.*?\}\s*\]", r"\[.*?\]"]:
            m = re.search(pattern, full_text, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group())
                    if isinstance(parsed, list) and parsed:
                        programs = parsed
                        break
                except Exception:
                    pass
        if not programs:
            try:
                parsed = json.loads(full_text.strip())
                if isinstance(parsed, list):
                    programs = parsed
            except Exception:
                pass

        # Drop hallucinated entries: must have a plausible source_url and a name.
        verified: List[Dict] = []
        dropped = 0
        for p in programs:
            if not isinstance(p, dict):
                continue
            if not p.get("name"):
                dropped += 1
                continue
            if not _is_plausible_url(p.get("source_url")):
                dropped += 1
                continue
            verified.append(p)

        print(f"[Matching] Verified {len(verified)} programs (dropped {dropped} without source_url)")
        return verified
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
