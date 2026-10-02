"""Junior colleges on the profile app: routes, girls-first gate, ranking, model inputs, links, drafts.

Every outside effect is a fake: college_programs.store (Agent DB), read_identity
(GMTM) and model_json (model). junior_entry.store is a MemoryStore.
"""
from datetime import datetime, timezone
import json

from fastapi.testclient import TestClient
import pytest

import auth
import candidate_app
import college_programs as cp
import junior_eligibility as elig
import junior_entry
from backend.tests.junior_fakes import MemoryStore
from backend.tests.test_profile_candidate_app import session  # noqa: F401  (fixture)
from backend.tests.test_profile_candidate_app import profile_app  # noqa: F401  (fixture)

SUBJECT, USER_ID = "user_junior", 7301
NAME, CITY, EMAIL = "Avery Quintero", "Plano", "avery@example.com"
ROUTES = {
    ("GET", "/api/workspace/colleges/{clerk_id}"), ("POST", "/api/workspace/trigger-matching/{clerk_id}"),
    ("GET", "/api/workspace/colleges/{clerk_id}/{program_id}"),
    ("GET", "/api/workspace/colleges/{clerk_id}/{program_id}/outreach-draft"),
    ("POST", "/api/workspace/colleges/{clerk_id}/{program_id}/outreach-draft"),
}


class CollegeStore:
    def __init__(self, state="TX"):
        self.rows, self.drafts, self.saves = {}, [], 0
        self.profiles = {SUBJECT: {"clerk_id": SUBJECT, "name": NAME, "position": "QB", "class_year": 2028, "state": state,
                                 "city": CITY, "email": EMAIL,
                                 "combine_metrics": json.dumps({"fortyYardDash": 5.4, "vertical": 21, "weight": 120})}}

    def profile(self, clerk_id): return self.profiles.get(clerk_id)
    def gmtm_user_id(self, clerk_id): return USER_ID if clerk_id == SUBJECT else None
    def load(self, clerk_id): return dict(self.rows[clerk_id]) if clerk_id in self.rows else None

    def save_identity(self, clerk_id, gender, sport):
        self.rows.setdefault(clerk_id, {}).update(gmtm_gender=gender, gmtm_sport=sport)

    def save_list(self, clerk_id, key, items):
        self.saves += 1
        self.rows[clerk_id].update(inputs_key=key, programs=items)

    def insert_draft(self, clerk_id, title, summary, payload, sources):
        self.drafts.append({"id": len(self.drafts) + 1, "clerk_id": clerk_id, "payload": payload, "sources": sources})
        return len(self.drafts)

    def latest_draft(self, clerk_id, program_id):
        rows = [d for d in self.drafts if d["clerk_id"] == clerk_id and d["payload"]["program_id"] == program_id]
        return rows[-1] if rows else None


class Model:
    def __init__(self, fail=False, draft=None):
        self.calls, self.fail = [], fail
        self.draft = draft or {"subject": "2028 QB flag football", "body": "Hello Coach,\n\nI play QB.\n\nAvery"}

    def __call__(self, system, user, max_tokens):
        self.calls.append((system, user))
        if self.fail:
            raise RuntimeError("provider down")
        if system == cp.REASON_SYSTEM:
            ids = [p["id"] for p in json.loads(user)["programs"]]
            return {"reasons": [{"id": i, "reason": f"Plain reason for {i}. It uses only given facts."} for i in ids]}
        return dict(self.draft)


@pytest.fixture
def app(profile_app, monkeypatch, session):
    monkeypatch.setattr(auth, "_rate_buckets", {})
    entries = MemoryStore()
    entries.record_entry(SUBJECT, USER_ID, datetime.now(timezone.utc))
    entries.accept_notice(SUBJECT, datetime.now(timezone.utc))
    monkeypatch.setattr(junior_entry, "store", entries)
    monkeypatch.setattr(elig, "reader", lambda uid: (True, datetime(2011, 1, 1).date()))
    store, model, identity = CollegeStore(), Model(), {"gender": 1, "sport": "Flag Football"}
    monkeypatch.setattr(cp, "store", store)
    monkeypatch.setattr(cp, "model_json", model)
    monkeypatch.setattr(cp, "read_identity", lambda uid: dict(identity) if uid == USER_ID else None)
    with TestClient(profile_app) as client:
        yield client, store, model, identity, session(sub=SUBJECT), entries


