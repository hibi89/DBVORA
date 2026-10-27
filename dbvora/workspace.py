"""Explicit, bounded and read-only multi-SQLite topology aggregation.

No path strings, customer rows or inferred cross-database relationships leave
this module. This is not a managed DB connection registry or a backup engine.
"""
from __future__ import annotations

from pathlib import Path
from dbvora.errors import InventoryError
from dbvora.inventory import inspect_sqlite

MAX_DATABASES = 8
MAX_TOTAL_TABLES = 2000


def inspect_workspace(db_paths: list[str | Path]) -> dict:
    if not isinstance(db_paths, (list, tuple)) or not 2 <= len(db_paths) <= MAX_DATABASES:
        raise InventoryError("INVALID_DATABASE_COUNT", "Select between 2 and 8 distinct SQLite databases.")
    members = []
    seen = set()
    total_tables = 0
    total_size = 0
    edges = []
    for position, user_path in enumerate(db_paths, 1):
        inventory = inspect_sqlite(user_path)
        stable_id = inventory["db_id"]
        if stable_id in seen:
            raise InventoryError("DUPLICATE_DATABASE", "Select distinct SQLite files.")
        seen.add(stable_id)
        tables = inventory["tables"]
        total_tables += len(tables)
        if total_tables > MAX_TOTAL_TABLES:
            raise InventoryError("WORKSPACE_LIMIT", "Workspace table count exceeds the safe limit.")
        total_size += inventory["size_bytes"]
        label = f"Database {position}"
        members.append({
            "db_id": stable_id,
            "label": label,
            "engine": "sqlite",
            "size_bytes": inventory["size_bytes"],
            "size_scope": inventory["size_scope"],
            "observed_at": inventory["observed_at"],
            "provenance": inventory["provenance"],
            "tables": tables,
        })
        table_names = {table["name"] for table in tables}
        for fk in inventory["relationships"]:
            # A SQLite-declared FK can only prove a relation within that DB.
            # A missing destination has evidence but cannot become a drawn edge.
            edges.append({
                "database_id": stable_id,
                "from_table": fk["from_table"],
                "from_columns": fk["from_columns"],
                "to_table": fk["to_table"],
                "to_columns": fk["to_columns"],
                "target_in_inventory": fk["to_table"] in table_names,
                "evidence": "declared_foreign_key",
            })
    return {
        "contract_version": "p0-03.workspace.v1",
        "scope": "explicit_read_only_sqlite_metadata",
        "database_count": len(members),
        "table_count": total_tables,
        "total_main_db_size_bytes": total_size,
        "size_scope": "sum_of_main_database_files_excludes_wal_and_shm",
        "cross_database_edges_verified": 0,
        "cross_database_relationships": "not_inferred",
        "cpu_usage": "unavailable",
        "ram_usage": "unavailable",
        "databases": members,
        "relationships": edges,
    }
