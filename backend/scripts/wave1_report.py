"""Wave 1 step report: how far each invited athlete got in SPARQ Recruit. Read only.

Joey, 2026-10-16: see what works from our own step data, not a screen recorder. The ids file holds the
invited GMTM user ids (a JSON list of ids or of {"user_id": ...}); keep it outside the repo, never commit it.
Output: the count at each step and one row per athlete as A1..An (file order). No names, emails or ids.

    cd /Users/joey/sparq-demo/deploy-8e3178b && npx -y @railway/cli@latest run \\
      --service c6becf80-b58f-4fa0-99c6-45f87f405756 -- \\
      /Users/joey/GMTM-Agent-SDK/backend/.venv/bin/python backend/scripts/wave1_report.py <ids file>
    python3 backend/scripts/wave1_report.py --demo   # self-check, no database

Needs MYSQL_PUBLIC_URL (railway run injects it) and pymysql. Database times are UTC; days are US Eastern.
"""
import json
import sys
from datetime import date, datetime, timezone
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo('America/New_York')
STEPS = [  # (key, label), in the order an athlete meets them
    ('signed_in', 'Signed in'),
    ('notice', 'Parent notice accepted'),
    ('list', 'College list built'),
    ('card', 'Picked My card clips'),
    ('school_page', 'Opened a school page'),
    ('saved', 'Saved a college'),
    ('drafted', 'Drafted a coach email'),
    ('email_opened', 'Opened her email or copied'),
    ('sent', 'Marked an email sent'),
]
# One refusal word covers age outside 13-17, no birth date on file and no junior event (junior_eligibility.py).
REFUSED = 'Stopped at sign-in (age or event check)'


def read_ids(path):
    try:
        with open(path) as f:
            ids = [int(r['user_id'] if isinstance(r, dict) else r) for r in json.load(f)]
    except (OSError, ValueError, TypeError, KeyError):
        sys.exit('The ids file could not be read, or it has a bad entry.')
    if not ids:
        sys.exit('The ids file is empty.')
    if len(set(ids)) != len(ids) or any(i <= 0 for i in ids):
        sys.exit('The ids file has a repeated or bad id.')
    return ids


def eastern_day(at):
    return at.replace(tzinfo=timezone.utc).astimezone(EASTERN).date()


def athlete_rows(ids, data):
    """data: per GMTM id, the facts read from the database. Returns one row per athlete, file order."""
    out = []
    for n, uid in enumerate(ids, 1):
        d = data.get(uid, {})
        done = {
            'signed_in': d.get('entries', 0) > 0, 'notice': bool(d.get('notice')), 'list': bool(d.get('list')),
            'saved': d.get('saved', 0) > 0, 'drafted': d.get('drafted', 0) > 0, 'sent': d.get('sent', 0) > 0,
            'card': d.get('card', 0) > 0, 'school_page': d.get('school_page', 0) > 0, 'email_opened': d.get('email_opened', 0) > 0,
        }
        # A visit inside one 24 h session writes no new entry, so a day counts when she signed in or did a step.
        # Step marks store an Eastern date already; database times are UTC datetimes.
        days = {at if type(at) is date else eastern_day(at) for at in d.get('active', []) if at}
        out.append({'label': f'A{n}', 'done': done, 'refused': d.get('refused', []), 'days': len(days),
                    'last': max(days) if days else None, 'saved': d.get('saved', 0), 'drafted': d.get('drafted', 0), 'sent': d.get('sent', 0)})
    return out


def report(rows):
    lines = [f'Invited: {len(rows)}']
    for key, label in STEPS:
        lines.append(f'{label}: {sum(r["done"][key] for r in rows)}')
    lines.append(f'Active on 2 or more days: {sum(r["days"] >= 2 for r in rows)}')
    refused = [r for r in rows if r['refused'] and not r['done']['signed_in']]
    lines.append(f'{REFUSED}: {len(refused)}')
    lines.append('')
    lines.append('Athlete  Furthest step               Saved  Drafts  Sent  Days  Last active')
    for r in rows:
        furthest = next((label for key, label in reversed(STEPS) if r['done'][key]), 'Stopped at sign-in' if r['refused'] else 'Not signed in')
        lines.append(f'{r["label"]:<8} {furthest:<27} {r["saved"]:>5} {r["drafted"]:>7} {r["sent"]:>5} {r["days"]:>5}  {r["last"] or "-"}')
    return '\n'.join(lines)