def walk(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k, v
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


def test_profile_app_mounts_exactly_the_reviewed_college_routes(profile_app):
    mounted = {(m, r.path) for r in profile_app.routes for m in getattr(r, "methods", ()) if "college" in r.path or "trigger" in r.path}
    assert mounted == ROUTES
    combine = candidate_app.create_app()
    assert not any("college" in r.path or "trigger" in r.path for r in combine.routes)


def test_owner_checks_401_and_403(app):
    client, store, model, *_ , headers, _ = app
    for method, path in ROUTES:
        url = path.replace("{program_id}", "midland-university")
        assert client.request(method, url.replace("{clerk_id}", SUBJECT)).status_code == 401
        assert client.request(method, url.replace("{clerk_id}", "user_other"), headers=headers).status_code == 403
    assert model.calls == [] and store.saves == 0


def test_parent_notice_still_gates_college_routes(app):
    client, store, model, _, headers, entries = app
    entries.notices.clear()
    response = client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers)
    assert response.status_code == 403 and response.json()["detail"] == "parent_notice_required"


@pytest.mark.parametrize("gender", [0, 2, None, "x"])
def test_only_gmtm_gender_1_gets_a_list(app, gender):
    client, store, model, identity, headers, _ = app
    identity["gender"] = gender
    for response in (client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers),
                     client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers)):
        assert response.status_code == 200
        body = response.json()
        assert body["eligible"] is False and body["programs"] == [] and body["notice"] == cp.NOT_ELIGIBLE
        assert "update it on GMTM" in body["notice"]
    for method in ("GET", "POST"):
        assert client.request(method, f"/api/workspace/colleges/{SUBJECT}/midland-university/outreach-draft", headers=headers).status_code == 403
    assert client.get(f"/api/workspace/colleges/{SUBJECT}/midland-university", headers=headers).status_code == 403
    assert model.calls == [] and store.saves == 0 and store.drafts == []


def test_gender_fix_on_gmtm_is_picked_up_by_the_next_build(app):
    client, store, model, identity, headers, _ = app
    identity["gender"] = 2
    assert client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers).json()["eligible"] is False
    identity["gender"] = 1
    assert client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers).json()["eligible"] is True  # GET re-reads GMTM
    body = client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers).json()
    assert body["eligible"] is True and len(body["programs"]) == 12
    assert store.rows[SUBJECT]["gmtm_sport"] == "Flag Football"


def test_build_ranks_home_state_first_caps_at_12_and_caches(app):
    client, store, model, _, headers, _ = app
    first = client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers).json()
    programs = first["programs"]
    assert first["eligible"] is True and first["built"] is True and len(programs) == 12
    assert programs[0]["state"] == "TX" and sum(p["state"] == "TX" for p in programs) >= 10
    assert {p["level"] for p in programs} == {"NCAA D1", "NCAA D2", "NCAA D3", "NAIA", "NJCAA"}
    assert all(p["reason"] for p in programs) and len(model.calls) == 1
    again = client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers).json()
    listed = client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers).json()
    assert again == first == listed and len(model.calls) == 1  # cached per athlete
    assert [p["id"] for p in cp.rank("TX")] == [p["id"] for p in cp.rank("TX")]


def test_rank_is_deterministic_and_home_state_first_for_each_state():
    for state in sorted(cp.REGION):
        ranked = cp.rank(state)
        assert len(ranked) == 12 and ranked == cp.rank(state)
        home = [p for p in cp.programs() if p["state"] == state]
        if home:
            assert ranked[0]["state"] == state
    assert cp.state_code("Texas") == "TX" and cp.state_code("tx") == "TX" and cp.state_code("Narnia") is None
    assert len(cp.rank(None)) == 12


def test_no_numeric_fit_score_in_any_response(app):
    client, store, model, _, headers, _ = app
    bodies = [client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers).json(),
              client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers).json(),
              client.get(f"/api/workspace/colleges/{SUBJECT}/midland-university", headers=headers).json()]
    for body in bodies:
        assert not any("score" in key.lower() or "rank" in key.lower() for key, _ in walk(body))
        assert not any(isinstance(v, (int, float)) and not isinstance(v, bool) for _, v in walk(body))


