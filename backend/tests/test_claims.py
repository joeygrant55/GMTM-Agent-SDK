"""
Unit tests for claim tokens (spec 2a / 2f). No database, no network.

Run:  cd backend && python -m pytest tests/test_claims.py -q

Covers token validation and ownership acquisition with a transactional fake store.
The fake models conflicting writes and failure cleanup, not InnoDB isolation,
advisory-lock server semantics, or actual concurrent MySQL transactions.
"""

import os
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import threading

import pymysql
import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# conftest supplies fake config and blocks DB/dotenv/network before app imports.
import claims_api  # noqa: E402
from claims_api import (  # noqa: E402
    CLAIM_TTL_SECONDS,
    ClaimTokenError,
    mint_token,
    token_hash,
    verify_token,
)

SECRET = b"test-share-secret"
NOW = 1_800_000_000.0  # fixed clock


# ── Pure token helpers ───────────────────────────────────────────────────────

def test_mint_then_verify_roundtrip():
    tok = mint_token(4521, 1317, SECRET, now=NOW)
    data = verify_token(tok, SECRET, now=NOW + 60)
    assert data == {"user_id": 4521, "event_id": 1317, "exp": int(NOW + CLAIM_TTL_SECONDS)}
    assert "." in tok and len(tok.split(".")) == 2


def test_token_is_url_safe():
    tok = mint_token(999999, 1318, SECRET, now=NOW)
    assert all(ch.isalnum() or ch in "-_." for ch in tok)


def test_expired_token_is_410():
    tok = mint_token(1, 1317, SECRET, exp=int(NOW) + 10)
    with pytest.raises(ClaimTokenError) as e:
        verify_token(tok, SECRET, now=NOW + 10)  # exp is exclusive
    assert e.value.code == "expired"
    assert e.value.status_code == 410
    # One second before expiry is still valid.
    assert verify_token(tok, SECRET, now=NOW + 9)["user_id"] == 1


def test_tampered_payload_is_400():
    tok = mint_token(1, 1317, SECRET, now=NOW)
    payload_b64, sig = tok.split(".")
    # Forge a token for a different user by re-encoding the payload with the same signature.
    forged_payload = claims_api._b64e(b'{"u":2,"e":1317,"x":%d}' % int(NOW + CLAIM_TTL_SECONDS))
    assert forged_payload != payload_b64
    with pytest.raises(ClaimTokenError) as e:
        verify_token(f"{forged_payload}.{sig}", SECRET, now=NOW)
    assert e.value.code == "bad_signature"
    assert e.value.status_code == 400


def test_tampered_signature_is_400():
    tok = mint_token(1, 1317, SECRET, now=NOW)
    payload_b64, sig = tok.split(".")
    flipped = ("A" if sig[0] != "A" else "B") + sig[1:]
    with pytest.raises(ClaimTokenError) as e:
        verify_token(f"{payload_b64}.{flipped}", SECRET, now=NOW)
    assert e.value.code == "bad_signature"


def test_wrong_secret_is_400():
    tok = mint_token(1, 1317, SECRET, now=NOW)
    with pytest.raises(ClaimTokenError) as e:
        verify_token(tok, b"another-secret", now=NOW)
    assert e.value.status_code == 400


def test_tampered_and_expired_is_400_not_410():
    """Signature is checked first, so an attacker cannot probe expiry of forged tokens."""
    tok = mint_token(1, 1317, SECRET, exp=int(NOW) - 1)
    payload_b64, sig = tok.split(".")
    with pytest.raises(ClaimTokenError) as e:
        verify_token(f"{payload_b64}.{sig[:-2]}xx", SECRET, now=NOW)
    assert e.value.status_code == 400


@pytest.mark.parametrize("bad", ["", "nodot", ".", "a.", ".b", "!!!.@@@", "x" * 600, "abc.def.ghi"])
def test_malformed_tokens_are_400(bad):
    with pytest.raises(ClaimTokenError) as e:
        verify_token(bad, SECRET, now=NOW)
    assert e.value.status_code == 400


def test_signed_but_wrong_shape_is_400():
    payload = b'{"hello":"world"}'
    tok = f"{claims_api._b64e(payload)}.{claims_api._sign(payload, SECRET)}"
    with pytest.raises(ClaimTokenError) as e:
        verify_token(tok, SECRET, now=NOW)
    assert e.value.code == "malformed"


