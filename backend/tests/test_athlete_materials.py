"""Actual owner route and bounded SQL/projection behavior with synthetic data."""
from copy import deepcopy
from datetime import datetime
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import athlete_materials as api
from auth import require_identity


OWNER = 7201
CALLER = "sub_material_owner"
LEGACY_THUMBNAIL = "users/undefined/uploads/11111111-2222-4333-8444-555555555555.jpg"


def event():
    return dict(event_id=1318, joined_event_id=1318, event_name="Sample combine",
                event_visibility=2, event_published=1, event_public=1,
                event_invite_only=0, event_networks_only=0, event_product_id=None)


def answer(value="4.75", unit="seconds", title="40 Yard Dash"):
    key = f"metric:{title}"
    return {key: {"key": key, "type": "metric", "value": {"value": value, "unit": unit}}}


def submission(**updates):
    data = json.dumps({"questions": answer()})
    row = dict(task_submission_id=101, user_id=OWNER, task_id=21, joined_task_id=21,
               task_title="Sprint test", task_visibility=2, created_on=datetime(2026, 9, 1, 12),
               visibility=2, payload=data, payload_bytes=len(data.encode()), **event())
    row.update(updates)
    return row


def film(**updates):
    row = dict(user_id=OWNER, film_id=301, direct_user_id=OWNER, career_id=None, joined_career_id=None,
               career_user_id=None, career_visibility=None, career_approved=None,
               career_suggested_by=None, career_suggested_by_org_id=None,
               task_submission_id=None, title="Game highlights", published_on=datetime(2026, 8, 20),
               visibility=2, approved=0, suggested_by=None, suggested_by_org_id=None,
               processed=1, dead_link=0, challenge_id=None, film_event_id=None,
               in_person_event_id=None, joined_event_id=None, event_name=None,
               event_visibility=None, event_published=None, event_public=None,
               event_invite_only=None, event_networks_only=None, event_product_id=None)
    row.update(updates)
    return row


def submitted_film(**updates):
    row = film(film_id=302, task_submission_id=101, joined_submission_id=101,
               submission_user_id=OWNER, submission_visibility=2, task_id=21,
               joined_task_id=21, task_visibility=2, task_title="Sprint test", **event())
    row.update(updates)
    return row


def career_film(**updates):
    row = film(film_id=303, direct_user_id=None, career_id=31, joined_career_id=31,
               career_user_id=OWNER, career_visibility=2, career_approved=0,
               career_suggested_by=None, career_suggested_by_org_id=None)
    row.update(updates)
    return row


class Cursor:
    def __init__(self, db):
        self.db, self.rows = db, []

    def __enter__(self):
        self.db.opened += 1
        return self

    def __exit__(self, *args):
        self.db.closed += 1

    def execute(self, query, params):
        sql = " ".join(query.split())
        assert sql.startswith("SELECT ") and ";" not in sql
        assert isinstance(params, tuple)
        self.db.queries.append((sql, params))
        if "FROM athlete_profiles WHERE clerk_id = %s" in sql:
            assert params == (CALLER,)
            self.rows = self.db.links
        elif "FROM athlete_profiles WHERE user_id = %s" in sql:
            assert params == (OWNER,)
            self.rows = self.db.reverse
        else:
            assert params == (OWNER, 51)
            assert sql.endswith("LIMIT %s")
            if "FROM event_task_submissions s" in sql:
                assert "WHERE s.user_id = %s" in sql
                assert "CASE WHEN OCTET_LENGTH(s.payload) <= 65536" in sql
                assert "NOT EXISTS" in sql and "newer.user_id = s.user_id" in sql
                assert "newer.task_id = s.task_id" in sql
                assert "newer.task_submission_id > s.task_submission_id" in sql
                self.rows = self.db.submissions
            elif "WHERE s.user_id = %s" in sql:
                self.rows = self.db.submitted_films
            elif "WHERE f.user_id = %s" in sql:
                assert "f.task_submission_id IS NULL" in sql
                self.rows = self.db.direct_films
            elif "WHERE c.user_id = %s" in sql:
                assert "f.user_id IS NULL AND f.task_submission_id IS NULL" in sql
                self.rows = self.db.career_films
            else:
                raise AssertionError("Unexpected query")
            if "FROM film f" in sql:
                assert "f.service," in sql
                assert "CASE WHEN OCTET_LENGTH(f.thumbnail_uri) <= 2048 THEN f.thumbnail_uri ELSE NULL END AS thumbnail_uri" in sql
            for forbidden in ("f.*", "video_uri", "description", "f.uri", "event_answers"):
                assert forbidden not in sql
        if self.db.fail_at == len(self.db.queries):
            raise RuntimeError("SECRET SQL HOST PASSWORD EMAIL")

    def fetchall(self):
        return deepcopy(self.rows)


