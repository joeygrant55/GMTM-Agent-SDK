"""Offline adult-admission policy tests; synthetic identities and private temp files."""
import asyncio
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os

import pytest

import profile_admission as api


NOW = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
CALLER = "clerk_pilot_synthetic"
OWNER = {"id": 191, "user_id": 8201, "clerk_id": CALLER}
ORIGINS = ("https://pilot.example.invalid",)


def revision(owner):
    raw = json.dumps([owner["clerk_id"], owner["id"], owner["user_id"]], separators=(",", ":"))
    return hashlib.sha256(("sparq-workspace-v1:" + raw).encode()).hexdigest()


def entry(owner=OWNER, **changes):
    return {"clerk_id": owner["clerk_id"], "user_id": owner["user_id"], "link_row_id": owner["id"],
            "link_revision": revision(owner), "adult_self_owned": True, "review_ref": "synthetic-adult-review-1",
            "reviewed_at": "2026-09-22T00:00:00Z", "starts_at": "2026-09-23T00:00:00Z",
            "expires_at": "2026-10-07T00:00:00Z", "revoked": False, **changes}


def document(*entries):
    return {"schema": 1, "admissions": list(entries or (entry(),))}


def write(path, value):
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
    path.chmod(0o600)


@pytest.fixture
def admissions(tmp_path):
    path = tmp_path.resolve() / "private-admissions.json"
    write(path, document())
    config = api.validate_configuration({"PROFILE_ADMISSION_ENABLED": "true", "PROFILE_ADMISSION_FILE": str(path)}, ORIGINS)
    yield config, path
    assert not api.is_active()


@contextmanager
def gated(config, caller=CALLER, *, now=NOW):
    token = api.begin_request(config, caller, now=now)
    try:
        yield
    finally:
        api.reset_request(token)


def denied(call, *, status=403):
    with pytest.raises(api.AdmissionError) as error:
        call()
    assert error.value.status_code == status
    assert error.value.code == ("profile_admission_denied" if status == 403 else "profile_admission_unavailable")
    assert all(value not in str(error.value) for value in (CALLER, "8201", "191", "private-admissions", "PRIVATE"))


def test_configuration_validation_is_pure_and_local_default_is_disabled(monkeypatch):
    monkeypatch.setattr(api.os, "open", lambda *args, **kwargs: pytest.fail("Configuration must not read files"))
    assert api.validate_configuration({}, ("http://localhost:3218",)) is None
    assert api.validate_configuration({"PROFILE_ADMISSION_ENABLED": "false"}, ("https://127.0.0.1:8443", "http://[::1]:3000")) is None
    config = api.validate_configuration({"PROFILE_ADMISSION_ENABLED": "true", "PROFILE_ADMISSION_FILE": "/private/synthetic.json"}, ORIGINS)
    assert config.file_path == "/private/synthetic.json"
    assert "/private/synthetic.json" not in repr(config)


@pytest.mark.parametrize("origins", [
    ORIGINS, ("http://localhost:3218", "https://pilot.example.invalid"),
    ("http://localhost.evil.invalid",), ("http://localhost@evil.invalid",),
    ("http://127.0.0.2",), ("http://localhost:0",), ("http://localhost:70000",),
    ("http://localhost/",), ("http://localhost?x=1",), ("http://localhost#x",),
    ("http://LOCALHOST",), (), "http://localhost", (None,),
])
def test_disabled_gate_cannot_silently_be_used_for_hosted_or_malformed_origins(origins):
    with pytest.raises(ValueError):
        api.validate_configuration({}, origins)