def test_token_hash_is_stable_and_distinct():
    a = mint_token(1, 1317, SECRET, now=NOW)
    b = mint_token(2, 1317, SECRET, now=NOW)
    assert token_hash(a) == token_hash(a)
    assert token_hash(a) != token_hash(b)
    assert len(token_hash(a)) == 64


# ── Endpoint tests with an in-memory fake DB ────────────────────────────────

class _FakeCursor:
    """Committed reads plus this connection's writes; never a real connection."""

    def __init__(self, db):
        self.db = db
        self.store = db.store
        self._result = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        params = params or ()
        s = " ".join(sql.split())
        with self.store["mutex"]:
            self.db.events.append(("sql", s, params))
            self._result = None
            self.rowcount = 0
            for prefix, error in list(self.store["failures"].items()):
                if s.startswith(prefix):
                    del self.store["failures"][prefix]
                    raise error
            self._execute(s, params)
        hook = self.store.get("after_execute")
        if hook:
            hook(self.db, s, params)

    def _execute(self, s, params):
        claims = self.db.rows("claims")
        if s.startswith("CREATE TABLE"):
            self._result = None
        elif s.startswith("SELECT GET_LOCK"):
            name, = params
            owner = self.store["named_locks"].get(name)
            acquired = self.store.get("lock_result", int(owner in (None, self.db)))
            if acquired == 1:
                self.store["named_locks"][name] = self.db
            self._result = {"acquired": acquired}
        elif s.startswith("SELECT RELEASE_LOCK"):
            name, = params
            assert self.store["named_locks"].get(name) is self.db
            del self.store["named_locks"][name]
        elif s.startswith("INSERT INTO claim_tokens"):
            thash, uid, eid, exp = params
            self.db.write("claims", thash, {
                "id": len(claims) + 1, "user_id": uid, "event_id": eid, "expires_at": exp,
                "opened_at": None, "claimed_at": None, "clerk_id": None,
            })
        elif s.startswith("SELECT id, user_id, event_id, opened_at, claimed_at, clerk_id FROM claim_tokens"):
            if s.endswith("FOR UPDATE"):
                assert self.db.in_transaction
                self.db.lock_row("claim", params[0])
            self._result = deepcopy(claims.get(params[0]))
        elif s.startswith("UPDATE claim_tokens SET opened_at"):
            key, row = next((k, deepcopy(r)) for k, r in claims.items() if r["id"] == params[0])
            if row["opened_at"] is None:
                row["opened_at"] = "now"
                self.db.write("claims", key, row)
                self.store["open_writes"] += 1
        elif s.startswith("SELECT user_id FROM athlete_profiles WHERE clerk_id"):
            clerk, requested_uid = params
            self._result = next(
                ({"user_id": uid} for uid, owner in self.db.rows("athlete_profiles").items()
                 if owner == clerk and uid != requested_uid), None,
            )
        elif s.startswith("SELECT clerk_id FROM athlete_profiles"):
            if s.endswith("FOR UPDATE"):
                self.db.lock_row("athlete", params[0])
            profiles = self.db.rows("athlete_profiles")
            self._result = {"clerk_id": profiles[params[0]]} if params[0] in profiles else None
        elif s.startswith("INSERT INTO athlete_profiles"):
            uid, clerk = params[:2]
            self.db.lock_row("athlete", uid)
            profiles = self.db.rows("athlete_profiles")
            # Model both the old overwrite and the new no-op so regressions fail.
            if uid not in profiles or "UPDATE clerk_id" in s:
                self.db.write("athlete_profiles", uid, clerk)
        elif s.startswith("UPDATE claim_tokens SET claimed_at"):
            clerk, row_id = params[:2]
            key, row = next((k, deepcopy(r)) for k, r in claims.items() if r["id"] == row_id)
            if not self.store.get("reject_claim_update") and row["claimed_at"] is None and row["clerk_id"] in (None, clerk):
                row["claimed_at"] = "now"
                row["clerk_id"] = clerk
                self.db.write("claims", key, row)
                self.rowcount = 1
        elif s.startswith("SELECT first_name FROM users"):
            self._result = {"first_name": "Ava"} if params[0] in self.store["users"] else None
        elif s.startswith("SELECT name FROM events"):
            self._result = {"name": "2027 Junior Digital Combine #2"} if params[0] == 1317 else None
        else:
            raise AssertionError(f"unexpected SQL in fake DB: {s}")

    def fetchone(self):
        return self._result