class Database:
    def __init__(self):
        self.links = [dict(user_id=OWNER, clerk_id=CALLER)]
        self.reverse = deepcopy(self.links)
        self.submissions = [submission()]
        self.submitted_films = [submitted_film()]
        self.direct_films = [film()]
        self.career_films = [career_film()]
        self.queries = []
        self.opened = self.closed = self.close_count = 0
        self.fail_at = None

    def cursor(self):
        return Cursor(self)

    def close(self):
        self.close_count += 1


@pytest.fixture
def source(monkeypatch):
    agent, gmtm = Database(), Database()
    calls = []

    def agent_db():
        calls.append("agent")
        return agent

    def source_db():
        assert agent.close_count == 1
        calls.append("gmtm")
        return gmtm

    monkeypatch.setattr(api, "_get_agent_db", agent_db)
    monkeypatch.setattr(api, "_get_gmtm_db", source_db)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[require_identity] = lambda: CALLER
    with TestClient(app) as client:
        yield client, agent, gmtm, calls


def fetch(source):
    response = source[0].get("/api/athlete/materials")
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    return response, response.json()


def test_actual_route_owner_projection_and_query_budget(source):
    response, body = fetch(source)
    assert response.status_code == 200 and body["state"] == "ready"
    assert body["owner_scope"] == api.owner_scope(CALLER, OWNER)
    assert len(body["items"]) == 4
    result = body["items"][0]
    assert result["title"] == "40 Yard Dash"
    assert result["result"] == {"value": 4.75, "unit": "seconds"}
    assert result["source_label"] == "Sample combine · Sprint test"
    assert result["recorded_at"] == "2026-09-01T12:00:00"
    assert result["date_label"] == "Submitted" and result["source_url"] is None
    assert all(item["can_include"] for item in body["items"])
    assert all(item["thumbnail_url"] is None for item in body["items"])
    for item in body["items"][1:]:
        assert item["source_url"] == f"https://gmtm.com/film/{item['id'][5:]}"
        assert item["availability"] == "unchecked" and item["result"] is None
    assert datetime.fromisoformat(body["fetched_at"]).utcoffset().total_seconds() == 0
    assert source[3] == ["agent", "gmtm"]
    assert len(source[1].queries) == 2 and len(source[2].queries) == 4
    for db in source[1:3]:
        assert db.close_count == 1 and db.opened == db.closed
    for forbidden in ("user_id", "sub_material_owner", "suggested_by", "approved", "task_submission_id"):
        assert forbidden not in json.dumps(body)


@pytest.mark.parametrize("query", ["?user_id=2", "?event_id=1318", "?x=", "?athlete_id=7201"])
def test_query_selectors_rejected_without_source_access(source, query):
    response = source[0].get("/api/athlete/materials" + query)
    assert response.status_code == 400 and source[3] == []


def test_unlinked_opens_no_gmtm_connection(source):
    source[1].links = []
    body = fetch(source)[1]
    assert body["state"] == "unlinked" and "owner_scope" not in body
    assert source[3] == ["agent"] and source[1].close_count == 1


@pytest.mark.parametrize("case", ["forward_duplicate", "forward_subject", "reverse_missing", "reverse_foreign"])
def test_link_conflicts_precede_source_reads(source, case):
    agent = source[1]
    if case == "forward_duplicate":
        agent.links *= 2
    elif case == "forward_subject":
        agent.links[0]["clerk_id"] = CALLER.upper()
    elif case == "reverse_missing":
        agent.reverse = []
    else:
        agent.reverse[0]["clerk_id"] = "foreign"
    response, body = fetch(source)
    assert response.status_code == 409 and source[3] == ["agent"]
    assert "items" not in body and agent.close_count == 1


