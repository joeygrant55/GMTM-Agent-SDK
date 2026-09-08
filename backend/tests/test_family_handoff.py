"""Synthetic family handoff through actual SPARQ endpoints; no live services.

The fixed actors below are invented test identities, not authorized participants.
An authenticated child is a separate hypothetical Clerk session, not a claim that
Clerk/GMTM child login or delegated guardian access has been established. Claims
reuse the existing transactional fake; combine/recovery reads share its committed
mapping and a small relational source containing deliberately competing records.
"""

from copy import deepcopy
import threading

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import claims_api
import combine_api
import combine_help_api
import profile_api
from auth import require_clerk_id
from backend.tests.test_claims import _FakeDB as ClaimDB
from backend.tests.test_combine_requirements import PUBLIC, definition_rows, submission_for


PARENT, CHILD, SIBLING, DUPLICATE = 910001, 910002, 910003, 910004
PARENT_SESSION = "family_parent"
CHILD_SESSION = "family_child"
SIBLING_SESSION = "family_sibling"
DUPLICATE_SESSION = "family_duplicate"


class FamilyReadDB:
    """A synthetic relational read interface, not a MySQL emulator.

    Scope predicates are checked before filtering the shared fixture, so a query
    losing its actor/event predicate cannot silently pass. Extra records compete
    for the same task; returned response assertions establish which one won.
    """

    def __init__(self, store, source):
        self.store, self.source = store, source
        self.result = []
        self.closed = False
        store["read_connections"].append(self)

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def close(self):
        self.closed = True

    def execute(self, sql, params):
        sql = " ".join(sql.split())
        assert sql.startswith("SELECT "), "Family progress/recovery must only read"
        self.store["read_queries"].append((self.source, sql, params))
        if "FROM athlete_profiles" in sql:
            assert self.source == "agent"
            mappings = [dict(user_id=uid, clerk_id=clerk)
                        for uid, clerk in self.store["athlete_profiles"].items()]
            if "WHERE clerk_id = %s" in sql:
                def matches(owner):
                    return (owner.casefold() == params[0].casefold()
                            if self.store["case_insensitive_mapping"] else owner == params[0])
                self.result = [row for row in mappings if matches(row["clerk_id"])]
            else:
                assert "WHERE user_id = %s" in sql
                self.result = [row for row in mappings if row["user_id"] == params[0]]
                if "reverse_override" in self.store:
                    self.result = deepcopy(self.store["reverse_override"])
            if sql.endswith("LIMIT 2"):
                self.result = self.result[:2]
            if sql.startswith("SELECT user_id FROM"):
                self.result = [{"user_id": row["user_id"]} for row in self.result]
        elif "FROM sparq_profiles" in sql:
            assert self.source == "agent" and "WHERE clerk_id = %s LIMIT 2" in sql
            self.result = [deepcopy(row) for row in self.store["workspaces"]
                           if row["clerk_id"] == params[0]]
        elif "FROM claim_tokens" in sql:
            assert self.source == "agent"
            assert "clerk_id = %s AND user_id = %s AND claimed_at IS NOT NULL" in sql
            clerk, uid, *events = params
            self.result = [{"event_id": event} for event in sorted({
                row["event_id"] for row in self.store["claims"].values()
                if row["clerk_id"] == clerk and row["user_id"] == uid
                and row["claimed_at"] is not None and row["event_id"] in events
            })]
        elif "FROM events" in sql:
            assert self.source == "gmtm" and params == (1317, 1318, 249002)
            self.result = deepcopy(self.store["events"])
        elif "FROM event_tasks" in sql:
            assert self.source == "gmtm" and "WHERE event_id = %s AND visibility = 2" in sql
            self.result = [deepcopy(row) for row in self.store["tasks"]
                           if row["event_id"] == params[0] and row["visibility"] == 2][:params[1]]
        elif "FROM event_task_submissions s" in sql:
            assert self.source == "gmtm"
            for predicate in ("s.user_id = %s AND t.event_id = %s", "s.visibility > 0",
                              "s.task_id IN (", "newer.user_id = s.user_id",
                              "newer.task_id = s.task_id"):
                assert predicate in sql
            uid, event_id, *tail = params
            task_ids, limit = tail[:-1], tail[-1]
            eligible = [row for row in self.store["submissions"]
                        if row["user_id"] == uid and row["event_id"] == event_id
                        and row["task_id"] in task_ids and row["visibility"] > 0]
            latest = {}
            for row in sorted(eligible, key=lambda item: (item["created_on"], item["task_submission_id"])):
                latest[row["task_id"]] = row
            self.result = list(latest.values())[:limit]
        else:
            raise AssertionError(f"Unexpected family read: {sql}")

    def fetchall(self):
        return deepcopy(self.result)

    def fetchone(self):
        return deepcopy(self.result[0]) if self.result else None


