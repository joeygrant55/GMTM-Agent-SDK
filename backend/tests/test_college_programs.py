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
    ("GET", "/api/workspace/college-emails/{clerk_id}"),
    ("GET", "/api/workspace/parent-contact/{clerk_id}"), ("POST", "/api/workspace/parent-contact/{clerk_id}"),
}
BODIES = {"/api/workspace/saved-colleges/{clerk_id}/{program_id}": {"saved": True},
          "/api/workspace/colleges/{clerk_id}/{program_id}/sent": {"sent": True},
          "/api/workspace/parent-contact/{clerk_id}": {"email": "parent@example.com"}}
HIGHLIGHT = {"url": "https://gmtm.com/film/301", "reel": True}


def card_clip(n, title="Game clip", reel=False):
    return {"id": f"film-{n}", "title": title, "source_label": "Your GMTM footage", "recorded_at": f"2026-09-{n:02d}T00:00:00",
            "thumbnail_url": None, "source_url": f"https://gmtm.com/film/{n}", "video_url": None, "reel": reel}


# Her eligible clips, newest first (read_card already dropped private and dead ones).
CARD = [card_clip(9), card_clip(7, "Highlight Reel", reel=True), card_clip(5)]
# Real GMTM junior drill names (events 1305/1314/1317); Plano, TX.
DRILLS = [{"name": "20-Yard Dash", "value": 3.42, "unit": "seconds"}, {"name": "5-10-5 Shuttle", "value": 5.1, "unit": "seconds"},
          {"name": "Standing Broad Jump", "value": 84, "unit": "inches"}]
ORIGIN = {"city": CITY, "state": "TX", "lat": 33.05, "lon": -96.75}


class CollegeStore:
    def __init__(self, state="TX"):
        self.rows, self.drafts, self.saves = {}, [], 0
        self.marked = {"sparq_saved_colleges": {}, "sparq_sent_emails": {}}
        self.mark_calls = []
        self.parents = {}
        self.cards = {}
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
        self.drafts.append({"id": len(self.drafts) + 1, "clerk_id": clerk_id, "payload": payload, "sources": sources,
                            "created_at": datetime(2026, 10, 1, 9, len(self.drafts))})
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

    def drafted(self, clerk_id):
        return {d["payload"]["program_id"]: d["created_at"] for d in self.drafts if d["clerk_id"] == clerk_id}

    def parent_email(self, clerk_id): return self.parents.get(clerk_id)

    def set_parent_email(self, clerk_id, email):
        if email:
            self.parents[clerk_id] = email
        else:
            self.parents.pop(clerk_id, None)

    def card_picks(self, clerk_id): return list(self.cards.get(clerk_id, []))

    def set_card_picks(self, clerk_id, film_ids):
        if film_ids:
            self.cards[clerk_id] = list(film_ids)
        else:
            self.cards.pop(clerk_id, None)

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
    store, model, identity = CollegeStore(), Model(), {"gender": 1, "sport": "Flag Football", "visibility": 2}
    athlete = {"drills": [dict(d) for d in DRILLS], "origin": dict(ORIGIN)}
    monkeypatch.setattr(cp, "store", store)
    monkeypatch.setattr(cp, "read_athlete", lambda uid: athlete if uid == USER_ID else None)
    monkeypatch.setattr(cp, "read_featured", lambda clerk_id: None)
    monkeypatch.setattr(cp, "read_highlight", lambda uid, featured=None: dict(HIGHLIGHT) if uid == USER_ID else None)
    monkeypatch.setattr(cp, "model_json", model)
    monkeypatch.setattr(cp, "read_identity", lambda uid: dict(identity) if uid == USER_ID else None)
    monkeypatch.setattr(cp, "read_card", lambda uid: [dict(c) for c in CARD] if uid == USER_ID else [])
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
    mounted = {(m, r.path) for r in profile_app.routes for m in getattr(r, "methods", ())
               if "college" in r.path or "trigger" in r.path or "parent-contact" in r.path}
    assert mounted == ROUTES
    combine = candidate_app.create_app()
    assert not any("college" in r.path or "trigger" in r.path or "parent-contact" in r.path for r in combine.routes)


def test_owner_checks_401_and_403(app):
    client, store, model, *_ , headers, _ = app
    for method, path in ROUTES:
        url = path.replace("{program_id}", "midland-university")
        body = BODIES.get(path)
        assert client.request(method, url.replace("{clerk_id}", SUBJECT), json=body).status_code == 401
        assert client.request(method, url.replace("{clerk_id}", "user_other"), headers=headers, json=body).status_code == 403
    assert model.calls == [] and store.saves == 0 and store.mark_calls == [] and store.parents == {}


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


