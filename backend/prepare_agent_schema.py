"""Explicit preparation for an existing Agent database; never imported by app startup.

No environment file, connection, or model is loaded on import or the default dry run.
Existing conversation storage is a prerequisite, not reconstructed by this command.
MySQL DDL commits implicitly: a failure may leave earlier statements applied.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping
import json
import os
import re
from typing import Any


# Preserved from the September 7 route initializers. The unsafe conversation ALTERs
# are intentionally excluded. Boolean marks only ADD COLUMN operations for which
# MySQL error 1060 (duplicate column) is the expected idempotent outcome.
STATEMENTS: tuple[tuple[str, str, bool], ...] = (
    (
        'create_sparq_profiles',
        """CREATE TABLE IF NOT EXISTS sparq_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clerk_id VARCHAR(255) NOT NULL UNIQUE,
    maxpreps_athlete_id VARCHAR(255),
    maxpreps_data JSON,
    name VARCHAR(255),
    position VARCHAR(100),
    school VARCHAR(255),
    class_year INT,
    city VARCHAR(100),
    state VARCHAR(50),
    gpa DECIMAL(3,2),
    major_area VARCHAR(100),
    hudl_url VARCHAR(500),
    combine_metrics JSON,
    recruiting_goals JSON,
    enrichment_complete TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)""",
        False,
    ),
    (
        'create_college_targets',
        """CREATE TABLE IF NOT EXISTS college_targets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sparq_profile_id INT NOT NULL,
    college_name VARCHAR(255) NOT NULL,
    college_city VARCHAR(100),
    college_state VARCHAR(50),
    division VARCHAR(20) DEFAULT 'D1',
    fit_score INT DEFAULT 75,
    fit_reasons JSON,
    status ENUM('Researching','Interested','Contacted','Visited','Offered','Committed','Declined') DEFAULT 'Researching',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_profile (sparq_profile_id)
)""",
        False,
    ),
    (
        'create_agent_sessions',
        """CREATE TABLE IF NOT EXISTS agent_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clerk_id VARCHAR(255) NOT NULL UNIQUE,
    session_id VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_clerk (clerk_id)
)""",
        False,
    ),
    (
        'create_outreach_log',
        """CREATE TABLE IF NOT EXISTS outreach_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sparq_profile_id INT NOT NULL,
    school VARCHAR(200) NOT NULL,
    coach VARCHAR(200) DEFAULT NULL,
    method ENUM("Email","Phone","Visit","Camp") NOT NULL DEFAULT "Email",
    contact_date DATE NOT NULL,
    status ENUM("Awaiting Response","Responded","Meeting Scheduled","Archived") NOT NULL DEFAULT "Awaiting Response",
    notes TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_profile (sparq_profile_id)
)""",
        False,
    ),
    (
        'add_sparq_profiles_enrichment_complete',
        """ALTER TABLE sparq_profiles ADD COLUMN enrichment_complete TINYINT(1) DEFAULT 0""",
        True,
    ),
    (
        'add_college_targets_research_data',
        """ALTER TABLE college_targets ADD COLUMN research_data JSON""",
        True,
    ),
    (
        'add_college_targets_deep_research_status',
        """ALTER TABLE college_targets ADD COLUMN deep_research_status VARCHAR(20) DEFAULT 'pending'""",
        True,
    ),
    (
        'create_agent_messages',
        """CREATE TABLE IF NOT EXISTS agent_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_conv (conversation_id)
)""",
        False,
    ),
    (
        'create_athlete_profiles',
        """CREATE TABLE IF NOT EXISTS athlete_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    clerk_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_clerk (clerk_id)
)""",
        False,
    ),
    (
        'create_athlete_links',
        """CREATE TABLE IF NOT EXISTS athlete_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    platform VARCHAR(50) NOT NULL,
    url VARCHAR(500) NOT NULL,
    label VARCHAR(120) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id)
)""",
        False,
    ),
    (
        'create_agent_reports',
        """CREATE TABLE IF NOT EXISTS agent_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    conversation_id INT DEFAULT NULL,
    report_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content MEDIUMTEXT,
    summary TEXT DEFAULT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id)
)""",
        False,
    ),
    (
        'create_artifacts',
        """CREATE TABLE IF NOT EXISTS artifacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clerk_id VARCHAR(255) NOT NULL,
    type VARCHAR(40) NOT NULL,
    state VARCHAR(40) NOT NULL DEFAULT 'draft',
    agent_id VARCHAR(64) DEFAULT NULL,
    parent_artifact_id INT DEFAULT NULL,
    title VARCHAR(255) DEFAULT NULL,
    summary TEXT DEFAULT NULL,
    payload JSON,
    sources JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_athlete_state_updated (clerk_id, state, updated_at),
    INDEX idx_athlete_type (clerk_id, type),
    INDEX idx_state_updated (state, updated_at)
)""",
        False,
    ),
    (
        'create_artifact_actions',
        """CREATE TABLE IF NOT EXISTS artifact_actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    artifact_id INT NOT NULL,
    kind VARCHAR(40) NOT NULL,
    performed_by VARCHAR(64) DEFAULT NULL,
    payload JSON,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_artifact (artifact_id, performed_at)
)""",
        False,
    ),
    (
        'create_claim_tokens',
        """CREATE TABLE IF NOT EXISTS claim_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token_hash CHAR(64) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    event_id INT NOT NULL,
    minted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    opened_at DATETIME NULL,
    claimed_at DATETIME NULL,
    clerk_id VARCHAR(255) NULL,
    INDEX idx_user (user_id),
    INDEX idx_event (event_id)
)""",
        False,
    ),
    # Junior pilot tables. Same reviewed DDL text as junior_entry.SCHEMA and
    # college_programs.SCHEMA (a test keeps them equal); prepared here in one step.
    (
        'create_sparq_entry_refusals',
        """CREATE TABLE IF NOT EXISTS sparq_entry_refusals (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    decision VARCHAR(32) NOT NULL,
    decided_at DATETIME(6) NOT NULL,
    KEY idx_entry_refusals_user (user_id)
)""",
        False,
    ),
    (
        'create_sparq_entries',
        """CREATE TABLE IF NOT EXISTS sparq_entries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    clerk_id VARBINARY(255) NOT NULL,
    user_id BIGINT NOT NULL,
    entered_at DATETIME(6) NOT NULL,
    KEY idx_entries_clerk (clerk_id, entered_at)
)""",
        False,
    ),
    (
        'create_sparq_parent_notices',
        """CREATE TABLE IF NOT EXISTS sparq_parent_notices (
    clerk_id VARBINARY(255) PRIMARY KEY,
    accepted_at DATETIME(6) NOT NULL,
    attested_by_session_kind VARCHAR(16) NOT NULL
)""",
        False,
    ),
    (
        'create_sparq_sessions',
        """CREATE TABLE IF NOT EXISTS sparq_sessions (
    clerk_id VARBINARY(255) PRIMARY KEY,
    jti VARCHAR(64) NOT NULL,
    issued_at DATETIME(6) NOT NULL
)""",
        False,
    ),
    (
        'create_sparq_college_lists',
        """CREATE TABLE IF NOT EXISTS sparq_college_lists (
    clerk_id VARBINARY(255) PRIMARY KEY,
    gmtm_gender TINYINT NULL,
    gmtm_sport VARCHAR(100) NULL,
    inputs_key CHAR(64) NULL,
    programs JSON NULL,
    built_at DATETIME(6) NULL,
    updated_at DATETIME(6) NOT NULL
)""",
        False,
    ),
)

CONVERSATION_COLUMNS = frozenset({
    "id", "clerk_id", "fork_scenario", "parent_id", "created_at", "updated_at",
})
_REQUIRED = ("HOST", "PORT", "USER", "PASSWORD", "NAME")
_FORBIDDEN_TARGET = re.compile(r"gmtm|db2[-_]dev|pre[-_]prod|family[-_]test", re.I)


class PreparationError(Exception):
    """Contains only a redacted report; database messages are never retained here."""
    def __init__(self, report: dict[str, Any]):
        self.report = report
        super().__init__(json.dumps(report, sort_keys=True))


def _guard(code: str) -> PreparationError:
    return PreparationError({"status": "failed", "stage": "validation", "reason": code})


def _error_summary(exc: Exception) -> dict[str, Any]:
    # Exception text can include passwords, connection strings, SQL, or user data.
    summary = {"type": type(exc).__name__}
    if exc.args and type(exc.args[0]) is int and 0 <= exc.args[0] <= 65535:
        summary["mysql_code"] = exc.args[0]
    return summary


def connection_settings(environ: Mapping[str, str], *, expected_host: str,
                        expected_database: str) -> dict[str, Any]:
    """Validate an explicitly acknowledged Agent target, without connecting."""
    values = {}
    for suffix in _REQUIRED:
        value = environ.get(f"AGENT_DB_{suffix}")
        if not isinstance(value, str) or not value or (suffix != "PASSWORD" and value != value.strip()):
            raise _guard(f"explicit_agent_db_{suffix.lower()}_required")
        values[suffix] = value
    host, database = values["HOST"], values["NAME"]
    # No URLs, socket paths, connection strings, embedded ports, or wildcard targets.
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?", host):
        raise _guard("invalid_agent_host")
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_$-]{0,63}", database):
        raise _guard("invalid_agent_database")
    if (_FORBIDDEN_TARGET.search(host) or _FORBIDDEN_TARGET.search(database)
            or re.search(r"(^|\.)rds\.amazonaws\.com(?:\.cn)?\.?$", host, re.I)):
        raise _guard("gmtm_or_rds_target_forbidden")
    if not expected_host or host != expected_host or not expected_database or database != expected_database:
        raise _guard("target_acknowledgment_mismatch")
    port = values["PORT"]
    if not port.isascii() or not port.isdecimal() or len(port) > 5 or not 1 <= int(port) <= 65535:
        raise _guard("invalid_agent_port")
    return {
        "host": host, "port": int(port), "user": values["USER"],
        "password": values["PASSWORD"], "database": database,
        "connect_timeout": 5, "read_timeout": 10, "write_timeout": 10,
        "autocommit": True,
    }


def _default_connector(**settings):
    import pymysql  # Driver import and any connection are explicit apply-only work.
    return pymysql.connect(**settings, cursorclass=pymysql.cursors.DictCursor)


def _check_conversations(cursor, database: str) -> None:
    """Read-only preflight of known conversation prerequisites; no schema repair."""
    cursor.execute("SELECT DATABASE() AS database_name")
    selected = cursor.fetchone()
    if not isinstance(selected, dict) or selected.get("database_name") != database:
        raise _guard("connected_database_mismatch")
    cursor.execute(
        "SELECT TABLE_TYPE AS table_type FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
        (database, "agent_conversations"),
    )
    table = cursor.fetchone()
    if not isinstance(table, dict) or table.get("table_type") != "BASE TABLE":
        raise _guard("existing_conversation_table_required")
    cursor.execute(
        "SELECT COLUMN_NAME AS column_name FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
        (database, "agent_conversations"),
    )
    columns = {row.get("column_name") for row in cursor.fetchall() if isinstance(row, dict)}
    if not CONVERSATION_COLUMNS.issubset(columns):
        raise _guard("existing_conversation_columns_required")
    cursor.execute(
        "SELECT INDEX_NAME AS index_name, NON_UNIQUE AS non_unique, "
        "COLUMN_NAME AS column_name FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY INDEX_NAME, SEQ_IN_INDEX",
        (database, "agent_conversations"),
    )
    indexes = defaultdict(list)
    for row in cursor.fetchall():
        if isinstance(row, dict) and row.get("non_unique") == 0:
            indexes[row.get("index_name")].append(row.get("column_name"))
    if any(columns == ["clerk_id"] for columns in indexes.values()):
        raise _guard("unique_conversation_clerk_index_incompatible_with_forks")


def prepare_schema(*, environ: Mapping[str, str], expected_host: str,
                   expected_database: str, connector=None) -> dict[str, Any]:
    """Apply the fixed existing-installation preparation after the explicit guards.

    DDL is not transactional. Reports record completed statements, but do not
    imply that an earlier operation was rolled back if any later step fails.
    """
    settings = connection_settings(environ, expected_host=expected_host,
                                   expected_database=expected_database)
    connection = None
    stage = "connect"
    completed: list[str] = []
    duplicates: list[str] = []
    failure = None
    try:
        connection = (connector or _default_connector)(**settings)
        stage = "conversation_preflight"
        with connection.cursor() as cursor:
            _check_conversations(cursor, settings["database"])
            for name, sql, allow_duplicate_column in STATEMENTS:
                stage = name
                try:
                    cursor.execute(sql)
                except Exception as exc:
                    if (allow_duplicate_column and exc.args
                            and type(exc.args[0]) is int and exc.args[0] == 1060):
                        duplicates.append(name)
                    else:
                        raise
                completed.append(name)
    except PreparationError as exc:
        failure = {**exc.report, "stage": stage}
    except Exception as exc:
        failure = {"status": "failed", "stage": stage, "error": _error_summary(exc)}
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception as exc:
                if failure is None:
                    failure = {"status": "failed", "stage": "close", "error": _error_summary(exc)}
                else:
                    failure["close_error"] = _error_summary(exc)
    report = {
        "completed_statements": completed,
        "duplicate_columns": duplicates,
        "ddl_is_atomic": False,
        "full_schema_validated": False,
    }
    if failure is not None:
        raise PreparationError({**failure, **report}) from None
    return {
        "status": "preparation_applied", "conversation_prerequisites": "passed",
        "limitation": "Required conversation table/column names and Clerk-only uniqueness were checked; existing column definitions and other constraints remain unverified.",
        **report,
    }


def plan() -> dict[str, Any]:
    """Safe default: list the fixed operations without reading environment values."""
    return {
        "status": "dry_run", "connected": False, "ddl_is_atomic": False,
        "prerequisite": "Existing conversation table/columns without a unique Clerk-only index; checked only on apply.",
        "statements": [name for name, _, _ in STATEMENTS],
        "limitation": "Preparation for an existing Agent installation, not a fresh database migration or full schema validation.",
    }


def main(argv=None, *, environ=None, connector=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Explicitly apply Agent-only preparation; default is a no-connection plan.")
    parser.add_argument("--expected-host", help="Exact AGENT_DB_HOST acknowledgment; never a password or URL.")
    parser.add_argument("--expected-database", help="Exact AGENT_DB_NAME acknowledgment.")
    args = parser.parse_args(argv)
    if not args.apply:
        print(json.dumps(plan(), sort_keys=True))
        return 0
    try:
        report = prepare_schema(environ=os.environ if environ is None else environ,
                                expected_host=args.expected_host,
                                expected_database=args.expected_database,
                                connector=connector)
    except PreparationError as exc:
        print(json.dumps(exc.report, sort_keys=True))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
