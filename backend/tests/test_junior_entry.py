"""Junior GMTM entry: eligibility, code exchange, Clerk ticket, per-request gate.

Every outside service is stubbed: GMTM redeem and Clerk go through
junior_entry.http, GMTM facts through junior_eligibility.reader, Agent rows
through MemoryStore / WorkspaceStore. conftest blocks real DB/network.
"""
from datetime import date, datetime, timedelta, timezone
import json

from fastapi.testclient import TestClient
import pytest

import athlete_workspace as workspace
import junior_eligibility as elig
import junior_entry
import workspace_bootstrap
from backend.tests.junior_fakes import MemoryStore
from backend.tests.test_candidate_app import signed  # noqa: F401  (fixture)
from backend.tests.test_profile_candidate_app import profile_app  # noqa: F401  (fixture)
from backend.tests.workspace_fixture_store import WorkspaceStore

TODAY = date.today()
SECRET = "synthetic-entry-secret"
CODE, STATE = "c" * 32, "s" * 32
USER_ID, CLERK = 7301, "user_junior"


def years_ago(years, days=0):
    try:
        d = TODAY.replace(year=TODAY.year - years)
    except ValueError:  # Feb 29
        d = TODAY.replace(year=TODAY.year - years, day=28)
    return d - timedelta(days=days)


# ── Pure eligibility ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("member,dob,expected", [
    (True, years_ago(13), True),             # 13th birthday today
    (True, years_ago(13, days=-1), False),   # 13 tomorrow -> 12
    (True, years_ago(17), True),
    (True, years_ago(18, days=-1), True),    # still 17, 18 tomorrow
    (True, years_ago(18), False),            # 18th birthday today
    (True, years_ago(30), False),
    (True, None, False),
    (False, years_ago(15), False),
    (True, datetime.combine(years_ago(15), datetime.min.time()), True),
    (True, TODAY + timedelta(days=1), False),
])
def test_decide_age_and_cohort(member, dob, expected):
    assert elig.decide(USER_ID, allowed=frozenset(), cohort_member=member, dob=dob, today=TODAY) is expected


def test_allowlist_admits_without_reading_gmtm(monkeypatch):
    monkeypatch.setattr(elig, "reader", lambda uid: pytest.fail("allow-list must not read GMTM"))
    assert elig.is_eligible(5, env={"SPARQ_TEST_ALLOWLIST": " 9, 5 ,x,-3"}) is True
    assert elig.allowlist({"SPARQ_TEST_ALLOWLIST": "9, 5 ,x,-3,0"}) == {5, 9}
    assert elig.decide(0, allowed=frozenset({0}), cohort_member=True, dob=years_ago(15), today=TODAY) is False


# ── Exchange ─────────────────────────────────────────────────────────────────────

class FakeServices:
    """Stub for junior_entry.http: GMTM redeem + Clerk Backend API."""
    def __init__(self, *, redeem=(200, {"user_id": USER_ID}), existing=None):
        self.redeem, self.users, self.calls = redeem, list(existing or []), []
        self.create_status = None  # force a Clerk failure on POST /users

    def __call__(self, method, url, *, headers, body=None, params=None):
        self.calls.append((method, url, headers, body, params))
        if url == "https://gmtm-api.example.invalid/v2/sparq/redeem":
            assert headers == {"x-sparq-secret": "synthetic-handoff"}
            return self.redeem
        assert url.startswith(junior_entry.CLERK_API) and headers == {"Authorization": "Bearer sk_test_synthetic"}
        path = url[len(junior_entry.CLERK_API):]
        if (method, path) == ("GET", "/users"):
            return 200, [u for u in self.users if u["external_id"] == params["external_id"]]
        if (method, path) == ("POST", "/users"):
            # Like an instance that requires an identifier: no username -> 422.
            if self.create_status or not body.get("username"):
                return self.create_status or 422, {"errors": [{"code": "form_data_missing"}]}
            assert len(body["username"]) <= 64 and body["username"].replace("_", "").isalnum()
            user = {"id": CLERK, "external_id": body["external_id"], "username": body["username"]}
            self.users.append(user)
            return 200, user
        if (method, path) == ("POST", "/sign_in_tokens"):
            return 200, {"token": "ticket-synthetic"}
        raise AssertionError((method, url))

    def clerk_calls(self):
        return [(m, u[len(junior_entry.CLERK_API):], b) for m, u, _, b, _ in self.calls if u.startswith(junior_entry.CLERK_API)]


