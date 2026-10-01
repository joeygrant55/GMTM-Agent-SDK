"""Junior pilot safety on the profile surface: no outreach email, no name in prompts, no public pages."""
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
import requests

import artifacts_api
import candidate_app
import email_sender
import profile_api
from backend.tests.test_candidate_app import ENV  # noqa: F401
from backend.tests.test_profile_candidate_app import session  # noqa: F401  (fixture)

ATHLETE = {
    "name": "Jordan Smithfield", "email": "jordan.smithfield@example.invalid", "phone": "555-0100",
    "address": "12 Elm Street", "dob": "2010-04-05", "school": "Smithfield Prep", "city": "Tampa",
    "position": "QB", "sport": "Flag Football", "class_year": 2028, "state": "FL", "gpa": "3.8",
    "combine_metrics": {"40yd": "5.1"}, "stats": {"TD": 9}, "season": "2025",
}
FORBIDDEN = ("Smithfield", "jordan.smithfield", "555-0100", "Elm Street", "2010-04-05", "Tampa")


@pytest.fixture
def profile_app(monkeypatch):
    for name in candidate_app._CONFIGURATION_KEYS:
        monkeypatch.delenv(name, raising=False)
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    return candidate_app.create_app(surface="profile")


@pytest.fixture
def no_email(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("Outreach email must never be sent from the profile app")
    monkeypatch.setattr(requests, "post", refuse)
    monkeypatch.setattr(email_sender.requests, "post", refuse)
    monkeypatch.setattr(email_sender, "send_outreach_email", refuse)
    monkeypatch.setattr(artifacts_api, "send_outreach_email", refuse)


class FakeCursor:
    def __init__(self, row=None):
        self.row, self.sql = row, []
        self.lastrowid = 7

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.sql.append(sql)

    def fetchone(self):
        return self.row

    def fetchall(self):
        return []


class FakeDB:
    def __init__(self, row=None):
        self.cur = FakeCursor(row)

    def cursor(self):
        return self.cur

    def commit(self):
        pass

    def close(self):
        pass


class FakeModel:
    """Captures every model call; returns a fixed draft."""
    calls = []

    def __init__(self, **kwargs):
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        FakeModel.calls.append(kwargs)
        text = json.dumps({"to_name": "Coach", "to_email": "", "school": "State", "subject": "QB 2028", "body": "Hi coach."})
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def _prompt_text(call):
    return json.dumps({k: call.get(k) for k in ("system", "messages")}, default=str)


def test_public_athlete_report_and_outreach_routes_are_absent(profile_app, session, no_email):
    with TestClient(profile_app) as client:
        for method, path in (
            ("GET", "/api/athlete/123"), ("GET", "/api/athlete/user_abc"),
            ("GET", "/api/reports/public/token"), ("GET", "/api/reports/user_abc/1"),
            ("POST", "/api/artifacts/1/approve"), ("POST", "/api/artifacts/draft-outreach"),
            ("POST", "/api/workspace/colleges/user_abc/1/research"),
        ):
            for headers in ({}, session()):
                assert client.request(method, path, headers=headers).status_code in (404, 405), path
    paths = profile_app.openapi()["paths"]
    assert not any(p.startswith(("/api/artifacts", "/api/reports", "/api/search")) or p == "/api/athlete/{athlete_id}" for p in paths)


@pytest.mark.parametrize("name", ["SENDGRID_API_KEY", "SPARQ_FROM_EMAIL"])
def test_profile_app_refuses_to_start_with_email_sending_configured(profile_app, monkeypatch, name):
    monkeypatch.setenv(name, "configured")
    with pytest.raises(candidate_app.CandidateConfigurationError):
        with TestClient(profile_app):
            pass
    # The other surface is unaffected by this profile-only rule.
    with TestClient(candidate_app.create_app()) as client:
        assert client.get("/health").status_code == 200


def test_approve_on_profile_app_never_reaches_sendgrid(profile_app, session, no_email, monkeypatch):
    # Simulates a later mount of the outreach routes on this app: approve still never sends.
    profile_app.include_router(artifacts_api.router)
    row = {"type": "outreach_draft", "state": "ready_for_review", "clerk_id": "user_123",
           "payload": json.dumps({"to_email": "coach@college.example.invalid", "subject": "s", "body": "b"})}
    db = FakeDB(row)
    monkeypatch.setattr(artifacts_api, "_get_agent_db", lambda: db)
    with TestClient(profile_app) as client:
        response = client.post("/api/artifacts/1/approve", headers=session(sub="user_123"),
                               json={"athlete_email": "a@example.invalid"})
    assert response.status_code == 200
    assert response.json() == {"ok": False, "status": "not_configured"}
    assert not any("UPDATE" in sql or "outreach_log" in sql for sql in db.cur.sql)


def test_outreach_draft_prompt_has_first_name_only_and_minor_rules(monkeypatch):
    FakeModel.calls = []
    monkeypatch.setattr(artifacts_api, "_load_athlete_profile_for_artifacts", lambda _id: dict(ATHLETE))
    monkeypatch.setattr(artifacts_api, "_get_agent_db", lambda: FakeDB())
    monkeypatch.setattr(artifacts_api.anthropic, "Anthropic", FakeModel)
    body = artifacts_api.DraftOutreachBody(athlete_id="user_123", college_name="State College")
    artifacts_api.draft_outreach(body, caller_clerk_id="user_123")
    assert len(FakeModel.calls) == 1
    prompt = _prompt_text(FakeModel.calls[0])
    assert "Jordan" in prompt
    for value in FORBIDDEN + ("Smithfield Prep",):
        assert value not in prompt, value
    for kept in ("QB", "2028", "FL", "5.1"):
        assert kept in prompt
    system = FakeModel.calls[0]["system"]
    assert "Never ask for a phone call, video call, campus visit or meeting" in system
    assert "coaches may not be able to reply yet" in system
    assert "camp," not in system


def test_deep_research_prompt_and_web_search_have_no_athlete_name(monkeypatch):
    FakeModel.calls = []
    profile = {"id": 1, "clerk_id": "user_123", "position": "QB", "class_year": 2028, "state": "FL",
               "city": "Tampa", "gpa": "3.8", "recruiting_goals": "{}",
               "maxpreps_data": json.dumps({"name": "Jordan Smithfield", "sport": "Flag Football"})}
    college = {"id": 2, "college_name": "State College", "division": "NAIA", "college_city": "X", "college_state": "FL"}
    rows = iter([profile, college])

    class ResearchCursor(FakeCursor):
        def fetchone(self):
            return next(rows)

    db = FakeDB()
    db.cur = ResearchCursor()
    monkeypatch.setattr(profile_api, "_get_agent_db", lambda: db)
    monkeypatch.setattr("anthropic.Anthropic", FakeModel)

    class InlineThread:
        def __init__(self, target, args, **kwargs):
            self.target, self.args = target, args

        def start(self):
            self.target(*self.args)

    monkeypatch.setattr(profile_api.threading, "Thread", InlineThread)
    import asyncio
    asyncio.run(profile_api.run_deep_research("user_123", 2, background_tasks=None, caller_clerk_id="user_123"))
    assert len(FakeModel.calls) == 1
    prompt = _prompt_text(FakeModel.calls[0])
    for value in ("Jordan", "Smithfield", "Tampa"):
        assert value not in prompt, value
    for kept in ("QB", "2028", "FL", "Flag Football"):
        assert kept in prompt
