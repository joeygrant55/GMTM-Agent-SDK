from combine_results import (
    canonical_drill, canonical_drill_from_task, parse_value, better,
    percentile_better_than, rank_in, format_for_prompt, _best_map,
)


def test_canonical_titles_map_every_gmtm_spelling():
    assert canonical_drill("Shuttle", True) == "5-10-5 Shuttle"
    assert canonical_drill("5-10-5 shuttle", False) == "5-10-5 Shuttle"
    assert canonical_drill("60 Yard", True) == "60-Yard Shuttle"
    assert canonical_drill("60 Yard Shuttle", False) == "60-Yard Shuttle"
    assert canonical_drill("Push ups", True) == "Max Push-Ups"
    assert canonical_drill("Sit ups", True) == "Max Sit-Ups"
    assert canonical_drill("Broad Jump", True) == "Standing Broad Jump"
    assert canonical_drill("20 Yard Dash", False) == "20-Yard Dash"


def test_20_yard_shuttle_alias_only_trusted_inside_an_event():
    assert canonical_drill("20 Yard Shuttle", has_event=True) == "20-Yard Dash"
    assert canonical_drill("20 Yard Shuttle", has_event=False) is None


def test_non_drills_are_ignored():
    assert canonical_drill("Weight", True) is None
    assert canonical_drill("Height", True) is None
    assert canonical_drill(None, True) is None


def test_task_titles_map():
    assert canonical_drill_from_task("5-10-5 Shuttle Run") == "5-10-5 Shuttle"
    assert canonical_drill_from_task("Max. Situps (Copy)") == "Max Sit-Ups"
    assert canonical_drill_from_task("Stick Overhead Squat") is None


def test_parse_value_rejects_junk_and_out_of_range():
    assert parse_value("2.9", "20-Yard Dash") == 2.9
    assert parse_value(".", "Max Sit-Ups") is None
    assert parse_value("100", "20-Yard Dash") is None      # junk time
    assert parse_value("0", "5-10-5 Shuttle") is None      # junk time
    assert parse_value("91", "Standing Broad Jump") == 91.0
    assert parse_value(None, "Max Push-Ups") is None


def test_best_keeps_direction():
    assert better(4.3, 4.5, "lower") == 4.3
    assert better(80, 91, "higher") == 91


def test_best_map_takes_best_of_two_shuttle_rows_per_athlete():
    rows = [(1, "4.6"), (1, "4.4"), (2, "4.9"), (2, "bad"), (3, "0")]
    best = _best_map(rows, "5-10-5 Shuttle")
    assert best == {1: 4.4, 2: 4.9}


def test_rank_and_percentile_lower_is_better():
    pool = [2.9, 3.1, 3.4, 2.7]
    assert rank_in(2.9, pool, "lower") == 2
    assert percentile_better_than(2.9, pool, "lower") == 50.0


def test_rank_and_percentile_higher_is_better():
    pool = [80, 91, 70, 95]
    assert rank_in(91, pool, "higher") == 2
    assert percentile_better_than(91, pool, "higher") == 50.0
    assert percentile_better_than(91, [], "higher") is None


def test_prompt_format_names_rank_percentile_and_trust():
    r = [dict(drill="20-Yard Dash", value=2.9, unit="seconds", event_name="2027 Junior Digital Combine #2", event_id=1317,
              rank_in_event=4, event_pool_size=87, pct_flag_all_time=82.0, pool_size_all_time=153,
              pct_same_org=None, pool_size_same_org=None, organization="USA Football",
              trust_tier="Remote App-Captured", video_uri="https://cdn.gmtm.com/x")]
    s = format_for_prompt(r)
    assert "20-Yard Dash 2.9s" in s
    assert "4 of 87 in 2027 Junior Digital Combine #2" in s
    assert "beats 82% of 153 GMTM athletes" in s
    assert "remote app-captured" in s
    assert "video on file" in s
    assert format_for_prompt([]) == ""


def test_prompt_caps_to_newest_two_events_and_counts_older():
    def r(ev, drill):
        return dict(drill=drill, value=3.0, unit="seconds", event_name=f"E{ev}", event_id=ev,
                    rank_in_event=1, event_pool_size=1, pct_flag_all_time=None, pool_size_all_time=None,
                    pct_same_org=None, pool_size_same_org=None, organization=None,
                    trust_tier="Remote App-Captured", video_uri=None)
    res = [r(1318, "20-Yard Dash"), r(1318, "5-10-5 Shuttle"), r(960, "20-Yard Dash"), r(763, "20-Yard Dash")]
    s = format_for_prompt(res)
    assert "E1318" in s and "E960" in s and "E763" not in s
    assert "+1 older combine on record" in s