KIT_BLOCK = ("My highlight reel: https://gmtm.com/film/301\nMy GMTM profile: https://gmtm.com/athletes/7301\n"
             "My combine results: 20-Yard Dash 3.42 s, 5-10-5 Shuttle 5.1 s")


def test_draft_uses_first_name_only_and_server_adds_coach_links_and_drills(app):
    client, store, model, _, headers, _ = app
    url = f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft"
    assert client.get(url, headers=headers).json() == {"draft": None}
    created = client.post(url, headers=headers).json()["draft"]
    # Sourced coach (Tyrone Poole, Alabama State staff page): the server adds the name and the To address.
    assert created["to_email"] == "Tpoole2483@alasu.edu"
    assert created["body"] == f"Hello Coach Poole,\n\nI play QB.\n\n{KIT_BLOCK}\n\nAvery"
    assert created["kit"] == {"grad_year": 2028, "position": "QB", "hometown": "Plano, TX",
                              "highlight_url": HIGHLIGHT["url"], "highlight_reel": True,
                              "profile_url": "https://gmtm.com/athletes/7301",
                              "drills": ["20-Yard Dash 3.42 s", "5-10-5 Shuttle 5.1 s"]}
    assert client.get(url, headers=headers).json()["draft"] == created
    system, user = model.calls[-1]
    # The model never sees a last name, city, coach, link or drill result.
    for secret in ("Quintero", CITY, EMAIL, "Poole", "alasu", "gmtm.com", "7301", "3.42", "Standing Broad"):
        assert secret not in user, secret
    assert "Avery" in user and "Coach email (if known): (none)" in user and "Alabama State University" in user
    assert system == cp.JUNIOR_DRAFT_SYSTEM and "never name a coach" in system and "recruit_questionnaire\": \"not available\"" in user
    saved = store.drafts[-1]["payload"]
    assert saved["to_email"] == "Tpoole2483@alasu.edu" and saved["to_name"] == "Tyrone Poole" and saved["program_id"] == "alabama-state-university"


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


# ── Slice 3: coach email kit, Emails page, CC my parent ───────────────────────

COACH_KEYS = ("coach", "coach_email", "head_coach_name", "staff_page_url", "names", "last_name")


def test_coach_contact_only_on_the_detail_route(app):
    client, store, model, _, headers, _ = app
    pid = "alabama-state-university"
    store.drafts.append({"id": 1, "clerk_id": SUBJECT, "payload": {"program_id": pid, "subject": "s", "body": "b"},
                         "sources": [], "created_at": datetime(2026, 10, 1)})
    detail = client.get(f"/api/workspace/colleges/{SUBJECT}/{pid}", headers=headers).json()
    assert detail["coach"] == {"names": ["Tyrone Poole"], "last_name": "Poole", "role": "Head coach, women's flag football",
                               "email": "Tpoole2483@alasu.edu",
                               "staff_page_url": "https://bamastatesports.com/sports/womens-flag-football/coaches",
                               "source_checked": "Source checked Oct 2, 2026"}
    assert [r["governing_body"] for r in detail["contact_rules"]] == ["NCAA-D1"]
    built(client, headers)
    for url in (f"/api/workspace/colleges/{SUBJECT}", f"/api/workspace/saved-colleges/{SUBJECT}", f"/api/workspace/college-emails/{SUBJECT}"):
        body = client.get(url, headers=headers).json()
        assert not any(k in COACH_KEYS for k, _ in walk(body)), url
        assert "@" not in json.dumps(body), url


def test_coach_is_never_invented_when_the_data_has_none(app):
    client, store, model, _, headers, _ = app
    none = [p for p in cp.programs() if not p.get("head_coach_name") and not p.get("coach_email")]
    assert none
    for p in none:
        c = cp.coach(p)
        assert c["names"] == [] and c["last_name"] is None and c["role"] is None and c["email"] is None and c["source_checked"] is None
        assert c["staff_page_url"] == cp.https(p.get("staff_page_url"))
    # No coach in the data: the draft keeps "Hello Coach," and To stays empty.
    pid = none[0]["id"]
    created = client.post(f"/api/workspace/colleges/{SUBJECT}/{pid}/outreach-draft", headers=headers).json()["draft"]
    assert created["to_email"] == "" and created["body"].startswith("Hello Coach,\n")
    assert store.drafts[-1]["payload"]["to_name"] == "Head coach"