def test_reason_prompt_has_only_the_allowed_fields(app):
    client, store, model, _, headers, _ = app
    client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers)
    (system, user), = model.calls
    for secret in (NAME, "Avery", "Quintero", CITY, EMAIL, "@"):
        assert secret not in user
    sent = json.loads(user)
    assert set(sent) == {"athlete", "programs"}
    assert sent["athlete"] == {"position": "QB", "grad_year": 2028, "state": "TX", "combine_metrics": [
        {"name": "40-Yard Dash", "value": 5.4, "unit": "s"}, {"name": "Vertical Jump", "value": 21, "unit": "in"}]}
    assert all(set(p) == {"id", "school", "state", "level", "conference", "notes"} for p in sent["programs"])
    for rule in ("never invent coaches, emails, rosters, scholarships, records", 'never say "verified" or "recruited"', "2 short sentences"):
        assert rule in system.lower()


def test_model_failure_still_returns_programs_without_reasons(app, monkeypatch):
    client, store, model, _, headers, _ = app
    model.fail = True
    body = client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers).json()
    assert len(body["programs"]) == 12 and all(p["reason"] is None for p in body["programs"])
    model.fail = False  # same inputs: a missing reason is final, no new paid call
    assert all(p["reason"] is None for p in client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers).json()["programs"])
    assert len(model.calls) == 1


def test_unsafe_reasons_are_dropped():
    chosen = cp.rank("TX")[:3]
    replies = ["She was recruited by this program.", "This is a verified fit.", "Fine and honest. It fits."]
    original = cp.model_json
    try:
        cp.model_json = lambda *a: {"reasons": [{"id": p["id"], "reason": r} for p, r in zip(chosen, replies)] + [{"id": "made-up", "reason": "x"}]}
        assert cp.explain({}, chosen) == {chosen[2]["id"]: "Fine and honest. It fits."}
    finally:
        cp.model_json = original


def test_links_are_https_only_and_generic_pages_are_not_confirmed(app):
    client, store, model, _, headers, _ = app
    for pid in ("midland-university", "delaware-state-university"):
        p = client.get(f"/api/workspace/colleges/{SUBJECT}/{pid}", headers=headers).json()["program"]
        assert p["program_link"] is None and p["program_link_label"] == "Program link not confirmed"
        assert p["source_links"] and all(u.startswith("https://") for u in p["source_links"])
        assert p["source_checked"] == "Source checked Oct 1, 2026"
    good = client.get(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university", headers=headers).json()["program"]
    assert good["program_link"].startswith("https://") and "flag" in good["program_link"] and good["program_link_label"] == "Program page"
    assert good["source_links"] == []
    q = client.get(f"/api/workspace/colleges/{SUBJECT}/harcum-college", headers=headers).json()["program"]
    assert q["questionnaire_link"] == "https://www.harcum.edu/recruitment"
    for p in cp.programs():
        c = cp.card(p)
        links = [c["program_link"], c["questionnaire_link"], *c["source_links"]]
        assert all(u is None or u.startswith("https://") for u in links)
    assert cp.https("javascript:alert(1)") is None and cp.https("https://u:p@x.edu") is None


def test_contact_rules_are_sourced_and_hide_the_njcaa_date():
    rules = {r["governing_body"]: r["rules"] for r in cp.contact_rules(cp.LEVELS)}
    assert rules["NJCAA"] == [{"text": "Check with the school.", "source_url": None, "source_label": None}]
    for body, items in rules.items():
        if body != "NJCAA":
            assert items and all(i["source_url"].startswith("https://") for i in items)
    assert "June 15 after your sophomore year" in rules["NCAA-D1"][0]["text"]


def test_draft_uses_first_name_only_and_leaves_to_empty(app):
    client, store, model, _, headers, _ = app
    url = f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft"
    assert client.get(url, headers=headers).json() == {"draft": None}
    created = client.post(url, headers=headers).json()["draft"]
    assert created["to_email"] == "" and created["body"] == "Hello Coach,\n\nI play QB.\n\nAvery"
    assert client.get(url, headers=headers).json()["draft"] == created
    system, user = model.calls[-1]
    assert "Avery" in user and "Quintero" not in user and CITY not in user and EMAIL not in user
    assert "Coach email (if known): (none)" in user and "Alabama State University" in user
    assert system == cp.JUNIOR_DRAFT_SYSTEM and "never name a coach" in system and "recruit_questionnaire\": \"not available\"" in user
    saved = store.drafts[-1]["payload"]
    assert saved["to_email"] == "" and saved["to_name"] == "Head coach" and saved["program_id"] == "alabama-state-university"


def test_draft_model_failure_is_502_and_nothing_saved(app):
    client, store, model, _, headers, _ = app
    model.fail = True
    response = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers)
    assert response.status_code == 502 and store.drafts == []
    assert client.get(f"/api/workspace/colleges/{SUBJECT}/no-such-school", headers=headers).status_code == 404


