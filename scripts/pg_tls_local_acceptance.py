"""Real PostgreSQL 16 TLS verify-full / least-privilege acceptance on localhost only.

Requires an ephemeral synthetic database prepared by the CI workflow.
Never prints or stores the DSN, credentials, schema paths, or connection errors.
A real network connection is used, but restricted to the local test container.
Not a customer DB or production acceptance; no remote host is supported.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

from dbvora.connectors import postgres_reader as pg

from dbvora.connectors.postgres_reader import PostgresInventoryError, inspect_postgres
from dbvora.multi_engine_report import assemble_workspace, render_report

_CANARY = "SYNTHETIC_ROW_MUST_NEVER_BE_EXPORTED"
_EXPECTED = {"users", "events", "event_view"}


def verify() -> dict:
    result = {
        "contract": "dbvora.local-pg16-tls-live.v1",
        "status": "FAIL_CLOSED",
        "checks": [],
        "real_postgres": False,
        "verified_tls": False,
        "read_only_role": False,
        "customer_data": False,
        "customer_ready": False,
    }
    phase = "ENVIRONMENT"
    last_query = "NONE"
    safe_sqlstate = "NONE"
    try:
        import psycopg
        dsn = os.environ.get("DBVORA_SYNTHETIC_PG_DSN", "")
        bad_ca = os.environ.get("DBVORA_SYNTHETIC_BAD_CA", "")
        if not dsn or not bad_ca or not Path(bad_ca).is_file():
            raise ValueError("TEST_ENV_UNAVAILABLE")
        # Only CI's temporary loopback container, never an operator's DB.
        parsed = psycopg.conninfo.conninfo_to_dict(dsn)
        if (parsed.get("host") != "localhost" or parsed.get("port") != "55439"
                or parsed.get("dbname") != "dbvora_test" or
                parsed.get("user") != "dbvora_reader" or
                "password" in parsed or "passfile" in parsed):
            raise ValueError("LOOPBACK_ONLY_REQUIRED")
        phase = "TLS_ROLE"
        with psycopg.connect(dsn, sslmode="verify-full", connect_timeout=5,
                             autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT ssl FROM pg_catalog.pg_stat_ssl WHERE pid=pg_backend_pid()")
                if cursor.fetchone() != (True,):
                    raise ValueError("TLS_NOT_ACTIVE")
                cursor.execute("SHOW transaction_read_only")
                if cursor.fetchone() != ("on",):
                    raise ValueError("ROLE_NOT_READ_ONLY")
                cursor.execute("SELECT has_table_privilege(current_user,"
                               " 'public.users','INSERT')")
                if cursor.fetchone() != (False,):
                    raise ValueError("UNEXPECTED_WRITE_PERMISSION")
        result["real_postgres"] = True
        result["verified_tls"] = True
        result["read_only_role"] = True
        result["checks"].append("real_postgres_verified_tls_readonly")
        # Exercise actual production connector, not the synthetic catalog fake.
        phase = "CONNECTOR"
        original_rows = pg._rows
        def traced_rows(connection, statement, *args):
            nonlocal last_query, safe_sqlstate
            if statement == pg.TABLES:
                last_query = "TABLES"
            elif statement == pg.COLUMNS:
                last_query = "COLUMNS"
            elif statement == pg.PRIMARY_KEY:
                last_query = "PRIMARY_KEY"
            elif statement == pg.INDEXES:
                last_query = "INDEXES"
            elif statement == pg.FOREIGN_KEYS:
                last_query = "FOREIGN_KEYS"
            else:
                last_query = "OTHER"
            try:
                return original_rows(connection, statement, *args)
            except Exception as exc:
                candidate = getattr(exc, "sqlstate", "")
                safe_sqlstate = (candidate if isinstance(candidate, str)
                                 and len(candidate) == 5 and candidate.isalnum()
                                 else "UNKNOWN")
                raise
        with patch.object(pg, "_rows", traced_rows):
            catalog = inspect_postgres(dsn, include_statistics=True)
        phase = "CATALOG"
        tables = {table["name"]: table for table in catalog["tables"]}
        if not _EXPECTED.issubset(tables):
            raise ValueError("MISSING_SYNTHETIC_TABLES")
        if (tables["event_view"]["relation_kind"] != "v"
                or tables["event_view"]["size_bytes"] is not None):
            raise ValueError("VIEW_SIZE_FALSE_MEASUREMENT")
        if (tables["events"]["primary_key_columns"] != ["id"]
                or tables["users"]["primary_key_columns"] != ["id"]):
            raise ValueError("PRIMARY_KEY_MISSING")
        fk = next((x for x in catalog["relationships"]
                   if x["from_table"] == "events"
                   and x["to_table"] == "users"), None)
        if fk is None or fk["from_columns"] != ["user_id"] or fk["to_columns"] != ["id"]:
            raise ValueError("DECLARED_FK_MISSING")
        if _CANARY in json.dumps(catalog, ensure_ascii=False):
            raise ValueError("PRIVATE_ROW_LEAK")
        result["checks"].append("real_catalog_fks_views_no_rows")
        phase = "STATISTICS"
        if (tables["users"]["statistics"].get("status") not in
                ("observed", "unavailable") or
                tables["event_view"]["statistics"].get("status") != "unavailable"):
            raise ValueError("STATISTICS_PROVENANCE_WRONG")
        result["checks"].append("real_pg_statistics_provenance")
        phase = "HTML"
        workspace = assemble_workspace([catalog])
        html = render_report(workspace)
        if (_CANARY in html or "events" not in html or "users" not in html
                or not html.lower().startswith("<!doctype html")):
            raise ValueError("PG_REPORT_UNSAFE")
        # Only generated report text; no written HTML or private DSN.
        result["checks"].append("real_pg_to_offline_html_no_rows")
        # Same host, but untrusted CA MUST fail without fallback or URL/secret leaks.
        phase = "BAD_CERTIFICATE"
        wrong = dsn + " sslrootcert=" + bad_ca
        try:
            inspect_postgres(wrong)
        except PostgresInventoryError as exc:
            if exc.code != "PG_CONNECTION_FAILED":
                raise ValueError("WRONG_CA_NOT_REJECTED") from None
        else:
            raise ValueError("WRONG_CA_ACCEPTED")
        result["checks"].append("wrong_certificate_fail_closed")
        if (catalog.get("ready_for_customer_data") is not False
                or "password" in json.dumps(result).lower()):
            raise ValueError("UNSAFE_TEST_OUTPUT")
        result["status"] = "PASS_SYNTHETIC_LOCAL_POSTGRES_TLS_ONLY"
    except PostgresInventoryError as exc:
        # These are stable public connector codes; never include libpq errors.
        result["error_code"] = ("CONNECTOR_" + exc.code + "_AT_" + last_query
                                + "_STATE_" + safe_sqlstate)
    except Exception:
        # Deliberately suppress exception messages that may include a DSN.
        # The fixed phase name makes CI failures diagnosable without secrets.
        result["error_code"] = "FAILED_PHASE_" + phase
    return result


def main() -> int:
    report = verify()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS_SYNTHETIC_LOCAL_POSTGRES_TLS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