def test_coach_name_parsing_and_bad_addresses():
    assert [cp.coach_last_name(n) for n in ("Tyrone Poole", "Todd Fox '95", "Janssen Wilborn II", "Madonna", "Anna Taylor '25")] == \
        ["Poole", "Fox", "Wilborn", None, "Taylor"]
    co = cp.coach({"head_coach_name": "Dominic Colavito; Joseph Newman", "coach_email": "dc@post.edu", "contacts_verified_on": "2026-10-02"})
    assert co["names"] == ["Dominic Colavito", "Joseph Newman"] and co["last_name"] is None and co["role"].startswith("Co-head coach")
    for bad in ("a@x.edu,b@y.com", "a@x.edu;b@y.com", "a%0D%0Abcc:x@y.com", "a@x", "a b@x.edu", "x" * 250 + "@a.edu", 5):
        assert cp.coach({"coach_email": bad})["email"] is None, bad
    for p in cp.programs():  # every served address is one plain address
        email = cp.coach(p)["email"]
        assert email is None or cp.PLAIN_EMAIL.fullmatch(email)


def test_hometown_and_links_are_server_inserted_never_sent_to_the_model(app):
    client, store, model, _, headers, _ = app
    model.draft = {"subject": f"2028 QB, {cp.HOMETOWN}, interested in Alabama State flag football",
                   "body": f"Hello Coach,\n\nI am Avery, a QB from {cp.HOMETOWN}.\n\n{cp.FACTS}\n\nCoaches may not be able to reply yet.\n\nAvery"}
    created = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers).json()["draft"]
    assert created["subject"] == "2028 QB, Plano, TX, interested in Alabama State flag football"
    assert created["body"] == f"Hello Coach Poole,\n\nI am Avery, a QB from Plano, TX.\n\n{KIT_BLOCK}\n\nCoaches may not be able to reply yet.\n\nAvery"
    assert CITY not in model.calls[-1][1] and cp.HOMETOWN in model.calls[-1][0] and cp.FACTS in model.calls[-1][0]


def test_draft_without_gmtm_city_footage_or_user_id_omits_those_parts(app, monkeypatch):
    client, store, model, _, headers, _ = app
    monkeypatch.setattr(cp, "read_highlight", lambda uid, featured=None: None)
    monkeypatch.setattr(cp, "read_athlete", lambda uid: {"drills": [], "origin": None})
    model.draft = {"subject": f"QB, {cp.HOMETOWN}", "body": f"Hello Coach,\n\nFrom {cp.HOMETOWN}.\n\n{cp.FACTS}\n\nAvery"}
    created = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers).json()["draft"]
    assert created["subject"] == "QB, Texas"
    assert created["body"] == "Hello Coach Poole,\n\nFrom Texas.\n\nMy GMTM profile: https://gmtm.com/athletes/7301\n\nAvery"
    assert created["kit"]["highlight_url"] is None and created["kit"]["drills"] == []
    # A footage read failure only drops the video line.
    monkeypatch.setattr(cp, "read_highlight", lambda uid, featured=None: (_ for _ in ()).throw(RuntimeError("down")))
    assert client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers).status_code == 200


def test_a_non_reel_clip_is_called_a_video_and_best_drills_put_speed_first():
    kit = {"highlight_url": "https://gmtm.com/film/9", "highlight_reel": False, "profile_url": None, "drills": []}
    assert cp.kit_block(kit) == "My video: https://gmtm.com/film/9"
    drills = [{"name": "Standing Broad Jump", "value": 84, "unit": "inches"}, {"name": "5-10-5 Shuttle Run", "value": 5.1, "unit": "seconds"},
              {"name": "Push-Ups", "value": 30, "unit": "reps"}]
    assert cp.best_drills(drills) == ["5-10-5 Shuttle Run 5.1 s", "Standing Broad Jump 84 in"]


def test_draft_safety_allows_only_the_server_inserted_link_and_coach():
    links = ["https://gmtm.com/athletes/2019", "https://gmtm.com/film/301"]
    text = "Hello Coach Poole,\n\nMy GMTM profile: https://gmtm.com/athletes/2019\nMy video: https://gmtm.com/film/301"
    assert cp.draft_is_clean(text, links + ["Coach Poole"])
    assert not cp.draft_is_clean(text, links)  # coach name not inserted by the server
    assert not cp.draft_is_clean(text + "\nhttps://hudl.com/x", links + ["Coach Poole"])
    assert not cp.draft_is_clean(text + "\nme@mail.com", links + ["Coach Poole"])
    # A user id that looks like a year inside her profile link is not a year.
    assert cp.year_is_clean(text, None, "{}") and not cp.year_is_clean(text + "\nClass of 2019", None, "{}")


