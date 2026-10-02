"""Junior GMTM entry: eligibility, code exchange, SPARQ session, per-request gate.

GMTM sign-in is the only sign-in (Joey, 2026-10-01). Every outside service is
stubbed: GMTM redeem goes through junior_entry.http, GMTM facts through junior_eligibility.reader, Agent rows
through MemoryStore / WorkspaceStore. conftest blocks real DB/network.
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
import os
import json
import time

from fastapi import HTTPException
from fastapi.testclient import TestClient
import jwt
import pytest

import athlete_workspace as workspace
import auth
import candidate_app
import junior_eligibility as elig
import junior_entry
import workspace_bootstrap
from backend.tests.junior_fakes import MemoryStore
from backend.tests.test_candidate_app import signed  # noqa: F401  (fixture)
import asyncio
from backend.tests.test_profile_candidate_app import ENTRY_ENV, SESSION_SECRET, profile_app, session  # noqa: F401  (fixtures)
from backend.tests.workspace_fixture_store import WorkspaceStore

TODAY = date.today()
SECRET = "synthetic-entry-secret"
CODE, STATE = "c" * 32, "s" * 32
USER_ID = 7301
SUBJECT = f"gmtm_{USER_ID}"  # the SPARQ session subject for a new athlete
GSH = hashlib.sha256(b"synthetic-gmtm-session-id").hexdigest()


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
    """Stub for junior_entry.http: GMTM redeem only."""
    def __init__(self, *, redeem=(200, {"user_id": USER_ID})):
        self.redeem, self.calls = redeem, []

    def __call__(self, method, url, *, headers, body=None, params=None):
        self.calls.append((method, url, headers, body, params))
        assert url == "https://gmtm-api.example.invalid/v2/sparq/redeem", url
        assert headers == {"x-sparq-secret": "synthetic-handoff"}
        return self.redeem


@pytest.fixture
def entry(profile_app, monkeypatch):
    for name, value in ENTRY_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SPARQ_ENTRY_SECRET", SECRET)
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
    return client.post("/gmtm-entry/exchange", headers=headers, json={"code": CODE, "state": STATE, "gsh": GSH} if body is None else body)


def bearer(token):
    return {"Authorization": "Bearer " + token}


def test_eligible_junior_gets_a_24_hour_session_token_and_link(entry):
    app, store, services, bootstraps = entry
    with TestClient(app) as client:
        response = post_exchange(client)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"eligible", "token"} and body["eligible"] is True
    assert response.headers["cache-control"] == "private, no-store"
    assert services.calls[0][3] == {"code": CODE, "state": STATE}  # gsh never goes to GMTM
    claims = jwt.decode(body["token"], SESSION_SECRET, algorithms=["HS256"], audience="profile")
    assert set(claims) == {"sub", "jti", "gsh", "aud", "iat", "exp"} and claims["aud"] == "profile"
    assert claims["sub"] == SUBJECT and claims["gsh"] == GSH
    assert claims["exp"] - claims["iat"] == 24 * 3600
    assert store.sessions == {SUBJECT: claims["jti"]} and len(claims["jti"]) >= 43
    assert store.links == {USER_ID: SUBJECT}
    assert bootstraps == [(SUBJECT, USER_ID)]
    assert [(e["clerk_id"], e["user_id"]) for e in store.entries] == [(SUBJECT, USER_ID)]
    assert store.refusals == []


def test_new_entry_replaces_the_old_session(entry):
    app, store, *_ = entry
    store.accept_notice(SUBJECT, datetime.now(timezone.utc))
    with TestClient(app) as client:
        first = post_exchange(client).json()["token"]
        assert client.get("/api/athlete/parent-notice", headers=bearer(first)).status_code == 200
        second = post_exchange(client).json()["token"]
        old = client.get("/api/athlete/parent-notice", headers=bearer(first))
        assert old.status_code == 401 and "session ended" in old.json()["detail"]
        assert client.get("/api/athlete/parent-notice", headers=bearer(second)).status_code == 200


def test_sign_out_ends_the_session_and_is_idempotent(entry):
    app, store, *_ = entry
    with TestClient(app) as client:
        token = post_exchange(client).json()["token"]
        assert client.post(junior_entry.SIGN_OUT_PATH).status_code == 401
        assert client.post(junior_entry.SIGN_OUT_PATH, headers=bearer(token)).json() == {"signed_out": True}
        assert store.sessions == {}
        assert client.get("/api/athlete/parent-notice", headers=bearer(token)).status_code == 401
        assert client.post(junior_entry.SIGN_OUT_PATH, headers=bearer(token)).status_code == 200


def test_session_token_verification(entry, session):
    app, *_ = entry
    now = int(time.time())
    with TestClient(app) as client:
        get = lambda headers: client.get("/api/athlete/parent-notice", headers=headers).status_code
        assert get(session(sub="user_any")) == 200
        assert get(session(sub="user_any", exp=now - 1)) == 401                      # expired
        assert get(session(sub="user_any", secret="w" * 40)) == 401                  # wrong secret
        assert get(session(sub="user_any", active=False)) == 401                     # jti not active
        assert get(session(sub="user_any", jti=None)) == 401                         # no jti
        assert get(session(sub="user_any", gsh="A" * 64)) == 401                     # gsh not sha256 hex
        none_alg = jwt.encode({"sub": "user_any", "jti": "x", "gsh": GSH, "iat": now, "exp": now + 60}, None, algorithm="none")
        assert get(bearer(none_alg)) == 401


def test_short_session_secret_disables_entry(entry, monkeypatch):
    app, _, services, _ = entry
    with TestClient(app) as client:
        monkeypatch.setenv("SPARQ_SESSION_SECRET", "x" * 31)
        assert post_exchange(client).status_code == 503
    assert services.calls == []


def test_legacy_and_combine_admit_only_allowlisted_sparq_sessions(configured_combine, signed, session):
    # Neither app overrides auth.require_identity: SPARQ session + SPARQ_TEST_ALLOWLIST.
    assert auth.require_identity not in configured_combine.dependency_overrides
    import main
    assert auth.require_identity not in main.app.dependency_overrides
    allowed = signed("user_allowed")["Authorization"]
    assert asyncio.run(junior_entry.require_allowlisted_identity(allowed, "combine")) == "user_allowed"
    with TestClient(configured_combine) as client:
        get = lambda headers: client.get("/api/profile/by-owner/user_any", headers=headers).status_code
        assert get(signed("user_any", allowlisted=False)) == 403      # GMTM user not allow-listed
        assert get(session(sub="user_junior", aud="combine")) == 403  # no recorded entry
        assert get(session(sub="user_junior")) == 401                 # profile token on combine
        assert get({"Authorization": "Bearer not-a-token"}) == 401


@pytest.mark.parametrize("issued, accepted_by", [("profile", "combine"), ("combine", "legacy"),
                                                 ("legacy", "profile"), ("combine", "profile")])
def test_a_token_for_one_surface_is_refused_on_every_other(entry, signed, issued, accepted_by):
    # Same secret, same active jti, allow-listed user: only the audience differs.
    headers = signed("user_cross", aud=issued)["Authorization"]
    with pytest.raises(HTTPException) as caught:
        if accepted_by == "profile":
            asyncio.run(junior_entry.require_identity(headers))
        else:
            asyncio.run(junior_entry.require_allowlisted_identity(headers, accepted_by))
    assert caught.value.status_code == 401
    same = signed("user_same", aud=accepted_by)["Authorization"]
    if accepted_by == "profile":
        assert asyncio.run(junior_entry.require_identity(same)) == "user_same"
    else:
        assert asyncio.run(junior_entry.require_allowlisted_identity(same, accepted_by)) == "user_same"


def test_cross_surface_token_is_401_over_http(configured_combine, signed, session):
    import main
    profile_token = session(sub="user_cross")              # aud=profile, active jti
    with TestClient(configured_combine) as client:
        assert client.get("/api/profile/by-owner/user_cross", headers=profile_token).status_code == 401
    combine_token = signed("user_cross2")                  # aud=combine, allow-listed
    with TestClient(main.app) as client:
        assert client.get("/api/profile/by-owner/user_cross2", headers=combine_token).status_code == 401


@pytest.mark.parametrize("allowed, eligible", [("", False), (str(USER_ID), True)])
def test_combine_exchange_admits_only_the_allowlist(configured_combine, monkeypatch, allowed, eligible):
    monkeypatch.setenv("SPARQ_ENTRY_SECRET", SECRET)
    monkeypatch.setenv("SPARQ_TEST_ALLOWLIST", allowed)
    store = MemoryStore()
    monkeypatch.setattr(junior_entry, "store", store)
    monkeypatch.setattr(junior_entry, "http", FakeServices())
    monkeypatch.setattr(elig, "reader", lambda uid: (True, years_ago(15)))  # a junior, but not allow-listed
    monkeypatch.setattr(workspace_bootstrap, "ensure_workspace_profile", lambda c, u: None)
    with TestClient(configured_combine) as client:
        body = post_exchange(client).json()
    assert body["eligible"] is eligible and ("token" in body) is eligible
    if eligible:
        assert jwt.decode(body["token"], SESSION_SECRET, algorithms=["HS256"], audience="combine")["sub"]
    assert [r["decision"] for r in store.refusals] == ([] if eligible else ["ineligible"])


@pytest.fixture
def configured_combine(monkeypatch, session):
    from backend.tests.test_candidate_app import ENV
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    return candidate_app.create_app()


def test_athlete_linked_to_an_old_owner_id_keeps_it_and_its_rows(entry, monkeypatch):
    # No repoint: the existing link id becomes the SPARQ subject, so rows keyed by it
    # (workspace, college list, notices) stay reachable. It works only inside a
    # SPARQ-signed token.
    app, store, *_ = entry
    old = "user_old_subject"
    store.links[USER_ID] = old
    store.accept_notice(old, datetime.now(timezone.utc))
    monkeypatch.setattr(workspace, "_get_agent_db", WorkspaceStore([{"id": 93, "user_id": USER_ID, "clerk_id": old}]).connect)
    with TestClient(app) as client:
        token = post_exchange(client).json()["token"]
        assert jwt.decode(token, SESSION_SECRET, algorithms=["HS256"], audience="profile")["sub"] == old
        assert store.links == {USER_ID: old} and store.sessions == {old: jwt.decode(token, SESSION_SECRET, algorithms=["HS256"], audience="profile")["jti"]}
        assert [e["clerk_id"] for e in store.entries] == [old]
        assert client.get("/api/athlete/workspace", headers=bearer(token)).status_code == 200
        assert client.get(f"/api/workspace/colleges/{SUBJECT}", headers=bearer(token)).status_code == 403
    # Owner check passes for the old id (the handler then needs the college DB, blocked offline).
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get(f"/api/workspace/colleges/{old}", headers=bearer(token)).status_code not in (401, 403)


def test_mysql_link_never_overwrites_an_existing_owner(monkeypatch):
    class Cursor:
        def __init__(self, db): self.db = db
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, sql, params=None): self.db.sql.append(" ".join(sql.split()))
        def fetchone(self):
            last = self.db.sql[-1]
            if "GET_LOCK" in last: return {"acquired": 1}
            if "SELECT clerk_id FROM athlete_profiles WHERE user_id" in last: return self.db.owner
            return None
    class DB:
        def __init__(self, owner): self.owner, self.sql, self.committed = owner, [], False
        def cursor(self): return Cursor(self)
        def begin(self): pass
        def commit(self): self.committed = True
        def rollback(self): pass
        def close(self): pass
    for owner, ok in (({"clerk_id": SUBJECT}, True), ({"clerk_id": "user_someone_else"}, False)):
        db = DB(owner)
        monkeypatch.setattr(junior_entry.MySQLStore, "_db", lambda self: db)
        if ok:
            junior_entry.MySQLStore().ensure_link(SUBJECT, USER_ID)
        else:
            with pytest.raises(junior_entry.LinkConflict):
                junior_entry.MySQLStore().ensure_link(SUBJECT, USER_ID)
        assert db.committed is ok
        assert not any(q.startswith("UPDATE") for q in db.sql)
        assert any(q.startswith("INSERT INTO athlete_profiles") and "ON DUPLICATE KEY UPDATE user_id = user_id" in q for q in db.sql)


@pytest.mark.parametrize("facts", [
    (True, years_ago(12)), (True, None), (False, years_ago(15)), (True, years_ago(18)),
], ids=["under-13", "no-dob", "not-in-cohort", "18-plus"])
def test_ineligible_gets_no_account_and_only_a_refusal_row(entry, monkeypatch, facts):
    app, store, services, bootstraps = entry
    monkeypatch.setattr(elig, "reader", lambda uid: facts)
    with TestClient(app) as client:
        response = post_exchange(client)
    assert response.status_code == 200 and response.json() == {"eligible": False}
    assert store.sessions == {} and store.links == {} and store.entries == [] and bootstraps == []
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


@pytest.mark.parametrize("body", [{}, {"code": CODE, "gsh": GSH}, {"code": "short", "state": STATE, "gsh": GSH},
                                  {"code": CODE, "state": "bad state with spaces", "gsh": GSH}, {"code": 1, "state": STATE, "gsh": GSH},
                                  {"code": CODE, "state": STATE}, {"code": CODE, "state": STATE, "gsh": "raw-gmtm-session-id"},
                                  {"code": CODE, "state": STATE, "gsh": GSH.upper()}])
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
    assert store.sessions == {} and store.entries == [] and store.refusals == []


# ── Per-request gate ─────────────────────────────────────────────────────────────

LINK = {"id": 93, "user_id": USER_ID, "clerk_id": SUBJECT}


@pytest.fixture
def junior(entry, monkeypatch):
    app, store, services, _ = entry
    with TestClient(app) as client:
        token = post_exchange(client).json()["token"]
    monkeypatch.setattr(workspace, "_get_agent_db", WorkspaceStore([LINK]).connect)
    return app, store, bearer(token)


def test_parent_notice_blocks_personal_routes_until_accepted(junior):
    app, store, headers = junior
    with TestClient(app) as client:
        blocked = client.get("/api/athlete/workspace", headers=headers)
        assert blocked.status_code == 403 and blocked.json()["detail"] == "parent_notice_required"
        assert client.get("/api/athlete/parent-notice", headers=headers).json() == {"required": True, "accepted": False}
        assert client.post("/api/athlete/parent-notice", headers=headers).json() == {"required": True, "accepted": True}
        assert client.get("/api/athlete/workspace", headers=headers).status_code == 200
    assert store.notices[SUBJECT]["attested_by_session_kind"] == "unknown"
    assert set(store.notices[SUBJECT]) == {"accepted_at", "attested_by_session_kind"}


def test_session_without_entry_row_is_refused_even_on_notice_routes(profile_app, session):
    with TestClient(profile_app) as client:
        for method in ("GET", "POST"):
            response = client.request(method, "/api/athlete/parent-notice", headers=session(entry=False))
            assert response.status_code == 403, response.text


def test_session_older_than_24_hours_is_denied(junior):
    app, store, headers = junior
    store.accept_notice(SUBJECT, datetime.now(timezone.utc))
    with TestClient(app) as client:
        assert client.get("/api/athlete/workspace", headers=headers).status_code == 200
        store.entries[-1]["entered_at"] -= timedelta(hours=24, seconds=1)
        assert client.get("/api/athlete/workspace", headers=headers).status_code == 401
        assert client.get("/api/athlete/parent-notice", headers=headers).status_code == 401


def test_dob_change_is_denied_on_recheck_after_cache_window(junior, monkeypatch):
    app, store, headers = junior
    store.accept_notice(SUBJECT, datetime.now(timezone.utc))
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


def test_junior_is_admitted_but_a_session_without_entry_is_not(junior, session):
    # Was the adult-file bypass test: the adult file is gone, so a valid session
    # for any subject without an entry row must now be refused (fail closed).
    app, store, headers = junior
    store.accept_notice(SUBJECT, datetime.now(timezone.utc))
    with TestClient(app) as client:
        assert client.get("/api/athlete/workspace", headers=headers).status_code == 200
        assert client.get("/api/athlete/workspace", headers=session(sub="user_adult", entry=False)).status_code == 403


# ── Route table: 401 without auth, 403 for another clerk_id ─────────────────────

def _personal_routes(app):
    for route in app.routes:
        if route.path in ("/health", junior_entry.EXCHANGE_PATH, junior_entry.SIGN_OUT_PATH) or route.path.startswith("/api/claims/"):
            continue  # health is public; exchange uses its server secret; sign-out has its own test; claims are 403 in the pilot
        for method in sorted(route.methods - {"HEAD"}):
            yield method, route.path


@pytest.mark.parametrize("origin", ["loopback", "hosted"])
def test_every_personal_route_requires_auth_and_owner(profile_app, session, monkeypatch, origin):
    if origin == "hosted":
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://sparq.gmtm.com")
    store = MemoryStore()
    store.record_entry(SUBJECT, USER_ID, datetime.now(timezone.utc))
    store.accept_notice(SUBJECT, datetime.now(timezone.utc))
    monkeypatch.setattr(junior_entry, "store", store)
    headers = session(sub=SUBJECT)
    monkeypatch.setattr(elig, "reader", lambda uid: (True, years_ago(15)))
    routes = list(_personal_routes(profile_app))
    assert len(routes) >= 10
    owned = [r for r in routes if "{clerk_id}" in r[1]]
    assert owned, "expected at least one clerk_id route"
    with TestClient(profile_app) as client:
        for method, route_path in routes:
            url = route_path.replace("{clerk_id}", SUBJECT)
            response = client.request(method, url, json={})
            # A disabled feature answers 404 before auth (no data).
            disabled = response.status_code == 404 and "disabled" in response.text
            assert response.status_code == 401 or disabled, (method, route_path, response.text)
        for method, route_path in owned:
            response = client.request(method, route_path.replace("{clerk_id}", "user_other"), headers=headers)
            assert response.status_code == 403, (method, route_path, response.text)


@pytest.mark.parametrize("name", ["SPARQ_SESSION_SECRET", "GMTM_API_URL", "SPARQ_HANDOFF_SECRET"])
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
    full = {"SPARQ_ENTRY_SECRET": "a", "SPARQ_HANDOFF_SECRET": "b", "GMTM_API_URL": "http://127.0.0.1:9", "SPARQ_SESSION_SECRET": "c" * 32}
    assert junior_entry.entry_configuration({}) is None
    assert junior_entry.entry_configuration(full)["GMTM_API_URL"] == "http://127.0.0.1:9"
    for bad in ("", "c" * 31):
        with pytest.raises(ValueError):
            junior_entry.entry_configuration({**full, "SPARQ_SESSION_SECRET": bad})
    monkeypatch.setenv("SPARQ_ENTRY_SECRET", "only-one")
    with pytest.raises(ValueError):
        with TestClient(profile_app):
            pass


# ── Hosted startup: GMTM entry replaces the removed adult admission file ────────

@pytest.mark.parametrize("origin", ["loopback", "hosted"])
def test_valid_session_without_entry_row_is_refused_on_every_personal_route(profile_app, session, monkeypatch, origin):
    # sparq_sessions row (active jti) but no sparq_entries row: gate() is False -> 403.
    if origin == "hosted":
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://sparq.gmtm.com")
    monkeypatch.setattr(workspace, "_get_agent_db", lambda: pytest.fail("no source work for a refused session"))
    headers = session(sub=SUBJECT, entry=False)
    assert junior_entry.store.session_jti(SUBJECT) and junior_entry.store.latest_entry(SUBJECT) is None
    routes = list(_personal_routes(profile_app))
    assert len(routes) >= 10
    with TestClient(profile_app) as client:
        for method, route_path in routes:
            response = client.request(method, route_path.replace("{clerk_id}", SUBJECT), headers=headers, json={})
            assert response.status_code == 403, (method, route_path, response.text)
            assert response.headers["cache-control"] == "private, no-store"
        assert client.get("/health").status_code == 200


def test_hosted_profile_starts_with_gmtm_entry_and_no_admission_settings(profile_app, monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://sparq.gmtm.com")
    monkeypatch.delenv("PROFILE_ADMISSION_ENABLED", raising=False)
    monkeypatch.delenv("PROFILE_ADMISSION_FILE", raising=False)
    for name, value in ENTRY_ENV.items():
        monkeypatch.setenv(name, value)
    with TestClient(profile_app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["gmtm_sign_in_configured"] is True
        assert "pilot_admission_enabled" not in response.json()


def test_hosted_profile_without_gmtm_entry_refuses_startup(profile_app, monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://127.0.0.1:3218,https://sparq.gmtm.com")
    for name in junior_entry.ENTRY_KEYS:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(candidate_app.CandidateConfigurationError, match="GMTM entry configuration"):
        with TestClient(profile_app):
            pass


def test_loopback_profile_runs_without_entry_and_refuses_sessions(profile_app):
    for name in junior_entry.ENTRY_KEYS:
        assert not os.environ.get(name)
    with TestClient(profile_app) as client:
        response = client.get("/health")
        assert response.status_code == 200 and response.json()["gmtm_sign_in_configured"] is False
        assert client.get("/api/athlete/workspace").status_code == 401