@pytest.mark.parametrize("query_number", [1, 2, 3, 4])
def test_source_failure_has_no_partial_material_and_closes(source, query_number):
    source[2].fail_at = query_number
    _, body = fetch(source)
    assert body["state"] == "source_unavailable" and body["items"] == []
    assert body["owner_scope"] == api.owner_scope(CALLER, OWNER)
    assert "SECRET" not in json.dumps(body)
    assert source[2].close_count == 1 and source[2].opened == source[2].closed


@pytest.mark.parametrize("path,key", [
    ("submissions", "user_id"), ("submitted_films", "submission_user_id"),
    ("submitted_films", "direct_user_id"), ("submitted_films", "career_user_id"),
    ("direct_films", "direct_user_id"), ("direct_films", "career_user_id"),
    ("career_films", "career_user_id"), ("career_films", "direct_user_id")])
def test_every_foreign_owner_reference_fails_whole_projection(source, path, key):
    getattr(source[2], path)[0][key] = OWNER + 1
    _, body = fetch(source)
    assert body["state"] == "source_unavailable" and body["items"] == []


@pytest.mark.parametrize("value", [True, "7201", -1, None])
def test_submission_owner_requires_exact_positive_integer(source, value):
    source[2].submissions[0]["user_id"] = value
    assert fetch(source)[1]["state"] == "source_unavailable"


@pytest.mark.parametrize("key,value", [("joined_task_id", None), ("joined_task_id", 99),
                                     ("joined_event_id", None), ("joined_event_id", 99),
                                     ("task_visibility", -1), ("event_visibility", -2),
                                     ("visibility", None), ("visibility", True), ("visibility", 6)])
def test_missing_removed_or_inconsistent_submission_context_is_omitted(source, key, value):
    source[2].submissions[0][key] = value
    body = fetch(source)[1]
    assert body["state"] == "ready"
    assert all(item["kind"] != "submitted_result" for item in body["items"])


@pytest.mark.parametrize("key,value", [("visibility", 0), ("visibility", 5),
                                     ("task_visibility", 1), ("event_visibility", 3),
                                     ("event_published", 0), ("event_public", 0),
                                     ("event_invite_only", 1), ("event_networks_only", 1),
                                     ("event_networks_only", None), ("event_product_id", 12)])
def test_private_and_restricted_results_are_context_not_draft_eligible(source, key, value):
    source[2].submissions[0][key] = value
    item = fetch(source)[1]["items"][0]
    assert item["kind"] == "submitted_result" and item["can_include"] is False


@pytest.mark.parametrize("raw,unit,expected", [(4750, "SS.00", {"value": 4750.0, "unit": "milliseconds"}),
    (4750, "Time (MM:SS.00)", {"value": 4750.0, "unit": "milliseconds"}),
    (4.75, "seconds", {"value": 4.75, "unit": "seconds"}),
    (4.75, "SS.00", None), (True, "seconds", None), ("NaN", "seconds", None),
    ("Infinity", "seconds", None), (-2, "seconds", None), (0, "seconds", None),
    (4.75, "unknown", None), ({"value": 4.75}, "seconds", None)])
def test_numeric_time_units_are_never_guessed(raw, unit, expected):
    q = answer(raw, unit)
    key = next(iter(q))
    actual = api._numeric_result(q[key], key)
    assert (actual[1] if actual else None) == expected


@pytest.mark.parametrize("title,raw,unit,expected", [
    ("Push-Ups", 0, "reps", {"value": 0.0, "unit": "repetitions"}),
    ("Push-Ups", 1.5, "reps", None), ("Height", 72, "inches", {"value": 72.0, "unit": "inches"}),
    ("Height", 72, "seconds", None), ("Email", 123, "seconds", None),
    ("20 Yard Shuttle", 4.75, "seconds", None)])
def test_recognized_title_unit_pairs_only(title, raw, unit, expected):
    q = answer(raw, unit, title)
    key = next(iter(q))
    actual = api._numeric_result(q[key], key)
    assert (actual[1] if actual else None) == expected


