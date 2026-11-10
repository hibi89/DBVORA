"""Optional path-free SQLite workspace size baselines. No schedules or deletes."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from dbvora.safe_metadata_file import MetadataInputError, read_local_json
from dbvora.publication_cleanup import remove_new_observation
import re
import stat
import uuid

class ObservationError(Exception):
    """Safe, fixed public error code."""

CONTRACT = "dbvora.workspace-size-observation.v1"
MAX_OBSERVATION_BYTES = 512 * 1024
_ID = re.compile(r"[a-f0-9]{24}\Z")
_SIZE_SCOPE = "main_database_file_only_excludes_wal_and_shm"


def _iso(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("no timezone")
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise ObservationError("INVALID_OBSERVATION") from None


def from_workspace(workspace: dict) -> dict:
    """Capture measured aggregates only; no DB paths, rows, or source SQL."""
    if workspace.get("contract_version") != "p0-03.workspace.v1":
        raise ObservationError("INVALID_OBSERVATION")
    members = []
    for db in workspace["databases"]:
        entries = {}
        for table in db["tables"]:
            storage = table.get("storage", {})
            if storage.get("status") == "measured":
                entries[table["name"]] = storage["allocated_btree_bytes"]
        members.append({"db_id": db["db_id"], "size_bytes": db["size_bytes"],
                        "size_scope": db["size_scope"], "observed_at": db["observed_at"],
                        "btree_bytes": entries})
    result = {"contract": CONTRACT, "databases": members}
    validate_observation(result)
    return result


def validate_observation(data: dict) -> dict:
    if type(data) is not dict or set(data) != {"contract", "databases"} or data["contract"] != CONTRACT:
        raise ObservationError("INVALID_OBSERVATION")
    members = data["databases"]
    if type(members) is not list or not 2 <= len(members) <= 8:
        raise ObservationError("INVALID_OBSERVATION")
    seen = set()
    for db in members:
        if type(db) is not dict or set(db) != {"db_id", "size_bytes", "size_scope", "observed_at", "btree_bytes"}:
            raise ObservationError("INVALID_OBSERVATION")
        dbid, count = db["db_id"], db["size_bytes"]
        if (type(dbid) is not str or not _ID.fullmatch(dbid) or dbid in seen
                or type(count) is not int or count < 0 or count > 16 * 1024**4
                or db["size_scope"] != _SIZE_SCOPE):
            raise ObservationError("INVALID_OBSERVATION")
        _iso(db["observed_at"])
        seen.add(dbid)
        mapping = db["btree_bytes"]
        if type(mapping) is not dict or len(mapping) > 1000:
            raise ObservationError("INVALID_OBSERVATION")
        for name, size in mapping.items():
            if type(name) is not str or not name or len(name) > 512 or type(size) is not int or size < 0:
                raise ObservationError("INVALID_OBSERVATION")
    return data


def compare_growth(previous: dict, current: dict) -> dict:
    """Compare repeated *actual measurements*, never predict a trend."""
    validate_observation(previous)
    validate_observation(current)
    previous_by_id = {db["db_id"]: db for db in previous["databases"]}
    growth = {}
    for db in current["databases"]:
        before = previous_by_id.get(db["db_id"])
        if before is None:
            growth[db["db_id"]] = {"status": "unavailable", "reason": "no_matching_baseline"}
            continue
        if _iso(db["observed_at"]) <= _iso(before["observed_at"]):
            growth[db["db_id"]] = {"status": "unavailable", "reason": "non_increasing_observation_time"}
            continue
        tables = {name: {"status": "measured", "delta_allocated_btree_bytes": value - before["btree_bytes"][name]}
                  if name in before["btree_bytes"] else {"status": "unavailable", "reason": "no_prior_dbstat"}
                  for name, value in db["btree_bytes"].items()}
        growth[db["db_id"]] = {"status": "measured", "delta_main_file_bytes": db["size_bytes"] - before["size_bytes"],
                                "earlier_observed_at": before["observed_at"], "later_observed_at": db["observed_at"],
                                "table_deltas": tables, "trend": "two_observations_only_no_forecast"}
    return growth


def read_observation(raw: str | Path) -> dict:
    try:
        return validate_observation(read_local_json(raw, max_bytes=MAX_OBSERVATION_BYTES))
    except MetadataInputError:
        raise ObservationError("INVALID_OBSERVATION_FILE") from None


def write_observation(directory: str | Path, data: dict) -> str:
    validate_observation(data)
    content = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(content) > MAX_OBSERVATION_BYTES:
        raise ObservationError("OBSERVATION_TOO_LARGE")
    folder = Path(directory)
    if (not folder.is_absolute() or any(part.is_symlink() for part in (folder, *folder.parents))
            or not folder.is_dir()):
        raise ObservationError("INVALID_OBSERVATION_OUTPUT")
    name = "dbvora-observation-" + uuid.uuid4().hex + ".json"
    fd = None
    created_stat = None
    try:
        fd = os.open(folder / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0), 0o600)
        created_stat = os.fstat(fd)
        with os.fdopen(fd, "wb") as out:
            fd = None
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        return name
    except OSError:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        remove_new_observation(folder, name, created_stat)
        raise ObservationError("OBSERVATION_WRITE_FAILED") from None
