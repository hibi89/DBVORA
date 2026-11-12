"""Offline-testable PostgreSQL catalog inventory; no table rows or user SQL.

Opt-in connection requires psycopg 3, a user-provided approved DSN, verified
TLS by default, and a read-only transaction. No connection is attempted on
import. This connector is not yet tested against a real PostgreSQL server.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from typing import Any

MAX_TABLES = 300
MAX_COLUMNS = 300
MAX_INDEXES = 300
MAX_FOREIGN_KEYS = 300

TABLES = """
SELECT n.nspname, c.relname, c.oid::bigint, c.relkind,
       CASE WHEN c.relkind IN ('r', 'm')
            THEN pg_catalog.pg_total_relation_size(c.oid)
            ELSE NULL::bigint END
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p', 'v', 'm')
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND n.nspname NOT LIKE 'pg_toast%'
ORDER BY n.nspname COLLATE "C", c.relname COLLATE "C"
LIMIT %s
"""
COLUMNS = """
SELECT attname, pg_catalog.format_type(atttypid, atttypmod), attnotnull, attnum
FROM pg_catalog.pg_attribute
WHERE attrelid = %s AND attnum > 0 AND NOT attisdropped
ORDER BY attnum LIMIT %s
"""
PRIMARY_KEY = """
SELECT conkey FROM pg_catalog.pg_constraint
WHERE conrelid = %s AND contype = 'p' LIMIT 2
"""
INDEXES = """
SELECT ci.relname, ix.indisunique, ix.indisprimary, ix.indpred IS NOT NULL,
       ix.indkey::smallint[], ix.indnkeyatts
FROM pg_catalog.pg_index AS ix
JOIN pg_catalog.pg_class AS ci ON ci.oid = ix.indexrelid
WHERE ix.indrelid = %s ORDER BY ci.relname COLLATE "C" LIMIT %s
"""
FOREIGN_KEYS = """
SELECT conname, confrelid::bigint, conkey, confkey
FROM pg_catalog.pg_constraint
WHERE conrelid = %s AND contype = 'f'
ORDER BY conname COLLATE "C" LIMIT %s
"""


class PostgresInventoryError(Exception):
    """Stable safe errors never include a DSN, credential or server response."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _rows(connection: Any, statement: str, *args: object) -> list:
    # No caller-provided SQL or interpolated identifiers, only literal SELECT.
    with closing(connection.cursor()) as cursor:
        cursor.execute(statement, args)
        return list(cursor.fetchall())


def _array(value: Any, maximum: int) -> list[int]:
    if not isinstance(value, (tuple, list)) or len(value) > maximum:
        raise PostgresInventoryError("INVALID_CATALOG")
    if any(type(x) is not int or x < 0 or x > 32767 for x in value):
        raise PostgresInventoryError("INVALID_CATALOG")
    return list(value)


