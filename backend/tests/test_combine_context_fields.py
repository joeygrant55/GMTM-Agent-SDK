"""Public field definitions reach assistance without carrying submitted values."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from combine_context import build_combine_context
from combine_requirements import Activity, RequiredField, parse_activities, project_activity


def activity(fields=None):
    return Activity(4907, 1318, "20-Yard Dash", 7, "exercise", "Complete the listed activity.",
                    tuple(fields or [RequiredField("metric", "40 Yard Dash Time"), RequiredField("video", "20 Yard Dash")]))


def snapshot(projected, linked=True):
    return {"clerk_id":"synthetic-owner", "athlete_id":9000001 if linked else None,
            "state":"ready" if linked else "link_required",
            "selected_event":{"event_id":1318,"name":"Synthetic adult combine","division":"adult",
                "continuation_url":"https://gmtm.com/virtuals/1318","deadline_display":"September 21, 2026",
                "deadline_source_url":"https://usafootball.com/national-team/digital-combine"},
            "activities":[projected], "counts":{"activities":1,"submitted":0 if linked else None,"fields_present":0 if linked else None},
            "fetched_at":"2026-09-07T12:00:00Z"}


def context(projected, linked=True):
    return build_combine_context(snapshot(projected,linked),"synthetic-owner",1318,4907)


def test_public_field_types_survive_before_linking_without_personal_progress():
    projected=project_activity(activity(),None,personal_available=False)
    result=context(projected,linked=False)
    assert result["activities"][0]["required_fields"] == [
        {"type":"metric","title":"40 Yard Dash Time"}, {"type":"video","title":"20 Yard Dash"}]
    assert result["activities"][0]["missing_fields"] == []
    assert result["activities"][0]["submission_state"] == "unavailable"
    assert result["counts"]["submitted"] is None
    assert not result["personal_progress_available"]


def test_submitted_values_and_extra_metadata_never_enter_definitions():
    submission={"created_on":"2026-09-07T11:00:00Z","payload":{"questions":{
        "metric:40 Yard Dash Time":{"value":{"value":"PRIVATE-RESULT"}},
        "video:20 Yard Dash":{"value":{"value":"https://private.invalid/video"}}}}}
    projected=project_activity(activity(),submission,personal_available=True)
    projected["required_fields"][0].update(value="PRIVATE-ANSWER",metric_template={"unit":"INVENTED-UNIT"})
    result=context(projected)
    serialized=json.dumps(result)
    for forbidden in ["PRIVATE-RESULT","private.invalid","PRIVATE-ANSWER","INVENTED-UNIT","synthetic-owner","9000001"]:
        assert forbidden not in serialized
    assert set(result["activities"][0]["required_fields"][0]) == {"type","title"}


def test_unknown_public_format_is_unknown_not_inferred_from_caption():
    projected=project_activity(activity([RequiredField("unrecognized-widget","Upload a video")]),None,personal_available=False)
    result=context(projected,linked=False)
    assert result["activities"][0]["required_fields"] == [{"type":"unknown","title":"Upload a video"}]


def test_legacy_snapshot_omits_format_claims_and_preserves_missing_fields():
    projected=project_activity(activity(),None,personal_available=True)
    projected.pop("required_fields")
    result=context(projected)
    assert result["activities"][0]["required_fields"] is None
    assert result["activities"][0]["missing_fields"] == ["40 Yard Dash Time","20 Yard Dash"]


@pytest.mark.parametrize("bad", ["video",{},[None],[{"type":"video","title":""}],
    [{"type":{},"title":"valid"}],[{"type":"video","title":"x"*2001}],
    [{"type":"x"*101,"title":"valid"}], [{"type":"video","title":"valid"}]*101])
def test_invalid_definitions_fail_closed(bad):
    projected=project_activity(activity(),None,personal_available=True)
    projected["required_fields"]=bad
    projected["required_field_count"]=len(bad) if isinstance(bad,list) else 2
    with pytest.raises(HTTPException) as error:context(projected)
    assert error.value.status_code==503


def test_inconsistent_count_cannot_claim_complete_public_definition():
    projected=project_activity(activity(),None,personal_available=True)
    projected["required_field_count"]=3
    with pytest.raises(HTTPException):context(projected)


def test_definition_projection_is_independent_and_context_size_stays_bounded():
    projected=project_activity(activity(),None,personal_available=True)
    result=context(projected)
    result["activities"][0]["required_fields"][0]["title"]="changed"
    assert projected["required_fields"][0]["title"]=="40 Yard Dash Time"
    projected["required_fields"]=[{"type":"essay","title":str(i)+"x"*1995} for i in range(30)]
    projected["required_field_count"]=30
    with pytest.raises(HTTPException):context(projected)


def test_all_public_required_questions_preserve_exact_labels_and_types():
    public=json.loads((Path(__file__).parent/'fixtures/usaf_2027_combine2_public.json').read_text())
    for event in public["events"]:
        event_id=event["event"]["event_id"]
        rows=[{**task,"description":"Public organizer task.","payload":{"questions":task["questions"]}}
              for task in event["tasks"]]
        sources={task["task_id"]:task for task in event["tasks"]}
        for parsed in parse_activities(rows,event_id):
            projected=project_activity(parsed,None,personal_available=False)
            expected=[{"type":q["type"],"title":q["title"]} for q in sources[parsed.task_id]["questions"] if q["required"]]
            assert projected["required_fields"]==expected
            assert len(expected)==projected["required_field_count"]