@pytest.fixture
def family(monkeypatch):
    tasks = definition_rows(1317) + definition_rows(1318)
    junior = [task for task in tasks if task["event_id"] == 1317]
    adult = [task for task in tasks if task["event_id"] == 1318]
    store = {
        "athlete_profiles": {PARENT: PARENT_SESSION, SIBLING: SIBLING_SESSION,
                             DUPLICATE: DUPLICATE_SESSION},
        "claims": {}, "users": {PARENT, CHILD, SIBLING, DUPLICATE},
        "names": {PARENT: "Morgan Fixture", CHILD: "Taylor Fixture",
                  SIBLING: "Riley Fixture", DUPLICATE: "Taylor Fixture"},
        "parent_ids": {CHILD: PARENT, SIBLING: PARENT, DUPLICATE: PARENT},
        "events": [deepcopy(item["event"]) for item in PUBLIC["events"]],
        "tasks": tasks,
        "submissions": [
            submission_for(junior[0], sid=11, user_id=PARENT, answers={}),
            submission_for(junior[0], sid=21, user_id=CHILD),
            submission_for(junior[1], sid=22, user_id=CHILD),
            submission_for(adult[2], sid=23, user_id=CHILD),
            submission_for(junior[8], sid=31, user_id=SIBLING),
        ],
        "workspaces": [{"id": 501, "clerk_id": PARENT_SESSION}],
        "connections": [], "named_locks": {}, "row_locks": {}, "failures": {},
        "mutex": threading.RLock(), "open_writes": 0, "bootstrap_calls": [],
        "read_connections": [], "read_queries": [], "case_insensitive_mapping": False,
        "model_clients": 0,
    }
    monkeypatch.setattr(claims_api, "_get_agent_db", lambda: ClaimDB(store))
    monkeypatch.setattr(claims_api, "_get_gmtm_db", lambda: ClaimDB(store))
    monkeypatch.setattr(profile_api, "_get_agent_db", lambda: FamilyReadDB(store, "agent"))
    monkeypatch.setattr(combine_api, "_get_agent_db", lambda: FamilyReadDB(store, "agent"))
    monkeypatch.setattr(combine_api, "_get_gmtm_db", lambda: FamilyReadDB(store, "gmtm"))
    def bootstrap(clerk_id, user_id):
        # Actual bootstrap can create a workspace and invoke models. This fake
        # records the boundary only; it does not establish bootstrap acceptance.
        store["bootstrap_calls"].append((clerk_id, user_id))
        return {"ready": True, "created": False, "profile_id": None}
    monkeypatch.setattr(claims_api, "ensure_workspace_profile", bootstrap)
    monkeypatch.setattr(combine_help_api, "_rate_buckets", {})
    def forbidden_model():
        store["model_clients"] += 1
        raise AssertionError("A refused family owner must never initialize a model client")
    monkeypatch.setattr(combine_help_api, "_new_client", forbidden_model)
    app = FastAPI()
    for router in (profile_api.router, claims_api.router, combine_api.router, combine_help_api.router):
        app.include_router(router)
    identity = {"clerk": PARENT_SESSION}
    app.dependency_overrides[require_clerk_id] = lambda: identity["clerk"]
    with TestClient(app) as client:
        client.store, client.identity = store, identity
        yield client
    assert all(db.closed for db in store["connections"] + store["read_connections"])
    assert store["named_locks"] == store["row_locks"] == {}
    assert store["model_clients"] == 0


def mint_child(family):
    response = family.post("/api/claims/mint", json={"user_ids": [CHILD], "event_id": 1317},
                           headers={"X-Claims-Admin": "test-admin-secret"})
    assert response.status_code == 200, response.text
    return response.json()[0]["token"]