@pytest.mark.parametrize("changes", [
    {"PROFILE_ADMISSION_ENABLED": "TRUE"}, {"PROFILE_ADMISSION_ENABLED": "1"},
    {"PROFILE_ADMISSION_ENABLED": True}, {"PROFILE_ADMISSION_ENABLED": None},
    {"PROFILE_ADMISSION_FILE": None}, {"PROFILE_ADMISSION_FILE": "relative.json"},
    {"PROFILE_ADMISSION_FILE": "/private/../private/admission.json"},
    {"PROFILE_ADMISSION_FILE": "/private//admission.json"}, {"PROFILE_ADMISSION_FILE": "//private/admission.json"},
    {"PROFILE_ADMISSION_FILE": "/private/PRIVATE\nfile.json"},
])
def test_invalid_configuration_never_echoes_values(changes):
    env = {"PROFILE_ADMISSION_ENABLED": "true", "PROFILE_ADMISSION_FILE": "/private/synthetic.json", **changes}
    with pytest.raises(ValueError) as error:
        api.validate_configuration(env, ORIGINS)
    assert "PRIVATE" not in str(error.value) and "/private/" not in str(error.value)


def test_valid_admission_is_immutable_private_and_uses_actual_workspace_revision(admissions):
    from athlete_workspace import _revision
    config, _ = admissions
    rows = api.load_admissions(config)
    assert isinstance(rows, tuple) and len(rows) == 1
    row = rows[0]
    assert row.link_revision == _revision(OWNER)
    assert row.adult_self_owned is True and row.revoked is False
    assert row.starts_at <= NOW < row.expires_at
    assert all(value not in repr(row) for value in (CALLER, "8201", "191", "synthetic-adult-review"))
    with pytest.raises(AttributeError):
        row.user_id = 2


@pytest.mark.parametrize("change", [
    lambda x: x.update(extra="PRIVATE EMAIL"), lambda x: x.update(schema=True),
    lambda x: x.update(schema=2), lambda x: x.update(admissions={}),
    lambda x: x["admissions"][0].update(email="PRIVATE EMAIL"),
    lambda x: x["admissions"][0].pop("adult_self_owned"),
    lambda x: x["admissions"][0].update(adult_self_owned=False),
    lambda x: x["admissions"][0].update(adult_self_owned=1),
    lambda x: x["admissions"][0].update(revoked="false"),
    lambda x: x["admissions"][0].update(clerk_id=" " + CALLER),
    lambda x: x["admissions"][0].update(clerk_id="private@example.invalid"),
    lambda x: x["admissions"][0].update(user_id=True),
    lambda x: x["admissions"][0].update(user_id=0),
    lambda x: x["admissions"][0].update(user_id=9007199254740992),
    lambda x: x["admissions"][0].update(link_row_id="191"),
    lambda x: x["admissions"][0].update(link_revision="A" * 64),
    lambda x: x["admissions"][0].update(link_revision="a" * 64),
    lambda x: x["admissions"][0].update(review_ref=""),
    lambda x: x["admissions"][0].update(review_ref="review@example.invalid"),
    lambda x: x["admissions"][0].update(reviewed_at="2026-09-24T00:00:00Z"),
    lambda x: x["admissions"][0].update(starts_at="2026-09-23"),
    lambda x: x["admissions"][0].update(starts_at="2026-09-23T00:00:00-04:00"),
    lambda x: x["admissions"][0].update(expires_at="2026-09-23T00:00:00Z"),
    lambda x: x["admissions"][0].update(expires_at="2026-10-25T00:00:00Z"),
    lambda x: x["admissions"].append(deepcopy(x["admissions"][0])),
    lambda x: x.update(admissions=[entry()] * (api.MAX_ADMISSIONS + 1)),
])
def test_strict_adult_review_schema_fails_closed(admissions, change):
    config, path = admissions
    value = document()
    change(value)
    write(path, value)
    denied(lambda: api.begin_request(config, CALLER, now=NOW), status=503)
    assert not api.is_active()


@pytest.mark.parametrize("owner", [
    {"id": 192, "user_id": 8202, "clerk_id": CALLER},
    {"id": 192, "user_id": OWNER["user_id"], "clerk_id": "different-subject"},
    {"id": OWNER["id"], "user_id": 8202, "clerk_id": "different-subject"},
])
def test_duplicate_subject_athlete_or_link_is_never_ambiguously_admitted(admissions, owner):
    config, path = admissions
    write(path, document(entry(), entry(owner, review_ref="synthetic-review-2")))
    denied(lambda: api.load_admissions(config), status=503)


