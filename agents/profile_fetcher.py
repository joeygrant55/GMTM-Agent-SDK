"""
Profile Fetcher Agent
=====================

Fetches comprehensive athlete profile data using GMTM MCP.
Returns structured profile data including metrics, highlights, and social links.
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# Claude Agent SDK imports
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

# Path to the MCP configuration file
MCP_CONFIG_PATH = Path("/Users/joey/Desktop/GMTM Marketing/.mcp.json")

# Base URLs for GMTM assets
GMTM_CDN_BASE = "https://cdn.gmtm.com"

# Social media URL patterns
SOCIAL_URL_PATTERNS = {
    "facebook": "https://facebook.com/{handle}",
    "instagram": "https://instagram.com/{handle}",
    "twitter": "https://twitter.com/{handle}",
    "hudl": "https://hudl.com/profile/{handle}",
    "maxpreps": "https://maxpreps.com/{handle}",
    "linkedin": "https://linkedin.com/in/{handle}",
}


PROFILE_FETCH_PROMPT = """
You are a data fetcher that retrieves comprehensive athlete profile data from the GMTM database.

## Your Task
Fetch ALL available data for athlete with user_id = {user_id}

## Required Queries (Execute ALL of these)

### Query 1: Basic Profile
```sql
SELECT u.user_id, u.first_name, u.last_name, u.graduation_year,
       u.avatar_uri, u.about, l.city, l.province as state
FROM users u
LEFT JOIN locations l ON u.location_id = l.location_id
WHERE u.user_id = {user_id}
```

### Query 2: SPARQ Metrics
```sql
SELECT m.title as metric_name, m.value, m.score as sparq_score,
       m.percentile, ipe.name as event_name
FROM metrics m
LEFT JOIN in_person_events ipe ON m.in_person_event_id = ipe.in_person_event_id
WHERE m.user_id = {user_id} AND m.is_current = 1
ORDER BY m.score DESC
```

### Query 3: Video Highlights
```sql
SELECT f.film_id, f.title, f.thumbnail_uri, f.uri as video_url, f.published_on
FROM film f
WHERE f.user_id = {user_id}
ORDER BY f.published_on DESC
LIMIT 8
```

### Query 4: Social Profiles
```sql
SELECT mp.uri as handle, mp.name as platform, mp.type
FROM media_profiles mp
WHERE mp.user_id = {user_id} AND mp.uri IS NOT NULL
```

## Response Format
Return a JSON object with this EXACT structure:
```json
{{
  "profile": {{
    "user_id": {user_id},
    "first_name": "...",
    "last_name": "...",
    "graduation_year": null,
    "city": "...",
    "state": "...",
    "avatar_uri": "...",
    "about": "..."
  }},
  "metrics": [
    {{"name": "40 Yard Dash", "value": "4.5", "sparq_score": 850, "percentile": 90, "event_name": "..."}}
  ],
  "highlights": [
    {{"film_id": 123, "title": "...", "thumbnail_uri": "...", "video_url": "...", "published_on": "..."}}
  ],
  "social_profiles": [
    {{"platform": "instagram", "handle": "..."}}
  ]
}}
```