def recover(family):
    return family.get(f'/api/profile/by-clerk/{family.identity["clerk"]}')


def progress(family, event_id=1317, **request):
    response = family.get("/api/combine/current", params={"event_id": event_id}, **request)
    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "private, no-store"
    return response.json()


def submitted_tasks(body):
    return {item["task_id"] for item in body["activities"] if item["submission_state"] == "submitted"}


def assert_combine_and_help_refuse(family):
    for response in (
        family.get("/api/combine/current?event_id=1317"),
        family.post("/api/combine/help", json={"event_id": 1317, "message": "Which junior activities have I saved?"}),
    ):
        assert response.status_code == 409, "An uncertain owner must be refused before reading progress or generating help"
        assert "athlete_id" not in response.json() and "user_id" not in response.json()
    assert not any(source == "gmtm" for source, _, _ in family.store["read_queries"])
    assert family.store["model_clients"] == 0
    bucket = combine_help_api._rate_buckets[family.identity["clerk"]]
    assert bucket["until"] == 0 and bucket["source_running"] is False


def test_parent_self_link_cannot_be_repurposed_by_child_invitation_or_profile_id(family):
    token = mint_child(family)
    before_links = deepcopy(family.store["athlete_profiles"])
    before_claims = deepcopy(family.store["claims"])
    before_submissions = deepcopy(family.store["submissions"])
    assert family.post(f"/api/claims/{token}/redeem").status_code == 409
    for uid in (CHILD, SIBLING, DUPLICATE):
        response = family.post("/api/profile/connect", json={"user_id": uid, "clerk_id": PARENT_SESSION})
        assert response.status_code == 403
    assert recover(family).json()["user_id"] == PARENT
    body = progress(family)
    assert body["athlete_id"] == PARENT
    assert body["counts"] == {"activities": 9, "submitted": 1, "fields_present": 0}
    assert family.store["athlete_profiles"] == before_links
    assert family.store["claims"] == before_claims
    assert family.store["submissions"] == before_submissions
    assert family.store["bootstrap_calls"] == []


def test_independent_child_claim_recovers_its_existing_submissions_without_moving_family_work(family):
    token = mint_child(family)
    family.identity["clerk"] = CHILD_SESSION
    assert recover(family).json() == {"found": False, "user_id": None, "has_sparq_profile": False}
    before_links = deepcopy(family.store["athlete_profiles"])
    before_submissions = deepcopy(family.store["submissions"])
    response = family.post(f"/api/claims/{token}/redeem")
    assert response.status_code == 200 and response.json()["user_id"] == CHILD
    assert family.store["athlete_profiles"] == {**before_links, CHILD: CHILD_SESSION}
    assert recover(family).json()["user_id"] == CHILD
    body = progress(family)
    expected = {row["task_id"] for row in before_submissions if row["user_id"] == CHILD and row["event_id"] == 1317}
    assert body["athlete_id"] == CHILD and submitted_tasks(body) == expected
    assert body["counts"] == {"activities": 9, "submitted": 2, "fields_present": 2}
    assert family.store["submissions"] == before_submissions
    assert family.store["bootstrap_calls"] == [(CHILD_SESSION, CHILD)]


def test_division_and_untrusted_selected_child_hints_never_change_the_authenticated_athlete(family):
    family.store["athlete_profiles"][CHILD] = CHILD_SESSION
    family.identity["clerk"] = CHILD_SESSION
    before = deepcopy(family.store["athlete_profiles"])
    for event_id, count in ((1317, 2), (1318, 1), (1317, 2)):
        response = family.get("/api/combine/current", params={
            "event_id": event_id, "user_id": PARENT, "athlete_id": SIBLING,
            "selected_child_id": DUPLICATE, "parent_id": PARENT, "clerk_id": PARENT_SESSION,
        }, headers={"X-Athlete-Id": str(SIBLING), "Cookie": f"selected_child_id={DUPLICATE}"})
        assert response.status_code == 200
        body = response.json()
        assert body["athlete_id"] == CHILD and body["clerk_id"] == CHILD_SESSION
        assert body["selected_event"]["event_id"] == event_id
        assert body["counts"]["submitted"] == count
        assert all(item["event_id"] == event_id for item in body["activities"])
    assert family.store["athlete_profiles"] == before