class _FakeDB:
    def __init__(self, store):
        self.store = store
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self.in_transaction = False
        self.pending = {"claims": {}, "athlete_profiles": {}}
        self.events = []
        store["connections"].append(self)

    def rows(self, table):
        return {**self.store[table], **self.pending[table]}

    def write(self, table, key, row):
        self.pending[table][key] = deepcopy(row)

    def lock_row(self, table, key):
        lock = (table, key)
        owner = self.store["row_locks"].get(lock)
        if owner not in (None, self):
            # Deliberately fail immediately; this is not a MySQL wait simulation.
            raise pymysql.err.OperationalError(1205, "fake row lock contention")
        self.store["row_locks"][lock] = self

    def _release_rows(self):
        for key, owner in list(self.store["row_locks"].items()):
            if owner is self:
                del self.store["row_locks"][key]

    def begin(self):
        self.events.append(("begin",))
        self.in_transaction = True

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        with self.store["mutex"]:
            self.events.append(("commit",))
            error = self.store["failures"].pop("commit", None)
            if error:
                raise error
            for table, rows in self.pending.items():
                self.store[table].update(deepcopy(rows))
                rows.clear()
            self.commits += 1
            self.in_transaction = False
            self._release_rows()

    def rollback(self):
        with self.store["mutex"]:
            self.events.append(("rollback",))
            self.rollbacks += 1
            for rows in self.pending.values():
                rows.clear()
            self.in_transaction = False
            self._release_rows()

    def close(self):
        with self.store["mutex"]:
            self.events.append(("close",))
            self.closed = True
            self._release_rows()
            for name, owner in list(self.store["named_locks"].items()):
                if owner is self:
                    del self.store["named_locks"][name]


