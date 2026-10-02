"""Profile-only adapters over the legacy owner resolvers.

Every profile request already passed the GMTM entry gate (candidate_app), so
these keep the legacy behavior. They do no I/O until called.
"""
from fastapi import Depends

from auth import require_identity
from combine_api import _linked_athlete as legacy_linked_athlete


def linked_profile_athlete(db, clerk_id):
    return legacy_linked_athlete(db, clerk_id)


async def current_profile_recovery(clerk_id: str, caller_id: str = Depends(require_identity)):
    from profile_api import get_profile_by_owner
    return await get_profile_by_owner(clerk_id, caller_id)
