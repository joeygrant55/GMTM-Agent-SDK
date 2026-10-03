import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import college_research  # noqa: E402
import college_research_job as job  # noqa: E402

PROGRAMS = [{"id": i, "school": i.title(), "program_url": f"https://{i}.com/sports/flag/index", "staff_page_url": None}
            for i in ("zeta-college", "alpha-college", "mid-college")]


class FakeStore:
    def __init__(self, lock=True):
        self.lock, self.saved, self.progressed, self.finished = lock, [], [], []

    def take_lock(self, run_id): return self.lock
    def save(self, run_id, result): self.saved.append(result["program_id"])
    def progress(self, run_id, result): self.progressed.append(result["cost_usd"])
    def finish(self, run_id, status): self.finished.append(status)


def fake_research(costs=None, fail_on=None):
    def research(p, extract):
        if p["id"] == fail_on:
            raise RuntimeError("non_json")
        return {"program_id": p["id"], "cost_usd": (costs or {}).get(p["id"], 0.01), "notes": [], "drops": [], "pages": ["x"]}
    return research


def test_fixed_alphabetical_order_independent_of_input_order(monkeypatch):
    monkeypatch.setattr(college_research, "research_program", fake_research())
    store = FakeStore()
    summary = job.run_job(PROGRAMS, extract=None, store=store, log=lambda s: None)
    assert store.saved == ["alpha-college", "mid-college", "zeta-college"] and store.finished == ["done"]
    assert summary["programs"] == 3 and summary["status"] == "done"


def test_cap_stops_launching_new_programs(monkeypatch):
    monkeypatch.setattr(college_research, "research_program", fake_research(costs={"alpha-college": 2.0, "mid-college": 2.0}))
    store = FakeStore()
    summary = job.run_job(PROGRAMS, extract=None, store=store, cap=3.0, log=lambda s: None)
    assert store.saved == ["alpha-college", "mid-college"] and summary["status"] == "stopped" and store.finished == ["stopped"]


def test_run_stopping_failure_is_recorded_and_stops(monkeypatch):
    monkeypatch.setattr(college_research, "research_program", fake_research(fail_on="mid-college"))
    store = FakeStore()
    summary = job.run_job(PROGRAMS, extract=None, store=store, log=lambda s: None)
    assert store.saved == ["alpha-college"] and summary["status"] == "failed" and store.finished == ["failed"]


def test_locked_run_does_nothing(monkeypatch):
    monkeypatch.setattr(college_research, "research_program", fake_research())
    store = FakeStore(lock=False)
    assert job.run_job(PROGRAMS, extract=None, store=store, log=lambda s: None)["status"] == "locked"
    assert store.saved == [] and store.finished == []


def test_dry_run_writes_nothing(monkeypatch):
    monkeypatch.setattr(college_research, "research_program", fake_research())
    assert job.run_job(PROGRAMS, extract=None, store=None, log=lambda s: None)["programs"] == 3


class Cursor:
    def __init__(self, log): self.log = log
    def execute(self, sql, args=()): self.log.append((sql, args))
    def fetchone(self): return None


def capture():
    calls = []
    return calls, (lambda fn, write=False: fn(Cursor(calls)))


def test_save_keeps_last_good_roster_and_camps_when_this_run_could_not_read_them():
    calls, run = capture()
    store = job.Store(run=run)
    store.save("r1", {"program_id": "a", "roster_state": "not_found", "roster": None, "camps": [],
                      "notes": ["program_page:ReadTimeout"], "drops": [], "pages": []})
    sql, args = calls[-1]
    assert "roster = IF(%s, VALUES(roster), roster)" in sql
    assert args[1] is None and args[3] is None and args[-4:] == (False, False, False, False)


def test_save_replaces_parts_read_this_run_and_stores_no_athlete_fields():
    calls, run = capture()
    roster = {"season": "2026", "by_class": {"Fr": 3}, "by_position": {}, "total": 3, "source_url": "https://a.com/r",
              "method": "page_structure"}
    job.Store(run=run).save("r1", {"program_id": "a", "roster_state": "found", "roster": roster, "camps": [],
                                   "notes": [], "drops": [], "pages": ["https://a.com/sports/flag/index"]})
    sql, args = calls[-1]
    assert args[-4:] == (True, True, True, True) and args[3] == "[]"
    assert "clerk_id" not in sql and "user_id" not in sql


def test_lock_claims_in_one_commit_checks_in_the_next_and_a_loser_deletes_its_row():
    calls, commits = [], []

    class LockCursor(Cursor):
        def fetchone(self): return {"run_id": "older-run"}

    def run(fn, write=False):
        result = fn(LockCursor(calls))
        commits.append(len(calls))
        return result

    assert job.Store(run=run).take_lock("my-run") is False
    assert "status = 'running' AND started_at < %s" in calls[0][0] and calls[1][0].startswith("INSERT")
    assert commits[0] == 2  # expire + insert committed before the check reads
    assert calls[-1] == ("DELETE FROM sparq_research_runs WHERE run_id = %s", ("my-run",))


def test_job_never_imports_athlete_tables():
    source = (Path(job.__file__)).read_text()
    for table in ("sparq_saved_colleges", "sparq_college_lists", "athlete_profiles", "sparq_profiles"):
        assert table not in source


def test_camps_page_error_keeps_last_weeks_camps_but_a_clean_none_replaces_them():
    calls, run = capture()
    store = job.Store(run=run)
    base = {"program_id": "a", "roster_state": "not_found", "roster": None, "camps": [], "drops": [],
            "pages": ["https://a.edu/sports/flag/index"]}
    store.save("r1", {**base, "notes": ["camps_page:ReadTimeout"]})
    assert calls[-1][1][3] is None and calls[-1][1][-2:] == (False, False)
    store.save("r1", {**base, "notes": ["camps_page:none"]})
    assert calls[-1][1][3] == "[]" and calls[-1][1][-2:] == (True, True)


def test_any_exception_and_interrupt_still_finish_the_run_as_failed(monkeypatch):
    def boom(p, extract):
        raise KeyboardInterrupt
    monkeypatch.setattr(college_research, "research_program", boom)
    store = FakeStore()
    with pytest.raises(KeyboardInterrupt):
        job.run_job(PROGRAMS, extract=None, store=store, log=lambda s: None)
    assert store.finished == ["failed"]


def test_unknown_option_exits_before_any_paid_call(monkeypatch):
    called = []
    monkeypatch.setattr(college_research, "research_program", lambda p, e: called.append(p))
    monkeypatch.setitem(sys.modules, "college_research_probe", type(sys)("college_research_probe"))
    sys.modules["college_research_probe"].extract = None
    with pytest.raises(SystemExit, match="unknown option"):
        job.main(["--aply"])
    assert called == []


@pytest.mark.parametrize("args", [["-apply"], ["apply"], ["--cap", "nan"], ["--cap", "inf"], ["--cap", "0"]])
def test_bad_arguments_exit_before_any_paid_call(monkeypatch, args):
    called = []
    monkeypatch.setattr(college_research, "research_program", lambda p, e: called.append(p))
    monkeypatch.setitem(sys.modules, "college_research_probe", type(sys)("college_research_probe"))
    sys.modules["college_research_probe"].extract = None
    with pytest.raises(SystemExit):
        job.main(args)
    assert called == []