@pytest.mark.parametrize("bad", ["See https://hudl.com/x", "Hello Coach Johnson,", "Email avery@mail.com"])
def test_model_written_links_or_coach_still_rejected_with_server_inserts(app, bad):
    client, store, model, _, headers, _ = app
    model.draft = {"subject": "QB", "body": f"Hello Coach,\n\n{bad}\n\n{cp.FACTS}\n\nAvery"}
    response = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers)
    assert response.status_code == 502 and store.drafts == []


def test_emails_page_lists_drafts_and_sent_sorted_without_contact(app):
    client, store, model, identity, headers, _ = app
    assert client.get(f"/api/workspace/college-emails/{SUBJECT}", headers=headers).json() == {"eligible": True, "notice": None, "emails": []}
    a, b, c = built(client, headers)[:3]
    for pid in (a, b, c):
        client.post(f"/api/workspace/colleges/{SUBJECT}/{pid}/outreach-draft", headers=headers)
    client.post(f"/api/workspace/colleges/{SUBJECT}/{a}/sent", headers=headers, json={"sent": True})
    emails = client.get(f"/api/workspace/college-emails/{SUBJECT}", headers=headers).json()["emails"]
    # Drafts waiting first (newest first), then sent.
    assert [(e["id"], e["status"]) for e in emails] == [(c, "draft"), (b, "draft"), (a, "sent")]
    assert emails[2]["sent_at"].startswith("2026-10-02T12:") and emails[0]["sent_at"] is None and emails[0]["drafted_at"]
    assert set(emails[0]) == {"id", "school", "city", "state", "level", "primary_color", "status", "drafted_at", "sent_at"}
    identity["gender"], store.rows[SUBJECT]["gmtm_gender"] = 2, 2  # not eligible on GMTM: nothing listed
    assert client.get(f"/api/workspace/college-emails/{SUBJECT}", headers=headers).json()["emails"] == []


def test_parent_contact_is_owner_checked_validated_and_clearable(app):
    client, store, model, _, headers, _ = app
    url = f"/api/workspace/parent-contact/{SUBJECT}"
    assert client.get(url, headers=headers).json() == {"email": None}
    assert client.post(url, headers=headers, json={"email": " mom@example.com "}).json() == {"email": "mom@example.com"}
    assert client.get(url, headers=headers).json() == {"email": "mom@example.com"} and store.parents == {SUBJECT: "mom@example.com"}
    for bad in ("a@x.edu,b@y.com", "a@x.edu;b@y.com", "a@x.edu%0D%0Abcc:z@y.com", "a@x.edu\r\nBcc: z@y.com", "mom", "a b@x.edu"):
        assert client.post(url, headers=headers, json={"email": bad}).status_code == 422, bad
    for body in (None, {}, {"email": 5}, {"email": "m@x.edu", "extra": 1}, {"email": "x" * 250 + "@a.edu"}):
        assert client.post(url, headers=headers, json=body).status_code == 422, body
    assert store.parents == {SUBJECT: "mom@example.com"}
    other = f"/api/workspace/parent-contact/user_other"
    assert client.get(other, headers=headers).status_code == 403
    assert client.post(other, headers=headers, json={"email": "evil@example.com"}).status_code == 403
    assert client.post(url, headers=headers, json={"email": ""}).json() == {"email": None} and store.parents == {}


def test_parent_contact_read_fails_soft_if_the_table_is_missing(app, monkeypatch):
    client, store, *_ , headers, _ = app
    monkeypatch.setattr(store, "parent_email", lambda c: (_ for _ in ()).throw(RuntimeError("1146 table missing")))
    assert client.get(f"/api/workspace/parent-contact/{SUBJECT}", headers=headers).json() == {"email": None}


def test_sent_still_requires_a_draft_from_the_kit(app):
    client, store, model, _, headers, _ = app
    pid = built(client, headers)[0]
    assert client.post(f"/api/workspace/colleges/{SUBJECT}/{pid}/sent", headers=headers, json={"sent": True}).status_code == 409
    assert store.mark_calls == []