@pytest.mark.parametrize("bad", ["Email me at avery@mail.com", "See https://hudl.com/x", "Call 555-123-4567",
                                 "Hello Coach Johnson,", "Visit www.example.com"])
def test_draft_with_invented_contact_link_or_coach_is_rejected(app, bad):
    client, store, model, _, headers, _ = app
    model.draft = {"subject": "2028 QB", "body": f"Hello Coach,\n\n{bad}\n\nAvery"}
    response = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers)
    assert response.status_code == 502 and store.drafts == []


def test_questionnaire_link_is_inserted_by_the_server_only(app):
    client, store, model, _, headers, _ = app
    model.draft = {"subject": "2028 QB", "body": f"Hello Coach,\n\nI will fill out your questionnaire:\n{cp.QUESTIONNAIRE}\n\nAvery"}
    body = client.post(f"/api/workspace/colleges/{SUBJECT}/harcum-college/outreach-draft", headers=headers).json()["draft"]["body"]
    assert "https://www.harcum.edu/recruitment" in body and cp.QUESTIONNAIRE not in body
    assert 'recruit_questionnaire": "available"' in model.calls[-1][1] and "harcum.edu" not in model.calls[-1][1]
    stripped = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers).json()["draft"]["body"]
    assert cp.QUESTIONNAIRE not in stripped


def test_paid_calls_are_rate_limited_per_athlete(app):
    client, store, model, _, headers, _ = app
    builds = [client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers).status_code for _ in range(6)]
    assert builds == [200] * 5 + [429]
    url = f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft"
    drafts = [client.post(url, headers=headers).status_code for _ in range(11)]
    assert drafts == [200] * 10 + [429]
    assert client.post(url, headers=headers).json()["detail"] == cp.TOO_MANY


def test_banned_reason_is_cached_not_rebuilt(app, monkeypatch):
    client, store, model, _, headers, _ = app
    original = model.__call__
    def scholarship(system, user, max_tokens):
        reply = original(system, user, max_tokens)
        reply["reasons"][0]["reason"] = "It offers a scholarship."
        return reply
    monkeypatch.setattr(cp, "model_json", scholarship)
    first = client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers).json()
    assert first["programs"][0]["reason"] is None
    client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers)
    assert len(model.calls) == 1


def test_news_release_links_are_not_confirmed():
    p = {"id": "x", "school": "University of Nebraska", "city": "Lincoln", "state": "NE", "governing_body": "NCAA-D1",
         "program_url": "https://huskers.com/news/2025/10/1/womens-flag-football-added", "source_urls": ["https://huskers.com/news/x"],
         "verified_on": "2026-10-01"}
    c = cp.card(p)
    assert c["program_link"] is None and c["program_link_label"] == "Program link not confirmed" and c["source_links"]
    for path in ("/releases/flag", "/blog/flag", "/general/2025/flag"):
        assert cp.card({**p, "program_url": "https://x.edu" + path})["program_link"] is None
    assert cp.card({**p, "program_url": "https://x.edu/sports/womens-flag-football"})["program_link"]


def test_data_rows_are_checked_at_load():
    good = json.dumps([{"school": "A", "city": "B", "state": "TX", "governing_body": "NAIA", "verified_on": "2026-10-01", "source_urls": []}])
    assert cp.load_programs(good)[0]["id"] == "a"
    for bad in ([], [{"school": "A"}], [{**json.loads(good)[0], "governing_body": "NCAA"}], json.loads(good) * 2):
        with pytest.raises(ValueError):
            cp.load_programs(json.dumps(bad))
    assert len(cp.programs()) == 189


def test_d3_has_no_eligibility_center_rule():
    rules = {r["governing_body"]: [i["text"] for i in r["rules"]] for r in cp.contact_rules(cp.LEVELS)}
    assert not any("Eligibility Center" in t for t in rules["NCAA-D3"])
    assert all(any("Eligibility Center" in t for t in rules[b]) for b in ("NCAA-D1", "NCAA-D2"))


def test_plausible_grad_year_window_is_this_year_to_plus_six():
    from datetime import date
    today = date(2026, 10, 2)
    assert [elig.plausible_grad_year(v, today) for v in (2011, 2025, 2026, 2029, 2033, 2034, None, True, "2029", "x")] == \
        [None, None, 2026, 2029, 2033, None, None, None, 2029, None]


