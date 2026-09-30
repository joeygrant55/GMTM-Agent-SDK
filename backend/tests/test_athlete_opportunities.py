"""Reviewed opportunity evidence and owner-bound HTTP reads, entirely synthetic."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import athlete_opportunities as api
import athlete_workspace as workspace
import combine_api
from auth import require_clerk_id
from backend.tests.workspace_fixture_store import WorkspaceStore


CALLER = "clerk_opportunity_owner"
LINK = {"id": 191, "user_id": 8201, "clerk_id": CALLER}
NOW = datetime(2026, 9, 10, 12, tzinfo=timezone.utc)
PATH = "/api/athlete/opportunities"
SOURCE_URL = "https://usafootball.com/national-team/synthetic-review"


def query(**changes):
    return {"pathway": "adult_flag", "category": "unspecified", "format": "any",
            "link_revision": api._revision(LINK), **changes}


def record(identifier="synthetic-assessment", **changes):
    return {"id": identifier, "title": "Synthetic assessment", "organization": "Synthetic program",
            "kind": "assessment", "summary": "A synthetic reviewed route for testing.",
            "status": "check_details", "valid_until": "2026-09-17T12:00:00Z",
            "categories": ["men", "women"], "format": "remote",
            "focuses": ["national_team"], "state": None, "participation": "individual",
            "opens_at": "2026-09-01T00:00:00Z", "closes_at": "2026-09-21T00:00:00Z",
            "sources": [{"id": "source-1", "title": "Synthetic source", "url": SOURCE_URL,
                         "checked_at": "2026-09-09T12:00:00Z", "expires_at": "2026-09-17T12:00:00Z"}],
            "facts": [{"key": key, "label": key.title(),
                       "value": None if key == "contact" else f"Synthetic {key} fact",
                       "source_ids": [] if key == "contact" else ["source-1"]}
                      for key in ("dates", "location", "cost", "eligibility", "contact")],
            "action": {"kind": "open_source", "label": "Review official details", "href": SOURCE_URL,
                       "recipient": None, "purpose": None, "source_ids": ["source-1"]}, **changes}


def contact_record():
    item = record("synthetic-contact", kind="contact", status="published_route", format="any",
                  opens_at=None, closes_at=None, participation="information")
    item["facts"][4].update(value="Synthetic program inquiry desk", source_ids=["source-1"])
    item["action"].update(kind="prepare_introduction", label="Prepare introduction",
                          recipient="Synthetic program inquiry desk", purpose="Ask which pathway requirements apply.")
    return item


def shortlist(records, **changes):
    return api.reviewed_shortlist(query(**changes), records, NOW)


@pytest.fixture
def store(monkeypatch):
    fixture = WorkspaceStore([LINK])
    fixture.rows[CALLER.encode()] = {"payload": "PRIVATE EXISTING DRAFT MUST NOT BE READ"}
    before = deepcopy(fixture.rows)
    source_attempts = []

    def forbidden_source(*args, **kwargs):
        source_attempts.append(True)
        raise AssertionError("GMTM reads forbidden")

    monkeypatch.setattr(api, "_get_agent_db", fixture.connect)
    monkeypatch.setattr(workspace, "_get_gmtm_db", forbidden_source)
    monkeypatch.setattr(combine_api, "_get_gmtm_db", forbidden_source)
    monkeypatch.setattr(api, "RECORDS", (record(),))
    monkeypatch.setattr(api, "_now", lambda: NOW)
    yield fixture
    assert not source_attempts
    assert fixture.rows == before
    assert all(db.closed and not db.transaction and db.commits == 0 for db in fixture.connections)
    assert all(sql.startswith("SELECT ") and "athlete_profiles" in sql
               and "athlete_workspaces" not in sql for sql, _ in fixture.queries)


@pytest.fixture
def client(store):
    app = FastAPI()
    app.add_api_route(PATH, api.current_athlete_opportunities, methods=["POST"])
    app.dependency_overrides[require_clerk_id] = lambda: CALLER
    with TestClient(app) as instance:
        yield instance


def test_http_returns_only_bound_owner_and_readonly_public_records(client, store):
    response = client.post(PATH, json=query())
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"state", "owner_scope", "link_revision", "generated_at", "items", "limitations"}
    assert body["owner_scope"] == api.owner_scope(CALLER, LINK["user_id"])
    assert body["link_revision"] == api._revision(LINK)
    assert body["generated_at"] == NOW.isoformat() and body["state"] == "ready"
    assert [item["id"] for item in body["items"]] == ["synthetic-assessment"]
    assert "PRIVATE" not in response.text
    assert store.queries == [
        ("SELECT id, user_id, clerk_id FROM athlete_profiles WHERE clerk_id = %s LIMIT 2", (CALLER,)),
        ("SELECT id, user_id, clerk_id FROM athlete_profiles WHERE user_id = %s LIMIT 2", (LINK["user_id"],)),
    ]
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"


@pytest.mark.parametrize("changes", [
    {"pathway": "junior_flag"}, {"pathway": "college"}, {"category": "boys"}, {"format": "virtual"},
    {"link_revision": "a" * 63}, {"link_revision": "A" * 64}, {"link_revision": None},
    {"athlete_id": 2}, {"user_id": 2}, {"clerk_id": "other"}, {"owner_scope": "other"},
    {"goal": "PRIVATE GOAL"}, {"category": []}, {"format": False},
])
def test_invalid_search_and_actor_overrides_fail_before_database(client, store, changes):
    response = client.post(PATH, json=query(**changes))
    assert response.status_code == 400 and response.json()["code"] == "opportunities_invalid"
    assert not store.connections


@pytest.mark.parametrize("body", [
    b"{}", b"[]", b"null", b'{"x":NaN}', b"\xff",
    ('{"pathway":"adult_flag",' + json.dumps(query())[1:]).encode(),
    ('"' + "x" * api.MAX_BODY + '"').encode(),
    ("[" * 1100 + "]" * 1100).encode(),
])
def test_raw_json_duplicates_unicode_shapes_and_size_fail_before_database(client, store, body):
    response = client.post(PATH, content=body, headers={"content-type": "application/json"})
    assert response.status_code == 400 and not store.connections


def test_query_parameters_and_wrong_content_type_fail_before_database(client, store):
    assert client.post(PATH + "?athlete_id=8201", json=query()).status_code == 400
    assert client.post(PATH, content=json.dumps(query()), headers={"content-type": "text/plain"}).status_code == 400
    assert not store.connections


def test_chunked_oversize_request_is_bounded_before_connect(client, store):
    chunks = iter([b" " * (api.MAX_BODY // 2), b" " * (api.MAX_BODY // 2), b"{}"])
    response = client.post(PATH, content=chunks, headers={"content-type": "application/json"})
    assert response.status_code == 400 and not store.connections


@pytest.mark.parametrize("links,code", [
    ([], "workspace_unlinked"),
    ([LINK, {**LINK, "id": 192, "user_id": 8202}], "workspace_link_changed"),
    ([LINK, {**LINK, "id": 192, "clerk_id": "another_caller"}], "workspace_link_changed"),
    ([{**LINK, "id": True}], "workspace_link_changed"),
    ([{**LINK, "user_id": True}], "workspace_link_changed"),
    ([{**LINK, "clerk_id": None}], "workspace_unlinked"),
])
def test_missing_ambiguous_and_invalid_link_never_returns_shortlist(client, store, links, code):
    store.links = deepcopy(links)
    response = client.post(PATH, json=query())
    assert response.status_code == 409 and response.json()["code"] == code
    assert "items" not in response.json()


@pytest.mark.parametrize("change", [{"id": 192}, {"user_id": 8202}])
def test_recreated_or_relinked_owner_rejects_old_revision(client, store, change):
    store.links = [{**LINK, **change}]
    response = client.post(PATH, json=query())
    assert response.status_code == 409 and response.json()["code"] == "workspace_link_changed"
    assert "items" not in response.json()


def test_casefolded_database_match_does_not_authorize(client, store):
    store.case_insensitive = True
    store.links = [{**LINK, "clerk_id": CALLER.upper()}]
    response = client.post(PATH, json=query())
    assert response.status_code == 409 and response.json()["code"] == "workspace_link_changed"


@pytest.mark.parametrize("stage", ["connect", "execute", "close"])
def test_database_failures_are_redacted_and_opened_connections_closed(client, store, stage):
    store.failures[stage] = RuntimeError("PRIVATE HOST PASSWORD SQL DATA")
    response = client.post(PATH, json=query())
    assert response.status_code == 503 and "PRIVATE" not in response.text
    assert "items" not in response.json()
    assert response.headers["cache-control"] == "private, no-store"


def test_invalid_catalog_fails_after_closing_owner_connection(client, store, monkeypatch):
    monkeypatch.setattr(api, "RECORDS", (record(sources=[]),))
    response = client.post(PATH, json=query())
    assert response.status_code == 503 and response.json()["code"] == "opportunities_unavailable"
    assert len(store.connections) == 1 and store.connections[0].closed


def test_unknown_facts_remain_null_and_response_does_not_mutate_catalog():
    original = record()
    records = [original]
    before = deepcopy(records)
    items, limitations = shortlist(records, category="women")
    assert len(items) == 1 and limitations
    assert len(items[0]["facts"]) == 5
    assert items[0]["facts"][4]["value"] is None and items[0]["facts"][4]["source_ids"] == []
    assert "women's flag football" in items[0]["relevance"]
    assert set(items[0]).isdisjoint({"categories", "format", "opens_at", "closes_at", "fit_score"})
    items[0]["facts"][0]["value"] = "Changed only in response"
    items[0]["sources"][0]["title"] = "Changed only in response"
    assert records == before


@pytest.mark.parametrize("mutation", [
    lambda x: x["facts"].pop(),
    lambda x: x["facts"].append(deepcopy(x["facts"][0])),
    lambda x: x["facts"][0].update(key="contact"),
    lambda x: x["facts"][0].update(source_ids=[]),
    lambda x: x["facts"][0].update(source_ids=["missing"]),
    lambda x: x["facts"][0].update(source_ids=["source-1", "source-1"]),
    lambda x: x["facts"][4].update(source_ids=["source-1"]),
    lambda x: x["facts"][0].update(value=" "),
    lambda x: x["facts"][0].update(extra="unsupported"),
    lambda x: x["sources"].clear(),
    lambda x: x["sources"].append(deepcopy(x["sources"][0])),
    lambda x: x["sources"][0].update(extra="unsupported"),
    lambda x: x["sources"][0].update(checked_at="2026-09-17T12:00:00Z"),
    lambda x: x["sources"][0].update(expires_at="2026-09-16T12:00:00Z"),
    lambda x: x["action"].update(source_ids=["missing"]),
    lambda x: x["action"].update(href="https://usafootball.com/unrelated-source"),
    lambda x: x["action"].update(recipient="Unrequested recipient"),
    lambda x: x.update(extra="unsupported"),
    lambda x: x.update(categories=["men", "men"]),
])
def test_missing_duplicate_or_unsupported_evidence_fails_closed(mutation):
    item = record()
    mutation(item)
    with pytest.raises(ValueError):
        shortlist([item])


@pytest.mark.parametrize("url", [
    "http://usafootball.com/national-team", "https://usafootball.com.evil.test/national-team",
    "https://leaguefinder-int.usafootball.com/events", "https://user@usafootball.com/national-team",
    "https://usafootball.com:443/national-team", "https://usafootball.com/national-team?secret=x",
    "https://usafootball.com/national-team#contact", "https://usafootball.com/%2e%2e/contact",
    "https://usafootball.com/../contact", "https://usafootball.com//contact",
    "https://usafootball.com/\\contact", "https://usafootball.com/é", "https://usafootball.com",
])
def test_unreviewed_hosts_and_ambiguous_urls_are_rejected(url):
    item = record()
    item["sources"][0]["url"] = url
    item["action"]["href"] = url
    with pytest.raises(ValueError):
        shortlist([item])


def test_introduction_requires_sourced_public_recipient_and_purpose():
    items, _ = shortlist([contact_record()])
    assert items[0]["action"]["kind"] == "prepare_introduction"
    for field, value in (("recipient", None), ("recipient", " "), ("purpose", None), ("purpose", "")):
        invalid = contact_record()
        invalid["action"][field] = value
        with pytest.raises(ValueError):
            shortlist([invalid])
    missing = contact_record()
    missing["facts"][4].update(value=None, source_ids=[])
    with pytest.raises(ValueError):
        shortlist([missing])
    unrelated = contact_record()
    unrelated["sources"].append({**unrelated["sources"][0], "id": "source-2",
                                 "url": "https://usafootball.com/unrelated-contact"})
    unrelated["facts"][4]["source_ids"] = ["source-2"]
    with pytest.raises(ValueError):
        shortlist([unrelated])


@pytest.mark.parametrize("changes", [
    {"valid_until": "2026-09-10T12:00:00Z"},
    {"closes_at": "2026-09-10T12:00:00Z"},
    {"opens_at": "2026-09-11T00:00:00Z"},
])
def test_expired_past_and_future_windows_are_omitted(changes):
    items, limitations = shortlist([record(**changes)])
    assert items == [] and any("outside their reviewed dates" in text for text in limitations)


def test_future_source_check_is_not_current_and_close_caps_output_validity():
    item = record()
    item["sources"][0]["checked_at"] = "2026-09-11T12:00:00Z"
    assert shortlist([item])[0] == []
    item = record(closes_at="2026-09-12T00:00:00Z")
    assert shortlist([item])[0][0]["valid_until"] == "2026-09-12T00:00:00+00:00"


def test_source_expiry_and_open_boundary_are_exact():
    item = record(valid_until="2026-09-10T12:00:00Z")
    item["sources"][0]["expires_at"] = "2026-09-10T12:00:00Z"
    assert shortlist([item])[0] == []
    assert shortlist([record(opens_at="2026-09-10T12:00:00Z")])[0]


@pytest.mark.parametrize("value", ["2026-09-17", "2026-09-17T12:00:00", "2026-09-17T12:00:00-04:00", "2026-02-30T12:00:00Z"])
def test_source_times_require_real_utc_timestamps(value):
    with pytest.raises(ValueError):
        shortlist([record(valid_until=value)])


def test_registration_open_needs_explicit_window_and_sourced_date_fact():
    assert shortlist([record(status="registration_open")])[0]
    for changes in ({"opens_at": None}, {"closes_at": None},
                    {"opens_at": "2026-09-21T00:00:00Z", "closes_at": "2026-09-01T00:00:00Z"}):
        with pytest.raises(ValueError):
            shortlist([record(status="registration_open", **changes)])
    item = record(status="registration_open")
    item["facts"][0].update(value=None, source_ids=[])
    with pytest.raises(ValueError):
        shortlist([item])


def test_category_and_format_filter_before_returning_up_to_three():
    records = [record("women-remote", categories=["women"]),
               record("men-in-person", categories=["men"], format="in_person", kind="event"),
               contact_record()]
    assert [x["id"] for x in shortlist(records, category="women", format="remote")[0]] == ["women-remote"]
    assert [x["id"] for x in shortlist(records, category="men", format="in_person")[0]] == ["men-in-person"]
    items, limitations = shortlist(records, category="women", format="in_person")
    assert items == [] and any("No current reviewed options" in text for text in limitations)
    assert len(shortlist([record(f"item-{n}") for n in range(5)])[0]) == 3


def test_duplicate_even_beyond_visible_limit_and_unbounded_collection_are_rejected():
    first = record("item-0")
    with pytest.raises(ValueError):
        shortlist([first, record("item-1"), record("item-2"), deepcopy(first)])
    with pytest.raises(ValueError):
        shortlist([record(f"item-{n}") for n in range(31)])
    with pytest.raises(ValueError):
        shortlist(iter([first]))


@pytest.mark.parametrize("now", [NOW.replace(tzinfo=None), NOW.astimezone(timezone(timedelta(hours=-4)))])
def test_review_clock_requires_utc(now):
    with pytest.raises(ValueError):
        api.reviewed_shortlist(query(), [record()], now)


def competition_record(identifier="synthetic-team-event", *, state="FL", participation="team"):
    item = record(identifier, kind="event", format="in_person", focuses=["competition"],
                  state=state, participation=participation)
    item["sources"][0]["url"] = "https://iflag.org/tournaments/synthetic-reviewed-event/"
    item["action"]["href"] = item["sources"][0]["url"]
    item["facts"][1]["value"] = f"Synthetic venue in {state}" if state else None
    item["facts"][1]["source_ids"] = ["source-1"] if state else []
    item["facts"][2]["value"] = "Synthetic $375 per team; additional charges unconfirmed"
    item["facts"][3]["value"] = "Synthetic team entry; no individual spot established"
    return item


def test_old_four_field_query_defaults_to_national_team_without_mutating_input(client, monkeypatch):
    legacy = query()
    original = deepcopy(legacy)
    normalized = api.validate_query(legacy)
    assert normalized == {**legacy, "focus": "national_team", "state": None, "entry": "any"}
    assert legacy == original and set(legacy) == {"pathway", "category", "format", "link_revision"}
    monkeypatch.setattr(api, "RECORDS", (competition_record(), record()))
    response = client.post(PATH, json=legacy)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["synthetic-assessment"]
    assert response.json()["items"][0]["participation"] == "individual"


@pytest.mark.parametrize("optional", [
    {"focus": "competition"}, {"focus": "any"}, {"state": "FL"}, {"state": "DC"},
    {"state": None}, {"entry": "individual"}, {"entry": "team"},
    {"focus": "competition", "state": "TX", "entry": "team"},
])
def test_optional_constraints_can_be_supplied_independently(optional):
    assert api.validate_query(query(**optional)) == {
        **query(), "focus": "national_team", "state": None, "entry": "any", **optional}


@pytest.mark.parametrize("optional", [
    {"focus": "olympics"}, {"focus": "college"}, {"focus": None}, {"focus": []}, {"focus": True},
    {"entry": "information"}, {"entry": "free_agent"}, {"entry": None}, {"entry": []},
    {"state": "fl"}, {"state": "Florida"}, {"state": " FL"}, {"state": "FL\n"},
    {"state": "ZZ"}, {"state": ""}, {"state": False}, {"state": []}, {"state": {"code": "FL"}},
    {"location": "FL"}, {"states": ["FL"]}, {"focuses": ["competition"]}, {"participation": "team"},
    {"radius_miles": 50}, {"home_state": "FL"},
])
def test_malformed_or_unreviewed_constraints_fail_before_database(client, store, optional):
    response = client.post(PATH, json=query(**optional))
    assert response.status_code == 400 and response.json()["code"] == "opportunities_invalid"
    assert not store.connections


@pytest.mark.parametrize("key,value", [("focus", "competition"), ("state", "FL"), ("entry", "team")])
def test_duplicate_optional_fields_are_rejected_before_database(client, store, key, value):
    body = json.dumps(query(**{key: value}))[:-1] + "," + json.dumps(key) + ":" + json.dumps(value) + "}"
    response = client.post(PATH, content=body, headers={"content-type": "application/json"})
    assert response.status_code == 400 and not store.connections


def test_goal_focus_separates_competition_from_national_team_evaluation():
    records = [competition_record(), record(), contact_record()]
    national, _ = shortlist(records)
    competition, limits = shortlist(records, focus="competition")
    assert [item["id"] for item in national] == ["synthetic-assessment", "synthetic-contact"]
    assert [item["id"] for item in competition] == ["synthetic-team-event"]
    assert competition[0]["participation"] == "team" and "Enter with a team" in competition[0]["relevance"]
    assert any("does not establish a USA Football or Olympic qualification route" in text for text in limits)


def test_team_individual_and_information_routes_are_distinct():
    information = contact_record()
    information["focuses"] = ["national_team", "competition"]
    records = [competition_record(), record(), information]
    individuals, _ = shortlist(records, focus="any", entry="individual")
    teams, _ = shortlist(records, focus="any", entry="team")
    assert [item["id"] for item in individuals] == ["synthetic-assessment", "synthetic-contact"]
    assert [item["id"] for item in teams] == ["synthetic-team-event", "synthetic-contact"]
    assert individuals[-1]["participation"] == teams[-1]["participation"] == "information"
    assert all(item["participation"] != "team" for item in individuals)


def test_destination_filters_physical_venues_keeps_remote_and_excludes_unknown_state():
    remote = record("remote-evaluation", focuses=["competition"])
    information = contact_record()
    information.update(focuses=["competition"], format="remote")
    records = [competition_record("fl-team", state="FL"), competition_record("tx-team", state="TX"),
               competition_record("unknown-venue", state=None), remote, information]
    florida, limits = shortlist(records, focus="competition", state="FL")
    texas, _ = shortlist(records, focus="competition", state="TX", format="in_person")
    elsewhere, _ = shortlist(records, focus="competition", state="CA")
    assert [item["id"] for item in florida] == ["fl-team", "remote-evaluation", "synthetic-contact"]
    assert [item["id"] for item in texas] == ["tx-team"]
    assert [item["id"] for item in elsewhere] == ["remote-evaluation", "synthetic-contact"]
    assert any("Your home location was not inferred" in text for text in limits)
    assert all("unknown-venue" != item["id"] for item in florida + texas + elsewhere)
    unconstrained, _ = shortlist(records, focus="competition", format="in_person")
    assert [item["id"] for item in unconstrained] == ["fl-team", "tx-team", "unknown-venue"]


def test_all_constraints_are_applied_together_on_actual_owner_bound_http(client, store, monkeypatch):
    team = competition_record("selected-team", state="FL")
    team["categories"] = ["women"]
    others = [competition_record("wrong-state", state="TX"), record(),
              competition_record("wrong-category", state="FL")]
    others[-1]["categories"] = ["men"]
    monkeypatch.setattr(api, "RECORDS", tuple(others + [team]))
    response = client.post(PATH, json=query(focus="competition", state="FL", entry="team",
                                            category="women", format="in_person"))
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == ["selected-team"]
    assert items[0]["participation"] == "team"
    assert set(items[0]).isdisjoint({"state", "focuses", "categories", "format"})
    assert len(store.connections) == 1 and len(store.queries) == 2


@pytest.mark.parametrize("changes", [
    {"focuses": []}, {"focuses": "competition"}, {"focuses": ["any"]},
    {"focuses": ["competition", "competition"]}, {"focuses": ["college"]},
    {"state": "Florida"}, {"state": "fl"}, {"state": []},
    {"participation": "free_agent"}, {"participation": None}, {"participation": []},
    {"format": "remote", "state": "FL"}, {"format": "any", "state": "FL"},
])
def test_reviewed_constraint_metadata_must_be_exact_and_unambiguous(changes):
    with pytest.raises(ValueError):
        shortlist([competition_record() | changes], focus="any")


@pytest.mark.parametrize("key", ["focuses", "state", "participation"])
def test_missing_constraint_metadata_is_not_silently_inferred(key):
    item = competition_record()
    del item[key]
    with pytest.raises(ValueError):
        shortlist([item], focus="any")


@pytest.mark.parametrize("fact_key", ["location", "eligibility"])
@pytest.mark.parametrize("missing", ["value", "references", "unknown_source"])
def test_team_participation_and_state_require_supported_material_facts(fact_key, missing):
    item = competition_record()
    fact = next(fact for fact in item["facts"] if fact["key"] == fact_key)
    if missing == "value":
        fact.update(value=None, source_ids=[])
    elif missing == "references":
        fact["source_ids"] = []
    else:
        fact["source_ids"] = ["unreviewed-source"]
    with pytest.raises(ValueError):
        shortlist([item], focus="competition")


def test_information_route_does_not_require_invented_participation_eligibility():
    item = contact_record()
    next(fact for fact in item["facts"] if fact["key"] == "eligibility").update(value=None, source_ids=[])
    result, _ = shortlist([item], entry="individual")
    assert result[0]["participation"] == "information"
    assert next(fact for fact in result[0]["facts"] if fact["key"] == "eligibility")["value"] is None


@pytest.mark.parametrize("url", [
    "https://dev.iflag.org/tournaments/example/", "https://dev.usaflag.org/tournaments/example/",
    "https://iflag.org.evil.test/tournaments/example/", "https://iflag.org/tournaments/example/?secret=x",
    "https://iflag.org/tournaments/example/#register", "https://iflag.org:443/tournaments/example/",
    "https://user@iflag.org/tournaments/example/", "https://iflag.org/tournaments/%2e%2e/example/",
])
def test_expanded_organizer_host_does_not_allow_test_sites_or_url_variants(url):
    item = competition_record()
    item["sources"][0]["url"] = item["action"]["href"] = url
    with pytest.raises(ValueError):
        shortlist([item], focus="competition")


def test_new_reviewed_organizer_keeps_team_fee_basis_and_source_context():
    item = competition_record()
    result, _ = shortlist([item], focus="competition")
    assert result[0]["action"]["href"] == "https://iflag.org/tournaments/synthetic-reviewed-event/"
    assert "per team" in next(fact for fact in result[0]["facts"] if fact["key"] == "cost")["value"]
    assert result[0]["participation"] == "team"


def test_top_three_limit_counts_only_matching_current_options_and_explains_truncation():
    current = [competition_record(f"event-{index}") for index in range(4)]
    past = competition_record("expired-event")
    past["valid_until"] = "2026-09-10T12:00:00Z"
    items, limits = shortlist([record(), past, *current], focus="competition", state="FL")
    assert [item["id"] for item in items] == ["event-0", "event-1", "event-2"]
    assert "Showing 3 of 4 current options. Choose a search focus to narrow the collection." in limits
    assert any("outside their reviewed dates" in text for text in limits)
    assert len(limits) <= 6
    three, three_limits = shortlist(current[:3], focus="competition")
    assert len(three) == 3 and not any(text.startswith("Showing 3 of") for text in three_limits)


def test_reviewed_catalog_keeps_solo_inquiries_separate_from_team_tournaments():
    from opportunity_catalog import CHECKED, RECORDS as reviewed_catalog

    checked = datetime.fromisoformat(CHECKED.replace("Z", "+00:00"))
    national, _ = api.reviewed_shortlist(query(), reviewed_catalog, checked)
    solo, _ = api.reviewed_shortlist(query(focus="competition", entry="individual"), reviewed_catalog, checked)
    events, _ = api.reviewed_shortlist(query(focus="competition", format="in_person", state="FL"), reviewed_catalog, checked)
    everything, limits = api.reviewed_shortlist(query(focus="any"), reviewed_catalog, checked)
    assert national and solo and events
    assert all(item["kind"] != "event" for item in national)
    assert all(item["participation"] == "information" for item in solo)
    assert all(item["kind"] == "event" and item["participation"] == "team" for item in events)
    assert {item["id"] for item in national}.isdisjoint(item["id"] for item in events + solo)
    assert len(everything) == 3 and any(text.startswith("Showing 3 of ") for text in limits)