def read_data(ids):
    import os
    import pymysql
    u = urlparse(os.environ['MYSQL_PUBLIC_URL'])
    conn = pymysql.connect(host=u.hostname, port=u.port or 3306, user=unquote(u.username), password=unquote(u.password),
                           database=u.path.lstrip('/'), cursorclass=pymysql.cursors.DictCursor, connect_timeout=10, read_timeout=30)
    data = {i: {'entries': 0, 'active': [], 'refused': []} for i in ids}
    marks = ', '.join(['%s'] * len(ids))
    owners, users = {}, {}  # subject -> first GMTM id; subject -> every GMTM id that links to it

    def own(subject, uid):
        owners.setdefault(subject, uid)
        users.setdefault(subject, set()).add(uid)

    try:
        with conn.cursor() as c:
            c.execute('SET SESSION TRANSACTION READ ONLY')
            c.execute('START TRANSACTION READ ONLY')
            # Every SPARQ subject an invited athlete used: entries since October, plus the older profile link.
            c.execute(f'SELECT user_id, clerk_id, entered_at FROM sparq_entries WHERE user_id IN ({marks})', ids)
            for row in c.fetchall():
                data[row['user_id']]['entries'] += 1
                data[row['user_id']]['active'].append(row['entered_at'])
                own(bytes(row['clerk_id']), row['user_id'])
            c.execute(f'SELECT user_id, clerk_id FROM athlete_profiles WHERE user_id IN ({marks})', ids)
            for row in c.fetchall():
                own(row['clerk_id'].encode(), row['user_id'])
            c.execute(f'SELECT user_id, decision FROM sparq_entry_refusals WHERE user_id IN ({marks})', ids)
            for row in c.fetchall():
                data[row['user_id']]['refused'].append(row['decision'])
            shared = {s for s, linked in users.items() if len(linked) > 1}
            subjects = [s for s in owners if s not in shared]  # a subject two invitees share is left out and reported
            if subjects:
                held = ', '.join(['%s'] * len(subjects))
                counts = {  # one row per athlete-subject; a GMTM user can have two subjects (October link + older link)
                    'notice': f'SELECT clerk_id, 1 AS n, accepted_at AS at FROM sparq_parent_notices WHERE clerk_id IN ({held})',
                    'list': f'SELECT clerk_id, 1 AS n, built_at AS at FROM sparq_college_lists WHERE built_at IS NOT NULL AND clerk_id IN ({held})',
                    'card': f'SELECT clerk_id, JSON_LENGTH(film_ids) AS n, updated_at AS at FROM sparq_card_clips WHERE clerk_id IN ({held})',
                }
                schools = {  # program ids, so a school counted under both subjects counts once
                    'saved': f'SELECT clerk_id, program_id, saved_at AS at FROM sparq_saved_colleges WHERE clerk_id IN ({held})',
                    'sent': f'SELECT clerk_id, program_id, sent_at AS at FROM sparq_sent_emails WHERE clerk_id IN ({held})',
                    'drafted': "SELECT clerk_id, JSON_UNQUOTE(JSON_EXTRACT(payload, '$.program_id')) AS program_id, created_at AS at "
                               f"FROM artifacts WHERE type = 'outreach_draft' AND clerk_id IN ({held})",
                }
                owner_of = lambda row: owners.get(row['clerk_id'] if isinstance(row['clerk_id'], bytes) else row['clerk_id'].encode())
                for key, sql in counts.items():
                    c.execute(sql, subjects)
                    for row in c.fetchall():
                        if (uid := owner_of(row)) is not None:
                            data[uid][key] = max(data[uid].get(key, 0), int(row['n'] or 0))
                            data[uid]['active'].append(row['at'])
                for key, sql in schools.items():
                    c.execute(sql, subjects)
                    for row in c.fetchall():
                        if (uid := owner_of(row)) is not None and row['program_id']:
                            data[uid].setdefault(key + '_ids', set()).add(row['program_id'])
                            data[uid]['active'].append(row['at'])
                for uid in data:
                    for key in schools:
                        data[uid][key] = len(data[uid].pop(key + '_ids', ()))
                # Step marks (since 2026-10-21): one row per step and Eastern day; the value is the number of days.
                try:
                    c.execute(f'SELECT clerk_id, step, day FROM sparq_step_marks WHERE clerk_id IN ({held})', subjects)
                    for row in c.fetchall():
                        if (uid := owner_of(row)) is not None and row['step'] in ('school_page', 'email_opened'):
                            data[uid][row['step']] = data[uid].get(row['step'], 0) + 1
                            data[uid]['active'].append(row['day'])
                except Exception as error:
                    if not (error.args and error.args[0] == 1146):  # 1146: the table is not created yet
                        raise
            c.execute('ROLLBACK')
    finally:
        conn.close()
    labels = {uid: f'A{n}' for n, uid in enumerate(ids, 1)}
    return data, sorted({labels[uid] for s in shared for uid in users[s]}, key=lambda a: int(a[1:]))


