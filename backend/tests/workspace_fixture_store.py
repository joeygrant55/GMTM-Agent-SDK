"""Strict in-memory workspace SQL fixture; never connects or prepares schema."""
from copy import deepcopy
import threading


class DriverError(Exception):
    pass


class WorkspaceStore:
    def __init__(self, links=None, *, mutex=None, link_reader=None):
        self.links = deepcopy(links or [])
        self.rows, self.connections, self.queries = {}, [], []
        self.mutex = mutex or threading.RLock()
        self.link_reader = link_reader
        self.failures = {}
        self.case_insensitive = False

    def connect(self):
        if self.failures.get("connect"):
            raise self.failures["connect"]
        return WorkspaceDB(self)


class WorkspaceDB:
    def __init__(self, store):
        self.store = store
        self.rows, self.pending = [], {}
        self.rowcount, self.commits, self.rollbacks = 0, 0, 0
        self.closed, self.transaction = False, False
        store.connections.append(self)

    def _fail(self, stage):
        error = self.store.failures.get(stage)
        if error:
            raise error

    def cursor(self):
        assert not self.closed
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def begin(self):
        self._fail("begin")
        assert not self.transaction
        self.store.mutex.acquire()
        self.transaction = True

    def execute(self, sql, params=None):
        assert not self.closed
        query = " ".join(sql.split())
        assert ";" not in query
        self.store.queries.append((query, deepcopy(params)))
        self._fail("execute")
        self.rows, self.rowcount = [], 0
        with self.store.mutex:
            links = self.store.link_reader() if self.store.link_reader else self.store.links
            if query == "SET SESSION innodb_lock_wait_timeout = 3":
                assert params is None
            elif query.startswith("SELECT id, user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2"):
                assert len(params) == 1
                match = lambda value: value.casefold() if self.store.case_insensitive else value
                self.rows = deepcopy([row for row in links if match(row["clerk_id"]) == match(params[0])][:2])
                assert query.endswith("LIMIT 2") or query.endswith("LIMIT 2 FOR UPDATE")
            elif query.startswith("SELECT id, user_id, clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 2"):
                assert len(params) == 1
                self.rows = deepcopy([row for row in links if row["user_id"] == params[0]][:2])
                assert query.endswith("LIMIT 2") or query.endswith("LIMIT 2 FOR UPDATE")
            elif query.startswith("SELECT clerk_id, athlete_link_id, gmtm_user_id, version, payload, created_at, updated_at FROM athlete_workspaces WHERE clerk_id = %s LIMIT 2"):
                self._fail("read_workspace")
                assert len(params) == 1 and isinstance(params[0], bytes)
                row = self.pending.get(params[0], self.store.rows.get(params[0]))
                self.rows = [deepcopy(row)] if row else []
                assert query.endswith("LIMIT 2") or query.endswith("LIMIT 2 FOR UPDATE")
            elif query == "INSERT INTO athlete_workspaces (clerk_id, athlete_link_id, gmtm_user_id, version, payload, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)":
                assert self.transaction and len(params) == 7
                self._fail("write")
                subject, link_id, athlete, version, payload, created, updated = params
                if subject in self.store.rows or subject in self.pending:
                    raise DriverError(1062, "Synthetic duplicate")
                self.pending[subject] = dict(clerk_id=subject, athlete_link_id=link_id, gmtm_user_id=athlete,
                                            version=version, payload=payload, created_at=created, updated_at=updated)
                self.rowcount = 1
            elif query == "UPDATE athlete_workspaces SET version = %s, payload = %s, updated_at = %s WHERE clerk_id = %s AND athlete_link_id = %s AND gmtm_user_id = %s AND version = %s":
                assert self.transaction and len(params) == 7
                self._fail("write")
                version, payload, updated, subject, link_id, athlete, expected = params
                row = self.store.rows.get(subject)
                if row and row["athlete_link_id"] == link_id and row["gmtm_user_id"] == athlete and row["version"] == expected:
                    self.pending[subject] = {**deepcopy(row), "version": version, "payload": payload, "updated_at": updated}
                    self.rowcount = 1
            else:
                raise AssertionError(f"Unexpected synthetic workspace query: {query}")

    def fetchall(self):
        return deepcopy(self.rows)

    def fetchone(self):
        return deepcopy(self.rows[0]) if self.rows else None

    def commit(self):
        assert self.transaction
        self._fail("commit")
        self.store.rows.update(deepcopy(self.pending))
        self.pending.clear()
        self.commits += 1
        self.transaction = False
        self.store.mutex.release()
        self._fail("commit_after_apply")

    def rollback(self):
        self.pending.clear()
        self.rollbacks += 1
        if self.transaction:
            self.transaction = False
            self.store.mutex.release()
        self._fail("rollback")

    def close(self):
        self.pending.clear()
        if self.transaction:
            self.transaction = False
            self.store.mutex.release()
        self.closed = True
        self._fail("close")
