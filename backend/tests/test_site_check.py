import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import site_check as sc

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import site_check_job as job  # noqa: E402


class Resp:
    def __init__(self, status, body="", headers=None):
        self.status_code, self.text, self.headers = status, body, headers or {}


class Session:
    def __init__(self, responses):
        self.responses, self.calls = responses, []

    def post(self, url, **kw):
        assert kw["json"] == {}
        self.posts = getattr(self, "posts", []) + [url]
        return self.get(url, **kw)

    def get(self, url, **kw):
        assert kw["allow_redirects"] is False and "User-Agent" in kw["headers"]
        self.calls.append(url)
        r = self.responses.get(url)
        if isinstance(r, Exception):
            raise r
        return r or Resp(404)


def good_responses():
    out = {}
    for c in sc.CHECKS:
        headers = {"content-type": (c.content_type or "text/html") + "; charset=utf-8"}
        if c.location:
            headers["location"] = {"gmtm_athlete_page": "/athletes/2/joey-grant/feed", "sparq_root": "/home",
                                   "sparq_enter": "https://gmtm.com/sparq/authorize?state=x",
                                   "sparq_home_signed_out": "https://gmtm.com/"}[c.name]
        body = (c.contains or "") + (json.dumps({c.json_true: True}) if c.json_true else "")
        out[c.url] = Resp(c.status, body, headers)
    return out


def test_all_checks_pass_on_the_measured_responses():
    results = [sc.run_check(c, Session(good_responses())) for c in sc.CHECKS]
    assert all(r["ok"] for r in results), results


def test_each_failure_kind_is_reported():
    r = good_responses()
    c = {c.name: c for c in sc.CHECKS}
    s = Session({**r, c["gmtm_home"].url: Resp(503, "", {"content-type": "text/html"})})
    assert sc.run_check(c["gmtm_home"], s)["detail"].startswith("status 503")
    s = Session({**r, c["sparq_root"].url: Resp(307, "", {"location": "https://evil.example/"})})
    assert sc.run_check(c["sparq_root"], s)["detail"] == "location"
    s = Session({**r, c["sparq_backend_health"].url: Resp(200, '{"configuration_ready": false}', {"content-type": "application/json"})})
    assert "configuration_ready not true" in sc.run_check(c["sparq_backend_health"], s)["detail"]
    s = Session({**r, c["gmtm_home"].url: Resp(200, "<title>Maintenance</title>", {"content-type": "text/html"})})
    assert sc.run_check(c["gmtm_home"], s)["detail"] == "text missing"
    import requests
    s = Session({**r, c["gmtm_api_health"].url: requests.exceptions.ConnectTimeout()})
    assert sc.run_check(c["gmtm_api_health"], s) == {"check_name": "gmtm_api_health", "ok": False, "status_code": None,
                                                     "ms": None, "detail": "ConnectTimeout"}


def test_research_freshness():
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    class C:
        def __init__(self, last): self.last = last
        def execute(self, sql, args=()): assert "status = 'done'" in sql
        def fetchone(self): return {"last": self.last}
    assert sc.research_freshness(lambda fn: fn(C(now - timedelta(days=2))))["ok"]
    assert not sc.research_freshness(lambda fn: fn(C(now - timedelta(days=9))))["ok"]
    assert not sc.research_freshness(lambda fn: fn(C(None)))["ok"]


def test_job_writes_rows_only_with_apply_and_never_raises(monkeypatch):
    writes = []

    def run_db(fn, write=False):
        class C:
            def execute(self, sql, args=()): pass
            def fetchone(self): return {"last": datetime.now(timezone.utc).replace(tzinfo=None)}
            def executemany(self, sql, rows): writes.append(rows)
        return fn(C())
    logs = []
    job.run(False, run_db=run_db, session=Session(good_responses()), log=logs.append)
    assert writes == [] and json.loads(logs[-1])["failed"] == []
    job.run(True, run_db=run_db, session=Session(good_responses()), log=logs.append)
    assert len(writes[0]) == len(sc.CHECKS) + 1 and all(row[2] == 1 for row in writes[0])

    def broken(fn, write=False):
        raise OSError("db down")
    job.run(True, run_db=broken, session=Session(good_responses()), log=logs.append)
    assert any("store_error" in line for line in logs)


@pytest.mark.parametrize("argv,called", [(["--apply", "--cap", "3.00"], [True]), (["--apply"], [True]), ([], [False]),
                                         (["--bogus"], []), (["--apply", "--cap"], [True])])
def test_main_always_exits_zero_and_strips_the_shared_cap(monkeypatch, argv, called):
    calls = []
    monkeypatch.setattr(job, "run", lambda apply: calls.append(apply) or [])
    with pytest.raises(SystemExit) as stop:
        job.main(argv)
    assert stop.value.code == 0 and calls == called


def test_one_retry_on_failure():
    c = sc.CHECKS[0]

    class Flaky:
        def __init__(self): self.n = 0
        def get(self, url, **kw):
            self.n += 1
            return Resp(503) if self.n == 1 else Resp(200, c.contains, {"content-type": c.content_type})
    assert sc.run_check(c, Flaky())["ok"]


@pytest.mark.parametrize("value", ["site-check", "sitecheck", "SITE_CHECK", ""])
def test_a_mistyped_job_name_never_runs_the_paid_research_job(value):
    import subprocess
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_job.py"
    env = {"PATH": "/usr/bin:/bin", "SPARQ_JOB": value}
    out = subprocess.run([sys.executable, str(script), "--apply", "--cap", "3.00"], env=env, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and "unknown SPARQ_JOB" in out.stdout


def test_only_public_signed_out_urls():
    for c in sc.CHECKS:
        assert c.url.startswith("https://") and "token" not in c.url and "session=" not in c.url



def test_post_checks_send_an_empty_body_and_expect_a_refusal():
    posts = [c for c in sc.CHECKS if c.method == "POST"]
    assert {c.name for c in posts} == {"gmtm_sparq_handoff_refuses", "gmtm_sparq_redeem_refuses"}
    assert all(c.status in (401, 403) for c in posts)
    c = posts[0]
    s = Session({c.url: Resp(500, "boom", {"content-type": "application/json"})})
    assert not sc.run_check(c, s)["ok"]


def test_post_checks_really_post():
    s = Session(good_responses())
    for c in sc.CHECKS:
        sc.run_check(c, s)
    assert sorted(s.posts) == sorted(c.url for c in sc.CHECKS if c.method == "POST")
