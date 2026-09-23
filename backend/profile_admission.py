"""Small adult-pilot admission boundary; no database, network or import-time I/O.

Configuration validation is pure. A gated request loads a private admission file
and pins one reviewed identity. Existing profile owner resolvers must call
``enforce_owner`` before using personal data; sensitive later work can call
``recheck_admission``. Neither helper grants authority from a browser field.
"""
from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
import stat
from urllib.parse import urlsplit

from fastapi import HTTPException


CONFIG_KEYS = ("PROFILE_ADMISSION_ENABLED", "PROFILE_ADMISSION_FILE")
MAX_BYTES = 64 * 1024
MAX_ADMISSIONS = 50
MAX_INTERVAL = timedelta(days=31)
_SUBJECT = re.compile(r"[A-Za-z0-9_-]{1,255}\Z")
_HEX = re.compile(r"[a-f0-9]{64}\Z")
_REFERENCE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)\Z")


class AdmissionError(HTTPException):
    """Fixed public errors; never include identities, file paths or raw failures."""
    def __init__(self, code="profile_admission_denied"):
        if code == "profile_admission_denied":
            status, detail = 403, "This profile pilot requires a current adult invitation."
        elif code == "profile_admission_unavailable":
            status, detail = 503, "Profile pilot access could not be checked."
        else:
            raise ValueError("Unsupported admission error")
        self.code = code
        super().__init__(status_code=status, detail=detail)


@dataclass(frozen=True, repr=False)
class Configuration:
    file_path: str


@dataclass(frozen=True, repr=False)
class Admission:
    clerk_id: str
    user_id: int
    link_row_id: int
    link_revision: str
    adult_self_owned: bool
    review_ref: str
    reviewed_at: datetime
    starts_at: datetime
    expires_at: datetime
    revoked: bool


@dataclass(frozen=True, repr=False)
class _RequestAdmission:
    configuration: Configuration
    admission: Admission


_CURRENT: ContextVar[_RequestAdmission | None] = ContextVar("profile_admission", default=None)


