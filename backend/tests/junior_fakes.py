"""In-memory stand-in for junior_entry.MySQLStore and SPARQ session minting (offline suite only)."""
from datetime import datetime, timezone
import hashlib
import secrets
import time

import jwt

import junior_eligibility
import junior_entry
from junior_entry import LinkConflict

SESSION_SECRET = "synthetic-sparq-session-secret-32-bytes!"
GSH = hashlib.sha256(b"synthetic-gmtm-session").hexdigest()
ENTRY_ENV = {"SPARQ_ENTRY_SECRET": "synthetic-entry-secret", "SPARQ_HANDOFF_SECRET": "synthetic-handoff",
             "GMTM_API_URL": "https://gmtm-api.example.invalid", "SPARQ_SESSION_SECRET": SESSION_SECRET}


ENTRY_USER_ID = 990001  # synthetic GMTM user behind a minted profile session


def mint_session(sub="sub_owner", *, active=True, entry=True, secret=SESSION_SECRET, aud="profile", **claims):
    """SPARQ session headers. ``active`` makes the jti the current one for ``sub`` in
    junior_entry.store. ``entry`` (profile only) also records what a real exchange
    leaves: a current entry row, an accepted parent notice and a cached eligible
    decision, so the profile gate admits it. ``entry=False`` = session row but no
    entry row. Claim overrides replace token claims; None removes one."""
    now = int(time.time())
    body = {"sub": sub, "jti": secrets.token_urlsafe(32), "gsh": GSH, "aud": aud, "iat": now, "exp": now + 86400, **claims}
    body = {k: v for k, v in body.items() if v is not None}
    if active:
        junior_entry.store.set_session(sub, body.get("jti"), datetime.now(timezone.utc))
    if entry and aud == "profile" and isinstance(sub, str) and junior_entry.store.latest_entry(sub) is None:
        stamp = datetime.now(timezone.utc)
        junior_entry.store.record_entry(sub, ENTRY_USER_ID, stamp)
        junior_entry.store.accept_notice(sub, stamp)
        junior_eligibility._cache[ENTRY_USER_ID] = (True, time.monotonic())
    return {"Authorization": "Bearer " + jwt.encode(body, secret, algorithm="HS256")}


class MemoryStore:
    def __init__(self, links=None):
        self.refusals, self.entries, self.notices = [], [], {}
        self.links = dict(links or {})  # user_id -> clerk_id
        self.sessions = {}  # clerk_id -> active jti

    def record_refusal(self, user_id, decision, at):
        self.refusals.append({"user_id": user_id, "decision": decision, "decided_at": at})

    def record_entry(self, clerk_id, user_id, at):
        self.entries.append({"clerk_id": clerk_id, "user_id": user_id, "entered_at": at})

    def latest_entry(self, clerk_id):
        rows = [e for e in self.entries if e["clerk_id"] == clerk_id]
        return max(rows, key=lambda e: e["entered_at"]) if rows else None

    def notice_accepted(self, clerk_id):
        return clerk_id in self.notices

    def accept_notice(self, clerk_id, at):
        self.notices.setdefault(clerk_id, {"accepted_at": at, "attested_by_session_kind": "unknown"})

    def set_session(self, clerk_id, jti, at):
        self.sessions[clerk_id] = jti

    def session_jti(self, clerk_id):
        return self.sessions.get(clerk_id)

    def end_session(self, clerk_id, jti):
        if self.sessions.get(clerk_id) == jti:
            del self.sessions[clerk_id]

    def linked_owner_id(self, user_id):
        return self.links.get(user_id)

    def ensure_link(self, clerk_id, user_id):
        if any(c == clerk_id and u != user_id for u, c in self.links.items()):
            raise LinkConflict()
        if self.links.setdefault(user_id, clerk_id) != clerk_id:
            raise LinkConflict()