def inspect_catalog(connection: Any, *, include_statistics: bool = False) -> dict:
    """Read existing read-only PostgreSQL connection; return metadata only.

    Caller must already have an authorized connection with a read-only role.
    Using a read-write connection is rejected, not silently downgraded.
    """
    if getattr(connection, "read_only", None) is not True:
        raise PostgresInventoryError("READ_ONLY_CONNECTION_REQUIRED")
    if type(include_statistics) is not bool:
        raise PostgresInventoryError("INVALID_STATISTICS_OPTION")
    try:
        catalog = _rows(connection, TABLES, MAX_TABLES + 1)
        if len(catalog) > MAX_TABLES:
            raise PostgresInventoryError("CATALOG_LIMIT")
        oids: dict[int, tuple[str, str]] = {}
        tables: list[dict] = []
        details: list[tuple[int, dict]] = []
        for item in catalog:
            if not isinstance(item, (tuple, list)) or len(item) != 5:
                raise PostgresInventoryError("INVALID_CATALOG")
            schema, name, oid, kind, size = item
            if (not all(type(v) is str and 1 <= len(v) <= 256 for v in (schema, name, kind))
                    or kind not in ('r', 'p', 'v', 'm')
                    or type(oid) is not int or oid <= 0 or oid in oids
                    or (size is not None and (type(size) is not int or size < 0))):
                raise PostgresInventoryError("INVALID_CATALOG")
            oids[oid] = schema, name
            result = {"schema": schema, "name": name, "relation_kind": kind,
                      "size_bytes": size,
                      "size_provenance": "pg_total_relation_size" if size is not None
                                         else "unavailable_not_storage_or_transient",
                      "columns": [], "primary_key_columns": [],
                      "indexes": [], "foreign_keys": []}
            tables.append(result)
            details.append((oid, result))
        relations = []
        attributes_by_oid = {}
        unresolved_fk_columns = []
        for oid, result in details:
            column_rows = _rows(connection, COLUMNS, oid, MAX_COLUMNS + 1)
            if len(column_rows) > MAX_COLUMNS:
                raise PostgresInventoryError("CATALOG_LIMIT")
            attnums = {}
            for entry in column_rows:
                if not isinstance(entry, (tuple, list)) or len(entry) != 4:
                    raise PostgresInventoryError("INVALID_CATALOG")
                name, declared, not_null, attnum = entry
                if (type(name) is not str or not 1 <= len(name) <= 256
                        or type(declared) is not str or len(declared) > 256
                        or type(not_null) is not bool
                        or type(attnum) is not int or attnum < 1 or attnum in attnums):
                    raise PostgresInventoryError("INVALID_CATALOG")
                attnums[attnum] = name
                result["columns"].append({"name": name, "type": declared,
                                          "nullable_declared": not not_null,
                                          "attnum": attnum})
            attributes_by_oid[oid] = attnums
            pk_rows = _rows(connection, PRIMARY_KEY, oid)
            if len(pk_rows) > 1:
                raise PostgresInventoryError("INVALID_CATALOG")
            if pk_rows:
                key_nums = _array(pk_rows[0][0], MAX_COLUMNS)
                if not key_nums or any(n not in attnums for n in key_nums):
                    raise PostgresInventoryError("INVALID_CATALOG")
                result["primary_key_columns"] = [attnums[n] for n in key_nums]
            ix_rows = _rows(connection, INDEXES, oid, MAX_INDEXES + 1)
            if len(ix_rows) > MAX_INDEXES:
                raise PostgresInventoryError("CATALOG_LIMIT")
            for ix in ix_rows:
                if len(ix) != 6:
                    raise PostgresInventoryError("INVALID_CATALOG")
                ix_name, unique, primary, partial, keys, key_count = ix
                if (type(ix_name) is not str or len(ix_name) > 256
                        or not all(type(flag) is bool for flag in (unique, primary, partial))
                        or type(key_count) is not int):
                    raise PostgresInventoryError("INVALID_CATALOG")
                key_nums = _array(keys, MAX_COLUMNS)
                if not 0 <= key_count <= len(key_nums):
                    raise PostgresInventoryError("INVALID_CATALOG")
                result["indexes"].append({"name": ix_name, "unique": unique,
                                          "primary": primary, "partial": partial,
                                          "key_columns": [attnums.get(n) if n else None
                                                          for n in key_nums[:key_count]]})
            fk_rows = _rows(connection, FOREIGN_KEYS, oid, MAX_FOREIGN_KEYS + 1)
            if len(fk_rows) > MAX_FOREIGN_KEYS:
                raise PostgresInventoryError("CATALOG_LIMIT")
            for fk in fk_rows:
                if len(fk) != 4:
                    raise PostgresInventoryError("INVALID_CATALOG")
                constraint, target_oid, local, remote = fk
                local_ids = _array(local, MAX_COLUMNS)
                remote_ids = _array(remote, MAX_COLUMNS)
                if (type(constraint) is not str or len(constraint) > 256
                        or type(target_oid) is not int or target_oid <= 0
                        or not local_ids or len(local_ids) != len(remote_ids)
                        or any(n not in attnums for n in local_ids)):
                    raise PostgresInventoryError("INVALID_CATALOG")
                dest = oids.get(target_oid)
                evidence = {"constraint": constraint, "from_columns": [attnums[n] for n in local_ids],
                            "target_in_inventory": dest is not None,
                            "to_schema": dest[0] if dest else None,
                            "to_table": dest[1] if dest else None,
                            "to_columns": [],
                            "evidence": "declared_pg_constraint_foreign_key"}
                result["foreign_keys"].append(evidence)
                unresolved_fk_columns.append((evidence, target_oid, remote_ids))
                relations.append({"from_schema": result["schema"], "from_table": result["name"],
                                  **evidence})
        # Referenced table metadata may be scanned *after* the referencing table.
        # Resolve column numbers only against actual target catalog, never guess.
        for reference, target_oid, remote_ids in unresolved_fk_columns:
            target = attributes_by_oid.get(target_oid)
            if target is not None:
                if any(n not in target for n in remote_ids):
                    raise PostgresInventoryError("INVALID_CATALOG")
                reference["to_columns"].extend(target[n] for n in remote_ids)
        if include_statistics:
            from dbvora.connectors.postgres_statistics import (
                StatisticsError, collect_relation_statistics,
            )
            try:
                statistics = collect_relation_statistics(connection, [oid for oid, _ in details])
            except StatisticsError:
                raise PostgresInventoryError("INVALID_STATISTICS") from None
            for oid, table in details:
                table["statistics"] = statistics[oid]
        return {"contract_version": "dbvora.pg_catalog.v1", "engine": "postgresql",
                "inspection_mode": "read_only_metadata_only",
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "database_count": 1, "table_count": len(tables),
                "tables": tables, "relationships": relations,
                "cpu_usage": "unavailable", "ram_usage": "unavailable",
                "ready_for_customer_data": False}
    except PostgresInventoryError:
        raise
    except Exception:
        raise PostgresInventoryError("PG_CATALOG_QUERY_FAILED") from None


def inspect_postgres(dsn: str, *, require_tls: bool = True,
                     include_statistics: bool = False) -> dict:
    """User-initiated opt-in network call; not used during offline verification."""
    if type(dsn) is not str or not dsn or len(dsn) > 4096:
        raise PostgresInventoryError("INVALID_DSN")
    if require_tls is not True:
        raise PostgresInventoryError("TLS_REQUIRED")
    if type(include_statistics) is not bool:
        raise PostgresInventoryError("INVALID_STATISTICS_OPTION")
    try:
        import psycopg
    except ImportError:
        raise PostgresInventoryError("DRIVER_UNAVAILABLE") from None
    try:
        with psycopg.connect(dsn, connect_timeout=5, sslmode="verify-full", autocommit=False,
                             options="-c statement_timeout=5000 -c lock_timeout=1000") as connection:
            connection.read_only = True
            return inspect_catalog(connection, include_statistics=include_statistics)
    except PostgresInventoryError:
        raise
    except Exception:
        raise PostgresInventoryError("PG_CONNECTION_FAILED") from None
