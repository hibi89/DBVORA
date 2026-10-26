"""Locally observable file metrics; no fabricated per-DB CPU or RAM data."""

from datetime import datetime, timezone
from pathlib import Path

from dbvora.errors import InventoryError


def observed_file_size(path: Path, initial_size: int, initial_mtime_ns: int) -> dict:
    try:
        info = path.stat()
    except OSError:
        raise InventoryError("CHANGED_DURING_READ", "Database changed during inspection.") from None
    if info.st_size != initial_size or info.st_mtime_ns != initial_mtime_ns:
        raise InventoryError("CHANGED_DURING_READ", "Database changed during inspection.")
    return {
        "size_bytes": info.st_size,
        "size_scope": "main_database_file_only_excludes_wal_and_shm",
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "provenance": {
            "size_bytes": "measured_local_filesystem",
            "tables": "measured_sqlite_catalog",
            "relationships": "declared_sqlite_foreign_keys",
            "cpu_usage": "unavailable",
            "ram_usage": "unavailable",
            "growth_trend": "unavailable_needs_multiple_observations",
        },
    }
