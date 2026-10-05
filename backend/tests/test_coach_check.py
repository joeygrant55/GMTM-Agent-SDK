import json
import sys
from pathlib import Path

import pytest

import coach_check as cc

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import apply_coach_change as apply_mod  # noqa: E402

PROGRAM = {"id": "test-college", "school": "Test College", "program_url": "https://testhawks.com/sports/womens-flag-football/index",
           "staff_page_url": "https://testhawks.com/sports/womens-flag-football/coaches", "head_coach_name": "Samantha Harris",
           "head_coach_title": "Head Coach", "coach_email": "samantha.harris@test.edu", "contact_notes": None}
COACHES = """<table><tr><th>Name</th><th>Title</th><th>Email Address</th></tr>
<tr><td><a href="/c/1">Samantha Harris</a></td><td>Head Coach</td><td><a href="mailto:samantha.harris@test.edu">e</a></td></tr>
<tr><td><a href="/c/2">Chris T</a></td><td>Assistant Flag Football Coach</td><td><a href="mailto:chris@test.edu">e</a></td></tr></table>"""
SPORT_PAGE = "https://testhawks.com/sports/womens-flag-football/coaches"
DIRECTORY = """<table><tr><th>Name</th><th>Title</th><th>Email address</th></tr>
<tr><td colspan="3">Football</td></tr><tr><td>Big Coach</td><td>Head Coach</td><td>big@test.edu</td></tr>
<tr><td colspan="3">Men's Flag Football</td></tr><tr><td>Men Coach</td><td>Head Coach</td><td>men@test.edu</td></tr>
<tr><td colspan="3">Women's Flag Football</td></tr><tr><td>Liz Sowers</td><td>Head Coach</td><td>liz@test.edu</td></tr>
<tr><td>Katie Sowers</td><td>Associate Head Coach</td><td>katie@test.edu</td></tr>
<tr><td colspan="3">Athletic Medicine</td></tr><tr><td>Sara W</td><td>Assistant Athletic Trainer (Flag Football)</td><td>s@test.edu</td></tr></table>"""
DIRECTORY_PAGE = "https://testhawks.com/staff-directory"


def heads(html, url):
    return cc.head_coaches(cc.people(html, url), url)


def test_title_rule_covers_measured_titles_and_excludes_assistants():
    for title in ("Head Coach", "Head Women's Flag Football Coach", "Head Flag Football Coach", "Co-Head Coach",
                  "Athletic Director/ Head Flag Football Coach", "Head Cheer Coach / Head Flag Football Coach"):
        assert cc._HEAD.search(title) and not cc._NOT_HEAD.search(title), title
    for title in ("Assistant Head Coach", "Associate Head Coach", "Asst. Head Coach", "Offensive Coordinator"):
        assert not (cc._HEAD.search(title) and not cc._NOT_HEAD.search(title)), title


def test_sport_page_and_directory_scoping():
    assert [h["name"] for h in heads(COACHES, SPORT_PAGE)] == ["Samantha Harris"]
    assert [h["name"] for h in heads(DIRECTORY, DIRECTORY_PAGE)] == ["Liz Sowers"]


def test_co_heads_kept_in_page_order_and_interim_only_when_alone():
    co = COACHES.replace("Head Coach</td>", "Co-Head Coach</td>", 1).replace("Assistant Flag Football Coach", "Co-Head Coach")
    assert [h["name"] for h in heads(co, SPORT_PAGE)] == ["Samantha Harris", "Chris T"]
    interim = COACHES.replace(">Head Coach<", ">Interim Head Coach<")
    assert [h["name"] for h in heads(interim, SPORT_PAGE)] == ["Samantha Harris"]
    both = co.replace(">Co-Head Coach<", ">Interim Head Coach<", 1).replace(">Co-Head Coach<", ">Head Coach<")
    assert [h["name"] for h in heads(both, SPORT_PAGE)] == ["Chris T"]