@pytest.mark.parametrize("stored, sent", [(2011, None), (None, None), (2029, 2029)])
def test_stale_grad_year_never_reaches_the_reason_or_draft_prompt(app, stored, sent):
    client, store, model, _, headers, _ = app
    store.profiles[SUBJECT]["class_year"] = stored
    model.draft = {"subject": "QB flag football", "body": "Hello Coach,\n\nI play QB.\n\nAvery"}
    client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers)
    reason_system, reason_user = model.calls[-1]
    assert json.loads(reason_user)["athlete"]["grad_year"] == sent
    assert "If grad_year is null, never mention a grad year" in reason_system
    url = f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft"
    assert client.post(url, headers=headers).status_code == 200
    draft_system, draft_user = model.calls[-1]
    assert f'"class_year": {json.dumps(sent)}' in draft_user
    assert "If class_year is null, never mention a grad year" in draft_system
    if sent is None:
        assert "2011" not in reason_user and "2011" not in draft_user


@pytest.mark.parametrize("subject, body", [("Class of 2011 QB", "Hello Coach,\n\nI play QB.\n\nAvery"),
                                           ("QB flag football", "Hello Coach,\n\nI am a 2011 grad.\n\nAvery"),
                                           ("QB", "Hello Coach,\n\nI graduate in 2030.\n\nAvery"),
                                           ("QB", "Hello Coach,\n\nI graduate in May 2030.\n\nAvery"),
                                           ("QB, class of \u201930", "Hello Coach,\n\nI play QB.\n\nAvery"),
                                           ("QB", "Hello Coach,\n\nI started playing in 2019.\n\nAvery")])
def test_draft_naming_a_grad_year_is_rejected_when_none_is_known(app, subject, body):
    client, store, model, _, headers, _ = app
    store.profiles[SUBJECT]["class_year"] = 2011
    model.draft = {"subject": subject, "body": body}
    response = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers)
    assert response.status_code == 502 and store.drafts == []


def test_plausible_grad_year_is_used_in_the_draft(app):
    client, store, model, _, headers, _ = app
    store.profiles[SUBJECT]["class_year"] = 2029
    model.draft = {"subject": "2029 QB flag football", "body": "Hello Coach,\n\nI am in the class of 2029.\n\nAvery"}
    created = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers).json()["draft"]
    assert created["subject"] == "2029 QB flag football"


def test_generic_all_sports_is_not_sent_as_the_sport(app):
    client, store, model, identity, headers, _ = app
    identity["sport"] = "All Sports"
    client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers)
    client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers)
    assert "All Sports" not in model.calls[-1][1]


def test_draft_naming_another_year_is_rejected_even_with_a_known_grad_year(app):
    client, store, model, _, headers, _ = app
    store.profiles[SUBJECT]["class_year"] = 2029
    model.draft = {"subject": "2029 QB", "body": "Hello Coach,\n\nClass of 2031.\n\nAvery"}
    response = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers)
    assert response.status_code == 502 and store.drafts == []


def test_cached_list_built_from_old_facts_is_not_served(app):
    client, store, model, _, headers, _ = app
    store.profiles[SUBJECT]["class_year"] = 2011  # stale year: omitted from facts
    built = client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers).json()
    assert built["built"] and built["programs"][0]["reason"]
    # A list saved under the old key (built when 2011 still reached the model) is not shown.
    store.rows[SUBJECT]["inputs_key"] = "built-with-class-year-2011"
    listed = client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers).json()
    assert listed["eligible"] and listed["built"] is False and listed["programs"] == []
    pid = built["programs"][0]["id"]
    assert client.get(f"/api/workspace/colleges/{SUBJECT}/{pid}", headers=headers).json()["program"]["reason"] is None
    # The current key is still served.
    client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers)
    assert client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers).json()["built"] is True


def test_stored_draft_with_a_stale_year_is_hidden(app):
    client, store, model, _, headers, _ = app
    url = f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft"
    client.post(url, headers=headers)
    store.drafts[-1]["payload"]["subject"] = "Class of 2011 QB"
    store.profiles[SUBJECT]["class_year"] = 2011
    assert client.get(url, headers=headers).json() == {"draft": None}
    store.drafts[-1]["payload"]["subject"] = "QB flag football"
    assert client.get(url, headers=headers).json()["draft"]["subject"] == "QB flag football"
