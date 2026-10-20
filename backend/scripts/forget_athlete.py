"""Delete one athlete's SPARQ Recruit rows when a parent asks. Dry run by default.

Joey, 2026-10-20: a parent asks us to delete their child's SPARQ data; Joey runs this once with her GMTM user id.
It finds every SPARQ subject linked to that id (as wave1_report.py does) and counts her rows in each SPARQ table.
It deletes SPARQ's own rows only, never GMTM data (that is a separate request to GMTM). No names, emails or ids
are printed. If a subject is linked to more than one GMTM id, it stops and changes nothing.

    npx -y @railway/cli@latest run --service c6becf80-b58f-4fa0-99c6-45f87f405756 -- \\
      /Users/joey/GMTM-Agent-SDK/backend/.venv/bin/python backend/scripts/forget_athlete.py <gmtm user id>
    ... forget_athlete.py <gmtm user id> --delete   # one transaction; re-counts, prints a receipt to keep

Needs MYSQL_PUBLIC_URL (railway run injects it) and pymysql. No audit table exists, so keep the printed receipt.
Limits: a Clerk-era subject with no link row to her GMTM id cannot be found (pilot athletes all entered via GMTM).
A Clerk account that claimed her combine token (claim_tokens) counts as hers and its SPARQ rows go too.
Not covered (not SPARQ's database): her browser storage, Railway logs, SendGrid, model providers, GMTM media.
"""
import re
import sys
from contextlib import suppress
from datetime import date

# Where a SPARQ subject is linked to a GMTM id: (table, subject column, GMTM id column).
LINKS = [
    ('sparq_entries', 'clerk_id', 'user_id'),
    ('athlete_profiles', 'clerk_id', 'user_id'),
    ('athlete_workspaces', 'clerk_id', 'gmtm_user_id'),
    ('claim_tokens', 'clerk_id', 'user_id'),
]
# Her rows in each SPARQ table, children before parents. {S} = her subjects, {U} = her GMTM id.
TABLES = [
    ('agent_messages', 'conversation_id IN (SELECT id FROM agent_conversations WHERE clerk_id IN {S})'),
    ('agent_conversations', 'clerk_id IN {S}'),
    ('agent_sessions', 'clerk_id IN {S}'),
    ('agent_reports', 'user_id = {U}'),
    ('artifact_actions', 'artifact_id IN (SELECT id FROM artifacts WHERE clerk_id IN {S})'),
    ('artifacts', 'clerk_id IN {S}'),
    ('college_targets', 'sparq_profile_id IN (SELECT id FROM sparq_profiles WHERE clerk_id IN {S})'),
    ('outreach_log', 'sparq_profile_id IN (SELECT id FROM sparq_profiles WHERE clerk_id IN {S})'),
    ('sparq_profiles', 'clerk_id IN {S}'),
    ('athlete_links', 'user_id = {U}'),
    ('sparq_parent_notices', 'clerk_id IN {S}'),
    ('sparq_parent_contact', 'clerk_id IN {S}'),
    ('sparq_college_lists', 'clerk_id IN {S}'),
    ('sparq_saved_colleges', 'clerk_id IN {S}'),
    ('sparq_sent_emails', 'clerk_id IN {S}'),
    ('sparq_card_clips', 'clerk_id IN {S}'),
    ('sparq_sessions', 'clerk_id IN {S}'),
    ('claim_tokens', 'user_id = {U} OR clerk_id IN {S}'),
    ('athlete_workspaces', 'gmtm_user_id = {U} OR clerk_id IN {S}'),
    ('sparq_entry_refusals', 'user_id = {U}'),
    ('sparq_entries', 'user_id = {U} OR clerk_id IN {S}'),
    ('athlete_profiles', 'user_id = {U} OR clerk_id IN {S}'),
]


class SharedSubject(Exception):
    """A subject is linked to another GMTM id too. Nothing was changed."""


class WrongTarget(Exception):
    """MYSQL_PUBLIC_URL is not the SPARQ Railway database. Nothing was read or changed."""


class RecountFailed(Exception):
    """The delete was committed, but the re-count after it failed."""


def subject(value):
    return value if isinstance(value, bytes) else bytes(value) if isinstance(value, (bytearray, memoryview)) else value.encode()


def where(clause, subjects, uid):
    """The clause with placeholders, and its arguments in order."""
    args = []

    def fill(m):
        if m.group() == '{U}':
            args.append(uid)
            return '%s'
        args.extend(subjects)
        return '(' + (', '.join(['%s'] * len(subjects)) or 'NULL') + ')'  # IN (NULL) matches nothing
    return re.sub(r'\{[SU]\}', fill, clause), args


def present_tables(c):
    c.execute('SELECT TABLE_NAME AS name FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()')
    return {row['name'] for row in c.fetchall()}


def resolve(c, uid, present):
    """Every subject linked to her GMTM id. Raises SharedSubject if one is linked to another id."""
    links = [link for link in LINKS if link[0] in present]
    subjects = set()
    for table, col, id_col in links:
        c.execute(f'SELECT {col} AS s FROM {table} WHERE {id_col} = %s AND {col} IS NOT NULL', (uid,))
        subjects |= {subject(row['s']) for row in c.fetchall()}
    subjects = sorted(subjects)
    for table, col, id_col in links:
        sql, args = where(f'{col} IN {{S}}', subjects, uid)
        c.execute(f'SELECT DISTINCT {id_col} AS u FROM {table} WHERE {sql}', args)
        if any(int(row['u']) != uid for row in c.fetchall()):
            raise SharedSubject()
    return subjects


