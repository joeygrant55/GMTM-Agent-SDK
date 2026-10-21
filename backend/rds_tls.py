"""TLS for the GMTM RDS connection: verify the server certificate and host name against the AWS RDS CA bundle.

The link already used TLS (measured 2026-10-13), but without a certificate check. Bundle source:
https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem (fetched 2026-10-21; AWS rotates CAs, refresh it then).
"""
from pathlib import Path

CA_BUNDLE = Path(__file__).resolve().parent / "data" / "rds-global-bundle.pem"


def ssl_args() -> dict:
    return {"ssl_ca": str(CA_BUNDLE), "ssl_verify_cert": True, "ssl_verify_identity": True}
