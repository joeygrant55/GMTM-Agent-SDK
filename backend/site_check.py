"""Daily signed-out checks of GMTM.com and SPARQ (roadmap idea 6, part 1). HTTP GETs of public URLs plus two empty
POSTs that must be refused (they stop before any Redis read/write: Fable review 2026-10-07); no redirect following,
no sign-in, no model call. Results go to sparq_site_checks; Fable reads them each session
(Joey 2026-10-06: "Fable checks daily"). Signed-in flows need a dedicated test account (not built).

Every expectation below was measured on 2026-10-06.
"""
import json
import re
import time
from dataclasses import dataclass
from typing import Optional

import requests
from urllib.parse import urljoin

UA = "SPARQ-site-check/0.1 (+https://sparq.gmtm.com; joey@gmtm.com)"
TIMEOUT = (5, 20)
SLOW_MS = 5000

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS sparq_site_checks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    check_name VARCHAR(80) NOT NULL,
    ok TINYINT(1) NOT NULL,
    status_code INT NULL,
    ms INT NULL,
    detail VARCHAR(300) NULL,
    checked_at DATETIME(6) NOT NULL,
    KEY site_checks_name_time (check_name, checked_at)
)""",
)


@dataclass(frozen=True)
class Check:
    name: str
    url: str
    status: int
    location: Optional[str] = None      # regex the Location header must match (redirect checks)
    contains: Optional[str] = None      # text the body must contain
    content_type: Optional[str] = None  # prefix the Content-Type must start with
    json_true: Optional[str] = None     # a JSON key that must be true
    method: str = "GET"                 # POST checks send an empty JSON body (a refusal is the expected answer)


CHECKS = (
    Check("gmtm_home", "https://gmtm.com/", 200, contains="<title>GMTM | ", content_type="text/html"),
    Check("gmtm_sign_in", "https://gmtm.com/sign-in", 200, contains="<title>GMTM | ", content_type="text/html"),
    Check("gmtm_athlete_page", "https://gmtm.com/athletes/2", 307, location=r"^https://gmtm\.com/athletes/2/"),
    Check("gmtm_api_health", "https://api.gmtm.com/health", 200, contains='"message":"Ok"', content_type="application/json"),
    Check("gmtm_cdn_media", "https://cdn.gmtm.com/assets/site/hero-houston.jpg", 200, content_type="image/jpeg"),  # site asset
    Check("sparq_root", "https://sparq.gmtm.com/", 307, location=r"^https://sparq\.gmtm\.com/home$"),
    Check("sparq_enter", "https://sparq.gmtm.com/enter", 302, location=r"^https://gmtm\.com/sparq/authorize\?state="),
    Check("sparq_logo", "https://sparq.gmtm.com/sparq-wordmark.png", 200, content_type="image/png"),
    Check("sparq_session_signed_out", "https://sparq.gmtm.com/api/sparq/session", 401),
    Check("sparq_backend_health", "https://sparq-junior-production.up.railway.app/health", 200,
          content_type="application/json", json_true="configuration_ready"),
    # Signed-in paths, checked from outside: each must refuse a visitor cleanly (not a 5xx). GMTM sign-in is an
    # emailed one-time code (resources/email/email.resolver.js), so a real daily sign-in would need inbox access.
    Check("gmtm_sparq_handoff_refuses", "https://api.gmtm.com/v2/sparq/handoff", 401, contains='"unauthenticated"',
          content_type="application/json", method="POST"),
    Check("gmtm_sparq_redeem_refuses", "https://api.gmtm.com/v2/sparq/redeem", 403, contains='"forbidden"',
          content_type="application/json", method="POST"),
    Check("gmtm_sparq_authorize_rejects_no_state", "https://gmtm.com/sparq/authorize", 400, content_type="text/html"),
    Check("sparq_home_signed_out", "https://sparq.gmtm.com/home", 307, location=r"^https://gmtm\.com/$"),
    Check("sparq_proxy_signed_out", "https://sparq.gmtm.com/api/sparq/proxy/api/athlete/evidence", 401,
          content_type="application/json", contains="session ended"),
)


def run_check(check: Check, session=None) -> dict:
    """One probe, retried once when it fails or is slow (a cold start or deploy window is not an outage)."""
    first = _probe(check, session)
    return first if first["ok"] else _probe(check, session)


def _probe(check: Check, session=None) -> dict:
    session = session or requests.Session()
    started = time.monotonic()
    try:
        if check.method == "POST":
            r = session.post(check.url, json={}, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=False)
        else:
            r = session.get(check.url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=False)
    except requests.RequestException as error:
        return {"check_name": check.name, "ok": False, "status_code": None, "ms": None, "detail": type(error).__name__}
    ms = int((time.monotonic() - started) * 1000)
    problems = []
    if r.status_code != check.status:
        problems.append(f"status {r.status_code} != {check.status}")
    if check.location and not re.match(check.location, urljoin(check.url, r.headers.get("location", ""))):  # often relative
        problems.append("location")
    if check.content_type and not r.headers.get("content-type", "").startswith(check.content_type):
        problems.append(f"content-type {r.headers.get('content-type', '')[:40]}")
    body = r.text[:200_000] if (check.contains or check.json_true) else ""
    if check.contains and check.contains not in body:
        problems.append("text missing")
    if check.json_true:
        try:
            if json.loads(body).get(check.json_true) is not True:
                problems.append(f"{check.json_true} not true")
        except ValueError:
            problems.append("not json")
    if ms > SLOW_MS:
        problems.append(f"slow {ms} ms")
    return {"check_name": check.name, "ok": not problems, "status_code": r.status_code, "ms": ms,
            "detail": "; ".join(problems)[:300] or None}


def research_freshness(run) -> dict:
    """The weekly research job must have a 'done' run in the last 8 days (it runs Mondays)."""
    def read(c):
        c.execute("SELECT MAX(finished_at) AS last FROM sparq_research_runs WHERE status = 'done'")
        return (c.fetchone() or {}).get("last")
    try:
        last = run(read)
    except Exception as error:
        return {"check_name": "research_job_fresh", "ok": False, "status_code": None, "ms": None, "detail": type(error).__name__}
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ok = last is not None and now - last <= timedelta(days=8)
    return {"check_name": "research_job_fresh", "ok": ok, "status_code": None, "ms": None,
            "detail": None if ok else f"last done run {last}"}
