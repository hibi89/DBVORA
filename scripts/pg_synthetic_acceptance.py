"""Offline PostgreSQL-to-HTML acceptance using only invented catalog metadata.

Exercises production modules; NO psycopg import, DSN, socket or database calls.
Synthetic results are not live PostgreSQL, Windows or customer acceptance.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

from dbvora.connectors.postgres_reader import inspect_catalog
from dbvora.multi_engine_report import assemble_workspace, render_report, export_report


class _Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def execute(self, sql, params):
        if not sql.lstrip().startswith("SELECT ") or "FROM pg_catalog." not in sql:
            raise ValueError("UNEXPECTED_QUERY")
        if "%" not in sql:
            raise ValueError("UNBOUND_QUERY")
        self.connection.calls += 1
        if "FROM pg_catalog.pg_class AS c" in sql:
            self.rows = [
                ("public", "users", 101, "r", 12582912),
                ("public", "events", 102, "r", 65011712),
                ("public", "event_view", 103, "v", None),
            ]
        elif "FROM pg_catalog.pg_stat_user_tables" in sql:
            if params[0] != [101, 102]:
                raise ValueError("UNEXPECTED_RELATION_SCOPE")
            self.rows = [
                (101, 50000, 100, 8388608, 4194304),
                (102, 4000, 2000, 10485760, 41943040),
            ]
        elif "FROM pg_catalog.pg_attribute" in sql:
            self.rows = {
                101: [("id", "bigint", True, 1), ("email", "text", False, 2)],
                102: [("id", "bigint", True, 1), ("user_id", "bigint", True, 2)],
                103: [("user_id", "bigint", False, 1)],
            }.get(params[0], [])
        elif "FROM pg_catalog.pg_index AS ix" in sql:
            self.rows = {
                101: [("users_pkey", True, True, False, [1], 1)],
                102: [("events_pkey", True, True, False, [1], 1)],
            }.get(params[0], [])
        elif "FROM pg_catalog.pg_constraint" in sql and "contype = 'p'" in sql:
            self.rows = {101: [([1],)], 102: [([1],)]}.get(params[0], [])
        elif "FROM pg_catalog.pg_constraint" in sql and "contype = 'f'" in sql:
            self.rows = {102: [("events_user_fk", 101, [2], [1])]}.get(params[0], [])
        else:
            raise ValueError("UNEXPECTED_QUERY")

    def fetchall(self):
        return self.rows

    def close(self):
        return None


class _Connection:
    read_only = True

    def __init__(self):
        self.calls = 0

    def cursor(self):
        return _Cursor(self)


def verify() -> dict:
    result = {"status": "FAIL_CLOSED", "contract": "dbvora.pg-synthetic-e2e.v1",
              "checks": 0, "real_pg_connected": False,
              "ready_for_customer_data": False, "automatic_actions": False}
    try:
        conn = _Connection()
        catalog = inspect_catalog(conn, include_statistics=True)
        if (catalog.get("table_count") != 3 or catalog.get("ready_for_customer_data") is not False
                or conn.calls < 10):
            raise ValueError("CATALOG_CHECK_FAILED")
        result["checks"] += 1
        tables = {x["name"]: x for x in catalog["tables"]}
        if (tables["event_view"]["size_bytes"] is not None
                or tables["event_view"]["statistics"]["status"] != "unavailable"
                or tables["events"]["statistics"]["estimated_dead_rows"] != 2000
                or tables["events"]["statistics"]["index_bytes"] != 41943040):
            raise ValueError("STATISTICS_CHECK_FAILED")
        result["checks"] += 1
        workspace = assemble_workspace([catalog])
        relationships = workspace["databases"][0]["relationships"]
        if (len(relationships) != 1 or relationships[0]["from"] != "public.events"
                or relationships[0]["to"] != "public.users"
                or workspace["cross_database_edges_verified"] != 0):
            raise ValueError("RELATIONSHIP_CHECK_FAILED")
        result["checks"] += 1
        output = {table["key"]: table for table in workspace["databases"][0]["tables"]}
        review = output["public.events"]["optimization_review"]
        if (review["automatic_actions"] is not False
                or review["recoverable_bytes_claimed"] is not False
                or {x["code"] for x in review["rules"]} != {
                    "REVIEW_ESTIMATED_DEAD_ROWS", "REVIEW_INDEX_ALLOCATION"}):
            raise ValueError("REVIEW_CHECK_FAILED")
        result["checks"] += 1
        html = render_report(workspace)
        if (not all(x in html for x in (
                "Estimated live rows", "measured heap", "Optimization review",
                '"estimated_dead_rows":2000', "public.events"))
                or "postgresql://" in html or "password=" in html
                or 'connect-src \'none\'' not in html):
            raise ValueError("HTML_CHECK_FAILED")
        result["checks"] += 1
        with tempfile.TemporaryDirectory(prefix="dbvora-synthetic-pg-") as temp:
            destination = Path(temp)
            report = export_report([catalog], destination)
            if (report.get("status") != "OFFLINE_METADATA_REPORT_CREATED"
                    or report.get("ready_for_customer_data") is not False):
                raise ValueError("EXPORT_CHECK_FAILED")
            file = destination / report["filename"]
            data = file.read_bytes()
            if (len(data) != report["bytes"]
                    or hashlib.sha256(data).hexdigest() != hashlib.sha256(
                        render_report(workspace).encode("utf-8")).hexdigest()):
                raise ValueError("EXPORT_CHECK_FAILED")
        result["checks"] += 1
        result["status"] = "PASS_SYNTHETIC_PG_ONLY"
    except Exception as error:
        allowed = {"CATALOG_CHECK_FAILED", "STATISTICS_CHECK_FAILED",
                   "RELATIONSHIP_CHECK_FAILED", "REVIEW_CHECK_FAILED",
                   "HTML_CHECK_FAILED", "EXPORT_CHECK_FAILED"}
        reason = str(error)
        result["error_code"] = reason if reason in allowed else "SYNTHETIC_PG_GATE_FAILED"
    return result


def main() -> int:
    result = verify()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS_SYNTHETIC_PG_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