def test_contact_essay_video_and_untrusted_extra_fields_never_leave_projection(source):
    questions = answer()
    questions["essay:About me"] = {"type": "essay", "value": "PRIVATE essay"}
    questions["parent:Parent"] = {"type": "parent", "value": {"email": "PRIVATE email"}}
    questions["video:Highlights"] = {"type": "video", "value": {"value": "https://PRIVATE"}}
    questions["metric:40 Yard Dash"]["value"]["secret"] = "PRIVATE hidden"
    raw = json.dumps({"questions": questions})
    source[2].submissions[0].update(payload=raw, payload_bytes=len(raw.encode()))
    body = fetch(source)[1]
    assert len([item for item in body["items"] if item["kind"] == "submitted_result"]) == 1
    assert "PRIVATE" not in json.dumps(body)


@pytest.mark.parametrize("raw,size", [('{bad json', 9), ('{"questions":[]}', 16),
    ('{"questions":{"metric:40 Yard Dash":{},"metric:40 Yard Dash":{}}}', 63),
    ('{"metrics":[{"title":"40 Yard Dash","value":4.75}]}', 48),
    (None, 65537), ('{}', None), ('{}', True)])
def test_malformed_legacy_or_oversized_newest_payload_is_not_filled_from_other_data(source, raw, size):
    source[2].submissions[0].update(payload=raw, payload_bytes=size)
    body = fetch(source)[1]
    assert body["state"] == "ready"
    assert all(item["kind"] != "submitted_result" for item in body["items"])


def test_conflicting_latest_attempts_fail_closed(source):
    source[2].submissions.append(submission(task_submission_id=102))
    assert fetch(source)[1]["state"] == "source_unavailable"


@pytest.mark.parametrize("key,value", [("approved", -1), ("approved", None),
    ("suggested_by", 71), ("suggested_by_org_id", 77), ("challenge_id", 1),
    ("career_id", 999), ("visibility", -1), ("visibility", 6), ("visibility", True),
    ("film_id", "301")])
def test_unusable_personal_film_records_excluded(source, key, value):
    source[2].direct_films[0][key] = value
    body = fetch(source)[1]
    assert body["state"] == "ready" and not any(item["id"] == "film-301" for item in body["items"])


@pytest.mark.parametrize("key,value", [("joined_submission_id", None), ("joined_submission_id", 999),
    ("joined_task_id", None), ("joined_event_id", 999), ("submission_visibility", -1),
    ("task_visibility", -1), ("event_visibility", -1), ("film_event_id", 999)])
def test_submitted_film_all_context_joins_must_agree(source, key, value):
    source[2].submitted_films[0][key] = value
    body = fetch(source)[1]
    assert body["state"] == "ready" and not any(item["id"] == "film-302" for item in body["items"])


@pytest.mark.parametrize("key,value", [("joined_career_id", None), ("joined_career_id", 99),
    ("career_visibility", -1), ("career_approved", -1), ("career_suggested_by", 71),
    ("career_suggested_by_org_id", 77)])
def test_legacy_career_reference_must_exist_and_be_usable(source, key, value):
    source[2].career_films[0][key] = value
    body = fetch(source)[1]
    assert body["state"] == "ready" and not any(item["id"] == "film-303" for item in body["items"])


@pytest.mark.parametrize("key,value", [("visibility", 0), ("visibility", 5), ("in_person_event_id", 1),
    ("dead_link", 1), ("dead_link", True), ("dead_link", False), ("dead_link", "0"),
    ("dead_link", "1"), ("dead_link", -1), ("dead_link", 2), ("dead_link", 0.0)])
def test_film_copy_eligibility_does_not_assume_publicity_or_playback(source, key, value):
    source[2].direct_films[0][key] = value
    item = next(item for item in fetch(source)[1]["items"] if item["id"] == "film-301")
    assert item["can_include"] is False
    if key == "dead_link" and type(value) is int and value == 1:
        assert item["source_url"] is None and item["availability"] == "unavailable"
    else:
        assert item["availability"] == "unchecked"


def test_missing_personal_event_context_stays_generic_and_private(source):
    source[2].direct_films[0].update(film_event_id=777, event_name="UNTRUSTED EVENT")
    item = next(item for item in fetch(source)[1]["items"] if item["id"] == "film-301")
    assert item["source_label"] == "Your GMTM footage" and item["can_include"] is False


def test_accepted_suggestion_can_be_shown_but_never_claims_verification(source):
    source[2].direct_films[0].update(approved=1, suggested_by=45, suggested_by_org_id=10)
    item = next(item for item in fetch(source)[1]["items"] if item["id"] == "film-301")
    assert item["availability"] == "unchecked"