def test_presto_cards():
    html = ('<div class="card"><a href="/sports/flagfball/coaches/Brian_Colubiale">Brian Colubiale</a>'
            '<span>Head Women\'s Flag Football Coach</span></div>'
            '<div class="card"><a href="/sports/flagfball/coaches/D">Darius Devine</a><span>Offensive Coordinator</span></div>')
    assert [h["name"] for h in heads(html, "https://dscfalcons.com/sports/flagfball/coaches")] == ["Brian Colubiale"]


def test_three_email_forms():
    from bs4 import BeautifulSoup
    hexed = "12" + "".join(f"{b ^ 0x12:02x}" for b in b"coach@test.edu")
    html = f'<p><a href="mailto:a@test.edu?subject=x">a</a><span data-cfemail="{hexed}">[email protected]</span> b [at] test [dot] edu</p>'
    assert cc.emails_in(BeautifulSoup(html, "html.parser")) == ["a@test.edu", "coach@test.edu", "b@test.edu"]
    assert cc.decode_cfemail("zz") is None


def test_buckets():
    hs = heads(COACHES, SPORT_PAGE)
    assert cc.compare(PROGRAM, SPORT_PAGE, hs)["bucket"] == "match"
    assert cc.compare({**PROGRAM, "head_coach_name": "Samantha Harris '09"}, SPORT_PAGE, hs)["bucket"] == "match"
    assert cc.compare({**PROGRAM, "head_coach_name": "Sam Harris"}, SPORT_PAGE, hs)["bucket"] == "different_person"
    assert cc.compare({**PROGRAM, "head_coach_name": "Samantha Harris-Smith"}, SPORT_PAGE, hs)["bucket"] == "spelling"
    assert cc.compare({**PROGRAM, "head_coach_name": "Jane Harris"}, SPORT_PAGE, hs)["bucket"] == "different_person"
    assert cc.compare({**PROGRAM, "head_coach_name": None}, SPORT_PAGE, hs)["bucket"] == "different_person"
    assert cc.compare({**PROGRAM, "coach_email": "old@test.edu"}, SPORT_PAGE, hs)["bucket"] == "email_changed"
    assert cc.compare({**PROGRAM, "coach_email": None}, SPORT_PAGE, hs)["bucket"] == "email_added"
    assert cc.compare({**PROGRAM, "coach_email": "SAMANTHA.HARRIS@TEST.EDU"}, SPORT_PAGE, hs)["bucket"] == "match"
    no_mail = [{**hs[0], "email": None}]
    assert cc.compare(PROGRAM, SPORT_PAGE, no_mail)["bucket"] == "email_not_on_page"
    noted = {**PROGRAM, "coach_email": None, "contact_notes": "Directory lists samantha.harris@test.edu (ops)."}
    assert cc.compare(noted, SPORT_PAGE, hs)["bucket"] == "noted"
    assert cc.compare(PROGRAM, SPORT_PAGE, [])["bucket"] == "not_found"


def test_co_head_set_compare_ignores_order():
    co = [{"name": "Joseph Newman", "title": "Co-Head Coach", "email": "j@test.edu", "section": ""},
          {"name": "Samantha Harris", "title": "Co-Head Coach", "email": "samantha.harris@test.edu", "section": ""}]
    program = {**PROGRAM, "head_coach_name": "Samantha Harris; Joseph Newman", "coach_email": "j@test.edu"}
    assert cc.compare(program, SPORT_PAGE, co)["bucket"] == "match"


def test_personal_or_shared_addresses_are_never_output():
    hs = [{"name": "Samantha Harris", "title": "Head Coach", "email": "coach.sam@gmail.com", "section": ""}]
    out = cc.compare({**PROGRAM, "coach_email": None}, SPORT_PAGE, hs)
    assert out["found_email"] is None and "gmail" not in json.dumps(out) and out["bucket"] == "match"
    shared = cc.compare({**PROGRAM, "coach_email": "A01272509@alabama.edu"}, SPORT_PAGE, [{**hs[0], "email": None}])
    assert shared["stored_email"] is None and shared["bucket"] == "match"