def test_profile_link_uses_the_working_gmtm_athletes_pattern(app):
    client, store, *_ , headers, _ = app
    assert cp.GMTM_PROFILE.format(7301) == "https://gmtm.com/athletes/7301"
    body = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers).json()["draft"]
    assert body["kit"]["profile_url"] == "https://gmtm.com/athletes/7301" and "My GMTM profile: https://gmtm.com/athletes/7301" in body["body"]
    assert "gmtm.com/profile/" not in json.dumps(body)


def clip(n, title="Game clip", label="Your GMTM footage", **extra):
    return {"id": f"film-{n}", "kind": "footage", "title": title, "source_label": label, "can_include": True,
            "availability": "unchecked", "source_url": f"https://gmtm.com/film/{n}", **extra}


def test_clip_pick_prefers_her_featured_clip_then_highlight_reel_then_newest():
    items = [clip(9), clip(7, label="Highlight Reel task"), clip(5), clip(3, can_include=False), clip(2, availability="unavailable"),
             {"id": "submission-1-x", "kind": "submitted_result", "can_include": True}]
    assert cp.pick_clip(items, "film-5") == {"url": "https://gmtm.com/film/5", "reel": False}
    assert cp.pick_clip(items, None) == {"url": "https://gmtm.com/film/7", "reel": True}
    assert cp.pick_clip(items, "film-404") == {"url": "https://gmtm.com/film/7", "reel": True}
    # A private or dead featured clip is never used.
    assert cp.pick_clip(items, "film-3")["url"] == "https://gmtm.com/film/7" and cp.pick_clip(items, "film-2")["url"] == "https://gmtm.com/film/7"
    assert cp.pick_clip([clip(9), clip(8)], None) == {"url": "https://gmtm.com/film/9", "reel": False}
    assert cp.pick_clip([], "film-1") is None


def test_featured_clip_id_reaches_the_footage_reader(app, monkeypatch):
    client, store, *_ , headers, _ = app
    seen = []
    monkeypatch.setattr(cp, "read_featured", lambda clerk_id: "film-5" if clerk_id == SUBJECT else None)
    monkeypatch.setattr(cp, "read_highlight", lambda uid, featured=None: seen.append(featured) or {"url": "https://gmtm.com/film/5", "reel": False})
    body = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers).json()["draft"]
    assert seen == [["film-5"]] and "My video: https://gmtm.com/film/5" in body["body"]
    # Workspace unreadable: the draft still gets a clip (no featured preference).
    monkeypatch.setattr(cp, "read_featured", lambda clerk_id: (_ for _ in ()).throw(RuntimeError("down")))
    assert client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers).status_code == 200
    assert seen[-1] == [None]


@pytest.mark.parametrize("visibility", [1, 0, None, "x"])
def test_private_or_unknown_gmtm_profile_gets_no_profile_link(app, visibility):
    client, store, model, identity, headers, _ = app
    identity["visibility"] = visibility
    body = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers).json()["draft"]
    assert body["kit"]["profile_url"] is None and "gmtm.com/athletes" not in body["body"]
    assert "My highlight reel: https://gmtm.com/film/301" in body["body"]


def test_profile_link_dropped_when_gmtm_visibility_read_fails(app, monkeypatch):
    client, store, *_ , headers, _ = app
    store.rows[SUBJECT] = {"gmtm_gender": 1}  # eligible as stored, so only the visibility read reaches GMTM
    monkeypatch.setattr(cp, "read_identity", lambda uid: (_ for _ in ()).throw(RuntimeError("down")))
    body = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers).json()["draft"]
    assert body["kit"]["profile_url"] is None


def test_coach_email_only_on_the_school_domain():
    jcsu = next(p for p in cp.programs() if p["school"] == "Johnson C. Smith University")
    susc = next(p for p in cp.programs() if p["school"] == "Southern Union State Community College")
    assert jcsu["coach_email"] == "coachanika.harris@gmail.com" and cp.coach(jcsu)["email"] is None
    assert susc["coach_email"] == "A01272509@alabama.edu" and cp.coach(susc)["email"] is None
    # Excluded address: the staff page is still offered.
    assert cp.coach(jcsu)["staff_page_url"] or cp.coach(susc)["staff_page_url"]
    uta = next(p for p in cp.programs() if p["school"] == "University of Texas at Arlington")
    assert cp.coach(uta)["email"] == "flagfootball@uta.edu"  # school .edu program inbox printed on the coach row
    base = {"head_coach_name": "A B", "staff_page_url": "https://goteam.com/coaches"}
    assert cp.coach({**base, "coach_email": "a@goteam.com"})["email"] == "a@goteam.com"  # athletics host
    assert cp.coach({**base, "coach_email": "a@yahoo.com"})["email"] is None
    served = [cp.coach(p)["email"] for p in cp.programs() if p.get("coach_email")]
    assert sum(e is None for e in served) == 2 and len(served) == 111


