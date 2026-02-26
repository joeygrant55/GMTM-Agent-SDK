"""
Enrichment Worker - runs after onboarding to research each college in parallel.
Uses Claude Agent SDK subagents so all colleges are researched simultaneously.
"""

import json
import os
import re
from typing import Dict, List

import pymysql
from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env"))
load_dotenv()


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
    except Exception as e:
        print(f"Warning: could not store research for college {college_target_id}: {e}")
    finally:
        db.close()


RESEARCHER_SYSTEM_PROMPT = """You are a college football recruiting researcher.
Research the given college program and return ONLY a valid JSON object - no other text.

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

Return ONLY the JSON object. No markdown, no explanation, just the JSON.
"""


async def enrich_college_targets(sparq_profile_id: int, athlete_position: str, athlete_state: str):
    """
    Background job: research each college using parallel subagents.
    Called fire-and-forget from profile_api after onboarding.
    """
    colleges = _get_college_targets(sparq_profile_id)
    if not colleges:
        print(f"No college targets found for profile {sparq_profile_id}")
        return

    print(f"Enriching {len(colleges)} colleges for profile {sparq_profile_id}...")

    agents = {}
    for col in colleges:
        agent_key = f"researcher-{col['id']}"
        agents[agent_key] = AgentDefinition(
            description=(
                f"Research {col['college_name']} ({col['division']}, {col['college_city']}, {col['college_state']}) "
                f"recruiting program for a {athlete_position} athlete from {athlete_state}. "
                "Use this agent to get coaching staff, position needs, and fit analysis."
            ),
            prompt=RESEARCHER_SYSTEM_PROMPT,
            tools=["WebSearch", "WebFetch"],
            model="sonnet",
        )

    college_lines = "\n".join(
        [
            f"- ID {col['id']}: {col['college_name']} ({col['division']}, {col['college_city']}, {col['college_state']})"
            for col in colleges
        ]
    )

    orchestration_prompt = f"""
Research each of these college football programs for a {athlete_position} recruit from {athlete_state}, Class of 2026.

For EACH school, invoke its dedicated researcher subagent and get the JSON result.
Run multiple subagents in parallel where possible to save time.

After all subagents complete, output ALL results as a JSON array in this format:
[
  {{"college_id": <ID>, "research": {{...JSON from subagent...}}}},
  ...
]

Colleges to research:
{college_lines}
"""

    options = ClaudeAgentOptions(
        allowed_tools=["WebSearch", "WebFetch", "Task"],
        permission_mode="bypassPermissions",
        agents=agents,
    )

    result_text = ""
    async for sdk_message in query(prompt=orchestration_prompt, options=options):
        if hasattr(sdk_message, "result") and sdk_message.result:
            result_text = sdk_message.result

    if result_text:
        _parse_and_store_results(result_text, colleges)
        print(f"Enrichment complete for profile {sparq_profile_id}")
    else:
        print(f"No enrichment results for profile {sparq_profile_id}")


def _parse_and_store_results(result_text: str, colleges: List[Dict]):
    """Parse the orchestrator's JSON array output and store per-college."""
    college_map = {col["id"]: col for col in colleges}

    try:
        json_match = re.search(r"\[.*\]", result_text, re.DOTALL)
        if json_match:
            results = json.loads(json_match.group())
            for item in results:
                college_id = item.get("college_id")
                research = item.get("research", {})
                if college_id and research and college_id in college_map:
                    _store_research(college_id, research)
            return
    except (json.JSONDecodeError, TypeError):
        pass

    for college in colleges:
        cid = college["id"]
        name = college["college_name"]
        patterns = [
            rf"ID {cid}[^{{]*(\{{[^}}]+\}})",
            rf"{re.escape(name)}[^{{]*(\{{[^}}]+\}})",
        ]
        for pattern in patterns:
            match = re.search(pattern, result_text, re.DOTALL | re.IGNORECASE)
            if match:
                try:
                    research = json.loads(match.group(1))
                    _store_research(cid, research)
                    break
                except json.JSONDecodeError:
                    continue