@pytest.mark.parametrize("session, uid, submitted", [(SIBLING_SESSION, SIBLING, 1), (DUPLICATE_SESSION, DUPLICATE, 0)])
def test_sibling_and_duplicate_name_profiles_do_not_inherit_child_progress(family, session, uid, submitted):
    family.store["athlete_profiles"][CHILD] = CHILD_SESSION
    assert family.store["names"][CHILD] == family.store["names"][DUPLICATE]
    assert family.store["parent_ids"][CHILD] == family.store["parent_ids"][uid]
    family.identity["clerk"] = session
    before = deepcopy(family.store["submissions"])
    assert recover(family).json()["user_id"] == uid
    body = progress(family)
    expected = {row["task_id"] for row in before if row["user_id"] == uid and row["event_id"] == 1317}
    assert body["athlete_id"] == uid and submitted_tasks(body) == expected
    assert body["counts"]["submitted"] == submitted
    assert family.store["submissions"] == before


def test_unlinked_parent_metadata_and_workspace_do_not_establish_child_authority(family):
    del family.store["athlete_profiles"][PARENT]
    before = deepcopy(family.store["athlete_profiles"])
    assert recover(family).json() == {"found": False, "user_id": None, "has_sparq_profile": True}
    body = progress(family)
    assert body["state"] == "link_required" and body["athlete_id"] is None
    assert body["counts"] == {"activities": 9, "submitted": None, "fields_present": None}
    assert all(item["submission_state"] == "unavailable" for item in body["activities"])
    assert not any("event_task_submissions" in sql for _, sql, _ in family.store["read_queries"])
    assert family.store["athlete_profiles"] == before


def test_historical_parent_and_child_mapping_is_refused_without_silently_picking_first(family):
    family.store["athlete_profiles"][CHILD] = PARENT_SESSION
    before = deepcopy(family.store["athlete_profiles"])
    for response in (recover(family), family.get("/api/combine/current?event_id=1317")):
        assert response.status_code == 409
        assert "athlete_id" not in response.json() and "user_id" not in response.json()
    assert not any(source == "gmtm" for source, _, _ in family.store["read_queries"])
    assert family.store["athlete_profiles"] == before


def test_case_colliding_identity_cannot_read_the_child_even_if_legacy_sql_collation_matches(family):
    family.store["athlete_profiles"][CHILD] = CHILD_SESSION
    family.store["case_insensitive_mapping"] = True
    family.identity["clerk"] = CHILD_SESSION.upper()
    before = deepcopy(family.store["athlete_profiles"])
    assert recover(family).status_code == 409
    assert_combine_and_help_refuse(family)
    assert family.store["athlete_profiles"] == before


@pytest.mark.parametrize("reverse_rows", [
    [],
    [{"user_id": CHILD, "clerk_id": CHILD_SESSION}, {"user_id": CHILD, "clerk_id": PARENT_SESSION}],
    [{"user_id": PARENT, "clerk_id": CHILD_SESSION}],
    [{"user_id": CHILD, "clerk_id": PARENT_SESSION}],
    [{"user_id": CHILD, "clerk_id": CHILD_SESSION.upper()}],
    [None], [{}], [{"user_id": str(CHILD), "clerk_id": CHILD_SESSION}],
])
def test_missing_malformed_or_conflicting_reverse_owner_is_refused_before_child_progress(family, reverse_rows):
    family.store["athlete_profiles"][CHILD] = CHILD_SESSION
    family.store["reverse_override"] = reverse_rows
    family.identity["clerk"] = CHILD_SESSION
    before = deepcopy(family.store["athlete_profiles"])
    assert recover(family).status_code == 409
    assert_combine_and_help_refuse(family)
    assert family.store["athlete_profiles"] == before


@pytest.mark.parametrize("bad_uid", [None, True, 0, -1, float(CHILD), str(CHILD)])
def test_malformed_forward_athlete_never_becomes_child_progress(family, bad_uid):
    family.store["athlete_profiles"][bad_uid] = CHILD_SESSION
    family.identity["clerk"] = CHILD_SESSION
    before = deepcopy(family.store["athlete_profiles"])
    assert recover(family).status_code == 409
    assert_combine_and_help_refuse(family)
    assert family.store["athlete_profiles"] == before