def test_unknown_title_is_coach_not_head_coach():
    assert cp.coach({"head_coach_name": "Pat Lee", "head_coach_title": None})["role"] == "Coach, women's flag football"
    assert cp.coach({"head_coach_name": "Pat Lee", "head_coach_title": "Flag Football Coach"})["role"] == "Coach, women's flag football"
    assert cp.coach({"head_coach_name": "Pat Lee", "head_coach_title": "Head Coach"})["role"] == "Head coach, women's flag football"


# ── Power ball: real GMTM title and plausible range (measured 2026-10-02) ───────

def _metric(title, value, unit="feet"):
    return {"metric_id": 7, "title": title, "value": value, "unit": unit, "created_on": "2026-01-10",
            "is_current": 1, "visibility": 2, "user_approved": 1, "suggested_by": None, "event_id": None}


def test_power_ball_real_title_is_read_and_range_is_enforced():
    import athlete_evidence as ev
    ok = ev._measurement(_metric("Kneeling Power Ball Toss (6 lb ball)", "24.5"))
    assert ok is not None and "Power Ball" in str(ok)
    for bad in ("2", "94", "4385"):
        assert ev._measurement(_metric("Kneeling Power Ball Toss (6 lb ball)", bad)) is None, bad


def test_coach_email_ignores_questionnaire_platform_hosts():
    p = {"coach_email": "coach@spry.so", "program_url": "https://school.edu/flag",
         "staff_page_url": "https://athletics.school.edu/staff", "questionnaire_url": "https://app.spry.so/x"}
    assert cp.coach_email(p) is None



# ── My card ────────────────────────────────────────────────────────────────────

CARD_URL = f"/api/workspace/card/{SUBJECT}"


def test_card_routes_are_owner_checked(app):
    client, store, *_ , headers, _ = app
    for method, body in (("GET", None), ("POST", {"film_ids": ["film-5"]})):
        assert client.request(method, CARD_URL, json=body).status_code == 401
        assert client.request(method, "/api/workspace/card/user_other", headers=headers, json=body).status_code == 403
    assert store.cards == {}


def test_card_default_order_is_featured_then_reel_then_newest(app, monkeypatch):
    client, store, *_ , headers, _ = app
    body = client.get(CARD_URL, headers=headers).json()
    assert body["state"] == "ready" and [c["id"] for c in body["clips"]] == ["film-9", "film-7", "film-5"]
    assert body["order"] == ["film-7"] and body["chosen"] is False  # Highlight Reel task clip
    monkeypatch.setattr(cp, "read_featured", lambda clerk_id: "film-5")
    assert client.get(CARD_URL, headers=headers).json()["order"] == ["film-5"]
    monkeypatch.setattr(cp, "read_card", lambda uid: [card_clip(9), card_clip(5)])
    monkeypatch.setattr(cp, "read_featured", lambda clerk_id: None)
    assert client.get(CARD_URL, headers=headers).json()["order"] == ["film-9"]  # newest
    monkeypatch.setattr(cp, "read_card", lambda uid: [])
    assert client.get(CARD_URL, headers=headers).json()["order"] == []


def test_card_save_keeps_her_order_max_3_and_only_her_eligible_clips(app):
    client, store, *_ , headers, _ = app
    saved = client.post(CARD_URL, headers=headers, json={"film_ids": ["film-5", "film-9"]})
    assert saved.status_code == 200 and saved.json()["order"] == ["film-5", "film-9"] and saved.json()["chosen"] is True
    assert store.cards[SUBJECT] == ["film-5", "film-9"]
    assert client.get(CARD_URL, headers=headers).json()["order"] == ["film-5", "film-9"]
    for bad in (["film-5", "film-7", "film-9", "film-1"],  # more than 3
                ["film-5", "film-5"],  # repeat
                ["film-404"],  # not hers, private or dead: not in her eligible clips
                ["5"], ["film-0"], [5], "film-5"):
        response = client.post(CARD_URL, headers=headers, json={"film_ids": bad})
        assert response.status_code == 422, bad
    assert client.post(CARD_URL, headers=headers, json={"film_ids": ["film-5"], "x": 1}).status_code == 422
    assert store.cards[SUBJECT] == ["film-5", "film-9"]
    # Empty clears: back to the default clip.
    assert client.post(CARD_URL, headers=headers, json={"film_ids": []}).json()["order"] == ["film-7"]
    assert SUBJECT not in store.cards


