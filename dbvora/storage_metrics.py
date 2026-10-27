"""Bounded, optional SQLite dbstat measurement; no table rows or DB mutations.

Allocated dbstat btree page bytes are not logical row size or physical disk
usage; the latter also depends on main database/WAL/SHM/filesystem accounting.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import time

from dbvora.connectors.sqlite_reader import read_only_connection

MAX_DBSTAT_MAIN_BYTES = 64 * 1024 * 1024
_DBSTAT_TIME_BUDGET_SECONDS = 0.75
_SCOPE = "logical_btree_pages_dbstat_including_indexes_wal_pages_possible"


def collect_table_storage(path: Path, main_file_size: int, tables: list[dict]) -> dict:
    """Optional dbstat scan on an existing read-only SQLite file, with a bound.

    A scan only returns btree aggregate page allocation for named tables and
    their indexes. Virtual table pages and unowned internal pages are excluded.
    """
    unavailable = {"status": "unavailable", "reason": "dbstat_unavailable_or_limited",
                   "scope": _SCOPE, "tables": {}}
    if (type(main_file_size) is not int or main_file_size > MAX_DBSTAT_MAIN_BYTES
            or main_file_size < 0 or not isinstance(tables, list)):
        return {**unavailable, "reason": "main_file_exceeds_scan_limit"}
    begun = time.monotonic()
    def watchdog() -> int:
        return 1 if time.monotonic() - begun > _DBSTAT_TIME_BUDGET_SECONDS else 0
    try:
        with read_only_connection(path) as con:
            con.set_progress_handler(watchdog, 1000)
            try:
                # Exactly one catalog query and a read-only grouped dbstat scan.
                schema = con.execute("SELECT type, name, tbl_name FROM sqlite_schema WHERE type IN ('table','index')").fetchall()
                alloc = dict(con.execute("SELECT name, SUM(pgsize) FROM dbstat GROUP BY name").fetchall())
            finally:
                con.set_progress_handler(None, 0)
    except (sqlite3.Error, TimeoutError, OSError):
        return unavailable
    table_names = {table["name"] for table in tables}
    owners = {name: set() for name in table_names}
    for typ, name, table in schema:
        if table not in owners:
            continue
        if typ == "index" or (typ == "table" and name == table):
            owners[table].add(name)
    result = {}
    for name, btrees in owners.items():
        if not btrees or not all(key in alloc and type(alloc[key]) is int and alloc[key] >= 0 for key in btrees):
            result[name] = {"status": "unavailable", "reason": "btree_not_measurable"}
        else:
            result[name] = {"status": "measured", "allocated_btree_bytes": sum(alloc[key] for key in btrees),
                            "btree_count": len(btrees), "source": "sqlite_dbstat_aggregate"}
    return {"status": "measured", "scope": _SCOPE, "tables": result,
            "scan_cap_main_file_bytes": MAX_DBSTAT_MAIN_BYTES}
