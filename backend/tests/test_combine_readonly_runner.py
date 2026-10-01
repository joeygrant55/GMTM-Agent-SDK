"""Runner isolation and privacy tests. All connections are explicit fakes."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location("readonly_runner", Path(__file__).parents[1] / "scripts/verify_combine_readonly.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def config():
    return dict(DB_HOST=runner.ALLOWED_GMTM_HOST, DB_USER="private_user", DB_PASSWORD="PRIVATE_PASSWORD",
                AGENT_DB_HOST="mysql.railway.internal", AGENT_DB_PORT="3306",
                AGENT_DB_USER="private_user", AGENT_DB_PASSWORD="PRIVATE_PASSWORD", AGENT_DB_NAME="railway")


class Cursor:
    def __init__(self, raw):
        self.raw = raw
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()
    def close(self):
        pass
    def execute(self, sql, params=None):
        self.raw.statements.append((sql, params))
        if self.raw.fail_begin and sql == "START TRANSACTION READ ONLY":
            raise RuntimeError("PRIVATE_DRIVER_DETAIL")
    def fetchall(self):
        return self.raw.rows


class Raw:
    def __init__(self, rows=None, fail_begin=False):
        self.rows = [{"clerk_id": "PRIVATE_SUBJECT"}] if rows is None else rows
        self.fail_begin, self.statements = fail_begin, []
        self.rollbacks = self.closes = 0
    def cursor(self):
        return Cursor(self)
    def rollback(self):
        self.rollbacks += 1
    def close(self):
        self.closes += 1


def setup(rows=None, mapped_id=2, fail_begin=False, fail_load=False):
    raws, options = [], []
    def connect(**kwargs):
        options.append(kwargs)
        raw = Raw(rows, fail_begin)
        raws.append(raw)
        return raw
    service = SimpleNamespace(_get_agent_db=lambda: None, _get_gmtm_db=lambda: None)
    def linked(db, subject):
        with db.cursor() as cursor:
            cursor.execute("SELECT user_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2", (subject,))
        return mapped_id
    service._linked_athlete = linked
    def load(subject, event):
        agent, gmtm = service._get_agent_db(), service._get_gmtm_db()
        try:
            with gmtm.cursor() as cursor:
                cursor.execute("SELECT event_id FROM events WHERE event_id = %s", (event,))
            if fail_load:
                raise RuntimeError("PRIVATE_DRIVER_DETAIL")
            return {"athlete_id": 2, "clerk_id": subject, "state": "ready",
                    "selected_event": {"event_id": event, "name": "PRIVATE_EXTRA"},
                    "activities": [{"task_id": 4892, "event_id": event, "submission_state": "not_submitted",
                                    "evidence_state": "missing_fields", "answer": "PRIVATE_ANSWER"}],
                    "counts": {"activities": 1, "submitted": 0, "fields_present": 0}}
        finally:
            agent.close()
            gmtm.close()
    service.load_current_combine = load
    return service, SimpleNamespace(connect=connect, cursors=SimpleNamespace(DictCursor=object)), raws, options


@pytest.mark.parametrize("key", runner.REQUIRED)
def test_missing_configuration_never_connects(key):
    env = config()
    del env[key]
    service, driver, raws, _ = setup()
    assert runner.verify(2, 1317, env, service=service, driver=driver)["reason"] == "missing_configuration"
    assert not raws


@pytest.mark.parametrize("host", ["pre-prod.example", "wrong.example", runner.ALLOWED_GMTM_HOST + ".evil", "localhost"])
def test_gmtm_exact_host_allowlist_before_connect(host):
    env = {**config(), "DB_HOST": host}
    service, driver, raws, _ = setup()
    assert runner.verify(2, 1317, env, service=service, driver=driver)["reason"] == "gmtm_host_not_allowed"
    assert not raws


@pytest.mark.parametrize("host", ["pre-prod.example", "preprod.example", runner.ALLOWED_GMTM_HOST, "mysql://private@host"])
def test_agent_retired_or_unexpected_host_before_connect(host):
    assert runner.check_config({**config(), "AGENT_DB_HOST": host})["status"] == "blocked"


def test_observation_is_redacted_readonly_and_factories_restored():
    service, driver, raws, options = setup()
    originals = service._get_agent_db, service._get_gmtm_db
    receipt = runner.verify(2, 1317, config(), service=service, driver=driver)
    assert receipt["status"] == "observed" and receipt["ownership_match"]
    assert receipt["counts"]["submitted"] == 0
    assert "PRIVATE" not in json.dumps(receipt) and "subject" not in json.dumps(receipt)
    assert receipt["eligibility_verified"] is False
    assert len(receipt["projection_sha256"]) == 64
    assert (service._get_agent_db, service._get_gmtm_db) == originals
    assert len(raws) == 2
    for raw in raws:
        assert raw.statements[:2] == [("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ", None),
                                      ("START TRANSACTION READ ONLY", None)]
        assert raw.rollbacks == raw.closes == 1
    assert all(o["autocommit"] is False and o["local_infile"] is False for o in options)


@pytest.mark.parametrize("rows,reason", [([], "unlinked_athlete"), ([{"clerk_id": ""}], "ambiguous_owner"),
    ([{"clerk_id": "a"}, {"clerk_id": "b"}], "ambiguous_owner")])
def test_no_link_or_ambiguous_link_stops_before_gmtm(rows, reason):
    service, driver, raws, _ = setup(rows=rows)
    result = runner.verify(2, 1317, config(), service=service, driver=driver)
    assert result["reason"] == reason and len(raws) == 1
    assert raws[0].rollbacks == raws[0].closes == 1


def test_reverse_mapping_mismatch_stops_before_gmtm():
    service, driver, raws, _ = setup(mapped_id=3)
    assert runner.verify(2, 1317, config(), service=service, driver=driver)["reason"] == "owner_or_event_mismatch"
    assert len(raws) == 1


@pytest.mark.parametrize("fail_begin,fail_load", [(True, False), (False, True)])
def test_failures_are_redacted_and_connections_rolled_back(fail_begin, fail_load):
    service, driver, raws, _ = setup(fail_begin=fail_begin, fail_load=fail_load)
    receipt = runner.verify(2, 1317, config(), service=service, driver=driver)
    assert receipt["status"] == "blocked" and "PRIVATE" not in json.dumps(receipt)
    assert all(r.rollbacks == r.closes == 1 for r in raws)


@pytest.mark.parametrize("sql", ["UPDATE events SET name='x'", "SELECT * FROM users", "SELECT 1; DELETE FROM events",
    "SELECT * FROM events INTO OUTFILE 'x'", "SELECT SLEEP(1) FROM events", "SELECT * FROM events FOR UPDATE",
    "SELECT * FROM events /* comment */", "CALL procedure()", "SELECT GET_LOCK('x',1) FROM events"])
def test_sql_guard_blocks_mutations_files_locks_and_unapproved_tables(sql):
    with pytest.raises(runner.Blocked):
        runner.validate_select(sql)


def test_preflight_writes_private_receipt_without_service_access(tmp_path, monkeypatch):
    for key, value in config().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(runner, "verify", lambda *a, **k: pytest.fail("preflight must not verify"))
    receipt = tmp_path / "receipt.json"
    assert runner.main(["--athlete-id", "2", "--event-id", "1317", "--check-config", "--receipt", str(receipt)]) == 0
    body = receipt.read_text()
    assert "PRIVATE" not in body and "private_user" not in body
    assert receipt.stat().st_mode & 0o777 == 0o600
    assert json.loads(body)["connectivity_verified"] is False
    assert runner.main(["--athlete-id", "2", "--event-id", "1317", "--check-config", "--receipt", str(receipt)]) == 2


def test_actual_service_runs_through_transaction_and_select_guards():
    import combine_api
    fixture = json.loads((Path(__file__).parent / "fixtures/usaf_2027_combine2_public.json").read_text())
    public = fixture["events"][0]
    tasks = [{**task, "description": "Instructions", "payload": json.dumps({"questions": task["questions"]})}
             for task in public["tasks"]]
    class SourceCursor(Cursor):
        def execute(self, sql, params=None):
            super().execute(sql, params)
            if "SELECT clerk_id" in sql:
                assert params == (2,)
                self.raw.rows = [{"clerk_id": "PRIVATE_SUBJECT"}]
            elif "SELECT user_id" in sql:
                assert sql.startswith("SELECT user_id, clerk_id FROM athlete_profiles ")
                assert params in (("PRIVATE_SUBJECT",), (2,))
                self.raw.rows = [{"user_id": 2, "clerk_id": "PRIVATE_SUBJECT"}]
            elif "FROM events" in sql:
                self.raw.rows = [public["event"]]
            elif "FROM event_tasks" in sql:
                self.raw.rows = tasks
            elif "FROM event_task_submissions" in sql:
                assert params[0] == 2
                self.raw.rows = []
    class SourceRaw(Raw):
        def cursor(self):
            return SourceCursor(self)
    raws = []
    def connect(**kwargs):
        raw = SourceRaw()
        raws.append(raw)
        return raw
    driver = SimpleNamespace(connect=connect, cursors=SimpleNamespace(DictCursor=object))
    receipt = runner.verify(2, 1317, config(), service=combine_api, driver=driver)
    assert receipt["status"] == "observed"
    assert receipt["counts"] == {"activities": 9, "submitted": 0, "fields_present": 0}
    assert len(raws) == 2 and all(raw.rollbacks == raw.closes == 1 for raw in raws)
    assert "PRIVATE" not in json.dumps(receipt)
