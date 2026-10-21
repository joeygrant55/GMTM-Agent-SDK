"""forget_athlete.py against an in-memory SQLite stand-in for the SPARQ MySQL database. No real database."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import forget_athlete as fa  # noqa: E402

HER, OTHER = 987654, 555
SCHEMA = """
CREATE TABLE agent_conversations (id INTEGER PRIMARY KEY, clerk_id BLOB);
CREATE TABLE agent_messages (id INTEGER PRIMARY KEY, conversation_id INT);
CREATE TABLE agent_sessions (clerk_id BLOB);
CREATE TABLE agent_reports (id INTEGER PRIMARY KEY, user_id INT);
CREATE TABLE artifacts (id INTEGER PRIMARY KEY, clerk_id BLOB);
CREATE TABLE artifact_actions (id INTEGER PRIMARY KEY, artifact_id INT);
CREATE TABLE sparq_profiles (id INTEGER PRIMARY KEY, clerk_id BLOB);
CREATE TABLE college_targets (id INTEGER PRIMARY KEY, sparq_profile_id INT);
CREATE TABLE outreach_log (id INTEGER PRIMARY KEY, sparq_profile_id INT);
CREATE TABLE athlete_links (id INTEGER PRIMARY KEY, user_id INT);
CREATE TABLE sparq_parent_notices (clerk_id BLOB);
CREATE TABLE sparq_parent_contact (clerk_id BLOB, parent_email TEXT);
CREATE TABLE sparq_college_lists (clerk_id BLOB);
CREATE TABLE sparq_saved_colleges (clerk_id BLOB, program_id TEXT);
CREATE TABLE sparq_sent_emails (clerk_id BLOB, program_id TEXT);
CREATE TABLE sparq_card_clips (clerk_id BLOB);
CREATE TABLE sparq_step_marks (clerk_id BLOB, step TEXT, day TEXT);
CREATE TABLE sparq_sessions (clerk_id BLOB);
CREATE TABLE claim_tokens (id INTEGER PRIMARY KEY, user_id INT, clerk_id BLOB);
CREATE TABLE athlete_workspaces (clerk_id BLOB, gmtm_user_id INT);
CREATE TABLE sparq_entry_refusals (id INTEGER PRIMARY KEY, user_id INT);
CREATE TABLE sparq_entries (id INTEGER PRIMARY KEY, clerk_id BLOB, user_id INT);
CREATE TABLE athlete_profiles (id INTEGER PRIMARY KEY, user_id INT, clerk_id BLOB);
CREATE TABLE sparq_college_research (program_id TEXT);
"""


class Cursor:
    """A pymysql-like dict cursor over SQLite: %s placeholders, information_schema, session SET."""
    def __init__(self, conn):
        self.conn, self.rows = conn, []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, args=()):
        if self.conn.fail_on and sql.startswith(self.conn.fail_on):
            raise RuntimeError("injected failure")
        if sql.startswith("SET SESSION"):
            return
        if "information_schema.TABLES" in sql:
            sql = "SELECT name FROM sqlite_master WHERE type = 'table'"
        cur = self.conn.db.execute(sql.replace("%s", "?"), list(args))
        names = [d[0] for d in cur.description or ()]
        self.rows = [dict(zip(names, row)) for row in cur.fetchall()]

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class Conn:
    def __init__(self, db, fail_on=None):
        self.db, self.fail_on = db, fail_on

    def cursor(self):
        return Cursor(self)

    def begin(self):
        pass  # SQLite opens the transaction at the first write

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def close(self):
        pass


def seed(db, uid, tag):
    """One athlete: an October subject (sparq_entries) and an older subject (athlete_profiles), rows in every table."""
    new, old = f"sbj-{tag}-new".encode(), f"sbj-{tag}-old"
    ins = lambda sql, *a: db.execute(sql, a).lastrowid
    for _ in range(2):
        ins("INSERT INTO sparq_entries (clerk_id, user_id) VALUES (?, ?)", new, uid)
    # Bytes: pymysql sends bytes as a plain string, which matches MySQL varchar; SQLite TEXT never equals BLOB.
    ins("INSERT INTO athlete_profiles (user_id, clerk_id) VALUES (?, ?)", uid, old.encode())
    ins("INSERT INTO athlete_workspaces VALUES (?, ?)", old.encode(), uid)
    ins("INSERT INTO claim_tokens (user_id, clerk_id) VALUES (?, NULL)", uid)
    ins("INSERT INTO claim_tokens (user_id, clerk_id) VALUES (?, ?)", uid, new)
    for table in ("sparq_entry_refusals", "athlete_links", "agent_reports"):
        ins(f"INSERT INTO {table} (user_id) VALUES (?)", uid)
    for s in (new, old.encode()):
        conv = ins("INSERT INTO agent_conversations (clerk_id) VALUES (?)", s)
        ins("INSERT INTO agent_messages (conversation_id) VALUES (?)", conv)
        ins("INSERT INTO agent_messages (conversation_id) VALUES (?)", conv)
        art = ins("INSERT INTO artifacts (clerk_id) VALUES (?)", s)
        ins("INSERT INTO artifact_actions (artifact_id) VALUES (?)", art)
        prof = ins("INSERT INTO sparq_profiles (clerk_id) VALUES (?)", s)
        ins("INSERT INTO college_targets (sparq_profile_id) VALUES (?)", prof)
        ins("INSERT INTO outreach_log (sparq_profile_id) VALUES (?)", prof)
        for table in ("agent_sessions", "sparq_parent_notices", "sparq_college_lists", "sparq_card_clips", "sparq_sessions", "sparq_step_marks"):
            ins(f"INSERT INTO {table} (clerk_id) VALUES (?)", s)
        ins("INSERT INTO sparq_parent_contact VALUES (?, ?)", s, f"parent-{tag}@example.com")
        for table in ("sparq_saved_colleges", "sparq_sent_emails"):
            ins(f"INSERT INTO {table} VALUES (?, 'p1')", s)
            ins(f"INSERT INTO {table} VALUES (?, 'p2')", s)


def make(both=True):
    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA + "INSERT INTO sparq_college_research VALUES ('p1');")  # program facts: never deleted
    seed(db, OTHER, "other")  # first, so her delete leaves the same ids as a database that never had her
    if both:
        seed(db, HER, "her")
    db.commit()
    return db


def dump(db):
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    return {t: sorted(map(repr, db.execute(f"SELECT * FROM {t}"))) for t in tables}


def test_dry_run_counts_every_table_and_deletes_nothing():
    db = make()
    before = dump(db)
    counts, after, absent, n_subjects = fa.run(Conn(db), HER)
    assert after is None and absent == [] and n_subjects == 2
    assert list(counts) == [t for t, _ in fa.TABLES] and all(n > 0 for n in counts.values())
    assert counts["sparq_entries"] == 2 and counts["agent_messages"] == 4 and counts["claim_tokens"] == 2
    assert dump(db) == before


def test_delete_removes_all_her_rows_and_keeps_everyone_else():
    db = make()
    counts, after, _, _ = fa.run(Conn(db), HER, delete=True)
    assert set(after.values()) == {0} and sum(counts.values()) > 0
    assert dump(db) == dump(make(both=False))  # every table: her rows gone, the other athlete's rows unchanged


def test_shared_subject_stops_and_changes_nothing():
    db = make()
    db.execute("INSERT INTO sparq_entries (clerk_id, user_id) VALUES (?, ?)", (b"sbj-her-old", 31337))
    db.commit()
    before = dump(db)
    for delete in (False, True):
        with pytest.raises(fa.SharedSubject):
            fa.run(Conn(db), HER, delete=delete)
        assert dump(db) == before


def test_shared_subject_in_athlete_profiles_only_stops():
    db = make()
    db.execute("INSERT INTO athlete_profiles (user_id, clerk_id) VALUES (?, ?)", (31337, b"sbj-her-old"))
    db.commit()
    before = dump(db)
    for delete in (False, True):
        with pytest.raises(fa.SharedSubject):
            fa.run(Conn(db), HER, delete=delete)
        assert dump(db) == before


def test_wrong_target_is_refused(monkeypatch):
    for url in ('mysql://u:p@gmtm-prod.abc.us-east-1.rds.amazonaws.com:3306/gmtm', 'mysql://u:p@x.proxy.rlwy.net:1234/other'):
        monkeypatch.setenv('MYSQL_PUBLIC_URL', url)
        with pytest.raises(fa.WrongTarget):
            fa.connect()


def test_error_mid_delete_rolls_back_everything():
    db = make()
    before = dump(db)
    with pytest.raises(RuntimeError):
        fa.run(Conn(db, fail_on="DELETE FROM sparq_entries"), HER, delete=True)  # after 21 earlier deletes
    assert dump(db) == before


def test_missing_tables_are_skipped():
    db = make()
    db.executescript("DROP TABLE agent_conversations; DROP TABLE agent_reports;")
    counts, after, absent, _ = fa.run(Conn(db), HER, delete=True)
    assert absent == ["agent_conversations", "agent_messages", "agent_reports"]
    assert "agent_messages" not in counts and set(after.values()) == {0}


def test_unknown_id_finds_nothing():
    counts, _, _, n_subjects = fa.run(Conn(make()), 424242)
    assert n_subjects == 0 and set(counts.values()) == {0}


def test_output_has_no_ids_and_errors_have_no_secrets(monkeypatch, capsys):
    db = make()
    monkeypatch.setattr(fa, "connect", lambda: Conn(db))
    fa.main([str(HER)])
    fa.main([str(HER), "--delete"])
    out = capsys.readouterr().out
    assert "DRY RUN: nothing was changed" in out and "Every count is now 0." in out and "Receipt (keep this)" in out
    assert str(HER) not in out and "sbj-" not in out and "@" not in out

    class OperationalError(Exception):
        pass

    def refuse():
        raise OperationalError(2003, "Can't connect to 'secret-host.railway.internal' as root:hunter2")
    monkeypatch.setattr(fa, "connect", refuse)
    with pytest.raises(SystemExit) as stop:
        fa.main([str(HER), "--delete"])
    assert str(stop.value) == "The database step failed (OperationalError 2003). It should have rolled back. Run the dry run again to check."
    for bad in (["x"], [], ["1", "2"], ["1", "--force"], ["0"], ["\u0660\u0667"], ["--delete"]):
        with pytest.raises(SystemExit) as stop:
            fa.main(bad)
        assert "Dry run by default" in str(stop.value)
