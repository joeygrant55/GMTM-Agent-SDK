"""September 30 official-source refresh; no DB, network, model or HTTP calls."""
from copy import deepcopy
from datetime import datetime, timedelta

from athlete_opportunities import reviewed_shortlist
from opportunity_catalog import CHECKED, EXPIRES, ORLANDO_EXPIRES, RECORDS


def utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def search(*, now=CHECKED, records=RECORDS, **changes):
    query = {"pathway": "adult_flag", "category": "unspecified", "format": "any",
             "focus": "any", "state": None, "entry": "any", "link_revision": "a" * 64,
             **changes}
    return reviewed_shortlist(query, records, utc(now))


def by_id(identifier):
    return next(record for record in RECORDS if record["id"] == identifier)


def test_review_has_four_current_records_and_one_withdrawn_combine():
    assert len(RECORDS) == 5
    national, _ = search(focus="national_team")
    assert [item["id"] for item in national] == ["usaf-high-performance-inquiry"]
    competition, _ = search(focus="competition")
    assert {item["id"] for item in competition} == {
        "iflag-battle-orlando-2026", "iflag-tampa-nationals-2027", "iflag-team-access-inquiry"}
    all_items, limits = search()
    assert len(all_items) == 3
    assert any("3 of 4 current options" in text for text in limits)


def test_renewing_source_dates_alone_cannot_reopen_ended_combine():
    ended = deepcopy(by_id("usaf-adult-digital-combine-2-2027"))
    ended["valid_until"] = EXPIRES
    for source in ended["sources"]:
        source.update(checked_at=CHECKED, expires_at=EXPIRES)
    items, limits = search(records=(ended,), focus="national_team")
    assert items == []
    assert any("outside their reviewed dates" in text for text in limits)
    original = by_id(ended["id"])
    assert original["closes_at"] == "2026-09-21T00:00:00Z"
    entry = next(source for source in original["sources"] if source["id"] == "entry")
    assert entry["checked_at"] == "2026-09-10T16:30:06Z"


def test_orlando_withdraws_before_final_deadline_but_tampa_remains_current():
    before, _ = search(now="2026-10-01T23:59:59Z", focus="competition", format="in_person")
    assert len(before) == 2
    after, _ = search(now=ORLANDO_EXPIRES, focus="competition", format="in_person")
    assert [item["id"] for item in after] == ["iflag-tampa-nationals-2027"]
    orlando = by_id("iflag-battle-orlando-2026")
    assert orlando["valid_until"] == ORLANDO_EXPIRES
    assert all(source["expires_at"] == ORLANDO_EXPIRES for source in orlando["sources"])
    assert utc(ORLANDO_EXPIRES) <= utc(orlando["closes_at"]) < utc(EXPIRES)
    assert orlando["status"] == "check_details"


def test_orlando_does_not_offer_a_deposit_after_its_balance_deadline():
    items, _ = search(focus="competition", format="in_person")
    orlando = next(item for item in items if item["id"] == "iflag-battle-orlando-2026")
    cost = next(fact["value"] for fact in orlando["facts"] if fact["key"] == "cost")
    assert "deadline passed Sep 25" in cost
    assert "Confirm whether new fully paid entries remain available" in cost
    assert "deposit-balance deadline has passed" in orlando["summary"]
    assert "confirm" in orlando["summary"].lower()


def test_no_records_survive_review_expiry_or_show_before_review():
    assert search(now=EXPIRES)[0] == []
    assert search(now=(utc(CHECKED) - timedelta(seconds=1)).isoformat())[0] == []
    assert timedelta(0) < utc(EXPIRES) - utc(CHECKED) <= timedelta(days=7)


def test_renewed_tampa_evidence_expires_before_balance_deadline():
    assert utc(EXPIRES) < utc("2026-10-09T00:00:00Z")
    record = by_id("iflag-tampa-nationals-2027")
    assert record["status"] == "check_details"
    eligibility = next(fact["value"] for fact in record["facts"] if fact["key"] == "eligibility")
    assert "U23 cutoff says Jan 1, 2026 for this 2027 event" in eligibility
    assert "Confirm age" in eligibility


def test_team_events_do_not_turn_into_individual_or_national_team_opportunities():
    solo, _ = search(focus="competition", entry="individual")
    assert [item["id"] for item in solo] == ["iflag-team-access-inquiry"]
    assert search(focus="national_team", format="in_person")[0] == []
    teams, limits = search(focus="competition", format="in_person", state="FL", entry="team")
    assert len(teams) == 2
    assert all(item["participation"] == "team" and item["status"] == "check_details" for item in teams)
    assert any("does not establish a USA Football or Olympic qualification route" in text for text in limits)
    for item in teams:
        facts = {fact["key"]: fact["value"] for fact in item["facts"]}
        assert "per team/division" in facts["cost"]
        assert "no prior qualification required" in facts["eligibility"]
        assert "Individual placement is not established" in facts["eligibility"]
    tampa_cost = next(fact["value"] for fact in by_id("iflag-tampa-nationals-2027")["facts"] if fact["key"] == "cost")
    assert "$50 late fee" in tampa_cost and "7pm EST" in tampa_cost and "5v5" in tampa_cost


def test_standing_contacts_keep_unknown_facts_unknown_and_only_prepare_drafts():
    contacts = [record for record in RECORDS if record["kind"] == "contact"]
    assert len(contacts) == 2
    for record in contacts:
        assert record["action"]["kind"] == "prepare_introduction"
        assert record["participation"] == "information"
        assert record["opens_at"] is None and record["closes_at"] is None
        for fact in record["facts"]:
            if fact["key"] != "contact":
                assert fact["value"] is None and fact["source_ids"] == []