def test_duplicate_film_across_source_paths_fails_closed(source):
    source[2].career_films[0]["film_id"] = 301
    assert fetch(source)[1]["state"] == "source_unavailable"


@pytest.mark.parametrize("path", ["submissions", "submitted_films", "direct_films", "career_films"])
def test_driver_returning_more_than_limit_fails_closed(source, path):
    setattr(source[2], path, getattr(source[2], path) * 52)
    assert fetch(source)[1]["state"] == "source_unavailable"


def test_overflow_submission_owner_checked_before_display_truncation(source):
    source[2].submissions = [submission(task_submission_id=100 + n, task_id=100 + n,
                                     joined_task_id=100 + n) for n in range(51)]
    source[2].submissions[-1]["user_id"] = OWNER + 1
    assert fetch(source)[1]["state"] == "source_unavailable"


def test_overflow_film_owner_checked_before_display_truncation(source):
    source[2].direct_films = [film(film_id=1000 + n) for n in range(51)]
    source[2].direct_films[-1]["career_user_id"] = OWNER + 1
    assert fetch(source)[1]["state"] == "source_unavailable"


def test_output_caps_preserve_more_material_notice(source):
    source[2].submissions = [submission(task_submission_id=100 + n, task_id=100 + n,
                                     joined_task_id=100 + n) for n in range(30)]
    source[2].direct_films = [film(film_id=1000 + n) for n in range(20)]
    body = fetch(source)[1]
    assert len(body["items"]) == 30
    assert sum(item["kind"] == "submitted_result" for item in body["items"]) == 20
    assert any("limited" in limit for limit in body["limitations"])


def test_empty_supported_projection_is_ready_not_source_failure(source):
    for path in ("submissions", "submitted_films", "direct_films", "career_films"):
        setattr(source[2], path, [])
    body = fetch(source)[1]
    assert body["state"] == "ready" and body["items"] == []
    assert any("outside this view" in limit for limit in body["limitations"])


@pytest.mark.parametrize("path", ["submitted_films", "direct_films", "career_films"])
def test_each_film_query_declares_the_current_owner(source, path):
    getattr(source[2], path)[0]["user_id"] = OWNER + 1
    assert fetch(source)[1]["state"] == "source_unavailable"


@pytest.mark.parametrize("path,film_id", [("submitted_films", 302), ("direct_films", 301), ("career_films", 303)])
def test_historical_zero_event_reference_does_not_hide_owned_film(source, path, film_id):
    getattr(source[2], path)[0]["film_event_id"] = 0
    item = next(item for item in fetch(source)[1]["items"] if item["id"] == f"film-{film_id}")
    assert item["can_include"] is True


@pytest.mark.parametrize("value", [True, False, "0", "1318", -1])
def test_malformed_film_event_reference_is_not_treated_as_absent(source, value):
    source[2].direct_films[0]["film_event_id"] = value
    body = fetch(source)[1]
    assert not any(item["id"] == "film-301" for item in body["items"])


@pytest.mark.parametrize("restriction", [{"event_visibility": 0}, {"event_visibility": -1},
    {"event_networks_only": 1}, {"event_published": 0}, {"event_product_id": 10}])
def test_personal_film_cannot_disclose_restricted_event_context(source, restriction):
    source[2].direct_films[0].update(film_event_id=1318, **event())
    source[2].direct_films[0].update(event_name="PRIVATE EVENT", **restriction)
    item = next(item for item in fetch(source)[1]["items"] if item["id"] == "film-301")
    assert item["source_label"] == "Your GMTM footage" and item["can_include"] is False


def test_submission_owner_can_inspect_restricted_participation_context(source):
    source[2].submitted_films[0].update(event_visibility=0, event_name="Private combine")
    item = next(item for item in fetch(source)[1]["items"] if item["id"] == "film-302")
    assert item["source_label"] == "Private combine · Sprint test" and item["can_include"] is False


def test_question_map_size_and_actual_payload_bytes_are_bounded(source):
    questions = {f"essay:{index}": {"type": "essay", "value": "omit"} for index in range(40)}
    questions.update(answer())
    raw = json.dumps({"questions": questions})
    source[2].submissions[0].update(payload=raw, payload_bytes=len(raw.encode()))
    assert all(item["kind"] != "submitted_result" for item in fetch(source)[1]["items"])
    huge = json.dumps({"questions": answer(), "ignored": "x" * 65536})
    source[2].submissions[0].update(payload=huge, payload_bytes=1)
    assert all(item["kind"] != "submitted_result" for item in fetch(source)[1]["items"])