def demo():
    ids = [11, 22, 33, 44]
    t = lambda d, h: datetime(2026, 10, d, h)  # UTC
    data = {
        11: {'entries': 1, 'active': [t(17, 20), t(18, 19), t(19, 1)], 'refused': [], 'notice': 1, 'list': 1, 'saved': 3, 'drafted': 2, 'sent': 1, 'card': 2,
             'school_page': 2, 'email_opened': 1},
        # 44 opened a school page on an Eastern date (a step mark) and stopped there.
        44: {'entries': 1, 'active': [t(17, 20), date(2026, 10, 19)], 'refused': [], 'notice': 1, 'list': 1, 'school_page': 1},
        22: {'entries': 2, 'active': [t(17, 23), t(18, 0)], 'refused': [], 'notice': 1, 'list': 1},  # 7 pm and 8 pm ET: one day
        33: {'entries': 0, 'active': [], 'refused': ['ineligible']},
    }
    text = report(athlete_rows(ids, data))
    lines = text.splitlines()
    assert 'Opened a school page: 2' in text and 'Opened her email or copied: 1' in text
    assert 'Opened a school page' in lines[-1] and lines[-1].split()[-2:] == ['2', '2026-10-19']
    assert 'Invited: 4' in text and 'Signed in: 3' in text and 'Saved a college: 1' in text and 'Marked an email sent: 1' in text
    # 11: Oct 17 4 pm ET, Oct 18 3 pm ET (same 24 h session, no new entry), Oct 18 9 pm ET -> 2 days, last Oct 18.
    assert 'Active on 2 or more days: 2' in text and f'{REFUSED}: 1' in text
    assert [line.split()[0] for line in lines[-4:]] == ['A1', 'A2', 'A3', 'A4']
    assert 'Marked an email sent' in lines[-4] and lines[-4].split()[-2:] == ['2', '2026-10-18']
    assert 'College list built' in lines[-3] and lines[-3].split()[-2:] == ['1', '2026-10-17']
    assert 'Stopped at sign-in' in lines[-2]
    print('demo ok')


if __name__ == '__main__':
    if sys.argv[1:] == ['--demo']:
        demo()
    elif len(sys.argv) == 2:
        ids = read_ids(sys.argv[1])
        try:
            data, clash = read_data(ids)
        except Exception as error:  # no host, user, address or id in the output
            code = error.args[0] if error.args and isinstance(error.args[0], int) else ''
            sys.exit(f'The database read failed ({type(error).__name__} {code}).')
        print(f'SPARQ Recruit wave 1, read {date.today()}')
        print(report(athlete_rows(ids, data)))
        print('Step marks (school page, email opened) start 2026-10-21. Earlier visits are not counted.')
        if clash:
            print(f'Check by hand: a SPARQ subject is linked to more than one invitee ({", ".join(clash)}); its rows are not counted.')
    else:
        sys.exit(__doc__)