def test_untrusted_names_are_cleaned():
    cleaned = cc.clean_text("Samantha <script>Harris</script> 555@x", 80)
    assert "<" not in cleaned and ">" not in cleaned and "@" not in cleaned and cleaned.startswith("Samantha")
    assert cc.clean_text("A" * 200, 80) == "A" * 80


def test_unreadable_vs_not_found():
    class Down:
        def get(self, url):
            raise cc.cr.FetchError("status:503")
    assert cc.check_program(PROGRAM, fetcher=Down())["bucket"] == "unreadable"
    assert cc.check_program({**PROGRAM, "staff_page_url": None, "program_url": None}, fetcher=Down())["bucket"] == "not_found"


def test_apply_patches_both_files_in_their_own_formats(tmp_path):
    data = [{"school": "Test College", "head_coach_name": "Old Coach", "coach_email": "old@test.edu",
             "head_coach_title": "Head Coach", "contacts_verified_on": "2026-10-02"}]
    research = [{"school": "Test College", "head_coach_name": "Old Coach", "coach_email": "old@test.edu",
                 "head_coach_title": "Head Coach", "verified_on": "2026-10-02"}]
    dp, rp = tmp_path / "data.json", tmp_path / "research.json"
    dp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    rp.write_text(json.dumps(research, indent=1))
    apply_mod.apply("test-college", "New Coach", "new@test.edu", "2026-10-05", data_path=dp, research_path=rp)
    d, r = json.loads(dp.read_text()), json.loads(rp.read_text())
    assert d[0]["head_coach_name"] == r[0]["head_coach_name"] == "New Coach"
    assert d[0]["coach_email"] == r[0]["coach_email"] == "new@test.edu"
    assert d[0]["contacts_verified_on"] == r[0]["verified_on"] == "2026-10-05"
    assert rp.read_text() == json.dumps(r, indent=1) and dp.read_text().endswith("\n")
    for bad in (("test-college", "X", "not an email", "2026-10-05"), ("nope", "X", None, "2026-10-05"),
                ("test-college", "X", None, "Oct 5")):
        with pytest.raises(ValueError):
            apply_mod.apply(*bad, data_path=dp, research_path=rp)


def test_real_data_and_research_files_agree_on_coach_fields():
    research_path = apply_mod.RESEARCH
    if not research_path.exists():
        pytest.skip(f"research file not on this machine: {research_path}")
    data = json.loads(apply_mod.DATA.read_text())
    research = {r["school"]: r for r in json.loads(research_path.read_text())}
    for row in data:
        if row["school"] in research:
            other = research[row["school"]]
            assert (row.get("head_coach_name"), row.get("coach_email")) == (other.get("head_coach_name"), other.get("coach_email")), row["school"]
            assert row.get("contacts_verified_on") == other.get("verified_on"), row["school"]


# ---- review fixes ----

def test_spelling_never_hides_an_email_change_and_noted_needs_no_stored_email():
    hs = [{"name": "Samantha Harris", "title": "Head Coach", "email": "new@test.edu", "section": ""}]
    assert cc.compare({**PROGRAM, "head_coach_name": "Samantha Harris-Smith"}, SPORT_PAGE, hs)["bucket"] == "email_changed"
    notes = {**PROGRAM, "contact_notes": "ops: new@test.edu"}
    assert cc.compare(notes, SPORT_PAGE, hs)["bucket"] == "email_changed"


def test_no_address_survives_in_names_or_titles():
    for text in ("Head Coach mailto:ann@gmail.com", "ann@gmail.com", "Head Coach ann@gmail.com"):
        assert "gmail" not in cc.clean_text(text, 120)
    hs = [{"name": "ann@gmail.com Ann Lee", "title": "Head Coach ann@gmail.com", "email": None, "section": ""}]
    assert "gmail" not in json.dumps(cc.compare({**PROGRAM, "head_coach_name": "Ann Lee"}, SPORT_PAGE, hs))