Execute ALL queries using mcp__gmtmmcp__run_sql and compile the results.
"""


async def fetch_full_profile(user_id: int) -> Dict[str, Any]:
    """
    Fetch comprehensive athlete profile from GMTM database.

    Args:
        user_id: The athlete's user_id

    Returns:
        FullAthleteProfile-compatible dict
    """
    try:
        prompt = PROFILE_FETCH_PROMPT.format(user_id=user_id)

        options = ClaudeAgentOptions(
            mcp_servers=str(MCP_CONFIG_PATH),
            allowed_tools=[
                "mcp__gmtmmcp__run_sql",
                "mcp__gmtmmcp__get_table_schema"
            ],
            permission_mode="bypassPermissions",
            max_turns=8,
            model="claude-sonnet-4-20250514",
            cwd=str(MCP_CONFIG_PATH.parent)
        )

        full_response = ""

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text

        # Parse the JSON response
        json_match = re.search(r'\{[\s\S]*"profile"[\s\S]*\}', full_response)
        if json_match:
            data = json.loads(json_match.group())
            return transform_to_profile_response(data, user_id)

        # Fallback if no JSON found
        return create_minimal_profile(user_id)

    except Exception as e:
        print(f"Profile fetch error: {e}")
        return create_minimal_profile(user_id)


def transform_to_profile_response(data: Dict, user_id: int) -> Dict[str, Any]:
    """Transform raw query results to FullAthleteProfile format."""
    profile = data.get("profile", {})

    first_name = profile.get("first_name", "Unknown")
    last_name = profile.get("last_name", "")
    slug = f"{first_name.lower()}-{last_name.lower()}".replace(" ", "-")

    # Transform metrics
    metrics = []
    for m in data.get("metrics", []):
        metrics.append({
            "name": m.get("name", m.get("metric_name", "")),
            "value": str(m.get("value", "")),
            "sparq_score": m.get("sparq_score"),
            "percentile": m.get("percentile"),
            "event_name": m.get("event_name")
        })

    # Transform highlights
    highlights = []
    for h in data.get("highlights", []):
        thumbnail_uri = h.get("thumbnail_uri", "")
        video_uri = h.get("video_url", h.get("uri", ""))

        # Construct full URLs using GMTM CDN
        thumbnail_url = f"{GMTM_CDN_BASE}/{thumbnail_uri}" if thumbnail_uri else None
        video_url = f"{GMTM_CDN_BASE}/{video_uri}" if video_uri else None

        highlights.append({
            "film_id": h.get("film_id", 0),
            "title": h.get("title", ""),
            "thumbnail_url": thumbnail_url,
            "video_url": video_url,
            "published_on": str(h.get("published_on", "")) if h.get("published_on") else None
        })

    # Transform social profiles
    social_profiles = []
    for s in data.get("social_profiles", []):
        platform = s.get("platform", s.get("name", "")).lower()
        handle = s.get("handle", s.get("uri", ""))

        if platform and handle:
            url_pattern = SOCIAL_URL_PATTERNS.get(platform)
            if url_pattern:
                url = url_pattern.format(handle=handle)
            elif handle.startswith("http"):
                url = handle
            else:
                url = f"https://{platform}.com/{handle}"

            social_profiles.append({
                "platform": platform.title(),
                "url": url
            })

    # Construct avatar URL
    avatar_uri = profile.get("avatar_uri", "")
    avatar_url = f"{GMTM_CDN_BASE}/avatars/{avatar_uri}" if avatar_uri else None

    return {
        "user_id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "graduation_year": profile.get("graduation_year"),
        "city": profile.get("city"),
        "state": profile.get("state"),
        "avatar_url": avatar_url,
        "about": profile.get("about"),
        "metrics": metrics,
        "highlights": highlights,
        "social_profiles": social_profiles,
        "gmtm_profile_url": f"https://gmtm.com/athletes/{user_id}/{slug}/feed"
    }


def create_minimal_profile(user_id: int) -> Dict[str, Any]:
    """Create a minimal profile when data fetch fails."""
    return {
        "user_id": user_id,
        "first_name": "Athlete",
        "last_name": str(user_id),
        "graduation_year": None,
        "city": None,
        "state": None,
        "avatar_url": None,
        "about": None,
        "metrics": [],
        "highlights": [],
        "social_profiles": [],
        "gmtm_profile_url": f"https://gmtm.com/athletes/{user_id}/athlete-{user_id}/feed"
    }


# Local testing
if __name__ == "__main__":
    import asyncio

    async def test():
        result = await fetch_full_profile(1391851)  # Chapman Beaird
        print(json.dumps(result, indent=2))

    asyncio.run(test())
