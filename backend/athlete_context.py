"""Pure tool contract: use the authorized request snapshot, never model-selected data."""

from copy import deepcopy


CURRENT_ATHLETE_TOOL = {
    "name": "get_current_athlete",
    "description": (
        "Return the current athlete's already-loaded profile, results, and existing "
        "aggregate comparisons. No arguments; no other-athlete lookup or database query."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}


def current_athlete_tool_result(name: str, arguments: object, profile: dict | None, *, is_demo: bool = False) -> dict:
    """The route supplies the authenticated snapshot; tool input cannot change its scope."""
    if name != CURRENT_ATHLETE_TOOL["name"]:
        return {"error": "Unknown tool. Use get_current_athlete with no arguments."}
    if not isinstance(arguments, dict) or arguments:
        return {"error": "get_current_athlete takes no arguments."}
    if is_demo:
        return {"available": False, "reason": "The demo has no private athlete data."}
    if not profile:
        return {"available": False, "reason": "No current athlete profile is available."}
    return {"available": True, "profile": deepcopy(profile)}
