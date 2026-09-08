"""Offline unit-suite boundary: never load credentials or contact a service.

Install these guards before test collection imports application modules, even
though ordinary app startup no longer performs schema setup. Tests supply explicit
fake connections/HTTP/model interfaces; a missing mock must fail, not hit a real
GMTM, Agent, Clerk, model or email service. This is not DB integration coverage.
"""
import os
from pathlib import Path
import socket
import sys
import types

import dotenv
import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
dotenv.load_dotenv = lambda *args, **kwargs: False


def _no_database(*args, **kwargs):
    raise AssertionError("Real database access is forbidden in the offline unit suite")


try:
    import pymysql
except ModuleNotFoundError:
    # The lightweight offline runner may not install the actual database driver.
    # No driver behavior is claimed by these unit tests.
    pymysql = types.ModuleType("pymysql")
    class MySQLError(Exception):
        pass
    class IntegrityError(MySQLError):
        pass
    class OperationalError(MySQLError):
        pass
    pymysql.err = types.SimpleNamespace(
        MySQLError=MySQLError, IntegrityError=IntegrityError,
        OperationalError=OperationalError,
    )
    pymysql.cursors = types.SimpleNamespace(DictCursor=object)
    sys.modules["pymysql"] = pymysql

pymysql.connect = _no_database


def _no_model(*args, **kwargs):
    raise AssertionError("A test must explicitly supply its fake model client")


try:
    import anthropic
except ModuleNotFoundError as exc:
    if exc.name != "anthropic":
        raise
    anthropic = types.ModuleType("anthropic")
    sys.modules["anthropic"] = anthropic
anthropic.Anthropic = _no_model
anthropic.AsyncAnthropic = _no_model
if not hasattr(anthropic, "DefaultAsyncHttpxClient"):
    anthropic.DefaultAsyncHttpxClient = httpx.AsyncClient

try:
    import openai
except ModuleNotFoundError as exc:
    if exc.name != "openai":
        raise
    openai = types.ModuleType("openai")
    sys.modules["openai"] = openai
openai.OpenAI = _no_model
openai.AsyncOpenAI = _no_model
if not hasattr(openai, "DefaultAsyncHttpxClient"):
    openai.DefaultAsyncHttpxClient = httpx.AsyncClient


def _block_network(event, args):
    if event == "socket.getaddrinfo":
        raise AssertionError("DNS is forbidden in the offline unit suite")
    if event == "socket.connect" and args[0].family in (socket.AF_INET, socket.AF_INET6):
        raise AssertionError("Network connections are forbidden in the offline unit suite")


sys.addaudithook(_block_network)
os.environ["ANTHROPIC_API_KEY"] = "test-key-no-network"
os.environ["SHARE_TOKEN_SECRET"] = "test-share-secret"
os.environ["CLAIMS_ADMIN_SECRET"] = "test-admin-secret"
os.environ["AUTH_ENFORCED"] = "true"
os.environ["FRONTEND_URL"] = "https://sparq-agent.test"


@pytest.fixture(autouse=True)
def _safe_environment(monkeypatch):
    monkeypatch.setenv("AUTH_ENFORCED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-no-network")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-no-network")
    for name in ("COMBINE_HELP_MODEL", "COMBINE_HELP_TEST_MODE", "COMBINE_HELP_MAX_MODEL_CALLS",
                 "COMBINE_HELP_MAX_CONCURRENT_CALLS", "PROFILE_DEBRIEF_ENABLED", "PROFILE_DEBRIEF_MODEL",
                 "PROFILE_DEBRIEF_MAX_MODEL_CALLS", "PROFILE_DEBRIEF_MAX_CONCURRENT_CALLS"):
        monkeypatch.delenv(name, raising=False)
    import model_usage
    monkeypatch.setattr(model_usage, "_ledger", None)
    monkeypatch.setattr(pymysql, "connect", _no_database)
    monkeypatch.setattr(anthropic, "Anthropic", _no_model)
    monkeypatch.setattr(anthropic, "AsyncAnthropic", _no_model)
    monkeypatch.setattr(openai, "OpenAI", _no_model)
    monkeypatch.setattr(openai, "AsyncOpenAI", _no_model)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