@pytest.mark.parametrize("raw", [
    b"", b"null", b"[]", b"\xff", b'{"schema":1,"admissions":[],"schema":1}',
    b'{"schema":1,"admissions":NaN}', ("[" * 1100 + "]" * 1100).encode(),
    json.dumps(document()).encode("utf-16"), b" " * (api.MAX_BYTES + 1),
])
def test_invalid_duplicate_or_unbounded_file_is_unavailable(admissions, raw):
    config, path = admissions
    write(path, raw)
    denied(lambda: api.load_admissions(config), status=503)


@pytest.mark.parametrize("mode", [0o644, 0o640, 0o660, 0o700, 0o400])
def test_file_must_have_exact_private_permissions(admissions, mode):
    config, path = admissions
    path.chmod(mode)
    denied(lambda: api.load_admissions(config), status=503)


def test_missing_wrong_owner_and_hardlinked_files_are_unavailable(admissions, monkeypatch):
    config, path = admissions
    real_uid = os.getuid()
    with monkeypatch.context() as local:
        local.setattr(api.os, "getuid", lambda: real_uid + 1)
        denied(lambda: api.load_admissions(config), status=503)
    second = path.with_name("second-private-name.json")
    os.link(path, second)
    denied(lambda: api.load_admissions(config), status=503)
    second.unlink()
    path.unlink()
    denied(lambda: api.load_admissions(config), status=503)


def test_terminal_or_parent_symlink_is_not_followed(admissions):
    config, path = admissions
    alias = path.with_name("alias.json")
    alias.symlink_to(path)
    denied(lambda: api.load_admissions(api.Configuration(str(alias))), status=503)
    parent_alias = path.parent / "parent-alias"
    parent_alias.symlink_to(path.parent, target_is_directory=True)
    denied(lambda: api.load_admissions(api.Configuration(str(parent_alias / path.name))), status=503)
    assert api.load_admissions(config)[0].clerk_id == CALLER


def test_fifo_or_directory_fails_without_blocking(admissions):
    _, path = admissions
    fifo = path.with_name("not-a-file")
    os.mkfifo(fifo, 0o600)
    denied(lambda: api.load_admissions(api.Configuration(str(fifo))), status=503)
    denied(lambda: api.load_admissions(api.Configuration(str(path.parent))), status=503)


def test_file_change_during_read_is_rejected(admissions, monkeypatch):
    config, path = admissions
    original = api.os.read
    changed = False

    def changing_read(fd, length):
        nonlocal changed
        data = original(fd, length)
        if data and not changed:
            changed = True
            write(path, document(entry(revoked=True)))
        return data

    monkeypatch.setattr(api.os, "read", changing_read)
    denied(lambda: api.load_admissions(config), status=503)


def test_all_opened_descriptors_close_on_success_and_validation_failure(admissions, monkeypatch):
    config, path = admissions
    opened, closed = [], []
    real_open, real_close = api.os.open, api.os.close

    def opening(*args, **kwargs):
        fd = real_open(*args, **kwargs)
        opened.append(fd)
        return fd

    def closing(fd):
        closed.append(fd)
        return real_close(fd)

    monkeypatch.setattr(api.os, "open", opening)
    monkeypatch.setattr(api.os, "close", closing)
    assert api.load_admissions(config)
    write(path, b"PRIVATE malformed data")
    denied(lambda: api.load_admissions(config), status=503)
    assert Counter(opened) == Counter(closed)


def test_begin_pins_identity_without_an_owner_lookup_and_reset_clears_it(admissions):
    config, _ = admissions
    assert not api.is_active()
    with gated(config):
        assert api.is_active()
        api.enforce_owner(OWNER, now=NOW)
        api.recheck_admission(now=NOW)
    assert not api.is_active()
    api.enforce_owner({"invalid": "legacy caller outside gate"}, now="unused")
    api.recheck_admission(now="unused")


@pytest.mark.parametrize("subject", ["uninvited-subject", CALLER.upper(), "", None, " " + CALLER])
def test_subject_selection_is_exact_and_never_inferred(admissions, subject):
    config, _ = admissions
    denied(lambda: api.begin_request(config, subject, now=NOW))
    assert not api.is_active()


