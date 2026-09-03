"""
Unit tests for claim tokens (spec 2a / 2f). No database, no network.

Run:  cd backend && python -m pytest tests/test_claims.py -q

Covers the pure token helpers and, with an in-memory fake DB, the three abuse cases:
    expired token   -> 410
    tampered token  -> 400
    reused by a different Clerk id -> 409
"""

import os
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Config the modules read at import time. AUTH_ENFORCED=false makes require_clerk_id
# return DEV_CLERK_ID, but we override the dependency per test anyway.
os.environ["SHARE_TOKEN_SECRET"] = "test-share-secret"
os.environ["CLAIMS_ADMIN_SECRET"] = "test-admin-secret"
os.environ["AUTH_ENFORCED"] = "false"
os.environ["FRONTEND_URL"] = "https://sparq-agent.test"

# profile_api and claims_api try to create their tables on import. Make every
# connection attempt fail fast so import never touches a real host.
import pymysql  # noqa: E402


def _no_db(*_a, **_kw):
    raise ConnectionError("no database in unit tests")


pymysql.connect = _no_db  # type: ignore[assignment]

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
    """Just enough of a pymysql DictCursor for claims_api's queries."""

    def __init__(self, store: dict):
        self.store = store
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        params = params or ()
        s = " ".join(sql.split())
        claims = self.store["claims"]
        if s.startswith("CREATE TABLE"):
            self._result = None
        elif s.startswith("INSERT INTO claim_tokens"):
            thash, uid, eid, exp = params
            claims[thash] = {
                "id": len(claims) + 1, "user_id": uid, "event_id": eid, "expires_at": exp,
                "opened_at": None, "claimed_at": None, "clerk_id": None,
            }
        elif s.startswith("SELECT id, user_id, event_id, opened_at, claimed_at, clerk_id FROM claim_tokens"):
            self._result = claims.get(params[0])
        elif s.startswith("UPDATE claim_tokens SET opened_at"):
            row = next(r for r in claims.values() if r["id"] == params[0])
            if row["opened_at"] is None:
                row["opened_at"] = "now"
                self.store["open_writes"] += 1
        elif s.startswith("INSERT INTO athlete_profiles"):
            uid, clerk, _ = params
            self.store["athlete_profiles"][uid] = clerk
        elif s.startswith("UPDATE claim_tokens SET claimed_at"):
            clerk, row_id = params
            row = next(r for r in claims.values() if r["id"] == row_id)
            row["claimed_at"] = row["claimed_at"] or "now"
            row["clerk_id"] = clerk
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

    def cursor(self):
        return _FakeCursor(self.store)

    def commit(self):
        self.commits += 1

    def close(self):
        pass


@pytest.fixture
def client(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from auth import require_clerk_id

    store = {"claims": {}, "athlete_profiles": {}, "users": {4521, 4522}, "open_writes": 0}
    monkeypatch.setattr(claims_api, "_get_agent_db", lambda: _FakeDB(store))
    monkeypatch.setattr(claims_api, "_get_gmtm_db", lambda: _FakeDB(store))

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
    res = client.get(f"/api/claims/{payload_b64}.{sig[:-1]}Q")
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
    assert first.json() == {"connected": True, "user_id": 4521, "event_id": 1317, "clerk_id": "user_alpha"}
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
    assert client.post(f"/api/claims/{p}.{s[:-1]}Q/redeem").status_code == 400
    assert client.store["athlete_profiles"] == {}
