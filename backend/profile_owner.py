"""Profile-only adapters: retain the admitted link row through source resolution.

The original combine entry and legacy recovery remain unchanged. These adapters
do no I/O until called, and disabled local previews retain existing behavior.
"""
from fastapi import Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from auth import require_clerk_id
from combine_api import _linked_athlete as legacy_linked_athlete, _get_agent_db
from profile_admission import is_active, recheck_admission


def _strict_owner(cursor, clerk_id):
    # Local import avoids the evidence -> workspace -> evidence import cycle.
    from athlete_workspace import _owner, WorkspaceError
    try:
        return _owner(cursor, clerk_id)
    except WorkspaceError:
        raise HTTPException(403, "Pilot access is unavailable for this account.") from None


def linked_profile_athlete(db, clerk_id):
    if not is_active():
        return legacy_linked_athlete(db, clerk_id)
    with db.cursor() as cursor:
        return _strict_owner(cursor, clerk_id)["user_id"]


def _recovery(clerk_id):
    db = _get_agent_db()
    try:
        with db.cursor() as cursor:
            owner = _strict_owner(cursor, clerk_id)
            cursor.execute("SELECT id, clerk_id FROM sparq_profiles WHERE clerk_id = %s LIMIT 2", (clerk_id,))
            rows = cursor.fetchall()
            if (len(rows) > 1 or rows and (not isinstance(rows[0], dict)
                    or rows[0].get("clerk_id") != clerk_id
                    or type(rows[0].get("id")) is not int or rows[0]["id"] <= 0)):
                raise HTTPException(409, "The existing account connection needs review.")
            recheck_admission()
            return {"found": True, "user_id": owner["user_id"], "has_sparq_profile": bool(rows)}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "The existing account connection could not be checked.") from None
    finally:
        db.close()


async def current_profile_recovery(clerk_id: str, caller_clerk_id: str = Depends(require_clerk_id)):
    if not is_active():
        from profile_api import get_profile_by_clerk
        return await get_profile_by_clerk(clerk_id, caller_clerk_id)
    if clerk_id != caller_clerk_id:
        raise HTTPException(403, "Not authorized.")
    return await run_in_threadpool(_recovery, caller_clerk_id)
