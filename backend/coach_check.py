"""Coach contact check: read each program's public coach page, find the women's flag head coach(es), and compare
with the reviewed data file. Reports only; never changes data. Spec: docs/specs/coach-contact-refresh-2026-10-05.md.

Code-only parsing (SIDEARM staff tables and department directories, PrestoSports coach cards); no model call.
"""
import re
import unicodedata
from typing import Optional
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

import college_programs as cp
import college_research as cr

_HEAD = re.compile(r"(?i)\bhead\b.*\bcoach\b")
_NOT_HEAD = re.compile(r"(?i)\b(?:assistant|asst|associate|strength|conditioning|trainer)\b")
_FLAG = re.compile(r"(?i)\bflag\b")
_MENS = re.compile(r"(?i)\bmen'?s\b")
_WOMENS = re.compile(r"(?i)\bwomen'?s\b")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_AT_TEXT = re.compile(r"(?i)([A-Za-z0-9._%+-]+)\s*[\[(]\s*at\s*[\])]\s*([A-Za-z0-9-]+(?:\s*(?:[\[(]\s*dot\s*[\])]|\.)\s*[A-Za-z0-9-]+)+)")
_NAME_OK = re.compile(r"[^A-Za-zÀ-ɏ .'\-,/&()]")
_CLASS_YEAR = re.compile(r"['’]\d{2}\b")


def clean_text(value: str, cap: int) -> str:
    """Untrusted page text: no email-like tokens at all, then letters, spaces and . ' - , / & ( ) only, capped."""
    value = _AT_TEXT.sub("", value or "")  # "ann [at] gmail [dot] com" is an address too
    value = re.sub(r"(?i)\S*[\[(]\s*at\s*[\])]\S*", "", value)
    value = " ".join(w for w in value.split() if "@" not in w and not w.lower().startswith("mailto"))
    return re.sub(r"\s+", " ", _NAME_OK.sub("", value)).strip()[:cap]


def is_head_title(title: str) -> bool:
    """Head coach if ANY part of a combined title ("Head Coach / Assistant AD") is a head-coach part, and that part
    is not an assistant/associate/strength/trainer role."""
    return any(_HEAD.search(part) and not _NOT_HEAD.search(part) for part in re.split(r"[/&,;|]", title or ""))


def decode_cfemail(hexed: str) -> Optional[str]:
    """Cloudflare email protection: first byte is the XOR key for the rest."""
    try:
        data = bytes.fromhex(hexed)
        return bytes(b ^ data[0] for b in data[1:]).decode("ascii")
    except (ValueError, IndexError, UnicodeDecodeError):
        return None


def emails_in(node) -> list:
    """mailto links, Cloudflare-protected addresses and 'name [at] school [dot] edu' text, in page order."""
    found = []
    for a in node.find_all("a", href=True):
        if a["href"].strip().lower().startswith("mailto:"):
            found.append(a["href"].strip()[7:].split("?", 1)[0])
    for tag in node.select("[data-cfemail]"):
        found.append(decode_cfemail(tag.get("data-cfemail", "")) or "")
    text = node.get_text(" ", strip=True)
    found += _EMAIL.findall(text)
    for user, domain in _AT_TEXT.findall(text):
        found.append(f"{user}@{re.sub(r'(?i)\s*(?:[\[(]\s*dot\s*[\])]|\.)\s*', '.', domain)}")
    return [e.strip() for e in found if e and "@" in e]


