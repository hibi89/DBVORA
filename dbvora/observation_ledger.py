"""Opt-in local SQLite metadata observation ledger (never opens a source DB).

The caller supplies already verified metadata, not SQL or credentials. This
module does not schedule observations, contact a network, or read customer rows.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
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


def _ledger_file(path: str | Path) -> Path:
    if not isinstance(path, (str, Path)) or not str(path):
        raise ObservationError("absolute observation ledger path required")
    file = Path(path).expanduser()
    if not file.is_absolute():
        raise ObservationError("absolute observation ledger path required")
    if any(candidate.is_symlink() for candidate in (file, *file.parents)):
        raise ObservationError("symlink ledger path is not allowed")
    if not file.parent.is_dir():
        raise ObservationError("ledger parent directory must already exist")
    if file.exists():
        try:
            info = file.lstat()
        except OSError:
            raise ObservationError("ledger file is unavailable") from None
        if not stat.S_ISREG(info.st_mode):
            raise ObservationError("ledger must be a regular file")
    return file


def validate_ledger_path(path: str | Path, *, source_path: str | Path | None = None) -> Path:
    """Validate a local ledger destination and optionally reject the source DB."""
    file = _ledger_file(path)
    if source_path is not None:
        source = Path(source_path).expanduser().resolve(strict=True)
        target = file.resolve(strict=False)
        try:
            same_file = file.exists() and os.path.samefile(file, source)
        except OSError:
            raise ObservationError("ledger file is unavailable") from None
        if target == source or same_file:
            raise ObservationError("ledger must be separate from the source database")
    return file


def _validate_ledger_connection(connection: sqlite3.Connection) -> None:
    objects = connection.execute(
        "SELECT type,name FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    if objects != [("table", "observations")]:
        raise ObservationError("existing file is not a DBVORA observation ledger")
    columns = connection.execute("PRAGMA table_info('observations')").fetchall()
    expected = [
        ("seq", "INTEGER", 0, 1),
        ("db_id", "TEXT", 1, 0),
        ("observed_at", "TEXT", 1, 0),
        ("size_bytes", "INTEGER", 1, 0),
        ("scope", "TEXT", 1, 0),
        ("prev_hash", "TEXT", 1, 0),
        ("record_hash", "TEXT", 1, 0),
    ]
    actual = [(row[1], str(row[2]).upper(), row[3], row[5]) for row in columns]
    if actual != expected:
        raise ObservationError("existing file is not a DBVORA observation ledger")
    indexes = connection.execute("PRAGMA index_list('observations')").fetchall()
    if (len(indexes) != 1 or indexes[0][2] != 1 or indexes[0][3] != "u"
            or indexes[0][4] != 0):
        raise ObservationError("existing file is not a DBVORA observation ledger")
    index_name = indexes[0][1]
    quoted = '"' + str(index_name).replace('"', '""') + '"'
    index_columns = connection.execute(f"PRAGMA index_info({quoted})").fetchall()
    if [row[2] for row in index_columns] != ["db_id", "observed_at", "scope"]:
        raise ObservationError("existing file is not a DBVORA observation ledger")


def _open_ledger_readonly(file: Path) -> sqlite3.Connection:
    connection = None
    try:
        before = file.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise ObservationError("ledger must be a regular file")
        connection = sqlite3.connect(
            file.resolve(strict=True).as_uri() + "?mode=ro", uri=True, timeout=5
        )
        after = file.lstat()
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ObservationError("ledger changed during validation")
        _validate_ledger_connection(connection)
        return connection
    except ObservationError:
        if connection is not None:
            connection.close()
        raise
    except (OSError, sqlite3.Error):
        if connection is not None:
            connection.close()
        raise ObservationError("ledger is unavailable or invalid") from None


def _connect(path: str | Path) -> sqlite3.Connection:
    file = _ledger_file(path)
    created = False
    connection = None
    try:
        if file.exists():
            probe = _open_ledger_readonly(file)
            probe.close()
            before = file.lstat()
        else:
            try:
                fd = os.open(file, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            except FileExistsError:
                raise ObservationError("ledger path appeared during creation") from None
            os.close(fd)
            created = True
            before = file.lstat()
        connection = sqlite3.connect(
            file.resolve(strict=True).as_uri() + "?mode=rw", uri=True,
            timeout=5, isolation_level=None
        )
        connection.execute("PRAGMA busy_timeout=5000")
        after = file.lstat()
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ObservationError("ledger changed during validation")
        if created:
            connection.execute("""CREATE TABLE observations (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                db_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                scope TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                UNIQUE(db_id, observed_at, scope)
            )""")
        else:
            _validate_ledger_connection(connection)
        return connection
    except ObservationError:
        if connection is not None:
            connection.close()
        raise
    except (OSError, sqlite3.Error):
        if connection is not None:
            connection.close()
        raise ObservationError("ledger is unavailable or invalid") from None


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
    file = _ledger_file(path)
    if not file.exists():
        return []
    # Reads never create or modify a ledger and reject unrelated SQLite files.
    conn = _open_ledger_readonly(file)
    try:
        try:
            rows = _rows(conn, db_id)
            _verify(rows)
            return [{"observed_at": r["observed_at"], "size_bytes": r["size_bytes"],
                     "scope": r["scope"], "record_hash": r["record_hash"]} for r in rows]
        except sqlite3.Error:
            raise ObservationError("ledger is unavailable or invalid") from None
    finally:
        conn.close()