def usable(present):
    """The TABLES entries whose tables all exist in this database."""
    return [(t, clause) for t, clause in TABLES if {t, *re.findall(r'FROM (\w+)', clause)} <= present]


def counts(c, subjects, uid, plan):
    out = {}
    for table, clause in plan:
        sql, args = where(clause, subjects, uid)
        c.execute(f'SELECT COUNT(*) AS n FROM {table} WHERE {sql}', args)
        out[table] = int(c.fetchone()['n'])
    return out


def run(conn, uid, delete=False):
    """Returns (counts before, counts after the commit or None, tables not present, subject count)."""
    with conn.cursor() as c:
        if not delete:
            c.execute('SET SESSION TRANSACTION READ ONLY')
        conn.begin()
        try:
            present = present_tables(c)
            plan = usable(present)
            subjects = resolve(c, uid, present)
            before = counts(c, subjects, uid, plan)
            if not delete:
                conn.rollback()
                return before, None, missing(plan), len(subjects)
            for table, clause in plan:
                sql, args = where(clause, subjects, uid)
                c.execute(f'DELETE FROM {table} WHERE {sql}', args)
            if any(counts(c, subjects, uid, plan).values()):
                raise RuntimeError('rows remain after the delete')
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        try:
            fresh = resolve(c, uid, present)  # a new read, after the commit: a sign-in can add a subject
            after = counts(c, fresh, uid, plan)
            conn.rollback()
        except Exception as error:
            raise RecountFailed() from error
    return before, after, missing(plan), len(subjects)


def missing(plan):
    used = {t for t, _ in plan}
    return sorted({t for t, _ in TABLES} - used)


def report(before, after, absent, n_subjects):
    lines = [f'SPARQ subjects linked to this GMTM id: {n_subjects}']
    lines += [f'  {t:<22} {n:>6}' + ('' if after is None else f'  -> {after[t]}') for t, n in before.items()]
    lines.append(f'Total: {sum(before.values())} rows in {sum(1 for n in before.values() if n)} tables.')
    if absent:
        lines.append(f'Not in this database (skipped): {", ".join(absent)}')
    if after is None:
        lines.append('DRY RUN: nothing was changed. Run again with --delete to delete these rows.')
    elif any(after.values()):
        lines.append('Deleted and committed, but new rows appeared after the commit (she may be signed in). Run --delete again.')
    else:
        kept = ', '.join(f'{t} {n}' for t, n in before.items() if n) or 'none'
        lines.append('Deleted. Every count is now 0.')
        lines.append(f'Receipt (keep this): SPARQ Recruit data delete on {date.today()}: {sum(before.values())} rows ({kept}).')
    return '\n'.join(lines)


def connect():
    import os
    from urllib.parse import unquote, urlparse
    import pymysql
    u = urlparse(os.environ['MYSQL_PUBLIC_URL'])
    # Only the SPARQ Railway database (measured 2026-10-20: a *.proxy.rlwy.net host, database railway). Never GMTM.
    if not (u.hostname or '').endswith('.proxy.rlwy.net') or u.path.lstrip('/') != 'railway':
        raise WrongTarget()
    return pymysql.connect(host=u.hostname, port=u.port or 3306, user=unquote(u.username), password=unquote(u.password),
                           database=u.path.lstrip('/'), cursorclass=pymysql.cursors.DictCursor, connect_timeout=10,
                           read_timeout=60, write_timeout=60, autocommit=False)


def main(argv):
    flags = [a for a in argv if a.startswith('--')]
    ids = [a for a in argv if not a.startswith('--')]
    if len(ids) != 1 or not ids[0].isascii() or not ids[0].isdecimal() or int(ids[0]) <= 0 or set(flags) - {'--delete'}:
        sys.exit(__doc__)
    uid, delete = int(ids[0]), '--delete' in flags
    try:
        conn = connect()
        try:
            result = run(conn, uid, delete)
        finally:
            with suppress(Exception):
                conn.close()
    except WrongTarget:
        sys.exit('Stopped: MYSQL_PUBLIC_URL is not the SPARQ Railway database. Nothing was read or changed.')
    except SharedSubject:
        sys.exit('Stopped: a SPARQ subject for this GMTM id is linked to another GMTM id too. Nothing was changed. Check by hand.')
    except RecountFailed:
        sys.exit('Deleted and committed, but the re-count failed. Run the dry run again to check every count is 0.')
    except Exception as error:  # no host, user, password, address or id in the output
        code = error.args[0] if error.args and isinstance(error.args[0], int) else ''
        done = ' It should have rolled back. Run the dry run again to check.' if delete else ''
        sys.exit(f'The database step failed ({type(error).__name__} {code}).{done}')
    print(f'SPARQ Recruit data delete, {"DELETE" if delete else "DRY RUN"}, {date.today()}')
    print(report(*result))


if __name__ == '__main__':
    main(sys.argv[1:])
