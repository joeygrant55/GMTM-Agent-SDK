"""Every GMTM RDS connection verifies the server certificate and host name (rds_tls.py). No database."""
import ssl
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rds_tls  # noqa: E402


def test_bundle_is_the_aws_rds_ca_set():
    context = ssl.create_default_context(cafile=str(rds_tls.CA_BUNDLE))
    names = {dict(x[0] for x in c["subject"]).get("organizationalUnitName") for c in context.get_ca_certs()}
    assert len(context.get_ca_certs()) >= 100 and names == {"Amazon RDS"}


@pytest.mark.parametrize("module, call", [
    ("profile_api", lambda m: m._get_gmtm_db()),
    ("combine_api", lambda m: m._get_gmtm_db()),
    ("agent_api", lambda m: m._get_gmtm_db()),
    ("db_connector", lambda m: m._ReadOnlyGmtmDb().execute_query("SELECT 1")),
])
def test_gmtm_connections_verify_the_certificate(monkeypatch, module, call):
    m = __import__(module)
    for key, value in {"DB_HOST": "gmtm.example.us-east-1.rds.amazonaws.com", "DB_USER": "u", "DB_PASSWORD": "p"}.items():
        monkeypatch.setenv(key, value)
    seen = {}

    def connect(**kwargs):
        seen.update(kwargs)
        raise ConnectionRefusedError("no database in tests")
    monkeypatch.setattr(m.pymysql, "connect", connect)
    with pytest.raises(ConnectionRefusedError):
        call(m)
    assert seen["ssl_ca"] == str(rds_tls.CA_BUNDLE) and seen["ssl_verify_cert"] is True and seen["ssl_verify_identity"] is True
