"""Repo check: the removed sign-in provider must not come back (Joey, 2026-10-01).

GMTM sign-in is the only sign-in. This scans source, package.json, the lockfile,
the env example, Dockerfiles, CSP code and READMEs. Allowed: the Agent DB column
``clerk_id`` and its indexes ``idx_clerk``/``idx_clerk_id`` (renaming them needs a
production schema migration). Historical docs (docs/state, docs/research,
.sammy/handoffs, other *.md) and the pilot spec's rev notes are not scanned.
Real env files are never opened.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
NAME = "cl" + "erk"  # keeps this file out of its own results
WORD = re.compile(NAME, re.I)
ALLOWED = re.compile(r"\b(?:idx_" + NAME + r"(?:_id)?|" + NAME + r"_id)\b")
SKIP_DIRS = {".git", "node_modules", ".next", "__pycache__", ".venv", "venv", ".vercel", ".pytest_cache"}
SKIP_PATHS = {"docs/state", "docs/research", ".sammy"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".mp4", ".mov", ".pdf", ".woff", ".woff2",
                 ".ttf", ".zip", ".tar", ".gz", ".tsbuildinfo", ".pyc"}


def scanned_files():
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if (any(part in SKIP_DIRS for part in rel.parts) or not path.is_file() or path.is_symlink()
                or any(str(rel).startswith(prefix + "/") for prefix in SKIP_PATHS)):
            continue
        name = path.name
        if name.startswith(".env") and name != ".env.example":
            continue  # never open real env files
        if path.suffix.lower() in SKIP_SUFFIXES or (path.suffix.lower() == ".md" and name != "README.md"):
            continue
        yield rel, path


def test_no_removed_sign_in_provider_anywhere():
    hits = []
    for rel, path in scanned_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if WORD.search(ALLOWED.sub("", line)):
                hits.append(f"{rel}:{number}: {line.strip()[:120]}")
    assert not hits, "Removed sign-in provider still referenced:\n" + "\n".join(hits[:50])


def test_check_sees_the_files_that_matter():
    seen = {str(rel) for rel, _ in scanned_files()}
    for required in ("frontend/package.json", "frontend/package-lock.json", ".env.example", "Dockerfile.candidate",
                     "backend/auth.py", "frontend/middleware.ts", "frontend/lib/backend-config.cjs", "README.md"):
        assert required in seen, required


def test_allowed_names_are_exact():
    assert not WORD.search(ALLOWED.sub("", "SELECT clerk_id FROM t; KEY idx_clerk_id (clerk_id); idx_clerk"))
    for bad in ("require_" + NAME + "_id", NAME.upper() + "_ISSUER", "@" + NAME + "/nextjs", NAME + "Id", NAME + "_owner", "a " + NAME + " token"):
        assert WORD.search(ALLOWED.sub("", bad)), bad
