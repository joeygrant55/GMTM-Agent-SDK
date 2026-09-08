"""
Bootstrap a workspace (`sparq_profiles`) row for a GMTM-linked athlete.

Claim redemption can prepare a workspace from GMTM identity and metric data after
establishing the athlete link. This helper only creates the missing workspace;
it never starts college matching, research, or provider work. Combine entry and
progress remain available independently of this optional preparation.
"""
from __future__ import annotations

import json
from typing import Optional

from combine_results import get_combine_results


def _best(results: list[dict], drill: str) -> Optional[float]:
    vals = [r["value"] for r in results if r.get("drill") == drill and r.get("value") is not None]
    if not vals:
        return None
    ideal = next((r["ideal"] for r in results if r.get("drill") == drill), "lower")
    return min(vals) if ideal == "lower" else max(vals)


def _gmtm_identity(user_id: int) -> Optional[dict]:
    from profile_api import _get_gmtm_db  # lazy: avoids a circular import at module load
    db = _get_gmtm_db()
    try:
        with db.cursor() as c:
            c.execute(
                """SELECT u.user_id, u.first_name, u.last_name, u.graduation_year, u.gender,
                          l.city, l.province AS state
                   FROM users u LEFT JOIN locations l ON l.location_id = u.location_id
                   WHERE u.user_id = %s""",
                (user_id,),
            )
            u = c.fetchone()
            if not u:
                return None
            c.execute(
                """SELECT p.name AS position, o.name AS school, s.name AS sport
                   FROM career c
                   LEFT JOIN user_positions up ON up.career_id = c.career_id AND up.is_primary = 1
                   LEFT JOIN positions p ON p.position_id = up.position_id
                   LEFT JOIN organizations o ON o.organization_id = c.organization_id
                   LEFT JOIN sports s ON s.sport_id = c.sport_id
                   WHERE c.user_id = %s
                   ORDER BY c.is_primary DESC, c.career_id DESC LIMIT 1""",
                (user_id,),
            )
            career = c.fetchone() or {}
            c.execute(
                """SELECT title, value FROM metrics
                   WHERE user_id = %s AND is_current = 1 AND title IN ('Height', 'Weight')""",
                (user_id,),
            )
            hw = {r["title"]: r["value"] for r in c.fetchall()}
        return {**u, **career, "height_in": hw.get("Height"), "weight_lb": hw.get("Weight")}
    finally:
        db.close()


def _num(v) -> Optional[float]:
    try:
        f = float(str(v).strip())
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def ensure_workspace_profile(clerk_id: str, user_id: int) -> dict:
    """Create the sparq_profiles row for this Clerk user from their GMTM record if missing.
    Returns {"ready": bool, "created": bool, "profile_id": int|None}."""
    from profile_api import _get_agent_db, _get_gmtm_db  # lazy

    def owned_profile_id(row):
        # Older SQL collations may match a different case-sensitive Clerk subject.
        profile_id = row.get("id") if isinstance(row, dict) else None
        if (type(profile_id) is not int or profile_id <= 0
                or row.get("clerk_id") != clerk_id):
            raise ValueError("Workspace ownership could not be confirmed.")
        return profile_id

    db = _get_agent_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id, clerk_id FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            row = c.fetchone()
            if row is not None:
                return {"ready": True, "created": False, "profile_id": owned_profile_id(row)}

        ident = _gmtm_identity(user_id)
        if not ident:
            return {"ready": False, "created": False, "profile_id": None}

        try:
            results = get_combine_results(user_id, _get_gmtm_db)
        except Exception:
            results = []
        height = _num(ident.get("height_in"))
        combine = {
            "fortyYardDash": _best(results, "40-Yard Dash"),
            "shuttle": _best(results, "5-10-5 Shuttle"),
            "vertical": _best(results, "Vertical Jump"),
            "heightFeet": int(height // 12) if height else None,
            "heightInches": int(height % 12) if height else None,
            "weight": _num(ident.get("weight_lb")),
        }
        combine = {k: v for k, v in combine.items() if v is not None}

        name = f"{ident.get('first_name') or ''} {ident.get('last_name') or ''}".strip()
        position = ident.get("position") or ""
        state = ident.get("state") or ""
        with db.cursor() as c:
            c.execute(
                """INSERT INTO sparq_profiles
                       (clerk_id, name, position, school, class_year, city, state,
                        combine_metrics, enrichment_complete)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0)
                   ON DUPLICATE KEY UPDATE id = id""",
                (clerk_id, name, position, ident.get("school") or "", ident.get("graduation_year"),
                 ident.get("city") or "", state, json.dumps(combine) if combine else None),
            )
            # The normal PyMySQL connection does not enable CLIENT_FOUND_ROWS:
            # an insert affects one row; a duplicate no-op affects zero.
            created = c.rowcount == 1
            db.commit()
            c.execute("SELECT id, clerk_id FROM sparq_profiles WHERE clerk_id = %s", (clerk_id,))
            pid = owned_profile_id(c.fetchone())
    finally:
        db.close()

    return {"ready": True, "created": created, "profile_id": pid}
