"""Optional PostgreSQL relation statistics. No rows, mutation or network on import.

All SQL is fixed, bound and catalog-only. Counters in pg_stat_user_tables
are *estimates*, not an exact count and not customer records.
"""
from __future__ import annotations

from contextlib import closing
from typing import Any

MAX_RELATIONS = 300
MAX_COUNTER = 2**63 - 1
STATISTICS_SQL = """
SELECT s.relid::bigint, s.n_live_tup::bigint, s.n_dead_tup::bigint,
       pg_catalog.pg_relation_size(s.relid)::bigint,
       pg_catalog.pg_indexes_size(s.relid)::bigint
FROM pg_catalog.pg_stat_user_tables AS s
WHERE s.relid = ANY(%s)
ORDER BY s.relid LIMIT %s
"""


class StatisticsError(ValueError):
    """Stable path-/credential-free failure code."""


def _ids(identifiers: list[int] | tuple[int, ...]) -> list[int]:
    if (type(identifiers) not in (list, tuple) or len(identifiers) > MAX_RELATIONS
            or any(type(value) is not int or not 1 <= value <= 2**32 - 1
                   for value in identifiers)
            or len(set(identifiers)) != len(identifiers)):
        raise StatisticsError("INVALID_RELATION_IDS")
    return list(identifiers)


def collect_relation_statistics(connection: Any, relation_ids: list[int] | tuple[int, ...]) -> dict[int, dict]:
    """Opt-in, read-only, limited pg_stat_user_tables metadata query.

    No SQL from callers, no driver import, no data rows and no connection
    ownership. Permission/query failure marks metrics unavailable, not zero.
    Invalid catalog-shaped responses fail closed. Uses supplied transaction.
    """
    if getattr(connection, "read_only", None) is not True:
        raise StatisticsError("READ_ONLY_CONNECTION_REQUIRED")
    ids = _ids(relation_ids)
    if not ids:
        return {}
    try:
        with closing(connection.cursor()) as cursor:
            cursor.execute(STATISTICS_SQL, (ids, MAX_RELATIONS + 1))
            rows = list(cursor.fetchall())
    except Exception:
        return {key: {"status": "unavailable", "reason": "pg_statistics_unavailable"} for key in ids}
    if len(rows) > len(ids):
        raise StatisticsError("INVALID_STATISTICS")
    seen: set[int] = set()
    valid = set(ids)
    parsed: dict[int, dict] = {}
    for row in rows:
        if type(row) not in (tuple, list) or len(row) != 5:
            raise StatisticsError("INVALID_STATISTICS")
        oid, live, dead, heap, indexes = row
        if (type(oid) is not int or oid not in valid or oid in seen
                or any(type(x) is not int or not 0 <= x <= MAX_COUNTER
                       for x in (live, dead, heap, indexes))):
            raise StatisticsError("INVALID_STATISTICS")
        seen.add(oid)
        parsed[oid] = {
            "status": "observed",
            "estimated_live_rows": live,
            "estimated_dead_rows": dead,
            "heap_bytes": heap,
            "index_bytes": indexes,
            "row_count_provenance": "pg_stat_user_tables_estimate_not_exact",
            "storage_provenance": "pg_relation_size_and_pg_indexes_size",
        }
    for oid in ids:
        if oid not in parsed:
            parsed[oid] = {"status": "unavailable", "reason": "relation_not_in_statistics_view"}
    return parsed