@pytest.fixture
def entry(profile_app, monkeypatch):
    monkeypatch.setenv("SPARQ_ENTRY_SECRET", SECRET)
    monkeypatch.setenv("SPARQ_HANDOFF_SECRET", "synthetic-handoff")
    monkeypatch.setenv("GMTM_API_URL", "https://gmtm-api.example.invalid")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_synthetic")
    monkeypatch.delenv("SPARQ_TEST_ALLOWLIST", raising=False)
    store, services = MemoryStore(), FakeServices()
    monkeypatch.setattr(junior_entry, "store", store)
    monkeypatch.setattr(junior_entry, "http", services)
    monkeypatch.setattr(elig, "reader", lambda uid: (True, years_ago(15)))
    bootstraps = []
    monkeypatch.setattr(workspace_bootstrap, "ensure_workspace_profile", lambda c, u: bootstraps.append((c, u)))
    return profile_app, store, services, bootstraps


def post_exchange(client, secret=SECRET, body=None):
    headers = {} if secret is None else {"x-sparq-entry-secret": secret}
    return client.post("/gmtm-entry/exchange", headers=headers, json={"code": CODE, "state": STATE} if body is None else body)


def test_eligible_junior_gets_a_60_second_ticket_and_link(entry):
    app, store, services, bootstraps = entry
    with TestClient(app) as client:
        response = post_exchange(client)
    assert response.status_code == 200, response.text
    assert response.json() == {"eligible": True, "ticket": "ticket-synthetic"}
    assert response.headers["cache-control"] == "private, no-store"
    assert services.calls[0][3] == {"code": CODE, "state": STATE}
    assert services.clerk_calls() == [
        ("GET", "/users", None),
        ("POST", "/users", {"external_id": f"gmtm:{USER_ID}", "username": f"gmtm_{USER_ID}", "skip_password_requirement": True}),
        ("POST", "/sign_in_tokens", {"user_id": CLERK, "expires_in_seconds": 60}),
    ]
    assert store.links == {USER_ID: CLERK}
    assert bootstraps == [(CLERK, USER_ID)]
    assert [(e["clerk_id"], e["user_id"]) for e in store.entries] == [(CLERK, USER_ID)]
    assert store.refusals == []


def test_existing_clerk_user_is_reused(entry):
    app, store, services, _ = entry
    services.users.append({"id": CLERK, "external_id": f"gmtm:{USER_ID}"})
    with TestClient(app) as client:
        assert post_exchange(client).json()["eligible"] is True
    assert [c[:2] for c in services.clerk_calls()] == [("GET", "/users"), ("POST", "/sign_in_tokens")]


def test_athlete_linked_to_another_account_is_a_conflict_without_ticket(entry):
    app, store, services, _ = entry
    store.links[USER_ID] = "user_someone_else"
    with TestClient(app) as client:
        assert post_exchange(client).status_code == 409
    assert ("POST", "/sign_in_tokens") not in [c[:2] for c in services.clerk_calls()]
    assert store.entries == []


@pytest.mark.parametrize("facts", [
    (True, years_ago(12)), (True, None), (False, years_ago(15)), (True, years_ago(18)),
], ids=["under-13", "no-dob", "not-in-cohort", "18-plus"])
def test_ineligible_gets_no_account_and_only_a_refusal_row(entry, monkeypatch, facts):
    app, store, services, bootstraps = entry
    monkeypatch.setattr(elig, "reader", lambda uid: facts)
    with TestClient(app) as client:
        response = post_exchange(client)
    assert response.status_code == 200 and response.json() == {"eligible": False}
    assert services.clerk_calls() == [] and store.links == {} and store.entries == [] and bootstraps == []
    assert store.notices == {}
    assert len(store.refusals) == 1
    refusal = store.refusals[0]
    assert set(refusal) == {"user_id", "decision", "decided_at"}
    assert (refusal["user_id"], refusal["decision"]) == (USER_ID, "ineligible")
    assert "dob" not in json.dumps(refusal, default=str) and str(years_ago(15)) not in json.dumps(refusal, default=str)


def test_allowlisted_user_is_admitted(entry, monkeypatch):
    app, store, *_ = entry
    monkeypatch.setenv("SPARQ_TEST_ALLOWLIST", str(USER_ID))
    monkeypatch.setattr(elig, "reader", lambda uid: (False, None))
    with TestClient(app) as client:
        assert post_exchange(client).json()["eligible"] is True


@pytest.mark.parametrize("secret", [None, "", "wrong-secret", SECRET + "x"])
def test_missing_or_wrong_secret_is_rejected_before_any_service(entry, secret):
    app, store, services, _ = entry
    with TestClient(app) as client:
        assert post_exchange(client, secret=secret).status_code == 401
    assert services.calls == [] and store.refusals == [] and store.entries == []


