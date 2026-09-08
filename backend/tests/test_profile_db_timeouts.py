"""Real PyMySQL timeout/cleanup behavior with synthetic transport interfaces.

No socket is opened: connection creation returns a fake socket or raises a
synthetic timeout. Driver query framing and failure cleanup execute unchanged.
These tests verify per-operation socket timeout configuration, not elapsed
network timing, DNS resolution, server query cancellation or a request deadline.
"""
import socket

import pytest
from pymysql.connections import Connection
from pymysql.err import OperationalError

import profile_api


@pytest.fixture(params=["_get_agent_db", "_get_gmtm_db"])
def connector(request, monkeypatch):
    for name, value in {
        "AGENT_DB_HOST": "agent.example.invalid", "AGENT_DB_PORT": "3307",
        "AGENT_DB_USER": "synthetic-agent", "AGENT_DB_PASSWORD": "synthetic-only",
        "AGENT_DB_NAME": "synthetic_agent", "DB_HOST": "source.example.invalid",
        "DB_USER": "synthetic-source", "DB_PASSWORD": "synthetic-only",
    }.items():
        monkeypatch.setenv(name, value)
    # conftest blocks the public factory. Restore only the real driver class,
    # with socket.create_connection replaced by each test before invocation.
    monkeypatch.setattr(profile_api.pymysql, "connect", Connection)
    return getattr(profile_api, request.param)


class StalledSocket:
    """Transport records driver settings and times out at a chosen operation."""
    def __init__(self, phase):
        self.phase = phase
        self.timeout = None
        self.timeouts = []
        self.closed = False
        self.reader_closed = False
        self.writes = []
        self.read_timeouts = []
        self.write_timeouts = []

    def settimeout(self, value):
        self.timeout = value
        self.timeouts.append(value)

    def setsockopt(self, *_):
        pass

    def makefile(self, mode):
        assert mode == "rb"
        return self.Reader(self)

    def sendall(self, payload):
        self.writes.append(bytes(payload))
        self.write_timeouts.append(self.timeout)
        if self.phase == "write":
            raise socket.timeout("Synthetic stalled write")

    def close(self):
        self.closed = True

    class Reader:
        def __init__(self, transport):
            self.transport = transport

        def read(self, count):
            assert count > 0
            self.transport.read_timeouts.append(self.transport.timeout)
            raise socket.timeout("Synthetic stalled read")

        def close(self):
            self.transport.reader_closed = True


def test_connect_timeout_reaches_driver_socket_creation(connector, monkeypatch):
    attempts = []

    def cannot_connect(address, timeout, **kwargs):
        attempts.append((address, timeout, kwargs))
        raise socket.timeout("Synthetic unreachable host")

    monkeypatch.setattr(socket, "create_connection", cannot_connect)
    with pytest.raises(OperationalError) as raised:
        connector()

    assert raised.value.args[0] == 2003
    assert isinstance(raised.value.original_exception, socket.timeout)
    assert len(attempts) == 1
    assert attempts[0][1] == 5
    assert attempts[0][0][0] in {"agent.example.invalid", "source.example.invalid"}


def test_stalled_initial_handshake_uses_read_timeout_and_closes(connector, monkeypatch):
    transport = StalledSocket("read")
    monkeypatch.setattr(socket, "create_connection", lambda *_args, **_kwargs: transport)

    with pytest.raises(OperationalError) as raised:
        connector()

    assert raised.value.args[0] == 2013
    assert transport.read_timeouts == [10]
    assert transport.closed and transport.reader_closed
    assert not transport.writes


@pytest.mark.parametrize("phase,error_code", [("read", 2013), ("write", 2006)])
def test_stalled_query_uses_operation_timeout_and_closes(connector, monkeypatch, phase, error_code):
    # Construct through the application connector with the real driver, then
    # attach a synthetic established transport. No MySQL auth is simulated.
    monkeypatch.setattr(
        profile_api.pymysql, "connect",
        lambda **kwargs: Connection(defer_connect=True, **kwargs),
    )
    db = connector()
    transport = StalledSocket(phase)
    db._sock = transport
    db._rfile = transport.makefile("rb")
    db._closed = False

    with pytest.raises(OperationalError) as raised:
        db.query("SELECT 1")

    assert raised.value.args[0] == error_code
    assert transport.write_timeouts == [10]
    assert transport.read_timeouts == ([10] if phase == "read" else [])
    assert b"SELECT 1" in transport.writes[0]
    assert transport.closed and transport.reader_closed
    assert db._sock is None and db._rfile is None
