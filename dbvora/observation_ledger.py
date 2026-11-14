"""Opt-in local SQLite metadata observation ledger (never opens a source DB).

The caller supplies already verified metadata, not SQL or credentials. This
module does not schedule observations, contact a network, or read customer rows.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

CONTRACT = "dbvora.local-observation.v1"
MAX_RECORDS = 10000


class ObservationError(ValueError):
    pass


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(payload: dict) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _validate(db_id: str, observed_at: str, size_bytes: int, scope: str) -> tuple[str, str, int, str]:
    if not isinstance(db_id, str) or not (1 <= len(db_id) <= 128) or not db_id.isascii() or not all(c.isalnum() or c in "-_" for c in db_id):
        raise ObservationError("invalid database identifier")
    if not isinstance(scope, str) or scope != "sqlite_main_file_excluding_wal_shm":
        raise ObservationError("unsupported measurement scope")
    if type(size_bytes) is not int or not (0 <= size_bytes <= 2**53 - 1):
        raise ObservationError("invalid measured size")
    try:
        timestamp = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ObservationError("invalid timestamp") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ObservationError("timestamp must include timezone")
    return db_id, timestamp.astimezone(timezone.utc).isoformat(timespec="microseconds"), size_bytes, scope


def _connect(path: str | Path) -> sqlite3.Connection:
    file = Path(path)
    if file.is_symlink():
        raise ObservationError("symlink ledger is not allowed")
    if not file.parent.is_dir():
        raise ObservationError("ledger parent directory must already exist")
    connection = sqlite3.connect(str(file), timeout=5, isolation_level=None)
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("""CREATE TABLE IF NOT EXISTS observations (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        db_id TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        scope TEXT NOT NULL,
        prev_hash TEXT NOT NULL,
        record_hash TEXT NOT NULL,
        UNIQUE(db_id, observed_at, scope)
    )""")
    return connection


def _rows(conn: sqlite3.Connection, db_id: str) -> list[dict]:
    columns = ("seq", "db_id", "observed_at", "size_bytes", "scope", "prev_hash", "record_hash")
    return [dict(zip(columns, row)) for row in conn.execute(
        "SELECT seq,db_id,observed_at,size_bytes,scope,prev_hash,record_hash FROM observations WHERE db_id=? ORDER BY seq", (db_id,))]


def _verify(rows: list[dict]) -> None:
    prev = "0" * 64
    last_time = ""
    for row in rows:
        body = {k: row[k] for k in ("db_id", "observed_at", "size_bytes", "scope", "prev_hash")}
        if row["prev_hash"] != prev or row["record_hash"] != _digest(body):
            raise ObservationError("ledger integrity failure")
        if row["observed_at"] <= last_time:
            raise ObservationError("ledger timestamps are not strictly increasing")
        _validate(row["db_id"], row["observed_at"], row["size_bytes"], row["scope"])
        last_time, prev = row["observed_at"], row["record_hash"]


def append_observation(path: str | Path, *, db_id: str, observed_at: str,
                       size_bytes: int, scope: str, consent: bool = False) -> dict:
    """Append a single manually authorized sample, idempotently.

    Refuses absent consent, corrupted chains, timestamp rollback and
    conflicting same-time values. No automatic collection is performed.
    """
    if consent is not True:
        raise ObservationError("explicit owner consent required")
    db_id, observed_at, size_bytes, scope = _validate(db_id, observed_at, size_bytes, scope)
    conn = _connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = _rows(conn, db_id)
        _verify(rows)
        for row in rows:
            if row["observed_at"] == observed_at and row["scope"] == scope:
                if row["size_bytes"] != size_bytes:
                    raise ObservationError("conflicting duplicate observation")
                conn.execute("COMMIT")
                return {"status": "duplicate", "record_hash": row["record_hash"]}
        if rows and observed_at <= rows[-1]["observed_at"]:
            raise ObservationError("out-of-order observation")
        if len(rows) >= MAX_RECORDS:
            raise ObservationError("ledger capacity reached")
        body = {"db_id": db_id, "observed_at": observed_at, "size_bytes": size_bytes,
                "scope": scope, "prev_hash": rows[-1]["record_hash"] if rows else "0" * 64}
        digest = _digest(body)
        conn.execute("INSERT INTO observations(db_id,observed_at,size_bytes,scope,prev_hash,record_hash) VALUES (?,?,?,?,?,?)",
                     (db_id, observed_at, size_bytes, scope, body["prev_hash"], digest))
        conn.execute("COMMIT")
        return {"status": "appended", "record_hash": digest}
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def read_observations(path: str | Path, *, db_id: str) -> list[dict]:
    _validate(db_id, "2026-01-01T00:00:00Z", 0, "sqlite_main_file_excluding_wal_shm")
    if not Path(path).exists():
        return []
    conn = _connect(path)
    try:
        rows = _rows(conn, db_id)
        _verify(rows)
        return [{"observed_at": r["observed_at"], "size_bytes": r["size_bytes"],
                 "scope": r["scope"], "record_hash": r["record_hash"]} for r in rows]
    finally:
        conn.close()
