"""Source-status regressions prompted by synthetic live answer failures.

These test the real projection and model context, not generated prose. The
post-evaluation prompt still needs a separate live-model verification.
"""

from copy import deepcopy
import json

from fastapi import HTTPException
import pytest

import combine_context
from combine_requirements import Activity, RequiredField, project_activity


FIELDS = (RequiredField("metric", "40 Yard Dash Time"), RequiredField("video", "20 Yard Dash"))


def projected(submission, *, linked=True, fields=FIELDS):
    activity = Activity(4907, 1318, "20-Yard Dash", 7, "exercise", "Public activity instructions.", fields)
    return project_activity(activity, submission, personal_available=linked)


def context(activity, *, linked=True):
    snapshot = {"schema_version": 1, "clerk_id": "synthetic-owner", "athlete_id": 9000001 if linked else None,
        "state": "ready" if linked else "link_required",
        "selected_event": {"event_id": 1318, "name": "Synthetic adult combine", "division": "adult",
            "continuation_url": "https://gmtm.com/virtuals/1318", "deadline_display": "September 21, 2026",
            "deadline_source_url": "https://usafootball.com/national-team/digital-combine"},
        "activities": [activity], "counts": {"activities": 1,
            "submitted": int(activity["submission_state"] == "submitted") if linked else None,
            "fields_present": int(activity["evidence_state"] == "fields_present") if linked else None},
        "fetched_at": "2026-09-07T12:00:00Z"}
    return combine_context.build_combine_context(snapshot, "synthetic-owner", 1318, 4907)


def attempt(questions):
    return {"created_on": "2026-09-07T11:00:00Z", "payload": {"questions": questions}}


def test_no_attempt_and_empty_saved_attempt_have_same_labels_but_different_observations():
    no_attempt = context(projected(None))
    saved_empty = context(projected(attempt({})))
    absent, saved = no_attempt["activities"][0], saved_empty["activities"][0]
    assert absent["missing_fields"] == saved["missing_fields"] == ["40 Yard Dash Time", "20 Yard Dash"]
    assert absent["required_fields"] == saved["required_fields"] == [
        {"type": "metric", "title": "40 Yard Dash Time"}, {"type": "video", "title": "20 Yard Dash"}]
    assert absent["submission_state"] == "not_submitted"
    assert absent["status_observation"] == {"visible_saved_attempt": False,
        "required_field_presence": "not_assessed_no_attempt", "organizer_acceptance": "unknown"}
    assert saved["submission_state"] == "submitted"
    assert saved["status_observation"] == {"visible_saved_attempt": True,
        "required_field_presence": "missing_fields", "organizer_acceptance": "unknown"}
    assert no_attempt["counts"]["submitted"] == 0 and saved_empty["counts"]["submitted"] == 1


def test_saved_partial_attempt_preserves_exact_missing_field_without_acceptance_claim():
    result = context(projected(attempt({"metric:40 Yard Dash Time": {"value": {"value": "PRIVATE-MEASUREMENT"}}})))
    activity = result["activities"][0]
    assert activity["missing_fields"] == ["20 Yard Dash"]
    assert activity["status_observation"] == {"visible_saved_attempt": True,
        "required_field_presence": "missing_fields", "organizer_acceptance": "unknown"}
    assert "PRIVATE-MEASUREMENT" not in json.dumps(result)


def test_saved_fields_present_does_not_mean_valid_or_accepted():
    result = context(projected(attempt({
        "metric:40 Yard Dash Time": {"value": {"value": "synthetic-not-a-valid-time"}},
        "video:20 Yard Dash": {"value": {"value": "synthetic-not-a-valid-video"}},
    })))
    activity = result["activities"][0]
    assert activity["status_observation"] == {"visible_saved_attempt": True,
        "required_field_presence": "fields_present", "organizer_acceptance": "unknown"}
    assert activity["missing_fields"] == [] and result["counts"]["fields_present"] == 1
    assert "synthetic-not-a-valid" not in json.dumps(result)
    assert result["athlete_id_status"] == "unknown"


@pytest.mark.parametrize("submission", [
    {"payload": "malformed-json"}, {"payload": {"questions": []}},
    attempt({"metric:40 Yard Dash Time": {"unexpected": "shape"}}),
])
def test_unreadable_saved_answers_leave_attempt_known_and_field_presence_unknown(submission):
    result = context(projected(submission))
    assert result["activities"][0]["status_observation"] == {"visible_saved_attempt": True,
        "required_field_presence": "unknown", "organizer_acceptance": "unknown"}
    assert result["counts"]["submitted"] == 1


def test_unavailable_personal_progress_keeps_public_help_requirements_and_unknown_counts():
    result = context(projected(None, linked=False), linked=False)
    activity = result["activities"][0]
    assert not result["personal_progress_available"]
    assert activity["submission_state"] == "unavailable" and activity["missing_fields"] == []
    assert activity["status_observation"] == {"visible_saved_attempt": None,
        "required_field_presence": "unknown", "organizer_acceptance": "unknown"}
    assert activity["required_fields"] == [
        {"type": "metric", "title": "40 Yard Dash Time"}, {"type": "video", "title": "20 Yard Dash"}]
    assert result["counts"] == {"activities": 1, "submitted": None, "fields_present": None}
    assert activity["continuation_url"] == "https://gmtm.com/virtuals/1318"


def test_unknown_or_absent_field_metadata_does_not_erase_known_submission_status():
    activity = projected(None)
    activity.pop("required_fields")
    result = context(activity)["activities"][0]
    assert result["required_fields"] is None
    assert result["status_observation"]["visible_saved_attempt"] is False
    unknown = projected(attempt({}), fields=(RequiredField("new-widget", "Unconfirmed format"),))
    result = context(unknown)["activities"][0]
    assert result["required_fields"] == [{"type": "unknown", "title": "Unconfirmed format"}]
    assert result["status_observation"]["visible_saved_attempt"] is True
    assert result["status_observation"]["required_field_presence"] == "unknown"


@pytest.mark.parametrize("state", [None, "", "unrecognized"])
def test_unrecognized_submission_state_never_becomes_no_attempt(state):
    activity = projected(None)
    activity["submission_state"] = state
    result = context(activity)["activities"][0]
    assert result["status_observation"] == {"visible_saved_attempt": None,
        "required_field_presence": "unknown", "organizer_acceptance": "unknown"}


def test_observation_is_recomputed_and_does_not_copy_injected_status_or_private_values():
    activity = projected(None)
    activity["status_observation"] = {"visible_saved_attempt": True, "organizer_acceptance": "accepted", "answer": "PRIVATE"}
    original = deepcopy(activity)
    result = context(activity)
    assert result["activities"][0]["status_observation"]["visible_saved_attempt"] is False
    assert result["activities"][0]["status_observation"]["organizer_acceptance"] == "unknown"
    assert "PRIVATE" not in json.dumps(result) and activity == original


def test_context_limit_includes_new_observation(monkeypatch):
    activity = projected(None)
    result = context(activity)
    before_observation = deepcopy(result)
    before_observation["activities"][0].pop("status_observation")
    previous_length = len(json.dumps(before_observation, ensure_ascii=False))
    assert previous_length < len(json.dumps(result, ensure_ascii=False))
    monkeypatch.setattr(combine_context, "MAX_CONTEXT_CHARS", previous_length)
    with pytest.raises(HTTPException) as error:
        context(activity)
    assert error.value.status_code == 503