@pytest.fixture
def client(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from auth import require_clerk_id

    store = {
        "claims": {}, "athlete_profiles": {}, "users": {4521, 4522}, "open_writes": 0,
        "connections": [], "named_locks": {}, "row_locks": {}, "failures": {},
        "mutex": threading.RLock(),
    }
    monkeypatch.setattr(claims_api, "_get_agent_db", lambda: _FakeDB(store))
    monkeypatch.setattr(claims_api, "_get_gmtm_db", lambda: _FakeDB(store))
    store["bootstrap_calls"] = []
    def _fake_bootstrap(clerk_id, user_id):
        store["bootstrap_calls"].append((clerk_id, user_id))
        return {"ready": True, "created": True, "profile_id": 1}
    monkeypatch.setattr(claims_api, "ensure_workspace_profile", _fake_bootstrap)

    app = FastAPI()
    app.include_router(claims_api.router)
    identity = {"clerk": "user_alpha"}
    app.dependency_overrides[require_clerk_id] = lambda: identity["clerk"]
    tc = TestClient(app)
    tc.store = store  # type: ignore[attr-defined]
    tc.identity = identity  # type: ignore[attr-defined]
    return tc


ADMIN = {"X-Claims-Admin": "test-admin-secret"}


def _mint(client, user_ids=(4521,), event_id=1317):
    res = client.post("/api/claims/mint", json={"user_ids": list(user_ids), "event_id": event_id}, headers=ADMIN)
    assert res.status_code == 200, res.text
    return res.json()


def test_mint_requires_admin_secret(client):
    assert client.post("/api/claims/mint", json={"user_ids": [4521], "event_id": 1317}).status_code == 401
    bad = {"X-Claims-Admin": "nope"}
    assert client.post("/api/claims/mint", json={"user_ids": [4521], "event_id": 1317}, headers=bad).status_code == 401


def test_mint_returns_url_per_user_and_stores_only_hash(client):
    out = _mint(client, (4521, 4522, 4521))
    assert [o["user_id"] for o in out] == [4521, 4522]  # deduped
    for o in out:
        assert o["url"] == f"https://sparq-agent.test/claim/{o['token']}"
        assert token_hash(o["token"]) in client.store["claims"]
        assert o["token"] not in str(client.store["claims"])  # raw token never persisted


def test_get_claim_returns_only_first_name_and_event(client):
    tok = _mint(client)[0]["token"]
    res = client.get(f"/api/claims/{tok}")
    assert res.status_code == 200
    body = res.json()
    assert body == {"valid": True, "first_name": "Ava", "event_name": "2027 Junior Digital Combine #2", "claimed": False}
    for forbidden in ("email", "last_name", "user_id"):
        assert forbidden not in body


def test_get_claim_logs_first_open_once(client):
    tok = _mint(client)[0]["token"]
    client.get(f"/api/claims/{tok}")
    client.get(f"/api/claims/{tok}")
    assert client.store["open_writes"] == 1


def test_get_expired_claim_is_410(client):
    tok = mint_token(4521, 1317, SECRET, exp=1)  # 1970
    client.store["claims"][token_hash(tok)] = {
        "id": 1, "user_id": 4521, "event_id": 1317, "opened_at": None, "claimed_at": None, "clerk_id": None,
    }
    res = client.get(f"/api/claims/{tok}")
    assert res.status_code == 410
    assert res.json()["detail"]["valid"] is False


def test_get_tampered_claim_is_400(client):
    tok = _mint(client)[0]["token"]
    payload_b64, sig = tok.split(".")
    flipped = ("A" if sig[0] != "A" else "B") + sig[1:]
    res = client.get(f"/api/claims/{payload_b64}.{flipped}")
    assert res.status_code == 400
    assert res.json()["detail"]["valid"] is False


def test_get_signed_but_unminted_claim_is_404(client):
    tok = mint_token(4521, 1317, SECRET)  # valid signature, never inserted
    res = client.get(f"/api/claims/{tok}")
    assert res.status_code == 404
    assert res.json()["detail"]["valid"] is False


def test_get_claim_for_missing_gmtm_user_is_404(client):
    tok = _mint(client, (777,))[0]["token"]  # 777 not in fake users table
    assert client.get(f"/api/claims/{tok}").status_code == 404


def test_redeem_links_profile_and_is_idempotent_for_same_clerk(client):
    tok = _mint(client)[0]["token"]
    first = client.post(f"/api/claims/{tok}/redeem")
    assert first.status_code == 200
    assert first.json() == {"connected": True, "user_id": 4521, "event_id": 1317, "clerk_id": "user_alpha",
                            "workspace_ready": True, "workspace_created": True}
    assert client.store["bootstrap_calls"] == [("user_alpha", 4521)]
    assert client.store["athlete_profiles"][4521] == "user_alpha"
    second = client.post(f"/api/claims/{tok}/redeem")
    assert second.status_code == 200
    assert client.get(f"/api/claims/{tok}").json()["claimed"] is True


def test_redeem_by_different_clerk_is_409(client):
    tok = _mint(client)[0]["token"]
    assert client.post(f"/api/claims/{tok}/redeem").status_code == 200
    client.identity["clerk"] = "user_beta"
    res = client.post(f"/api/claims/{tok}/redeem")
    assert res.status_code == 409
    # The original link is untouched.
    assert client.store["athlete_profiles"][4521] == "user_alpha"


def test_redeem_expired_is_410_and_tampered_is_400(client):
    expired = mint_token(4521, 1317, SECRET, exp=1)
    assert client.post(f"/api/claims/{expired}/redeem").status_code == 410
    tok = _mint(client)[0]["token"]
    p, s = tok.split(".")
    flipped = ("A" if s[0] != "A" else "B") + s[1:]
    assert client.post(f"/api/claims/{p}.{flipped}/redeem").status_code == 400
    assert client.store["athlete_profiles"] == {}


def test_redeem_refuses_to_repoint_an_already_linked_athlete(client):
    """A leaked claim link must not hijack a GMTM athlete already connected to another Clerk id."""
    tok = _mint(client)[0]["token"]
    client.store["athlete_profiles"][4521] = "user_original"  # linked earlier via /profile/connect
    client.identity["clerk"] = "user_attacker"
    res = client.post(f"/api/claims/{tok}/redeem")
    assert res.status_code == 409
    assert client.store["athlete_profiles"][4521] == "user_original"
    # The original owner can still redeem the same link.
    client.identity["clerk"] = "user_original"
    assert client.post(f"/api/claims/{tok}/redeem").status_code == 200


def test_redeem_survives_a_failing_workspace_bootstrap(client, monkeypatch):
    """The claim must still link the athlete even if building the workspace row blows up."""
    def _boom(clerk_id, user_id):
        raise RuntimeError("railway down")
    monkeypatch.setattr(claims_api, "ensure_workspace_profile", _boom)
    tok = _mint(client)[0]["token"]
    res = client.post(f"/api/claims/{tok}/redeem")
    assert res.status_code == 200
    assert res.json()["workspace_ready"] is False
    assert client.store["athlete_profiles"][4521] == "user_alpha"


def _assert_clean_claim_connection(client, *, committed=False, acquired=True):
    db = client.store["connections"][-1]
    assert db.closed
    assert db.commits == int(committed)
    assert db.rollbacks == int(not committed)
    assert not any(db.pending.values())
    assert client.store["named_locks"] == {}
    assert client.store["row_locks"] == {}
    event_names = [event[0] for event in db.events]
    release_indexes = [i for i, event in enumerate(db.events)
                       if event[0] == "sql" and event[1].startswith("SELECT RELEASE_LOCK")]
    assert bool(release_indexes) is acquired
    if acquired:
        assert event_names.index("commit" if committed else "rollback") < release_indexes[0] < event_names.index("close")


def test_redeem_keeps_original_claim_timestamp_on_retry(client):
    tok = _mint(client)[0]["token"]
    assert client.post(f"/api/claims/{tok}/redeem").status_code == 200
    row = client.store["claims"][token_hash(tok)]
    row["claimed_at"] = "original-claim-time"
    assert client.post(f"/api/claims/{tok}/redeem").status_code == 200
    assert client.store["claims"][token_hash(tok)]["claimed_at"] == "original-claim-time"
    _assert_clean_claim_connection(client, committed=True)


def test_second_token_for_same_owner_is_safe(client):
    first = _mint(client)[0]["token"]
    second = _mint(client, event_id=1318)[0]["token"]
    assert first != second
    assert client.post(f"/api/claims/{first}/redeem").status_code == 200
    response = client.post(f"/api/claims/{second}/redeem")
    assert response.status_code == 200
    assert response.json()["event_id"] == 1318
    assert client.store["athlete_profiles"] == {4521: "user_alpha"}
    assert all(row["clerk_id"] == "user_alpha" for row in client.store["claims"].values())


@pytest.mark.parametrize("also_link_requested", [False, True])
def test_redeem_rejects_unrelated_clerk_mapping_without_selecting_an_athlete(client, also_link_requested):
    tok = _mint(client)[0]["token"]
    client.store["athlete_profiles"][4522] = "user_alpha"
    if also_link_requested:
        # Historical multiple mappings also fail closed; do not pick either row.
        client.store["athlete_profiles"][4521] = "user_alpha"
    before = dict(client.store["athlete_profiles"])
    assert client.post(f"/api/claims/{tok}/redeem").status_code == 409
    assert client.store["athlete_profiles"] == before
    assert client.store["claims"][token_hash(tok)]["claimed_at"] is None
    assert client.store["bootstrap_calls"] == []
    _assert_clean_claim_connection(client)


@pytest.mark.parametrize("field,value", [("user_id", 4522), ("event_id", 1318)])
def test_redeem_rejects_row_that_does_not_match_signed_payload(client, field, value):
    tok = _mint(client)[0]["token"]
    client.store["claims"][token_hash(tok)][field] = value
    response = client.post(f"/api/claims/{tok}/redeem")
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "mismatch"
    assert client.store["athlete_profiles"] == {}
    assert client.store["bootstrap_calls"] == []
    _assert_clean_claim_connection(client)


@pytest.mark.parametrize("result", [0, None])
def test_redeem_fails_closed_if_advisory_lock_cannot_be_acquired(client, result):
    tok = _mint(client)[0]["token"]
    client.store["lock_result"] = result
    assert client.post(f"/api/claims/{tok}/redeem").status_code == 409
    assert client.store["athlete_profiles"] == {}
    assert client.store["bootstrap_calls"] == []
    _assert_clean_claim_connection(client, acquired=False)


def test_unminted_claim_rolls_back_and_releases_lock(client):
    tok = mint_token(4521, 1317, SECRET)
    assert client.post(f"/api/claims/{tok}/redeem").status_code == 404
    _assert_clean_claim_connection(client)


def test_lost_conditional_claim_update_rolls_back_new_mapping(client):
    tok = _mint(client)[0]["token"]
    client.store["reject_claim_update"] = True
    assert client.post(f"/api/claims/{tok}/redeem").status_code == 409
    assert client.store["athlete_profiles"] == {}
    assert client.store["claims"][token_hash(tok)]["claimed_at"] is None
    assert client.store["bootstrap_calls"] == []
    _assert_clean_claim_connection(client)


@pytest.mark.parametrize("stage", [
    "SELECT GET_LOCK", "SELECT id, user_id", "SELECT clerk_id FROM athlete_profiles",
    "UPDATE claim_tokens SET claimed_at", "commit",
])
def test_database_failure_never_leaves_a_partial_claim(client, stage):
    tok = _mint(client)[0]["token"]
    client.store["failures"][stage] = RuntimeError("simulated database failure")
    with pytest.raises(RuntimeError, match="simulated database failure"):
        client.post(f"/api/claims/{tok}/redeem")
    assert client.store["athlete_profiles"] == {}
    assert client.store["claims"][token_hash(tok)]["claimed_at"] is None
    assert client.store["bootstrap_calls"] == []
    _assert_clean_claim_connection(client, acquired=stage != "SELECT GET_LOCK")


@pytest.mark.parametrize("error_type,code", [
    (pymysql.err.IntegrityError, 1062),
    (pymysql.err.OperationalError, 1205),
    (pymysql.err.OperationalError, 1213),
])
def test_database_contention_is_retryable_without_partial_writes(client, error_type, code):
    tok = _mint(client)[0]["token"]
    client.store["failures"]["UPDATE claim_tokens SET claimed_at"] = error_type(code, "simulated conflict")
    assert client.post(f"/api/claims/{tok}/redeem").status_code == 409
    assert client.store["athlete_profiles"] == {}
    assert client.store["claims"][token_hash(tok)]["claimed_at"] is None
    _assert_clean_claim_connection(client)
    assert client.post(f"/api/claims/{tok}/redeem").status_code == 200


def test_release_failure_still_closes_connection(client):
    tok = _mint(client)[0]["token"]
    client.store["failures"]["SELECT RELEASE_LOCK"] = RuntimeError("simulated release failure")
    with pytest.raises(RuntimeError, match="simulated release failure"):
        client.post(f"/api/claims/{tok}/redeem")
    # Commit happened first. A retry must preserve that committed ownership.
    assert client.store["athlete_profiles"] == {4521: "user_alpha"}
    _assert_clean_claim_connection(client, committed=True)
    assert client.post(f"/api/claims/{tok}/redeem").status_code == 200


@pytest.mark.parametrize("race", ["same_token", "different_tokens_one_athlete", "one_clerk_two_athletes"])
def test_overlapping_claims_preserve_one_owner_and_leave_loser_unclaimed(client, race):
    """Two real handler calls interleave over fake locks, not a live MySQL test."""
    first_token = _mint(client)[0]["token"]
    if race == "different_tokens_one_athlete":
        second_token = _mint(client, event_id=1318)[0]["token"]
    elif race == "one_clerk_two_athletes":
        second_token = _mint(client, user_ids=(4522,))[0]["token"]
    else:
        second_token = first_token
    second_caller = "user_alpha" if race == "one_clerk_two_athletes" else "user_beta"
    inserted = threading.Event()
    finish_first = threading.Event()

    def pause_after_first_insert(db, sql, params):
        if sql.startswith("INSERT INTO athlete_profiles") and not inserted.is_set():
            inserted.set()
            assert finish_first.wait(5), "test did not release the first transaction"

    client.store["after_execute"] = pause_after_first_insert

    def redeem(caller, token):
        from fastapi import HTTPException
        try:
            asyncio.run(claims_api.redeem_claim(token, caller))
            return 200
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        winner = executor.submit(redeem, "user_alpha", first_token)
        try:
            assert inserted.wait(3), "first claim never reached the ownership write"
            loser = executor.submit(redeem, second_caller, second_token)
            assert loser.result(timeout=3) == 409
            # Uncommitted ownership and token writes remain invisible.
            assert client.store["athlete_profiles"] == {}
            assert client.store["claims"][token_hash(first_token)]["claimed_at"] is None
        finally:
            finish_first.set()
        assert winner.result(timeout=3) == 200

    assert client.store["athlete_profiles"] == {4521: "user_alpha"}
    assert client.store["claims"][token_hash(first_token)]["clerk_id"] == "user_alpha"
    if second_token != first_token:
        assert client.store["claims"][token_hash(second_token)]["claimed_at"] is None
    assert redeem(second_caller, second_token) == 409
    assert client.store["athlete_profiles"] == {4521: "user_alpha"}
    assert client.store["bootstrap_calls"] == [("user_alpha", 4521)]
    assert all(db.closed and not any(db.pending.values()) for db in client.store["connections"])
    assert client.store["named_locks"] == client.store["row_locks"] == {}