def test_changed_key_or_unsupported_type_does_not_relabel_an_answer():
    q = answer()
    key = next(iter(q))
    q[key]["key"] = "metric:Vertical Jump"
    assert api._numeric_result(q[key], key) is None
    q[key]["key"] = key
    q[key]["type"] = "essay"
    assert api._numeric_result(q[key], key) is None


def test_public_film_attached_to_private_career_does_not_export_career_metadata(source):
    source[2].career_films[0].update(career_visibility=1, career_name="PRIVATE CAREER")
    item = next(item for item in fetch(source)[1]["items"] if item["id"] == "film-303")
    assert item["can_include"] is True
    assert "career" not in json.dumps(item).lower() and "PRIVATE" not in json.dumps(item)


def test_film_identifier_outside_safe_integer_bound_cannot_create_a_url(source):
    source[2].direct_films[0]["film_id"] = 10 ** 17
    assert len(fetch(source)[1]["items"]) == 3


@pytest.mark.parametrize("processed", [0, 1, None, 2, -1, True, "0", 1.0])
@pytest.mark.parametrize("dead_link", [0, None])
def test_legacy_processing_values_never_claim_playability_or_block_public_page_reference(source, processed, dead_link):
    source[2].direct_films[0].update(processed=processed, dead_link=dead_link)
    item = next(item for item in fetch(source)[1]["items"] if item["id"] == "film-301")
    assert item["availability"] == "unchecked" and item["can_include"] is True
    assert item["source_url"] == "https://gmtm.com/film/301"


@pytest.mark.parametrize("processed", [0, None, 2])
@pytest.mark.parametrize("restriction", ["private_film", "private_event", "unknown_in_person"])
def test_legacy_processing_correction_never_expands_public_source_scope(source, processed, restriction):
    row = source[2].direct_films[0]
    row.update(processed=processed, dead_link=None)
    if restriction == "private_film":
        row["visibility"] = 0
    elif restriction == "private_event":
        row.update(film_event_id=1318, **event())
        row["event_visibility"] = 0
    else:
        row["in_person_event_id"] = 55
    item = next(item for item in fetch(source)[1]["items"] if item["id"] == "film-301")
    assert item["availability"] == "unchecked" and item["can_include"] is False


@pytest.mark.parametrize("processed", [0, 1, None, 2])
def test_explicit_dead_link_flag_always_overrides_legacy_processing_value(source, processed):
    source[2].direct_films[0].update(processed=processed, dead_link=1)
    item = next(item for item in fetch(source)[1]["items"] if item["id"] == "film-301")
    assert item["availability"] == "unavailable" and item["source_url"] is None
    assert item["can_include"] is False


def test_stored_thumbnail_paths_normalize_only_supported_services_and_families():
    cases = [
        ("gmtm", "videos/film/thumbnails/fixture-frame.png", "https://cdn.gmtm.com/videos/film/thumbnails/fixture-frame.png"),
        ("s3", "videos/events/1318/edited-thumbnails/sprint-1.jpg", "https://cdn.gmtm.com/videos/events/1318/edited-thumbnails/sprint-1.jpg"),
        ("gmtm", "users/7201/uploads/game.clip.jpeg", "https://cdn.gmtm.com/users/7201/uploads/game.clip.jpeg"),
        ("gmtm", "https://cdn.gmtm.com/videos/film/thumbnails/fixture.webp", "https://cdn.gmtm.com/videos/film/thumbnails/fixture.webp"),
        ("gmtm", LEGACY_THUMBNAIL, "https://cdn.gmtm.com/" + LEGACY_THUMBNAIL),
        ("s3", "https://cdn.gmtm.com/" + LEGACY_THUMBNAIL, "https://cdn.gmtm.com/" + LEGACY_THUMBNAIL),
        ("youtube", "vi/Abc_def-123/default.jpg", "https://i.ytimg.com/vi/Abc_def-123/default.jpg"),
        ("youtu", "https://i.ytimg.com/vi/Abc_def-123/hqdefault.jpg", "https://i.ytimg.com/vi/Abc_def-123/hqdefault.jpg"),
    ]
    for service, stored, expected in cases:
        item = api._film_item(film(service=service, thumbnail_uri=stored, processed=0), "direct")
        assert item["thumbnail_url"] == expected
        assert item["source_url"] == "https://gmtm.com/film/301"
        assert item["can_include"] is True and item["availability"] == "unchecked"


