"""Weekly college research job: all programs, fixed order, into the Agent DB. Dry run unless --apply.

Spec: docs/specs/college-research-agent-2026-10-02.md. Program-level public facts only; it never reads an athlete
table. Run as a Railway cron job (or by hand); the web app never imports this file and there is no HTTP trigger.

Usage: ANTHROPIC_API_KEY=... python backend/scripts/college_research_job.py [--apply] [--cap 3.00] [--only <id> ...]
Without --apply nothing is written to the database; model calls are still made and billed.
Cap: measured full run 2026-10-02 = $1.23 for 187 programs, so the $3 default covers every program with headroom.
"""
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import college_programs  # noqa: E402
import college_research  # noqa: E402

STALE_LOCK = timedelta(hours=6)


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, like every other SPARQ table


class Store:
    """Agent DB writes for the job. Each call opens and closes its own connection."""

    def __init__(self, run=None):
        self.run = run or college_programs.MySQLStore()._run

    def take_lock(self, run_id: str) -> bool:
        """Expire 'running' rows older than 6 h and insert ours (committed), then, in a new transaction that sees
        every committed row, keep ours only if it is the oldest running row. A loser deletes its own row."""
        t = now_utc()

        def claim(c):
            c.execute("UPDATE sparq_research_runs SET status = 'failed', finished_at = %s "
                      "WHERE status = 'running' AND started_at < %s", (t, t - STALE_LOCK))
            c.execute("INSERT INTO sparq_research_runs (run_id, started_at, status) VALUES (%s, %s, 'running')", (run_id, t))
        self.run(claim, write=True)

        def check(c):
            c.execute("SELECT run_id FROM sparq_research_runs WHERE status = 'running' ORDER BY started_at, run_id LIMIT 1")
            first = c.fetchone()
            if first and first["run_id"] == run_id:
                return True
            c.execute("DELETE FROM sparq_research_runs WHERE run_id = %s", (run_id,))
            return False
        return self.run(check, write=True)

    def save(self, run_id: str, result: dict) -> None:
        t = now_utc()
        roster = result.get("roster") if result.get("roster_state") == "found" else None
        # Camps are replaced only when the program page was read this run (a down site keeps last week's camps).
        # A camps-page fetch error also keeps last week's camps, unless this run still found camps elsewhere.
        notes = result.get("notes", [])
        read_program_page = bool(result.get("pages")) and not any(n.startswith("program_page") for n in notes)
        camps_page_failed = any(n.startswith("camps_page:") and n != "camps_page:none" for n in notes)
        found = result.get("camps", [])
        camps = found if read_program_page and (found or not camps_page_failed) else None
        notes = (result.get("notes", []) + result.get("drops", []))[:40]
        self.run(lambda c: c.execute(
            "INSERT INTO sparq_college_research (program_id, roster, roster_checked_at, camps, camps_checked_at, "
            "last_run_id, last_notes, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "roster = IF(%s, VALUES(roster), roster), roster_checked_at = IF(%s, VALUES(roster_checked_at), roster_checked_at), "
            "camps = IF(%s, VALUES(camps), camps), camps_checked_at = IF(%s, VALUES(camps_checked_at), camps_checked_at), "
            "last_run_id = VALUES(last_run_id), last_notes = VALUES(last_notes), updated_at = VALUES(updated_at)",
            (result["program_id"], json.dumps(roster) if roster else None, t if roster else None,
             json.dumps(camps) if camps is not None else None, t if camps is not None else None,
             run_id, json.dumps(notes), t,
             roster is not None, roster is not None, camps is not None, camps is not None)), write=True)

    def progress(self, run_id: str, result: dict) -> None:
        usage = result.get("usage", {})
        self.run(lambda c: c.execute(
            "UPDATE sparq_research_runs SET programs_done = programs_done + 1, items_dropped = items_dropped + %s, "
            "tokens_in = tokens_in + %s, tokens_out = tokens_out + %s, cost_usd = cost_usd + %s WHERE run_id = %s",
            (len(result.get("drops", [])), usage.get("input_tokens", 0), usage.get("output_tokens", 0),
             result.get("cost_usd", 0.0), run_id)), write=True)

    def finish(self, run_id: str, status: str) -> None:
        self.run(lambda c: c.execute("UPDATE sparq_research_runs SET status = %s, finished_at = %s WHERE run_id = %s",
                                     (status, now_utc(), run_id)), write=True)


def run_job(program_list, extract, store=None, cap=3.0, log=print) -> dict:
    """Fixed order over the given programs. Stops at the cap (status 'stopped') or at the first run-stopping
    failure (status 'failed'). store=None is a dry run: nothing is written."""
    run_id = now_utc().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    if store and not store.take_lock(run_id):
        log(json.dumps({"run_id": run_id, "status": "locked"}))
        return {"run_id": run_id, "status": "locked", "spent_usd": 0.0, "programs": 0}
    spent, done, status = 0.0, 0, "failed"  # anything that escapes (even Ctrl-C) is recorded as failed
    try:
        for p in sorted(program_list, key=lambda p: p["id"]):
            if spent >= cap:
                status = "stopped"
                break
            result = college_research.research_program(p, extract)
            spent += result.get("cost_usd", 0.0)
            done += 1
            if store:
                store.save(run_id, result)
                store.progress(run_id, result)
            log(json.dumps(result))
        else:
            status = "done"
    except Exception as error:  # model API errors, non-JSON, envelope shape, DB errors: stop the run and report
        log(json.dumps({"run_id": run_id, "status": "failed", "error": type(error).__name__, "after": done}))
    finally:
        if store:
            try:
                store.finish(run_id, status)
            except Exception as error:  # never hide the original failure behind a bookkeeping error
                log(json.dumps({"run_id": run_id, "finish_error": type(error).__name__}))
    summary = {"run_id": run_id, "status": status, "spent_usd": round(spent, 4), "cap_usd": cap, "programs": done}
    log(json.dumps(summary))
    return summary


def main(argv):
    from college_research_probe import extract  # the same single model call as the probe
    apply = "--apply" in argv
    argv = [a for a in argv if a != "--apply"]
    unknown = [a for a in argv if a.startswith("--") and a not in ("--cap", "--only")]
    if unknown:
        sys.exit(f"unknown option(s): {unknown}")  # before any paid call
    cap = 3.0
    if "--cap" in argv:
        i = argv.index("--cap")
        try:
            cap, argv = float(argv[i + 1]), argv[:i] + argv[i + 2:]
        except (IndexError, ValueError):
            sys.exit("--cap needs a dollar amount, e.g. --cap 3.00")
        if not 0 < cap <= 50:  # also rejects nan and inf, which would disable the cap
            sys.exit("--cap must be a dollar amount from 0 to 50")
    program_list = college_programs.programs()
    if argv and argv[0] != "--only":
        sys.exit(f"unexpected argument(s): {argv}")  # e.g. '-apply' or 'apply': stop before any paid call
    if argv[:1] == ["--only"]:
        wanted = set(argv[1:])
        program_list = [p for p in program_list if p["id"] in wanted]
        if len(program_list) != len(wanted):
            sys.exit("unknown program ids")
    summary = run_job(program_list, extract, store=Store() if apply else None, cap=cap)
    sys.exit(0 if summary["status"] in ("done", "stopped") else 1)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main(sys.argv[1:])
