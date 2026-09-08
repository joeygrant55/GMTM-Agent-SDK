"""Offline regression checks for the legacy account-linking route."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# Shared conftest installs the database/network guards before collection.
import profile_api
from auth import require_clerk_id
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeDB:
    def __init__(self, store):
        self.store = store
        self.result = None
        self.closed = False

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        normalized = ' '.join(sql.split())
        if normalized.startswith('SELECT clerk_id FROM athlete_profiles'):
            uid = params[0]
            self.result = ({'clerk_id': self.store['owners'][uid]}
                           if uid in self.store['owners'] else None)
        elif normalized.startswith('INSERT INTO athlete_profiles'):
            # Reproduces the old unsafe write so these tests fail against it.
            uid, clerk_id, _ = params
            self.store['owners'][uid] = clerk_id
            self.store['writes'] += 1
        else:
            raise AssertionError(f'Unexpected SQL: {normalized}')

    def fetchone(self):
        return self.result

    def commit(self):
        self.store['commits'] += 1

    def close(self):
        self.closed = True


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('AUTH_ENFORCED', 'true')
    store = {'owners': {4521: 'user_alpha', 4522: 'user_beta', 4523: None},
             'writes': 0, 'commits': 0, 'connections': []}

    def db():
        connection = FakeDB(store)
        store['connections'].append(connection)
        return connection

    monkeypatch.setattr(profile_api, '_get_agent_db', db)
    app = FastAPI()
    app.include_router(profile_api.router)
    app.dependency_overrides[require_clerk_id] = lambda: 'user_alpha'
    with TestClient(app) as http:
        http.store = store
        yield http


def post(client, user_id, clerk_id='user_alpha'):
    return client.post('/api/profile/connect', json={'user_id': user_id, 'clerk_id': clerk_id})


def test_existing_owner_can_confirm_without_writing(client):
    for _ in range(2):
        response = post(client, 4521)
        assert response.status_code == 200
        assert response.json() == {'connected': True, 'user_id': 4521, 'clerk_id': 'user_alpha'}
    assert client.store['owners'][4521] == 'user_alpha'
    assert client.store['writes'] == client.store['commits'] == 0
    assert all(db.closed for db in client.store['connections'])


@pytest.mark.parametrize('user_id', [4522, 4523, 9999])
def test_foreign_unclaimed_and_unknown_athletes_cannot_be_linked(client, user_id):
    original = dict(client.store['owners'])
    response = post(client, user_id)
    assert response.status_code == 403
    assert response.json() == {'detail': 'Use your secure combine invitation to connect this athlete profile.'}
    assert client.store['owners'] == original
    assert client.store['writes'] == client.store['commits'] == 0
    assert all(db.closed for db in client.store['connections'])


def test_caller_cannot_submit_a_different_clerk_identity(client):
    response = post(client, 4522, 'user_beta')
    assert response.status_code == 403
    assert client.store['connections'] == []
    assert client.store['owners'][4522] == 'user_beta'


def test_unauthenticated_request_never_reads_or_writes(client):
    client.app.dependency_overrides.clear()
    assert post(client, 4521).status_code == 401
    assert client.store['connections'] == []