def test_email_from_first_head_row_only():
    co = [{"name": "Dominic Colavito", "title": "Co-Head Coach", "email": None, "section": ""},
          {"name": "Joseph Newman", "title": "Co-Head Coach", "email": "jnewman@test.edu", "section": ""}]
    program = {**PROGRAM, "head_coach_name": "Dominic Colavito; Joseph Newman", "coach_email": "dominic@test.edu"}
    out = cc.compare(program, SPORT_PAGE, co)
    assert out["found_email"] is None and out["bucket"] == "email_not_on_page"


@pytest.mark.parametrize("title,head", [("Head Coach/Assistant Athletic Director", True), ("Head Coach / Associate AD", True),
                                        ("Head Strength Coach", False), ("Head Athletic Trainer / Coach", False),
                                        ("Assistant Head Coach", False), ("Head Women's Flag Football Coach", True)])
def test_combined_titles(title, head):
    assert cc.is_head_title(title) is head


def test_uppercase_mailto_and_thead_tables():
    html = ("<table><thead><tr><th>Name</th><th>Title</th><th>Email</th></tr></thead><tbody>"
            '<tr><td>Ann Lee</td><td>Head Coach</td><td><a href="MAILTO:ann@test.edu">e</a></td></tr></tbody></table>')
    assert heads(html, SPORT_PAGE)[0]["email"] == "ann@test.edu"


def test_apply_rejects_personal_addresses(tmp_path):
    row = {"school": "Test College", "head_coach_name": "A", "coach_email": None, "contacts_verified_on": "2026-10-02",
           "program_url": "https://testhawks.com/x", "staff_page_url": "https://testhawks.com/staff"}
    dp, rp = tmp_path / "d.json", tmp_path / "r.json"
    dp.write_text(json.dumps([row], indent=2) + "\n")
    rp.write_text(json.dumps([{"school": "Test College", "verified_on": "2026-10-02"}], indent=1))
    with pytest.raises(ValueError, match="school's own domain"):
        apply_mod.apply("test-college", "Ann Lee", "ann@gmail.com", "2026-10-05", data_path=dp, research_path=rp)
    assert apply_mod.apply("test-college", "Ann Lee", "ann@testhawks.com", "2026-10-05", data_path=dp, research_path=rp) == "Test College"


def test_coaches_index_fallback():
    class Pages:
        def get(self, url):
            return url, '<a href="/sports/womens-flag-football/coaches/index">Coaches</a>'
    program = {**PROGRAM, "staff_page_url": None}
    assert cc.coach_page(program, Pages()) == "https://testhawks.com/sports/womens-flag-football/coaches/index"


def test_obfuscated_addresses_do_not_survive_in_names():
    for text in ("Ann Lee ann(at)gmail.com", "ann [at] gmail [dot] com", "Ann Lee ann (at) gmail (dot) com"):
        assert "gmail" not in cc.clean_text(text, 80), text
    assert cc.clean_text("Seán O'Brien-Smith", 80) == "Seán O'Brien-Smith"


# ---- 187-run findings (2026-10-05): match gate 85% -> layouts, class years, other sports ----

def test_class_years_do_not_make_spelling_changes():
    hs = [{"name": "Anna Taylor '25", "title": "Interim Head Coach", "email": None, "section": ""}]
    out = cc.compare({**PROGRAM, "head_coach_name": "Anna Taylor '25", "coach_email": None}, SPORT_PAGE, hs)
    assert out["bucket"] == "match" and out["found_names"] == ["Anna Taylor"]


def test_other_sport_head_coach_is_not_the_flag_head_coach():
    assert not cc.is_head_title("Women's Volleyball Head Coach / Flag Football Coordinator / Intramural Director")
    assert not cc.is_head_title("Head Football Coach") and cc.is_head_title("Head Flag Football Coach")