def test_thumbnail_normalizer_rejects_unsafe_or_unsupported_values_without_losing_film_metadata(source):
    safe = "videos/film/thumbnails/frame.png"
    hostile = [
        None, "", 123, {}, safe + "?", safe + "#", safe + "?token=secret", safe + "#fragment",
        "https://cdn.gmtm.com/" + safe + "?", "https://cdn.gmtm.com/" + safe + "#",
        "https://cdn.gmtm.com.attacker.invalid/" + safe,
        "https://attacker.invalid/cdn.gmtm.com/" + safe,
        "https://user:pass@cdn.gmtm.com/" + safe, "https://cdn.gmtm.com:443/" + safe,
        "http://cdn.gmtm.com/" + safe, "//cdn.gmtm.com/" + safe, "/" + safe,
        "https://i.ytimg.com/vi/Abc_def-123/default.jpg", "data:image/png;base64,AAAA", "javascript:alert(1)",
        safe.replace("frame", "../frame"), safe.replace("frame", "./frame"), safe.replace("frame", "%2e%2e/frame"),
        safe.replace("thumbnails/", "thumbnails%2fframe/"), safe.replace("thumbnails/", "thumbnails%5cframe/"),
        safe.replace("/frame", "//frame"), safe.replace("/", "\\"), " " + safe, safe + "\n", safe + "\x00",
        safe.replace("frame", "fráme"), safe.replace("frame", "frame name"), safe.replace(".png", ".svg"),
        safe.replace(".png", ".mp4"), safe.replace(".png", ".gif"), "arbitrary/folder/frame.png",
        "videos/events/0/edited-thumbnails/frame.png", "videos/events/001/edited-thumbnails/frame.png",
        "users/9007199254740992/uploads/frame.png", "users/abc/uploads/frame.png",
        "videos/film/thumbnails/" + "a" * 2048 + ".png",
    ]
    for value in hostile:
        item = api._film_item(film(service="gmtm", thumbnail_uri=value), "direct")
        assert item["thumbnail_url"] is None, value
        assert item["can_include"] is True and item["source_url"] == "https://gmtm.com/film/301"
    for service in (None, "", "hudl", "yt", "vimeo", "GMTM", "gmtm "):
        assert api._thumbnail_url({"service": service, "thumbnail_uri": safe}) is None
    for value in ("vi/short/default.jpg", "vi/Abc_def-123/../default.jpg", "vi_webp/Abc_def-123/default.webp", safe):
        assert api._thumbnail_url({"service": "youtube", "thumbnail_uri": value}) is None
    source[2].direct_films[0].update(service="gmtm", thumbnail_uri="https://attacker.invalid/private.png")
    body = fetch(source)[1]
    assert body["state"] == "ready" and len(body["items"]) == 4
    assert all(item["thumbnail_url"] is None for item in body["items"])


@pytest.mark.parametrize("thumbnail", ["videos/film/thumbnails/private-marker.png", LEGACY_THUMBNAIL])
@pytest.mark.parametrize("restriction", ["private", "network", "event", "in_person", "dead", "unknown_dead", "boolean_dead"])
def test_thumbnail_is_absent_for_restricted_or_unknown_public_scope(source, restriction, thumbnail):
    row = source[2].direct_films[0]
    row.update(service="gmtm", thumbnail_uri=thumbnail)
    if restriction == "private": row["visibility"] = 1
    elif restriction in ("network", "event"):
        row.update(film_event_id=1318, **event())
        row["event_networks_only" if restriction == "network" else "event_visibility"] = 1
    elif restriction == "in_person": row["in_person_event_id"] = 51
    elif restriction == "dead": row["dead_link"] = 1
    elif restriction == "unknown_dead": row["dead_link"] = "0"
    else: row["dead_link"] = False
    item = next(item for item in fetch(source)[1]["items"] if item["id"] == "film-301")
    assert item["thumbnail_url"] is None and item["can_include"] is False
    assert thumbnail.rsplit("/", 1)[1] not in json.dumps(item)