def test_card_pick_that_became_private_or_dead_drops_out(app, monkeypatch):
    client, store, *_ , headers, _ = app
    store.cards[SUBJECT] = ["film-9", "film-5"]
    monkeypatch.setattr(cp, "read_card", lambda uid: [card_clip(7, "Highlight Reel", reel=True), card_clip(5)])
    assert client.get(CARD_URL, headers=headers).json()["order"] == ["film-5"]
    store.cards[SUBJECT] = ["film-9"]
    body = client.get(CARD_URL, headers=headers).json()
    assert body["order"] == ["film-7"] and body["chosen"] is False


def test_card_gmtm_down_or_unlinked_saves_nothing(app, monkeypatch):
    client, store, *_ , headers, _ = app
    monkeypatch.setattr(cp, "read_card", lambda uid: (_ for _ in ()).throw(RuntimeError("down")))
    assert client.get(CARD_URL, headers=headers).json()["state"] == "source_unavailable"
    assert client.post(CARD_URL, headers=headers, json={"film_ids": ["film-5"]}).status_code == 503
    monkeypatch.setattr(store, "gmtm_user_id", lambda clerk_id: None)
    assert client.get(CARD_URL, headers=headers).json()["state"] == "unlinked"
    assert client.post(CARD_URL, headers=headers, json={"film_ids": ["film-5"]}).status_code == 409
    assert store.cards == {}


def test_card_picks_store_failure_falls_back_to_the_default(app, monkeypatch):
    client, store, *_ , headers, _ = app
    monkeypatch.setattr(store, "card_picks", lambda clerk_id: (_ for _ in ()).throw(RuntimeError("no table")))
    assert client.get(CARD_URL, headers=headers).json()["order"] == ["film-7"]


@pytest.mark.parametrize("visibility,public", [(2, True), ("2", True), (1, False), (0, False), (None, False), ("x", False)])
def test_card_share_link_only_when_gmtm_profile_is_public(app, visibility, public):
    client, store, model, identity, headers, _ = app
    identity["visibility"] = visibility
    share = client.get(CARD_URL, headers=headers).json()["share"]
    if public:
        assert share == {"profile_url": f"https://gmtm.com/athletes/{USER_ID}", "settings_url": None}
    else:
        assert share == {"profile_url": None, "settings_url": "https://gmtm.com/settings"}


def test_email_kit_highlight_is_the_card_lead(app, monkeypatch):
    client, store, *_ , headers, _ = app
    seen = []
    monkeypatch.setattr(cp, "read_featured", lambda clerk_id: "film-9")
    monkeypatch.setattr(cp, "read_highlight", lambda uid, preferred=None: seen.append(preferred) or {"url": "https://gmtm.com/film/5", "reel": False})
    store.cards[SUBJECT] = ["film-5", "film-9"]
    body = client.post(f"/api/workspace/colleges/{SUBJECT}/alabama-state-university/outreach-draft", headers=headers).json()["draft"]
    assert seen == [["film-5", "film-9", "film-9"]] and "My video: https://gmtm.com/film/5" in body["body"]


def test_pick_clip_follows_card_picks_then_featured_and_skips_private_or_dead():
    items = [clip(9), clip(7, label="Highlight Reel task"), clip(5), clip(3, can_include=False), clip(2, availability="unavailable")]
    assert cp.pick_clip(items, ["film-3", "film-5", "film-9"]) == {"url": "https://gmtm.com/film/5", "reel": False}
    assert cp.pick_clip(items, ["film-2", "film-3", None]) == {"url": "https://gmtm.com/film/7", "reel": True}
    assert cp.pick_clip(items, ["film-404", "film-9"])["url"] == "https://gmtm.com/film/9"
    assert [c["id"] for c in cp.card_clips(items)] == ["film-9", "film-7", "film-5"]


