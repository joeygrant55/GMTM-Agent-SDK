"""
Read-only GMTM database access for search_api.

search_api.py has imported `get_db` from this module since it was written, but the module
was never committed, so the search router silently failed to load in production and every
/api/athlete/{id} call returned 404. This shim provides the one method search_api uses.
"""
import os
from typing import Any, Iterable, Optional

import pymysql


class _ReadOnlyGmtmDb:
    def execute_query(self, sql: str, params: Optional[Iterable[Any]] = None) -> list[dict]:
        if not sql.strip().upper().startswith("SELECT"):
            raise ValueError("db_connector is read-only: SELECT statements only.")
        conn = pymysql.connect(
            host=os.environ["DB_HOST"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            database=os.environ.get("DB_NAME", "gmtm"),
            port=int(os.environ.get("DB_PORT", 3306)),
            cursorclass=pymysql.cursors.DictCursor,
            read_timeout=15,
        )
        try:
            with conn.cursor() as c:
                c.execute(sql, tuple(params) if params else None)
                return list(c.fetchall())
        finally:
            conn.close()


def get_db() -> _ReadOnlyGmtmDb:
    return _ReadOnlyGmtmDb()
