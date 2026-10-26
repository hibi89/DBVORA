"""Deterministic read-only SQLite schema inventory; no row content inspection."""

import hashlib
from pathlib import Path
import sqlite3

from dbvora.connectors.sqlite_reader import read_only_connection, validate_path
from dbvora.errors import InventoryError
from dbvora.metrics import observed_file_size

MAX_TABLES = 1_000
MAX_COLUMNS_PER_TABLE = 500
MAX_INDEXES_PER_TABLE = 1_000
MAX_FOREIGN_KEYS_PER_TABLE = 1_000


def _list_columns(connection: sqlite3.Connection, table_name: str) -> list[dict]:
    rows = connection.execute(
        'SELECT name, type, "notnull", pk, hidden FROM pragma_table_xinfo(?) LIMIT ?',
        (table_name, MAX_COLUMNS_PER_TABLE + 1),
    ).fetchall()
    if len(rows) > MAX_COLUMNS_PER_TABLE:
        raise InventoryError("CATALOG_LIMIT", "Database metadata exceeds the inventory limit.")
    return [
        {
            "name": name,
            "type": declared_type,
            # SQLite's catalog notnull flag describes declarations, rather
            # than all runtime nullability (e.g. INTEGER PRIMARY KEY rowid).
            "nullable_declared": not bool(not_null),
            "pk_position": pk,
            "hidden": hidden,
        }
        for name, declared_type, not_null, pk, hidden in rows
    ]


def _list_indexes(connection: sqlite3.Connection, table_name: str) -> list[dict]:
    rows = connection.execute(
        "SELECT name, \"unique\", origin, partial FROM pragma_index_list(?) ORDER BY name LIMIT ?",
        (table_name, MAX_INDEXES_PER_TABLE + 1),
    ).fetchall()
    if len(rows) > MAX_INDEXES_PER_TABLE:
        raise InventoryError("CATALOG_LIMIT", "Database metadata exceeds the inventory limit.")
    result = []
    for index_name, unique, origin, partial in rows:
        # Expression-index key columns have cid < 0 and name=None. Never
        # generate executable SQL from any user-defined schema identifier.
        index_cols = connection.execute(
            'SELECT name, cid FROM pragma_index_xinfo(?) WHERE "key"=1 ORDER BY seqno',
            (index_name,),
        ).fetchall()
        result.append({
            "name": index_name,
            "unique": bool(unique),
            "origin": origin,
            "partial": bool(partial),
            "key_columns": [name if cid >= 0 else None for name, cid in index_cols],
        })
    return result


def _list_foreign_keys(connection: sqlite3.Connection, table_name: str) -> list[dict]:
    rows = connection.execute(
        'SELECT id, seq, "table", "from", "to", on_update, on_delete '
        'FROM pragma_foreign_key_list(?) ORDER BY id, seq LIMIT ?',
        (table_name, MAX_FOREIGN_KEYS_PER_TABLE + 1)
    ).fetchall()
    if len(rows) > MAX_FOREIGN_KEYS_PER_TABLE:
        raise InventoryError("CATALOG_LIMIT", "Database metadata exceeds the inventory limit.")
    grouped = {}
    for key_id, seq, target_table, from_column, to_column, on_update, on_delete in rows:
        if key_id not in grouped:
            grouped[key_id] = {
                "id": key_id,
                "to_table": target_table,
                "from_columns": [],
                "to_columns": [],
                "on_update": on_update,
                "on_delete": on_delete,
            }
        grouped[key_id]["from_columns"].append(from_column)
        grouped[key_id]["to_columns"].append(to_column)
    return [grouped[key] for key in sorted(grouped)]


def inspect_sqlite(path: str | Path) -> dict:
    """Return metadata without querying table rows or modifying the database.

    Raises InventoryError with a path-free message when validation fails.
    """
    checked_path, initial_size, initial_mtime_ns = validate_path(path)
    tables = []
    relationships = []
    try:
        with read_only_connection(checked_path) as connection:
            names = [r[0] for r in connection.execute(
                "SELECT name FROM sqlite_schema "
                "WHERE type='table' AND name NOT GLOB 'sqlite_*' "
                "ORDER BY name COLLATE BINARY LIMIT ?",
                (MAX_TABLES + 1,),
            ).fetchall()]
            if len(names) > MAX_TABLES:
                raise InventoryError("CATALOG_LIMIT", "Database metadata exceeds the inventory limit.")
            for name in names:
                foreign_keys = _list_foreign_keys(connection, name)
                tables.append({
                    "name": name,
                    "columns": _list_columns(connection, name),
                    "foreign_keys": foreign_keys,
                    "indexes": _list_indexes(connection, name),
                })
                for fk in foreign_keys:
                    relationships.append({
                        "from_table": name,
                        "from_columns": fk["from_columns"],
                        "to_table": fk["to_table"],
                        "to_columns": fk["to_columns"],
                        "evidence": "declared_foreign_key",
                    })
    except InventoryError:
        raise
    except sqlite3.Error:
        raise InventoryError("DB_READ_FAILED", "Cannot read the SQLite schema safely.") from None
    measurement = observed_file_size(checked_path, initial_size, initial_mtime_ns)
    return {
        "contract_version": "p0-01.v1",
        "db_id": hashlib.sha256(str(checked_path).encode("utf-8")).hexdigest()[:24],
        "engine": "sqlite",
        **measurement,
        "tables": tables,
        "relationships": relationships,
    }