def test_coach_bio_blocks_and_headerless_tables():
    bio = ('<div class="coach-bio"><a href="/sports/flagfball/coaches/cplumb">Chris Plumb</a><span>Head Flag Football Coach</span>'
           '<a href="mailto:cplumb@cottey.edu">cplumb@cottey.edu</a><span>Phone: 417</span></div>'
           '<div class="coach-bio"><a href="/sports/flagfball/coaches/x">Ann Lee</a><span>Defensive Coordinator</span></div>')
    got = heads(bio, "https://cotteycomets.com/sports/flagfball/coaches/index")
    assert [(h["name"], h["title"], h["email"]) for h in got] == [("Chris Plumb", "Head Flag Football Coach", "cplumb@cottey.edu")]
    table = ('<table><tr><th></th><th></th></tr><tbody><tr><td><a href="/sports/flag-football/roster/coaches/jazz-vinson/622">'
             'Jazz Vinson</a></td><td>Head Coach</td><td><a href="mailto:jcvinson@barton.edu">e</a></td></tr></tbody></table>')
    assert [h["name"] for h in heads(table, "https://bartonbulldogs.com/sports/flag-football/coaches")] == ["Jazz Vinson"]


def test_js_directory_falls_back_to_the_sports_coaches_page():
    pages = {"https://testhawks.com/staff-directory": "<div>loading...</div>",
             "https://testhawks.com/sports/womens-flag-football/index": '<a href="/sports/womens-flag-football/coaches">C</a>',
             "https://testhawks.com/sports/womens-flag-football/coaches": COACHES}

    class Pages:
        def get(self, url):
            return url, pages[url]
    program = {**PROGRAM, "staff_page_url": "https://testhawks.com/staff-directory"}
    out = cc.check_program(program, fetcher=Pages())
    assert out["bucket"] == "match" and out["source_url"].endswith("/coaches")


def test_single_coach_page_title_is_the_text_after_the_name():
    html = ('<div><h1>Flag Football</h1><button>Print</button><div class="coach-bio">'
            '<a href="/sports/flagfball/coaches/cplumb">Chris Plumb</a><span>Head Flag Football Coach</span></div></div>')
    assert cc.coach_cards(__import__("bs4").BeautifulSoup(html, "html.parser"))[0]["title"] == "Head Flag Football Coach"


def test_no_text_fallback_a_miss_is_not_found_never_a_wrong_person():
    html = ('<div><a href="/sports/flagfball/coaches/sb">Skeeter Benford</a><span>Assistant Coach</span></div>'
            '<div><span>Bart Stephenson</span><span>Head Coach</span></div>')
    assert heads(html, "https://calhoun.edu/sports/flagfball/coaches/index") == []
    for html in ('<span>Assistant Coach</span><span>Bob Roe</span><span>Head Coach</span><span>Jane Doe</span>',
                 '<p>Bob Roe</p><p>Head Coach</p><p>Jane Doe</p>', '<p>Bob Roe</p><p>Former Head Coach</p>'):
        assert heads(html, "https://x.edu/sports/flagfball/coaches") == []


# ---- fix-check of the parser changes ----

@pytest.mark.parametrize("html", ["<h2>Coaching Staff</h2><h3>Head Coach</h3><p>Bart Stephenson</p>",
                                  "<h1>Flag Football</h1><h2>Head Coach</h2><div>Bart Stephenson</div>",
                                  "<ul><li>Staff Directory</li><li>Head Coach</li><li>Bart Stephenson</li></ul>"])
def test_headings_are_never_names(html):
    assert heads(html, "https://calhoun.edu/sports/flagfball/coaches/index") == []


def test_card_title_before_the_name_and_capped():
    card = ('<h2>Coaching Staff</h2><div class="card"><span>Head Coach</span>'
            '<a href="/sports/flagfball/coaches/bs">Bart Stephenson</a></div>')
    assert [(h["name"], h["title"]) for h in heads(card, "https://x.edu/sports/flagfball/coaches")] == [("Bart Stephenson", "Head Coach")]
    news = '<div><a href="/sports/ff/coaches/cp">Chris Plumb</a><h3>Head Coach Chris Plumb signs 12 recruits for the 2027 class and more' + "x" * 80 + "</h3></div>"
    assert heads(news, "https://x.edu/sports/ff/coaches") == []


