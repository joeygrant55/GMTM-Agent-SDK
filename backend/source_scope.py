"""Pure comparison tag for responses belonging to the same current owner.

This is not an authorization token. Every endpoint still resolves its authenticated
owner independently. It lets a client reject responses that straddle a relink.
"""
import hashlib
import json


def owner_scope(clerk_id, athlete_id):
    if (not isinstance(clerk_id, str) or not clerk_id or len(clerk_id.encode("utf-8")) > 255
            or type(athlete_id) is not int or not 0 < athlete_id <= 9_007_199_254_740_991):
        raise ValueError("Invalid owner scope")
    value = json.dumps([clerk_id, athlete_id], separators=(",", ":"))
    return hashlib.sha256(("sparq-source-owner-v1:" + value).encode("utf-8")).hexdigest()
