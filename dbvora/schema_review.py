"""Bounded metadata-only SQLite schema review. Findings are advisory, not SQL errors."""
from __future__ import annotations

from dbvora.sqlite_identifiers import sqlite_identifier_key

MAX_FINDINGS = 200
MAX_DATABASES = 8
MAX_TABLES = 2000
MAX_RELATIONSHIPS = 8000


class SchemaReviewError(ValueError):
    """Fixed public failure code, without schema paths or row data."""


def _name(value: object) -> bool:
    return type(value) is str and bool(value) and len(value) <= 512


def _covered(table: dict, from_columns: list[str]) -> bool:
    """Check only leading index columns or declared primary-key columns."""
    key = tuple(sqlite_identifier_key(column) for column in from_columns)
    for idx in table["indexes"]:
        if type(idx) is not dict:
            raise SchemaReviewError("INVALID_WORKSPACE")
        cols = idx.get("key_columns")
        if (type(cols) is not list or len(cols) > 500 or type(idx.get("partial")) is not bool
                or not all(col is None or _name(col) for col in cols)):
            raise SchemaReviewError("INVALID_WORKSPACE")
        if (key and not idx["partial"] and len(cols) >= len(key)
                and all(col is not None and sqlite_identifier_key(col) == target
                        for col, target in zip(cols, key))):
            return True
    pk = []
    for col in table["columns"]:
        if type(col) is not dict or not _name(col.get("name")) or type(col.get("pk_position")) is not int:
            raise SchemaReviewError("INVALID_WORKSPACE")
        if col["pk_position"] > 0:
            pk.append((col["pk_position"], col["name"]))
    pk.sort()
    return bool(key) and tuple(sqlite_identifier_key(col) for _, col in pk[: len(key)]) == key


def summarize_workspace_schema(workspace: dict) -> dict:
    """Summarize declared SQLite catalog metadata only; never query tables."""
    if (type(workspace) is not dict or workspace.get("contract_version") != "p0-03.workspace.v1"
            or type(workspace.get("databases")) is not list
            or not 2 <= len(workspace["databases"]) <= MAX_DATABASES
            or type(workspace.get("relationships")) is not list
            or len(workspace["relationships"]) > MAX_RELATIONSHIPS):
        raise SchemaReviewError("INVALID_WORKSPACE")
    lookup: dict[tuple[str, str], dict] = {}
    report = {"contract": "dbvora.schema-review.v1", "status": "REVIEW_ONLY", "advisory_only": True,
              "source": "declared_sqlite_catalog_metadata", "no_row_scanning": True,
              "total_tables": 0, "without_declared_pk": 0, "unresolved_fk_targets": 0,
              "fk_index_review": 0, "findings": [], "truncated": False}
    seen_ids = set()
    for db in workspace["databases"]:
        if (type(db) is not dict or not _name(db.get("db_id"))
                or db["db_id"] in seen_ids or type(db.get("tables")) is not list):
            raise SchemaReviewError("INVALID_WORKSPACE")
        seen_ids.add(db["db_id"])
        for table in db["tables"]:
            if (type(table) is not dict or not _name(table.get("name"))
                    or type(table.get("columns")) is not list
                    or type(table.get("indexes")) is not list
                    or len(table["columns"]) > 500 or len(table["indexes"]) > 1000):
                raise SchemaReviewError("INVALID_WORKSPACE")
            key = (db["db_id"], table["name"])
            if key in lookup or len(lookup) >= MAX_TABLES:
                raise SchemaReviewError("INVALID_WORKSPACE")
            lookup[key] = table
            report["total_tables"] += 1
            _covered(table, [])  # Validate column/index structures even without FK.
            if not any(col["pk_position"] > 0 for col in table["columns"]):
                report["without_declared_pk"] += 1
                _append(report, "NO_DECLARED_PRIMARY_KEY", db["db_id"], table["name"])
    if (type(workspace.get("database_count")) is not int
            or workspace["database_count"] != len(seen_ids)
            or type(workspace.get("table_count")) is not int
            or workspace["table_count"] != report["total_tables"]):
        raise SchemaReviewError("INVALID_WORKSPACE")
    for edge in workspace["relationships"]:
        if (type(edge) is not dict or not _name(edge.get("database_id"))
                or not _name(edge.get("from_table")) or not _name(edge.get("to_table"))
                or type(edge.get("target_in_inventory")) is not bool
                or type(edge.get("from_columns")) is not list
                or not 1 <= len(edge["from_columns"]) <= 500
                or not all(_name(column) for column in edge["from_columns"])):
            raise SchemaReviewError("INVALID_WORKSPACE")
        source = lookup.get((edge["database_id"], edge["from_table"]))
        if source is None:
            raise SchemaReviewError("INVALID_WORKSPACE")
        if not edge["target_in_inventory"]:
            report["unresolved_fk_targets"] += 1
            _append(report, "FK_TARGET_OUTSIDE_INVENTORY", edge["database_id"], edge["from_table"])
        if not _covered(source, edge["from_columns"]):
            report["fk_index_review"] += 1
            _append(report, "FK_INDEX_REVIEW", edge["database_id"], edge["from_table"])
    return report


def _append(result: dict, code: str, db_id: str, table_name: str) -> None:
    if len(result["findings"]) >= MAX_FINDINGS:
        result["truncated"] = True
        return
    result["findings"].append({"code": code, "database_id": db_id, "table": table_name,
                               "severity": "review", "evidence": "declared_catalog_only"})