def test_unset_secret_fails_closed(entry, monkeypatch):
    app, _, services, _ = entry
    with TestClient(app) as client:
        monkeypatch.delenv("SPARQ_ENTRY_SECRET")
        assert post_exchange(client).status_code == 503
        assert post_exchange(client, secret="").status_code == 503
    assert services.calls == []


@pytest.mark.parametrize("body", [{}, {"code": CODE}, {"code": "short", "state": STATE},
                                  {"code": CODE, "state": "bad state with spaces"}, {"code": 1, "state": STATE}])
def test_malformed_body_is_rejected(entry, body):
    app, _, services, _ = entry
    with TestClient(app) as client:
        assert post_exchange(client, body=body).status_code == 400
    assert services.calls == []


@pytest.mark.parametrize("redeem", [(401, None), (200, {}), (200, {"user_id": 0}), (200, {"user_id": "7301"})])
def test_gmtm_rejection_including_state_mismatch_gets_no_ticket(entry, redeem):
    # GMTM binds the code to the state; a mismatched state is a redeem failure.
    app, store, services, _ = entry
    services.redeem = redeem
    with TestClient(app) as client:
        assert post_exchange(client).status_code == 401
    assert services.clerk_calls() == [] and store.entries == [] and store.refusals == []


# ── Per-request gate ─────────────────────────────────────────────────────────────

LINK = {"id": 93, "user_id": USER_ID, "clerk_id": CLERK}


@pytest.fixture
def junior(entry, monkeypatch, signed):
    app, store, services, _ = entry
    with TestClient(app) as client:
        assert post_exchange(client).json()["eligible"] is True
    monkeypatch.setattr(workspace, "_get_agent_db", WorkspaceStore([LINK]).connect)
    return app, store, signed(sub=CLERK)


def test_parent_notice_blocks_personal_routes_until_accepted(junior):
    app, store, headers = junior
    with TestClient(app) as client:
        blocked = client.get("/api/athlete/workspace", headers=headers)
        assert blocked.status_code == 403 and blocked.json()["detail"] == "parent_notice_required"
        assert client.get("/api/athlete/parent-notice", headers=headers).json() == {"required": True, "accepted": False}
        assert client.post("/api/athlete/parent-notice", headers=headers).json() == {"required": True, "accepted": True}
        assert client.get("/api/athlete/workspace", headers=headers).status_code == 200
    assert store.notices[CLERK]["attested_by_session_kind"] == "unknown"
    assert set(store.notices[CLERK]) == {"accepted_at", "attested_by_session_kind"}


def test_non_entry_user_has_no_notice_requirement(profile_app, signed):
    with TestClient(profile_app) as client:
        assert client.get("/api/athlete/parent-notice", headers=signed()).json() == {"required": False, "accepted": False}


def test_session_older_than_24_hours_is_denied(junior):
    app, store, headers = junior
    store.accept_notice(CLERK, datetime.now(timezone.utc))
    with TestClient(app) as client:
        assert client.get("/api/athlete/workspace", headers=headers).status_code == 200
        store.entries[-1]["entered_at"] -= timedelta(hours=24, seconds=1)
        assert client.get("/api/athlete/workspace", headers=headers).status_code == 401
        assert client.get("/api/athlete/parent-notice", headers=headers).status_code == 401


def test_dob_change_is_denied_on_recheck_after_cache_window(junior, monkeypatch):
    app, store, headers = junior
    store.accept_notice(CLERK, datetime.now(timezone.utc))
    clock = [1000.0]
    monkeypatch.setattr(elig.time, "monotonic", lambda: clock[0])
    with TestClient(app) as client:
        assert client.get("/api/athlete/workspace", headers=headers).status_code == 200
        monkeypatch.setattr(elig, "reader", lambda uid: (True, years_ago(18)))
        clock[0] += elig.CACHE_SECONDS - 1
        assert client.get("/api/athlete/workspace", headers=headers).status_code == 200  # cached
        clock[0] += 2
        denied = client.get("/api/athlete/workspace", headers=headers)
        assert denied.status_code == 403 and "junior flag athletes" in denied.json()["detail"]


def test_store_failure_fails_closed(junior, monkeypatch):
    app, store, headers = junior
    monkeypatch.setattr(store, "latest_entry", lambda c: (_ for _ in ()).throw(RuntimeError("db down")))
    with TestClient(app) as client:
        response = client.get("/api/athlete/workspace", headers=headers)
    assert response.status_code == 503 and "db down" not in response.text