def test_video_url_accepts_extensionless_gmtm_reel_uploads_and_one_leading_slash():
    key = "videos/events/1305/pre-edit-uploads/0b7c2d1e-4f5a-4b6c-9d8e-112233445566"
    assert cp.video_url("gmtm", key) == "https://cdn.gmtm.com/" + key
    assert cp.video_url("gmtm", "/" + key) == "https://cdn.gmtm.com/" + key
    assert cp.video_url("gmtm", "/users/7301/uploads/a.mp4") == "https://cdn.gmtm.com/users/7301/uploads/a.mp4"
    for service, uri in (("s3", key), ("youtube", key), ("gmtm", "//" + key), ("gmtm", "users/7301/uploads/abc"),
                         ("gmtm", key + "?x=1"), ("gmtm", key + "#t"), ("gmtm", key + "%2e"), ("gmtm", "videos:x/a/b"),
                         ("gmtm", "videos/events/../x"), ("gmtm", "videos//events/x"), ("gmtm", "videos/events/1305/a b"),
                         ("gmtm", "videos\\events\\x"), ("gmtm", "videos/undefined/x"), ("gmtm", "videos/x"),
                         ("gmtm", "videos/events/1305/caf\u00e9"), ("gmtm", "videos/" + "a/" * 130 + "b")):
        assert cp.video_url(service, uri) is None, (service, uri)


def test_home_lead_endpoint_returns_only_the_lead_and_skips_the_visibility_read(app, monkeypatch):
    client, store, *_ , headers, _ = app
    reads = []
    monkeypatch.setattr(cp, "read_identity", lambda uid: reads.append(uid) or {"visibility": 2})
    body = client.get(f"{CARD_URL}/lead", headers=headers).json()
    assert body == {"state": "ready", "clips": [card_clip(7, "Highlight Reel", reel=True)], "order": ["film-7"], "chosen": False, "share": None}
    assert reads == []
    assert client.get(f"/api/workspace/card/user_other/lead", headers=headers).status_code == 403
    assert client.get(f"{CARD_URL}/lead").status_code == 401


def test_video_url_is_a_plain_cdn_file_only():
    ok = cp.video_url("gmtm", "users/7301/uploads/My Clip (1).mp4")
    assert ok == "https://cdn.gmtm.com/users/7301/uploads/My%20Clip%20%281%29.mp4"
    assert cp.video_url("s3", "https://cdn.gmtm.com/videos/in-person/camp-12/a.MOV") == "https://cdn.gmtm.com/videos/in-person/camp-12/a.MOV"
    for service, uri in (("youtube", "abc.mp4"), ("hudl", "x.mp4"), ("gmtm", None), ("gmtm", ""),
                         ("gmtm", "users/1/uploads/a.m3u8"), ("gmtm", "users/1/uploads/a.jpg"),
                         ("gmtm", "//users/1/a.mp4"), ("gmtm", "users/../a.mp4"), ("gmtm", "users//a.mp4"),
                         ("gmtm", "users/undefined/uploads/a.mp4"), ("gmtm", "a.mp4?x=1"), ("gmtm", "a%2e.mp4"),
                         ("gmtm", "https://evil.example/a.mp4"), ("gmtm", "http://cdn.gmtm.com/a.mp4"),
                         ("gmtm", "a\\b.mp4"), ("gmtm", "caf\u00e9.mp4"), ("gmtm", "a" * 300 + ".mp4")):
        assert cp.video_url(service, uri) is None, (service, uri)


def test_read_card_uses_only_eligible_films_and_reads_only_their_file_key(monkeypatch):
    """Real materials projection on synthetic rows: private and dead films never reach the card."""
    import athlete_evidence
    from backend.tests import test_athlete_materials as tm
    queries = []

    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params):
            sql = " ".join(sql.split())
            queries.append((sql, params))
            if "FROM film WHERE film_id IN" in sql:
                self.rows = [{"film_id": 301, "service": "gmtm", "uri": "users/7201/uploads/game.mp4"}]
            elif "WHERE f.user_id = %s" in sql:
                self.rows = [tm.film(), tm.film(film_id=310, visibility=1, published_on=datetime(2026, 8, 21)),
                             tm.film(film_id=311, dead_link=1, published_on=datetime(2026, 8, 22))]
            else:
                self.rows = []
        def fetchall(self): return self.rows

    class DB:
        closed = False
        def cursor(self): return Cursor()
        def close(self): DB.closed = True

    monkeypatch.setattr(athlete_evidence, "_get_gmtm_db", lambda: DB())
    clips = cp.read_card(tm.OWNER)
    assert [c["id"] for c in clips] == ["film-301"] and DB.closed
    assert clips[0]["video_url"] == "https://cdn.gmtm.com/users/7201/uploads/game.mp4"
    files = [q for q in queries if "FROM film WHERE film_id IN" in q[0]]
    assert files == [("SELECT film_id, service, uri FROM film WHERE film_id IN (%s) AND visibility = 2 "
                      "AND (dead_link IS NULL OR dead_link = 0) LIMIT %s", (301, 1))]
