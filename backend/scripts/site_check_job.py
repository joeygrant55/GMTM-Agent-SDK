"""Daily signed-out site checks. Dry run (print only) unless --apply, which also writes sparq_site_checks.
Always exits 0 (a cron platform must not restart it); failures are rows with ok=0 and a JSON log line.

Usage: python backend/scripts/site_check_job.py [--apply]
"""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_check  # noqa: E402
from college_research_job import agent_run, now_utc  # noqa: E402


def run(apply: bool, run_db=agent_run, session=None, log=print) -> list:
    run_id = now_utc().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    import requests
    session = session or requests.Session()
    results = [site_check.run_check(c, session) for c in site_check.CHECKS]
    if apply:
        results.append(site_check.research_freshness(run_db))
    for r in results:
        log(json.dumps({"run_id": run_id, **r}))
    if apply:
        t = now_utc()
        try:
            run_db(lambda c: c.executemany(
                "INSERT INTO sparq_site_checks (run_id, check_name, ok, status_code, ms, detail, checked_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [(run_id, r["check_name"], int(r["ok"]), r["status_code"], r["ms"], r["detail"], t) for r in results]), write=True)
        except Exception as error:
            log(json.dumps({"run_id": run_id, "store_error": type(error).__name__}))
    failed = [r["check_name"] for r in results if not r["ok"]]
    log(json.dumps({"run_id": run_id, "status": "done", "checks": len(results), "failed": failed}))
    return results


def main(argv):
    if "--cap" in argv:  # the shared image's default CMD passes the research job's cap; not used here
        i = argv.index("--cap")
        argv = argv[:i] + argv[i + 2:]
    unknown = [a for a in argv if a != "--apply"]
    if unknown:
        print(json.dumps({"status": "failed", "error": f"unknown argument(s): {unknown}"}))
        sys.exit(0)
    run("--apply" in argv)
    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