@pytest.mark.parametrize("thumbnail", ["videos/film/thumbnails/owned-frame.png", LEGACY_THUMBNAIL])
def test_thumbnail_projection_keeps_existing_owner_checks_and_all_three_query_paths(source, thumbnail):
    db = source[2]
    for row in [*db.submitted_films, *db.direct_films, *db.career_films]:
        row.update(service="gmtm", thumbnail_uri=thumbnail, processed=None, dead_link=None)
    items = fetch(source)[1]["items"]
    assert items[0]["thumbnail_url"] is None
    assert all(item["thumbnail_url"] == "https://cdn.gmtm.com/" + thumbnail for item in items[1:])
    assert len(db.queries) == 4


@pytest.mark.parametrize("thumbnail", ["videos/film/thumbnails/owned-frame.png", LEGACY_THUMBNAIL])
def test_safe_thumbnail_does_not_bypass_foreign_owner_reference(source, thumbnail):
    source[2].direct_films[0].update(service="gmtm", thumbnail_uri=thumbnail, career_user_id=999)
    failed = fetch(source)[1]
    assert failed["state"] == "source_unavailable" and failed["items"] == []
    assert thumbnail.rsplit("/", 1)[1] not in json.dumps(failed)


def test_legacy_undefined_namespace_requires_stored_canonical_uuid_raster_and_existing_service():
    prefix = "users/undefined/uploads/"
    name = LEGACY_THUMBNAIL.removeprefix(prefix)
    hostile = [prefix + "arbitrary.jpg", prefix + "8243185.jpg", prefix + name.replace("-", ""),
               prefix + name.replace("11111111", "GGGGGGGG"), prefix + name.replace(".jpg", ".preview.jpg"),
               prefix + name.replace(".jpg", ".svg"), prefix + "../" + name,
               LEGACY_THUMBNAIL.replace("undefined", "null"), LEGACY_THUMBNAIL.replace("undefined", "Undefined"),
               LEGACY_THUMBNAIL + "?token=secret", LEGACY_THUMBNAIL + "#fragment",
               LEGACY_THUMBNAIL.replace("undefined", "%75ndefined"),
               "https://cdn.gmtm.com.attacker.invalid/" + LEGACY_THUMBNAIL,
               "https://cdn.gmtm.com:443/" + LEGACY_THUMBNAIL]
    for stored in hostile:
        assert api._thumbnail_url({"service": "gmtm", "thumbnail_uri": stored}) is None
    for service in ("youtube", "youtu", "vimeo", None):
        assert api._thumbnail_url({"service": service, "thumbnail_uri": LEGACY_THUMBNAIL}) is None
    for extension in ("jpg", "jpeg", "png", "webp", "JPG"):
        stored = LEGACY_THUMBNAIL.removesuffix("jpg") + extension
        assert api._thumbnail_url({"service": "gmtm", "thumbnail_uri": stored}) == "https://cdn.gmtm.com/" + stored
    stored = LEGACY_THUMBNAIL.replace("11111111", "AAAAAAAA")
    assert api._thumbnail_url({"service": "s3", "thumbnail_uri": stored}) == "https://cdn.gmtm.com/" + stored


def test_thumbnail_bounds_apply_to_stored_key_and_normalized_url():
    prefix = "videos/film/thumbnails/"
    at_limit = prefix + "a" * (2048 - len("https://cdn.gmtm.com/") - len(prefix) - len(".png")) + ".png"
    result = api._thumbnail_url({"service": "gmtm", "thumbnail_uri": at_limit})
    assert result is not None and len(result) == 2048
    assert api._thumbnail_url({"service": "gmtm", "thumbnail_uri": at_limit.replace(".png", "a.png")}) is None


@pytest.mark.parametrize("key, unit", [("metric:5-10-5 Shuttle Run", "s"), ("metric:Max. Push-Ups", "reps"),
                                       ("metric:Max. Sit Ups", "reps"), ("metric:20-Yard Dash", "s"),
                                       ("metric:Standing Broad Jump", "in")])
def test_junior_combine_drill_names_are_kept_with_their_real_titles(key, unit):
    import athlete_materials
    title, result = athlete_materials._numeric_result({"type": "metric", "value": {"value": "12", "unit": unit}}, key)
    assert title == key.partition(":")[2] and result["value"] == 12.0