def people(html: str, base: str) -> list:
    """[{name, title, email, section}] from SIDEARM tables (section = the last one-cell heading row) or, when no
    table lists staff, PrestoSports coach cards (a card with a /coaches/ name link)."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if not trs:
            continue
        heads = [c.get_text(" ", strip=True).lower() for c in trs[0].find_all(["th", "td"])]
        ni = next((i for i, h in enumerate(heads) if h == "name"), None)
        ti = next((i for i, h in enumerate(heads) if h in ("title", "position")), None)
        if ni is None or ti is None:
            continue
        section = ""
        for tr in trs[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) == 1:
                section = cells[0].get_text(" ", strip=True)
                continue
            if len(cells) <= max(ni, ti):
                continue
            link = cells[ni].find("a")
            name = (link or cells[ni]).get_text(" ", strip=True)
            mails = emails_in(tr)
            out.append({"name": name, "title": cells[ti].get_text(" ", strip=True), "email": mails[0] if mails else None,
                        "section": section})
    if out:
        return out
    for card in soup.select("div.card"):
        link = next((a for a in card.select('a[href*="/coaches/"]') if a.get_text(strip=True)), None)
        if not link:
            continue
        name = link.get_text(" ", strip=True)
        rest = [t for t in card.stripped_strings if t != name]
        mails = emails_in(card)
        out.append({"name": name, "title": rest[0] if rest else "", "email": mails[0] if mails else None, "section": ""})
    return out


def head_coaches(rows: list, page_url: str) -> list:
    """Women's flag head coach row(s) in page order. On a department directory the title or section must say flag
    (and not a men's section); on a sport's own coaches page the page is the sport. Interim only if alone."""
    directory = "/sports/" not in urlsplit(page_url).path
    heads = []
    for r in rows:
        if not is_head_title(r["title"]):
            continue
        if directory:
            scope = f"{r['section']} {r['title']}"
            if not _FLAG.search(scope) or (_MENS.search(scope) and not _WOMENS.search(scope)):
                continue
        heads.append(r)
    permanent = [r for r in heads if "interim" not in r["title"].lower()]
    return permanent or heads


def norm_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    text = _CLASS_YEAR.sub("", text)
    words = [w.strip(",.") for w in text.split()]
    words = [w for w in words if w and not cp._SUFFIX.fullmatch(w)]
    return " ".join(words)


def _first_last(name: str) -> tuple:
    words = norm_name(name).split()
    if not words:
        return "", set()
    last = set(re.split(r"[-\s]", " ".join(words[1:]) or words[0])) - {""}
    return words[0], last


def same_person(a: str, b: str) -> Optional[bool]:
    """True = same name form; False = a different person; None = same person, different spelling."""
    if norm_name(a) == norm_name(b):
        return True
    (fa, la), (fb, lb) = _first_last(a), _first_last(b)
    return None if la & lb and fa == fb else False


def compare(program: dict, page_url: str, heads: list) -> dict:
    """Bucket one program. Emails on both sides pass coach_email(); an address in contact_notes is 'noted'."""
    stored_names = [n.strip() for n in str(program.get("head_coach_name") or "").split(";") if n.strip()]
    stored_email = cp.coach_email(program)
    found_names = [clean_text(r["name"], 80) for r in heads]
    raw = heads[0]["email"] if heads else None  # the first head coach's own row only (co-heads: page order)
    found_email = cp.coach_email({**program, "coach_email": raw}) if raw else None  # personal/shared never output
    noted = {e.casefold() for e in _EMAIL.findall(program.get("contact_notes") or "")}
    out = {"program_id": program["id"], "school": program["school"], "source_url": page_url,
           "found_names": found_names, "found_title": clean_text(heads[0]["title"], 120) if heads else None,
           "found_email": found_email, "stored_names": stored_names, "stored_email": stored_email}
    if not heads:
        return {**out, "bucket": "not_found"}
    # Name verdict first, then email; the most serious bucket wins (a spelling change never hides an email change).
    name = "match"
    if not stored_names:
        name = "different_person"  # a coach appeared where the data has none
    elif {norm_name(n) for n in stored_names} != {norm_name(n) for n in found_names}:
        verdicts = [same_person(a, b) for a, b in zip(sorted(stored_names, key=norm_name), sorted(found_names, key=norm_name))]
        name = "different_person" if len(stored_names) != len(found_names) or False in verdicts else "spelling"
    if name == "different_person":
        return {**out, "bucket": "different_person"}
    if found_email and stored_email and found_email.casefold() != stored_email.casefold():
        return {**out, "bucket": "email_changed"}
    if found_email and not stored_email:
        # The Nebraska case: the data deliberately holds no address and its notes name the one the page prints.
        return {**out, "bucket": "noted" if found_email.casefold() in noted else "email_added"}
    if name == "spelling":
        return {**out, "bucket": "spelling"}
    if stored_email and not found_email:
        return {**out, "bucket": "email_not_on_page"}
    return {**out, "bucket": "match"}


def coach_page(program: dict, fetcher) -> Optional[str]:
    """staff_page_url, else the program page's own /sports/<slug>/coaches link (code-chosen, allowlisted)."""
    if program.get("staff_page_url"):
        return program["staff_page_url"]
    if not program.get("program_url"):
        return None
    url, html = fetcher.get(program["program_url"])
    m = cr._SLUG.match(urlsplit(url).path)
    if not m:
        return None
    hosts = cr.allowed_hosts(program)
    return next((u for u in cr._links(html, url, hosts)
                 if re.fullmatch(rf"/sports/{re.escape(m.group(1))}/coaches(?:/index)?/?", urlsplit(u).path)), None)


def check_program(program: dict, fetcher=None) -> dict:
    fetcher = fetcher or cr.Fetcher(cr.allowed_hosts(program))
    base = {"program_id": program["id"], "school": program["school"]}
    try:
        page = coach_page(program, fetcher)
        if not page:
            return {**base, "bucket": "not_found", "note": "no_coach_page"}
        url, html = fetcher.get(page)
    except cr.FetchError as e:
        return {**base, "bucket": "unreadable", "note": str(e).split(":")[0]}
    return compare(program, url, head_coaches(people(html, url), url))
