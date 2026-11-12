"""Read-only PostgreSQL optimization review from catalog facts, never rows.

Hints are triage labels, never guaranteed waste, bloat or reclaimable bytes.
No SQL generation, optimizer execution, customer access or mutation.
"""
from __future__ import annotations

from typing import Any

MIN_DEAD_TUPLES = 1000
MIN_INDEX_BYTES = 32 * 1024 * 1024
MIN_DEAD_PERCENT = 20
MIN_INDEX_PERCENT = 75


class ReviewError(ValueError):
    """Stable path- and credential-free error."""


def review_statistics(statistics: dict | None) -> dict:
    """Return at most two conservative manual-review hints."""
    empty = {"status": "not_collected", "rules": [],
             "automatic_actions": False, "recoverable_bytes_claimed": False}
    if statistics is None:
        return empty
    if type(statistics) is not dict:
        raise ReviewError("INVALID_STATISTICS")
    if statistics.get("status") == "unavailable":
        if set(statistics) != {"status", "reason"} or statistics["reason"] not in (
            "pg_statistics_unavailable", "relation_not_in_statistics_view"):
            raise ReviewError("INVALID_STATISTICS")
        return {**empty, "status": "unavailable"}
    fields = {"status", "estimated_live_rows", "estimated_dead_rows",
              "heap_bytes", "index_bytes", "row_count_provenance", "storage_provenance"}
    if (set(statistics) != fields or statistics.get("status") != "observed"
            or statistics.get("row_count_provenance") != "pg_stat_user_tables_estimate_not_exact"
            or statistics.get("storage_provenance") != "pg_relation_size_and_pg_indexes_size"):
        raise ReviewError("INVALID_STATISTICS")
    for field in ("estimated_live_rows", "estimated_dead_rows", "heap_bytes", "index_bytes"):
        value = statistics[field]
        if type(value) is not int or not 0 <= value <= 2**63 - 1:
            raise ReviewError("INVALID_STATISTICS")
    live, dead = statistics["estimated_live_rows"], statistics["estimated_dead_rows"]
    heap, indexes = statistics["heap_bytes"], statistics["index_bytes"]
    result = {**empty, "status": "assessed_estimates_not_verified_waste"}
    if dead >= MIN_DEAD_TUPLES and dead * 100 >= MIN_DEAD_PERCENT * (live + dead):
        result["rules"].append({
            "code": "REVIEW_ESTIMATED_DEAD_ROWS",
            "label": "Estimated dead-row share warrants a manual DBA review",
            "evidence": "pg_stat_user_tables_estimate_not_exact",
            "severity": "review_only",
        })
    if (indexes >= MIN_INDEX_BYTES
            and indexes * 100 >= MIN_INDEX_PERCENT * (heap + indexes)):
        result["rules"].append({
            "code": "REVIEW_INDEX_ALLOCATION",
            "label": "Measured index allocation warrants a workload review",
            "evidence": "pg_indexes_size_and_pg_relation_size",
            "severity": "review_only",
        })
    return result
