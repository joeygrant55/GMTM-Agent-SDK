"""Junior colleges on the profile app: routes, girls-first gate, ranking, model inputs, links, drafts.

Every outside effect is a fake: college_programs.store (Agent DB), read_identity and
read_athlete (GMTM) and model_json (model). junior_entry.store is a MemoryStore.
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
    ("GET", "/api/workspace/saved-colleges/{clerk_id}"), ("POST", "/api/workspace/saved-colleges/{clerk_id}/{program_id}"),
    ("POST", "/api/workspace/colleges/{clerk_id}/{program_id}/sent"),
}
BODIES = {"/api/workspace/saved-colleges/{clerk_id}/{program_id}": {"saved": True},
          "/api/workspace/colleges/{clerk_id}/{program_id}/sent": {"sent": True}}
# Real GMTM junior drill names (events 1305/1314/1317); Plano, TX.
DRILLS = [{"name": "20-Yard Dash", "value": 3.42, "unit": "seconds"}, {"name": "5-10-5 Shuttle", "value": 5.1, "unit": "seconds"},
          {"name": "Standing Broad Jump", "value": 84, "unit": "inches"}]
ORIGIN = {"city": CITY, "state": "TX", "lat": 33.05, "lon": -96.75}


class CollegeStore:
    def __init__(self, state="TX"):
        self.rows, self.drafts, self.saves = {}, [], 0
        self.marked = {"sparq_saved_colleges": {}, "sparq_sent_emails": {}}
        self.mark_calls = []
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

    def marks(self, clerk_id):
        return tuple({pid: at for (c, pid), at in self.marked[t].items() if c == clerk_id}
                     for t in ("sparq_saved_colleges", "sparq_sent_emails"))

    def set_mark(self, table, clerk_id, program_id, on):
        self.mark_calls.append((table, clerk_id, program_id, on))
        rows = self.marked[table]
        if on:
            rows.setdefault((clerk_id, program_id), datetime(2026, 10, 2, 12, len(self.mark_calls)))
        else:
            rows.pop((clerk_id, program_id), None)

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
    athlete = {"drills": [dict(d) for d in DRILLS], "origin": dict(ORIGIN)}
    monkeypatch.setattr(cp, "store", store)
    monkeypatch.setattr(cp, "read_athlete", lambda uid: athlete if uid == USER_ID else None)
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
        body = BODIES.get(path)
        assert client.request(method, url.replace("{clerk_id}", SUBJECT), json=body).status_code == 401
        assert client.request(method, url.replace("{clerk_id}", "user_other"), headers=headers, json=body).status_code == 403
    assert model.calls == [] and store.saves == 0 and store.mark_calls == []


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
        # Only distance and map position are numbers; never a fit number.
        numeric = {k for k, v in walk(body) if isinstance(v, (int, float)) and not isinstance(v, bool)}
        assert numeric <= {"distance_mi", "x", "y", "saved_count", "sent_count"}


def test_reason_prompt_has_only_the_allowed_fields(app):
    client, store, model, _, headers, _ = app
    client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers)
    (system, user), = model.calls
    for secret in (NAME, "Avery", "Quintero", CITY, EMAIL, "@"):
        assert secret not in user
    sent = json.loads(user)
    assert set(sent) == {"athlete", "programs"}
    # Real GMTM junior drills, not the old 40/shuttle/vertical profile copy (which had a 40 and a vertical).
    assert sent["athlete"] == {"position": "QB", "grad_year": 2028, "state": "TX", "drill_results": DRILLS}
    assert "40-Yard" not in user and "Vertical" not in user and "33.05" not in user and "-96.75" not in user
    assert all(set(p) == {"id", "school", "state", "level", "conference", "notes"} for p in sent["programs"])
    for rule in ("never invent coaches, emails, rosters, scholarships, records", 'never say "verified" or "recruited"', "2 short sentences",
                 "name a drill only as it is given in drill_results"):
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
    # Cards are shown closest first, so find the first ranked program by id.
    assert next(c for c in first["programs"] if c["id"] == cp.rank("TX")[0]["id"])["reason"] is None
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
    assert len(cp.programs()) == 187


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


# ── Slice 2: saves, "I sent it", distances, drills, data hygiene ──────────────

def built(client, headers):
    """Build her list; returns the listed program ids (a TX athlete)."""
    return [c["id"] for c in client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers).json()["programs"]]


def test_save_is_idempotent_and_unsave_removes(app):
    client, store, model, _, headers, _ = app
    pid = built(client, headers)[0]
    url = f"/api/workspace/saved-colleges/{SUBJECT}/{pid}"
    first = client.post(url, headers=headers, json={"saved": True})
    again = client.post(url, headers=headers, json={"saved": True})
    assert first.json() == again.json() == {"program_id": pid, "saved": True}
    saved, _ = store.marks(SUBJECT)
    assert list(saved) == [pid] and saved[pid] == datetime(2026, 10, 2, 12, 1)  # first time kept
    listed = client.get(f"/api/workspace/saved-colleges/{SUBJECT}", headers=headers).json()
    assert listed["saved_count"] == 1 and [c["id"] for c in listed["saved"]] == [pid] and listed["saved"][0]["saved"] is True
    assert client.post(url, headers=headers, json={"saved": False}).json()["saved"] is False
    assert client.post(url, headers=headers, json={"saved": False}).status_code == 200
    assert store.marks(SUBJECT)[0] == {} and client.get(f"/api/workspace/saved-colleges/{SUBJECT}", headers=headers).json()["saved"] == []


def test_marks_only_for_programs_in_her_built_list(app):
    client, store, model, _, headers, _ = app
    url = lambda pid: f"/api/workspace/saved-colleges/{SUBJECT}/{pid}"
    assert client.post(url("daytona-state-college"), headers=headers, json={"saved": True}).status_code == 409  # not built
    listed = built(client, headers)
    assert "daytona-state-college" not in listed  # Florida school, TX list
    assert client.post(url("daytona-state-college"), headers=headers, json={"saved": True}).status_code == 404
    assert client.post(f"/api/workspace/colleges/{SUBJECT}/daytona-state-college/sent", headers=headers, json={"sent": True}).status_code == 404
    assert store.mark_calls == []
    # Clearing is always allowed, so a mark left from an older list can be removed.
    assert client.post(url("daytona-state-college"), headers=headers, json={"saved": False}).status_code == 200


def test_missing_mark_tables_do_not_break_the_college_pages(app, monkeypatch, caplog):
    client, store, model, _, headers, _ = app
    pid = built(client, headers)[0]

    class ProgrammingError(Exception):
        pass

    def missing(clerk_id):
        raise ProgrammingError("(1146, \"Table 'agent.sparq_saved_colleges' doesn't exist\")")
    monkeypatch.setattr(store, "marks", missing)
    for url in (f"/api/workspace/colleges/{SUBJECT}", f"/api/workspace/colleges/{SUBJECT}/{pid}", f"/api/workspace/saved-colleges/{SUBJECT}"):
        response = client.get(url, headers=headers)
        assert response.status_code == 200, url
    body = client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers).json()
    assert body["saved_count"] == 0 and not any(c["saved"] for c in body["programs"])
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "ProgrammingError" in logged and "doesn't exist" not in logged and "sparq_saved_colleges" not in logged


def test_gmtm_read_failure_logs_only_the_class(app, monkeypatch, caplog):
    client, store, model, _, headers, _ = app
    monkeypatch.setattr(cp, "read_athlete", lambda uid: (_ for _ in ()).throw(ValueError(f"secret {NAME} {CITY}")))
    assert client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers).status_code == 200
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "ValueError" in logged and NAME not in logged and CITY not in logged


def test_contact_rules_follow_her_list_order():
    rules = cp.contact_rules(["NAIA", "NJCAA", "NAIA", "NCAA-D2"])
    assert [r["governing_body"] for r in rules] == ["NAIA", "NJCAA", "NCAA-D2"]


@pytest.mark.parametrize("body", [None, {}, {"saved": "yes"}, {"saved": 1}, {"saved": True, "extra": 1}])
def test_save_rejects_a_loose_body(app, body):
    client, store, *_ , headers, _ = app
    assert client.post(f"/api/workspace/saved-colleges/{SUBJECT}/{cp.rank('TX')[0]['id']}", headers=headers, json=body).status_code == 422
    assert store.mark_calls == []


def test_save_unknown_program_or_ineligible_is_refused(app):
    client, store, model, identity, headers, _ = app
    identity["gender"] = 2
    assert client.post(f"/api/workspace/saved-colleges/{SUBJECT}/daytona-state-college", headers=headers, json={"saved": True}).status_code == 403
    assert client.get(f"/api/workspace/saved-colleges/{SUBJECT}", headers=headers).json()["eligible"] is False
    identity["gender"] = 1
    assert client.post(f"/api/workspace/saved-colleges/{SUBJECT}/no-such-school", headers=headers, json={"saved": True}).status_code == 404
    assert store.mark_calls == []


def test_sent_needs_a_draft_is_idempotent_and_stores_no_text(app):
    client, store, model, _, headers, _ = app
    pid = built(client, headers)[0]
    sent = f"/api/workspace/colleges/{SUBJECT}/{pid}/sent"
    assert client.post(sent, headers=headers, json={"sent": True}).status_code == 409
    client.post(f"/api/workspace/colleges/{SUBJECT}/{pid}/outreach-draft", headers=headers)
    first = client.post(sent, headers=headers, json={"sent": True}).json()
    again = client.post(sent, headers=headers, json={"sent": True}).json()
    assert first == again and first["program_id"] == pid and first["sent_at"].startswith("2026-10-02T12:")
    # Only (table, owner, program, on): no subject, body or address reaches the sent table.
    assert all(len(call) == 4 and call[2] == pid for call in store.mark_calls)
    assert client.get(f"/api/workspace/saved-colleges/{SUBJECT}", headers=headers).json()["sent_count"] == 1
    detail = client.get(f"/api/workspace/colleges/{SUBJECT}/{pid}", headers=headers).json()["program"]
    assert detail["sent_at"] == first["sent_at"]
    assert client.post(sent, headers=headers, json={"sent": False}).json()["sent_at"] is None
    assert store.marks(SUBJECT)[1] == {}


def test_marks_are_rate_limited(app, monkeypatch):
    client, store, *_ , headers, _ = app
    monkeypatch.setattr(cp, "MARKS_PER_HOUR", 3)
    pid = built(client, headers)[0]
    codes = [client.post(f"/api/workspace/saved-colleges/{SUBJECT}/{pid}", headers=headers, json={"saved": i % 2 == 0}).status_code for i in range(4)]
    assert codes == [200, 200, 200, 429]


def test_list_has_distance_map_saved_flags_and_no_coach_contact(app):
    client, store, model, _, headers, _ = app
    client.post(f"/api/workspace/saved-colleges/{SUBJECT}/{built(client, headers)[0]}", headers=headers, json={"saved": True})
    body = client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers).json()
    assert body["origin"] == {"city": CITY, "state": "TX", "map": cp.map_point(33.05, -96.75)}
    distances = [c["distance_mi"] for c in body["programs"]]
    assert all(isinstance(d, int) and d > 0 for d in distances) and distances == sorted(distances)
    assert all(0 <= c["map"]["x"] <= 100 and 0 <= c["map"]["y"] <= 100 for c in body["programs"])
    assert body["saved_count"] == 1 and sum(c["saved"] for c in body["programs"]) == 1
    for key, _ in walk(body):
        assert key not in ("coach_email", "head_coach_name", "lat", "lon", "staff_page_url")
    assert "@" not in json.dumps(body)


def test_gmtm_down_still_lists_without_distance(app, monkeypatch):
    client, store, model, _, headers, _ = app
    client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers)
    monkeypatch.setattr(cp, "read_athlete", lambda uid: (_ for _ in ()).throw(RuntimeError("gmtm down")))
    body = client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers).json()
    assert body["built"] is True and len(body["programs"]) == 12 and body["origin"] is None
    assert all(c["distance_mi"] is None for c in body["programs"])


def test_new_drill_results_make_the_saved_list_stale(app):
    client, store, model, _, headers, _ = app
    client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers)
    assert client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers).json()["built"] is True
    cp.read_athlete(USER_ID)["drills"][0]["value"] = 3.3  # a newer, faster dash on GMTM
    assert client.get(f"/api/workspace/colleges/{SUBJECT}", headers=headers).json()["built"] is False
    client.post(f"/api/workspace/trigger-matching/{SUBJECT}", headers=headers)
    assert len(model.calls) == 2 and '"value": 3.3' in model.calls[-1][1]


def test_distance_math():
    orlando, daytona, miami = (28.5383, -81.3792), (29.1907, -81.0971), (25.7617, -80.1918)
    assert 45 < cp.miles(orlando, daytona) < 55 and cp.about_miles(cp.miles(orlando, daytona)) == 50
    assert 200 < cp.miles(orlando, miami) < 240 and cp.miles(orlando, orlando) == 0
    assert cp.miles((40.7128, -74.006), (34.0522, -118.2437)) == pytest.approx(2445, abs=10)  # NYC-LA
    assert [cp.about_miles(v) for v in (0, 2.4, 7.6, 98, 101, 146)] == [5, 5, 10, 100, 100, 150]
    assert cp.map_point(64.2, -149.5) is None and cp.map_point(None, -80) is None and cp.map_point(float("nan"), -80) is None
    west, east = cp.map_point(47.6, -122.3), cp.map_point(25.8, -80.2)  # Seattle, Miami
    assert west["x"] < 15 and west["y"] < 20 and east["x"] > 80 and east["y"] > 85


def test_origin_prefers_gmtm_point_then_program_city_then_nothing():
    assert cp._origin({"lat": 28.54, "lng": -81.38, "city": "Orlando", "state": "Florida"}) == \
        {"city": "Orlando", "state": "FL", "lat": 28.54, "lon": -81.38}
    fallback = cp._origin({"lat": None, "lng": None, "city": "Daytona Beach", "state": "FL"})
    assert (fallback["lat"], fallback["lon"]) == (29.191, -81.097)
    assert cp._origin({"lat": 0, "lng": 0, "city": "Nowhere", "state": "FL"}) is None
    assert cp._origin(None) is None and cp._origin({"lat": 51.5, "lng": -0.1, "city": "London", "state": None}) is None


def test_drills_are_newest_per_drill_without_body_size_in_seconds():
    metrics = [{"label": "Height", "value": 64, "unit": "inches", "recorded_at": "2026-09-01"},
               {"label": "20-Yard Dash", "value": 3.6, "unit": "seconds", "recorded_at": "2026-08-01"}]
    submitted = [{"label": "20-Yard Dash", "value": 3420, "unit": "milliseconds", "recorded_at": "2026-09-20T10:00:00"},
                 {"label": "Push-Ups", "value": 22.0, "unit": "repetitions", "recorded_at": "2026-09-20T10:00:00"},
                 {"label": "Weight", "value": 120, "unit": "lb", "recorded_at": "2026-09-21"}]
    assert cp._drills(metrics, submitted) == [{"name": "20-Yard Dash", "value": 3.42, "unit": "seconds"},
                                              {"name": "Push-Ups", "value": 22, "unit": "repetitions"}]
    bad = [{"label": "Sit-Ups", "value": "lots", "unit": "repetitions", "recorded_at": "2026-09-22"},
           {"label": "Broad Jump", "value": None, "unit": "inches", "recorded_at": "2026-09-22"},
           {"label": "60-Yard Shuttle", "value": float("inf"), "unit": "seconds", "recorded_at": "2026-09-22"}]
    assert cp._drills(metrics, submitted + bad) == cp._drills(metrics, submitted)  # bad drills skipped, others kept


def test_read_athlete_uses_the_read_only_evidence_readers(monkeypatch):
    import athlete_evidence as ev
    import athlete_materials as am

    class Cursor:
        def __init__(self, db): self.db = db
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, sql, args): self.db.sql.append(sql)
        def fetchall(self): return [{"user_id": USER_ID, "lat": 33.02, "lng": -96.70, "city": "Plano", "state": "TX"}]

    class DB:
        def __init__(self): self.sql, self.closed = [], False
        def cursor(self): return Cursor(self)
        def close(self): self.closed = True

    db = DB()
    monkeypatch.setattr(ev, "_get_gmtm_db", lambda: db)
    monkeypatch.setattr(ev, "_metric_rows", lambda d, uid: [{"metric_id": 1, "user_id": uid, "title": "20 Yard Dash", "value": "3.50", "unit": "s",
                                                             "created_on": "2026-08-01 10:00:00", "is_current": 1, "visibility": 2,
                                                             "user_approved": 1, "suggested_by": None, "event_id": None}])
    payload = json.dumps({"questions": {"metric:5-10-5 Shuttle": {"type": "metric", "value": {"value": 5100, "unit": "ss.00"}}}})
    monkeypatch.setattr(am, "_submission_rows", lambda d, uid: [{
        "task_submission_id": 9, "user_id": uid, "task_id": 3, "joined_task_id": 3, "created_on": "2026-09-20 10:00:00",
        "visibility": 2, "task_visibility": 2, "event_id": 1305, "joined_event_id": 1305, "event_visibility": 2,
        "event_published": 1, "event_public": 1, "event_invite_only": 0, "event_networks_only": 0, "event_product_id": None,
        "payload": payload, "payload_bytes": len(payload), "event_name": "USA Football Junior Combine", "task_title": "Shuttle"}])
    got = cp.read_athlete(USER_ID)
    assert got == {"drills": [{"name": "5-10-5 Shuttle", "value": 5.1, "unit": "seconds"}, {"name": "20-Yard Dash", "value": 3.5, "unit": "seconds"}],
                   "origin": {"city": "Plano", "state": "TX", "lat": 33.02, "lon": -96.7}}
    assert db.closed and all(sql.lstrip().upper().startswith("SELECT") for sql in db.sql)


def test_data_hygiene_from_the_contacts_research():
    rows = cp.programs()
    schools = {p["school"] for p in rows}
    assert "Augsburg University" not in schools and "Saint Vincent College" not in schools  # club, not varsity
    assert cp.program("albright-college")["starts"] == "Starts spring 2027"
    assert cp.card(cp.program("albright-college"))["starts"] == "Starts spring 2027"
    urls = lambda p: json.dumps([p.get(k) for k in ("program_url", "source_urls", "staff_page_url", "questionnaire_url", "color_source_url")])
    assert not any("davenportpanthers.com" in urls(p) for p in rows)
    assert "dupanthers.com" in cp.program("davenport-university")["staff_page_url"]
    assert all(cp.continental(p["lat"], p["lon"]) for p in rows)
    assert all(p["primary_color"] is None or len(p["primary_color"]) == 7 for p in rows)
    assert sum(1 for p in rows if p["primary_color"]) >= 130 and all(p["contacts_verified_on"] == "2026-10-02" for p in rows)
    sources = json.loads((cp.DATA_FILE.parent / "college_womens_flag_2026.sources.json").read_text())
    assert "Gazetteer" in sources["city_lat_lon"] and sources["no_lat_lon"] == []
    with pytest.raises(ValueError):
        cp.load_programs(json.dumps([{**rows[0], "lat": 51.5, "lon": -0.1}]))
    with pytest.raises(ValueError):
        cp.load_programs(json.dumps([{**rows[0], "primary_color": "red"}]))