@pytest.mark.parametrize("changes,now", [
    ({"revoked": True}, NOW), ({}, datetime(2026, 9, 22, 23, 59, 59, tzinfo=timezone.utc)),
    ({}, datetime(2026, 10, 7, 0, 0, tzinfo=timezone.utc)),
])
def test_revocation_start_and_expiry_are_enforced_before_context(admissions, changes, now):
    config, path = admissions
    write(path, document(entry(**changes)))
    denied(lambda: api.begin_request(config, CALLER, now=now))
    assert not api.is_active()


def test_empty_admission_list_denies_all_and_start_is_inclusive(admissions):
    config, path = admissions
    with gated(config, now=datetime(2026, 9, 23, tzinfo=timezone.utc)):
        api.enforce_owner(OWNER, now=datetime(2026, 9, 23, tzinfo=timezone.utc))
    write(path, {"schema": 1, "admissions": []})
    denied(lambda: api.begin_request(config, CALLER, now=NOW))


@pytest.mark.parametrize("owner", [
    None, {"user_id": 8201, "clerk_id": CALLER}, {**OWNER, "id": 192}, {**OWNER, "user_id": 8202},
    {**OWNER, "clerk_id": CALLER.upper()}, {**OWNER, "id": True}, {**OWNER, "user_id": "8201"},
    {**OWNER, "extra": "unsupported"},
])
def test_owner_must_match_exact_pinned_link_generation(admissions, owner):
    config, _ = admissions
    with gated(config):
        denied(lambda: api.enforce_owner(owner, now=NOW))


@pytest.mark.parametrize("update", [
    lambda: {"schema": 1, "admissions": []},
    lambda: document(entry(revoked=True)),
    lambda: document(entry(expires_at="2026-09-23T12:00:00Z")),
    lambda: document(entry(expires_at="2026-10-08T00:00:00Z")),
    lambda: document(entry(review_ref="replacement-adult-review")),
    lambda: document(entry({**OWNER, "id": 192})),
])
def test_existing_request_rechecks_current_authority_and_never_adopts_replacement(admissions, update):
    config, path = admissions
    with gated(config):
        api.enforce_owner(OWNER, now=NOW)
        write(path, update())
        denied(lambda: api.recheck_admission(now=NOW))
        denied(lambda: api.enforce_owner(OWNER, now=NOW))


def test_time_expiry_and_broken_file_are_rechecked_within_request(admissions):
    config, path = admissions
    with gated(config):
        denied(lambda: api.enforce_owner(OWNER, now=datetime(2026, 10, 7, tzinfo=timezone.utc)))
        write(path, b"PRIVATE unavailable document")
        denied(lambda: api.recheck_admission(now=NOW), status=503)


@pytest.mark.parametrize("now", [NOW.replace(tzinfo=None), NOW.astimezone(timezone(timedelta(hours=-4))), "2026-09-23"])
def test_clock_must_be_explicitly_utc(admissions, now):
    config, _ = admissions
    denied(lambda: api.begin_request(config, CALLER, now=now), status=503)


def test_nested_disabled_context_restores_previous_request(admissions):
    config, _ = admissions
    with gated(config):
        with gated(None, caller="unused"):
            assert not api.is_active()
            api.enforce_owner(None)
        assert api.is_active()
        api.enforce_owner(OWNER, now=NOW)


def test_concurrent_requests_and_worker_threads_keep_their_own_admission(admissions):
    config, path = admissions
    second = {"id": 192, "user_id": 8202, "clerk_id": "clerk_other_synthetic"}
    write(path, document(entry(), entry(second, review_ref="synthetic-review-2")))

    async def one(owner, other):
        with gated(config, caller=owner["clerk_id"]):
            await asyncio.sleep(0)
            assert api.is_active()
            await asyncio.to_thread(api.enforce_owner, owner, now=NOW)
            denied(lambda: api.enforce_owner(other, now=NOW))
        assert not api.is_active()

    async def both():
        await asyncio.gather(one(OWNER, second), one(second, OWNER))

    asyncio.run(both())
    assert not api.is_active()