def test_junior_bypasses_adult_file_but_others_still_need_it(junior, monkeypatch, tmp_path, signed):
    app, store, headers = junior
    store.accept_notice(CLERK, datetime.now(timezone.utc))
    path = (tmp_path / "admission.json").resolve()
    path.write_text(json.dumps({"schema": 1, "admissions": []}))
    path.chmod(0o600)
    monkeypatch.setenv("PROFILE_ADMISSION_ENABLED", "true")
    monkeypatch.setenv("PROFILE_ADMISSION_FILE", str(path))
    with TestClient(app) as client:
        assert client.get("/api/athlete/workspace", headers=headers).status_code == 200
        assert client.get("/api/athlete/workspace", headers=signed(sub="user_adult")).status_code == 403


# ── Route table: 401 without auth, 403 for another clerk_id ─────────────────────

def _personal_routes(app):
    for route in app.routes:
        if route.path in ("/health", junior_entry.EXCHANGE_PATH) or route.path.startswith("/api/claims/"):
            continue  # health is public; exchange uses its server secret; claims are 403 in the pilot
        for method in sorted(route.methods - {"HEAD"}):
            yield method, route.path


@pytest.mark.parametrize("admission", ["loopback", "pilot"])
def test_every_personal_route_requires_auth_and_owner(profile_app, signed, monkeypatch, tmp_path, admission):
    if admission == "pilot":
        path = (tmp_path / "admission.json").resolve()
        path.write_text(json.dumps({"schema": 1, "admissions": []}))
        path.chmod(0o600)
        monkeypatch.setenv("PROFILE_ADMISSION_ENABLED", "true")
        monkeypatch.setenv("PROFILE_ADMISSION_FILE", str(path))
    store = MemoryStore()
    store.record_entry(CLERK, USER_ID, datetime.now(timezone.utc))
    store.accept_notice(CLERK, datetime.now(timezone.utc))
    monkeypatch.setattr(junior_entry, "store", store)
    monkeypatch.setattr(elig, "reader", lambda uid: (True, years_ago(15)))
    routes = list(_personal_routes(profile_app))
    assert len(routes) >= 10
    owned = [r for r in routes if "{clerk_id}" in r[1]]
    assert owned, "expected at least one clerk_id route"
    with TestClient(profile_app) as client:
        for method, route_path in routes:
            url = route_path.replace("{clerk_id}", CLERK)
            response = client.request(method, url, json={})
            # Loopback mode only: a disabled feature answers 404 before auth (no data).
            disabled = admission == "loopback" and response.status_code == 404 and "disabled" in response.text
            assert response.status_code == 401 or disabled, (method, route_path, response.text)
        for method, route_path in owned:
            response = client.request(method, route_path.replace("{clerk_id}", "user_other"), headers=signed(sub=CLERK))
            assert response.status_code == 403, (method, route_path, response.text)


def test_clerk_user_creation_rejection_is_503_with_no_ticket(entry):
    app, store, services, bootstraps = entry
    services.create_status = 422
    with TestClient(app) as client:
        response = post_exchange(client)
    assert response.status_code == 503 and "ticket" not in response.text
    assert [c[:2] for c in services.clerk_calls()] == [("GET", "/users"), ("POST", "/users")]
    assert store.links == {} and store.entries == [] and bootstraps == []


@pytest.mark.parametrize("name", ["CLERK_SECRET_KEY", "GMTM_API_URL", "SPARQ_HANDOFF_SECRET"])
def test_missing_setting_is_503_before_the_code_is_redeemed(entry, monkeypatch, name):
    app, store, services, _ = entry
    with TestClient(app) as client:
        monkeypatch.delenv(name)
        assert post_exchange(client).status_code == 503
    assert services.calls == [] and store.refusals == []


@pytest.mark.parametrize("url", ["http://gmtm-api.example.invalid", "ftp://x.example", "https://u:p@x.example", "not a url"])
def test_insecure_gmtm_url_is_503_before_redeem(entry, monkeypatch, url):
    app, _, services, _ = entry
    with TestClient(app) as client:
        monkeypatch.setenv("GMTM_API_URL", url)
        assert post_exchange(client).status_code == 503
    assert services.calls == []


def test_entry_configuration_is_off_complete_or_startup_error(profile_app, monkeypatch):
    full = {"SPARQ_ENTRY_SECRET": "a", "SPARQ_HANDOFF_SECRET": "b", "GMTM_API_URL": "http://127.0.0.1:9", "CLERK_SECRET_KEY": "c"}
    assert junior_entry.entry_configuration({}) is None
    assert junior_entry.entry_configuration(full)["GMTM_API_URL"] == "http://127.0.0.1:9"
    with pytest.raises(ValueError):
        junior_entry.entry_configuration({**full, "CLERK_SECRET_KEY": ""})
    monkeypatch.setenv("SPARQ_ENTRY_SECRET", "only-one")
    with pytest.raises(ValueError):
        with TestClient(profile_app):
            pass
