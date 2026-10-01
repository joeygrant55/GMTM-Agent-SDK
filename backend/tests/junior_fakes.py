"""In-memory stand-in for junior_entry.MySQLStore (offline suite only)."""
from junior_entry import LinkConflict


class MemoryStore:
    def __init__(self, links=None):
        self.refusals, self.entries, self.notices = [], [], {}
        self.links = dict(links or {})  # user_id -> clerk_id

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

    def ensure_link(self, clerk_id, user_id):
        if any(c == clerk_id and u != user_id for u, c in self.links.items()):
            raise LinkConflict()
        if self.links.setdefault(user_id, clerk_id) != clerk_id:
            raise LinkConflict()