def _loopback_origin(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        host, port = parsed.hostname, parsed.port
    except ValueError:
        return False
    if (parsed.scheme not in ("http", "https") or host not in ("localhost", "127.0.0.1", "::1")
            or parsed.username is not None or parsed.password is not None
            or parsed.path or parsed.query or parsed.fragment
            or port is not None and not 1 <= port <= 65535):
        return False
    canonical = f"{parsed.scheme}://" + (f"[{host}]" if ":" in host else host)
    if port is not None:
        canonical += f":{port}"
    return value == canonical


def _path(value):
    return (isinstance(value, str) and 1 < len(value) <= 4096 and value.startswith("/")
            and not value.startswith("//") and os.path.normpath(value) == value
            and not re.search(r"[\x00-\x1f\x7f\ud800-\udfff]", value))


def validate_configuration(env, origins):
    """Pure startup validation. Disabled mode is limited to explicit loopback UI origins."""
    if not isinstance(origins, (tuple, list)) or not origins or any(not isinstance(x, str) for x in origins):
        raise ValueError("Explicit profile origins are required")
    enabled = env.get("PROFILE_ADMISSION_ENABLED", "false")
    if enabled in ("", "false"):
        if not all(_loopback_origin(origin) for origin in origins):
            raise ValueError("Hosted profile origins require adult pilot admission")
        return None
    if enabled != "true":
        raise ValueError("PROFILE_ADMISSION_ENABLED must be true or false")
    path = env.get("PROFILE_ADMISSION_FILE")
    if not _path(path):
        raise ValueError("PROFILE_ADMISSION_FILE must be an absolute canonical path")
    return Configuration(path)


def _pairs(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("Duplicate admission field")
        output[key] = value
    return output


def _constant(_value):
    raise ValueError("Invalid admission constant")


def _date(value):
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        raise ValueError("UTC admission time required")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _positive(value):
    return type(value) is int and 1 <= value <= 9_007_199_254_740_991


def _revision(clerk_id, link_id, user_id):
    payload = json.dumps([clerk_id, link_id, user_id], separators=(",", ":"))
    return hashlib.sha256(("sparq-workspace-v1:" + payload).encode()).hexdigest()


def _parse(data):
    value = json.loads(data.decode("utf-8", "strict"), object_pairs_hook=_pairs, parse_constant=_constant)
    if (not isinstance(value, dict) or set(value) != {"schema", "admissions"}
            or type(value["schema"]) is not int or value["schema"] != 1
            or not isinstance(value["admissions"], list) or len(value["admissions"]) > MAX_ADMISSIONS):
        raise ValueError("Invalid admission document")
    fields = {"clerk_id", "user_id", "link_row_id", "link_revision", "adult_self_owned",
              "review_ref", "reviewed_at", "starts_at", "expires_at", "revoked"}
    subjects, users, links, records = set(), set(), set(), []
    for item in value["admissions"]:
        if (not isinstance(item, dict) or set(item) != fields
                or not isinstance(item["clerk_id"], str) or not _SUBJECT.fullmatch(item["clerk_id"])
                or not _positive(item["user_id"]) or not _positive(item["link_row_id"])
                or not isinstance(item["link_revision"], str) or not _HEX.fullmatch(item["link_revision"])
                or item["adult_self_owned"] is not True or type(item["revoked"]) is not bool
                or not isinstance(item["review_ref"], str) or not 1 <= len(item["review_ref"]) <= 80
                or not _REFERENCE.fullmatch(item["review_ref"])
                or item["link_revision"] != _revision(item["clerk_id"], item["link_row_id"], item["user_id"])):
            raise ValueError("Invalid reviewed admission")
        reviewed, starts, expires = (_date(item[key]) for key in ("reviewed_at", "starts_at", "expires_at"))
        if not reviewed <= starts < expires or expires - starts > MAX_INTERVAL:
            raise ValueError("Invalid admission interval")
        if (item["clerk_id"] in subjects or item["user_id"] in users or item["link_row_id"] in links):
            raise ValueError("Ambiguous admission identity")
        subjects.add(item["clerk_id"])
        users.add(item["user_id"])
        links.add(item["link_row_id"])
        records.append(Admission(**{**item, "reviewed_at": reviewed, "starts_at": starts, "expires_at": expires}))
    return tuple(records)


def _read_private(path):
    """Resolve every path component without following links, then bound the read."""
    if not _path(path):
        raise ValueError("Invalid admission path")
    parent = descriptor = None
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent = os.open("/", directory_flags)
        components = path.split("/")[1:]
        for component in components[:-1]:
            child = os.open(component, directory_flags, dir_fd=parent)
            previous, parent = parent, child
            os.close(previous)
        descriptor = os.open(components[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1
                or not 0 < before.st_size <= MAX_BYTES):
            raise ValueError("Private admission file required")
        data = bytearray()
        while len(data) <= MAX_BYTES:
            chunk = os.read(descriptor, min(8192, MAX_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(descriptor)
        stable = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns,
                               item.st_ctime_ns, item.st_mode, item.st_uid, item.st_nlink)
        if len(data) != before.st_size or len(data) > MAX_BYTES or stable(before) != stable(after):
            raise ValueError("Admission file changed during read")
        return bytes(data)
    finally:
        try:
            if descriptor is not None:
                os.close(descriptor)
        finally:
            if parent is not None:
                os.close(parent)


def load_admissions(config):
    """Read/validate one bounded private snapshot; never return raw diagnostic text."""
    try:
        if not isinstance(config, Configuration):
            raise ValueError("Admission configuration required")
        return _parse(_read_private(config.file_path))
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise AdmissionError("profile_admission_unavailable") from None


def _clock(now):
    value = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise AdmissionError("profile_admission_unavailable")
    return value


def _select(config, clerk_id, now):
    if not isinstance(clerk_id, str) or not _SUBJECT.fullmatch(clerk_id):
        raise AdmissionError()
    records = load_admissions(config)
    admission = next((item for item in records if item.clerk_id == clerk_id), None)
    if admission is None or admission.revoked or not admission.starts_at <= now < admission.expires_at:
        raise AdmissionError()
    return admission


def begin_request(config, clerk_id, *, now=None):
    """Pin an admitted verified subject without a DB lookup; return the reset token."""
    if config is None:
        return _CURRENT.set(None)
    admission = _select(config, clerk_id, _clock(now))
    return _CURRENT.set(_RequestAdmission(config, admission))


def reset_request(token: Token):
    _CURRENT.reset(token)


def is_active():
    return _CURRENT.get() is not None


def recheck_admission(*, now=None):
    """Re-read current authority before sensitive work; does not resolve an owner."""
    current = _CURRENT.get()
    if current is None:
        return
    fresh = _select(current.configuration, current.admission.clerk_id, _clock(now))
    if fresh != current.admission:
        raise AdmissionError()


def enforce_owner(owner, *, now=None):
    """Require the downstream resolver's full tuple to equal the pinned admission."""
    current = _CURRENT.get()
    if current is None:
        return
    recheck_admission(now=now)
    expected = current.admission
    if (not isinstance(owner, dict) or set(owner) != {"id", "user_id", "clerk_id"}
            or not _positive(owner["id"]) or not _positive(owner["user_id"])
            or owner["clerk_id"] != expected.clerk_id or owner["id"] != expected.link_row_id
            or owner["user_id"] != expected.user_id
            or _revision(owner["clerk_id"], owner["id"], owner["user_id"]) != expected.link_revision):
        raise AdmissionError()
