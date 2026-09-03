"""Read-only smoke test: build combine results for every athlete in the given events.

Usage: DB_HOST=... DB_USER=... DB_PASSWORD=... python scripts/smoke_combine_results.py 1317 1318
Exit 1 if any athlete with drill data returns zero results or any rank exceeds its pool.
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pymysql
from combine_results import get_combine_results, format_for_prompt


def connect():
    return pymysql.connect(host=os.environ["DB_HOST"], user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
                           database="gmtm", port=int(os.environ.get("DB_PORT", 3306)), cursorclass=pymysql.cursors.DictCursor)


def main(event_ids):
    ph = ",".join(["%s"] * len(event_ids))
    db = connect()
    with db.cursor() as c:
        c.execute(f"""SELECT DISTINCT user_id FROM metrics WHERE event_id IN ({ph}) AND title NOT IN ('Weight','Height')
                      UNION SELECT DISTINCT s.user_id FROM event_task_submissions s JOIN event_tasks t ON t.task_id=s.task_id
                      WHERE t.event_id IN ({ph}) AND t.type=2""", (*event_ids, *event_ids))
        ids = [r["user_id"] for r in c.fetchall()]
    db.close()
    t0 = time.time(); failures = 0
    for uid in ids:
        res = get_combine_results(uid, connect)
        bad = [r for r in res if r["rank_in_event"] and r["event_pool_size"] and r["rank_in_event"] > r["event_pool_size"]]
        status = "ok" if res and not bad else "FAIL"
        if status == "FAIL":
            failures += 1
        print(f"{status:4} user {uid}: {len(res)} results, {len(bad)} rank violations")
    print(f"\n{len(ids) - failures}/{len(ids)} athletes ok in {time.time() - t0:.1f}s")
    if ids:
        print(format_for_prompt(get_combine_results(ids[0], connect)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main([int(a) for a in sys.argv[1:]] or [1317, 1318]))
