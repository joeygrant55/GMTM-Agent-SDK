from datetime import datetime, timedelta, timezone

import pytest

from profile_pathways import EXPIRES_AT, PathwayExpired, pathway_bundle


def test_expired_national_sources_fail_without_disabling_profile_work():
    assert pathway_bundle("national_team", EXPIRES_AT - timedelta(seconds=1))["references"]
    with pytest.raises(PathwayExpired):
        pathway_bundle("national_team", EXPIRES_AT)
    assert pathway_bundle("profile", EXPIRES_AT)["references"] == []
    assert len(pathway_bundle("outreach", EXPIRES_AT)["actions"]) == 2


def test_official_destinations_are_reviewed_and_caller_mutation_is_isolated():
    now = datetime(2026, 9, 9, tzinfo=timezone.utc)
    bundle = pathway_bundle("national_team", now)
    references = {item["id"]: item for item in bundle["references"]}
    for action in bundle["actions"]:
        if action["kind"] == "open_source":
            assert action["href"] == references[action["source_ref"]]["href"]
    assert {action["id"] for action in bundle["actions"]} == {
        "prepare_summary", "prepare_introduction", "usaf_support", "usaf_development"}
    bundle["references"][0]["detail"] = "Changed"
    assert pathway_bundle("national_team", now)["references"][0]["detail"] != "Changed"
