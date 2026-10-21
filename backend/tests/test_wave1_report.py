"""wave1_report.read_data with a fake pymysql: step marks count, and a missing step table (MySQL 1146) is tolerated."""
import sys
import types
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import wave1_report as w  # noqa: E402

SUBJECT = b"sbj-1"


class Cursor:
    def __init__(self, missing): self.missing, self.rows = missing, []
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def fetchall(self): return self.rows

    def execute(self, sql, args=()):
        self.rows = []
        if "FROM sparq_entries" in sql:
            self.rows = [{"user_id": 11, "clerk_id": SUBJECT, "entered_at": datetime(2026, 10, 21, 14)}]
        elif "FROM sparq_step_marks" in sql:
            if self.missing:
                raise Exception(1146, "Table 'railway.sparq_step_marks' doesn't exist")
            self.rows = [{"clerk_id": SUBJECT, "step": "school_page", "day": date(2026, 10, 21)},
                         {"clerk_id": SUBJECT, "step": "school_page", "day": date(2026, 10, 22)},
                         {"clerk_id": SUBJECT, "step": "email_opened", "day": date(2026, 10, 22)}]


def fake(monkeypatch, missing):
    conn = types.SimpleNamespace(cursor=lambda: Cursor(missing), close=lambda: None)
    mod = types.SimpleNamespace(connect=lambda **k: conn, cursors=types.SimpleNamespace(DictCursor=None))
    monkeypatch.setitem(sys.modules, "pymysql", mod)
    monkeypatch.setenv("MYSQL_PUBLIC_URL", "mysql://u:p@x.proxy.rlwy.net:1/railway")


def test_step_marks_count_days_and_activity(monkeypatch):
    fake(monkeypatch, missing=False)
    data, clash = w.read_data([11])
    assert data[11]["school_page"] == 2 and data[11]["email_opened"] == 1 and clash == []
    row = w.athlete_rows([11], data)[0]
    assert row["done"]["school_page"] and row["done"]["email_opened"] and row["days"] == 2


def test_missing_step_table_is_tolerated(monkeypatch):
    fake(monkeypatch, missing=True)
    data, _ = w.read_data([11])
    assert "school_page" not in data[11] and data[11]["entries"] == 1


def test_other_database_errors_still_fail(monkeypatch):
    fake(monkeypatch, missing=False)
    monkeypatch.setattr(Cursor, "execute", lambda self, sql, args=(): (_ for _ in ()).throw(Exception(2013, "lost")))
    with pytest.raises(Exception):
        w.read_data([11])