@pytest.mark.parametrize("title,head", [("Head Volleyball and Flag Football Coach", True),
                                        # A safe miss (not_found) under the stricter dual-sport rule: "flag" is
                                        # outside the "head ... coach" phrase.
                                        ("Head Coach Women's Beach Volleyball & Flag Football", False),
                                        ("Head Flag-Football Coach", True), ("Head Flag\xa0Football Coach", True),
                                        ("Head Flag  Football Coach", True), ("Head Flag\n  Football Coach", True),
                                        ("Women's Volleyball Head Coach / Flag Football Coordinator", False),
                                        ("Head Coach (Football)", False)])
def test_dual_sport_and_spacing(title, head):
    assert cc.is_head_title(title) is head


def test_failed_sport_fallback_keeps_the_directory_result():
    class Pages:
        def get(self, url):
            if url.endswith("staff-directory"):
                return url, "<div>no table</div>"
            raise cc.cr.FetchError("status:404")
    out = cc.check_program({**PROGRAM, "staff_page_url": "https://testhawks.com/staff-directory"}, fetcher=Pages())
    assert out["bucket"] == "not_found" and out["source_url"].endswith("staff-directory")



@pytest.mark.parametrize("title", ["Head Coach & Assistant AD", "Head Flag Football Coach & Assistant AD", "Head Coach & Athletic Trainer",
                                   "Head Women's Flag Football Coach & Associate Head Volleyball Coach", "Director of Esports & Head Coach"])
def test_ampersand_jobs_count(title):
    assert cc.is_head_title(title)


@pytest.mark.parametrize("title", ["Former Head Coach", "Head Coach Emeritus", "Head Coach (Strength & Conditioning)"])
def test_not_current_heads(title):
    assert not cc.is_head_title(title)


def test_card_link_text_must_be_a_name():
    html = '<div><a href="/sports/flagfball/coaches/staff">Coaching Staff</a><span>Head Coach</span></div>'
    assert heads(html, "https://x.edu/sports/flagfball/coaches") == []
    html = '<div><a href="/sports/flagfball/coaches/jd">Coach Jane Doe</a><span>Head Coach</span></div>'
    assert [h["name"] for h in heads(html, "https://x.edu/sports/flagfball/coaches")] == ["Jane Doe"]


# ---- final fix-check (latent false buckets) ----

@pytest.mark.parametrize("title,head", [("Head Volleyball Coach & Flag Football Coordinator", False),
                                        ("Head Women's Soccer Coach & Flag Football Coach", False),
                                        ("Head Volleyball and Flag Football Coach", True), ("Head Coach & Assistant AD", True)])
def test_flag_must_be_inside_the_head_phrase_when_another_sport_is_named(title, head):
    assert cc.is_head_title(title) is head


def test_email_never_taken_from_a_neighbours_block():
    html = ('<div><div><a href="/sports/flagfball/coaches/jd">Jane Doe</a><span>Head Coach</span></div>'
            '<div><span>Bob Roe</span><span>Assistant Coach</span><a href="mailto:broe@x.edu">e</a></div></div>')
    got = heads(html, "https://x.edu/sports/flagfball/coaches")
    assert [(h["name"], h["email"]) for h in got] == [("Jane Doe", None)]
    own = ('<div><div><a href="/sports/flagfball/coaches/jd">Jane Doe</a><span>Head Coach</span>'
           '<a href="mailto:jdoe@x.edu">e</a></div></div>')
    assert heads(own, "https://x.edu/sports/flagfball/coaches")[0]["email"] == "jdoe@x.edu"


def test_bio_links_are_not_names():
    html = ('<div><a href="/sports/flagfball/coaches/jd">View Bio</a><span>Head Coach</span>'
            '<a href="/sports/flagfball/coaches/jd">Jane Doe</a></div>')
    assert [h["name"] for h in heads(html, "https://x.edu/sports/flagfball/coaches")] == ["Jane Doe"]
