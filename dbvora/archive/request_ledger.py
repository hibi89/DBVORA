"""Opt-in local request reservation ledger for future archive idempotency.

Not connected to archive publication. It can prevent duplicate *authorization*
for the same request key; it does not establish exactly-once artifact creation,
Windows durability, power-loss safety, or customer readiness.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
from urllib.parse import quote

LEDGER_NAME = ".dbvora-request-ledger-v1.sqlite"
MAX_LEDGER_BYTES = 32 * 1024 * 1024
MAX_REQUESTS = 10000
APPLICATION_ID = 0x44425652  # DBVR
REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}\Z", re.ASCII)
DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class LedgerError(ValueError):
    """Safe, path-free public error code."""


def _directory(root: str | Path) -> Path:
    if not isinstance(root, (str, Path)):
        raise LedgerError("INVALID_LEDGER_DIRECTORY")
    path = Path(root)
    if not path.is_absolute():
        raise LedgerError("INVALID_LEDGER_DIRECTORY")
    try:
        for ancestor in (path, *path.parents):
            info = ancestor.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise LedgerError("UNSAFE_LEDGER_DIRECTORY")
        if not stat.S_ISDIR(path.lstat().st_mode):
            raise LedgerError("UNSAFE_LEDGER_DIRECTORY")
    except LedgerError:
        raise
    except OSError:
        raise LedgerError("LEDGER_DIRECTORY_UNAVAILABLE") from None
    return path


def _validate(request_id: str, plan_sha256: str) -> str:
    if type(request_id) is not str or REQUEST_ID.fullmatch(request_id) is None:
        raise LedgerError("INVALID_REQUEST_ID")
    if type(plan_sha256) is not str or DIGEST.fullmatch(plan_sha256) is None:
        raise LedgerError("INVALID_PLAN_DIGEST")
    # The plaintext request-id is never stored on disk.
    return hashlib.sha256(request_id.encode("ascii")).hexdigest()


def _file_identity(path: Path) -> tuple[int, int]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_LEDGER_BYTES:
        raise LedgerError("UNSAFE_LEDGER_FILE")
    return (info.st_dev, info.st_ino)


def _connect(root: Path, *, create: bool = True):
    path = root / LEDGER_NAME
    made_new = False
    try:
        if not create and not path.exists():
            raise LedgerError("UNRESERVED_REQUEST")
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                         getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
            made_new = True
        identity = _file_identity(path)
        if not made_new:
            uri = "file:" + quote(str(path), safe="/") + "?mode=ro"
            # A concurrent creator may expose an empty, not-yet-initialized file.
            # Give that race a bounded 1s grace period; never initialize an unknown
            # existing database or overwrite a corrupt/unrecognized ledger.
            checked = False
            for attempt in range(50):
                current = path.lstat()
                if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != identity:
                    raise LedgerError("LEDGER_REPLACED")
                if current.st_size < 100:
                    time.sleep(0.02)
                    continue
                with closing(sqlite3.connect(uri, uri=True, timeout=2.0)) as verifier:
                    version = verifier.execute("PRAGMA user_version").fetchone()[0]
                    app_id = verifier.execute("PRAGMA application_id").fetchone()[0]
                    if version == 1 and app_id == APPLICATION_ID:
                        checked = True
                        break
                    if version != 0 or app_id not in (0, APPLICATION_ID):
                        raise LedgerError("UNTRUSTED_LEDGER_FILE")
                if attempt < 49:
                    time.sleep(0.02)
            if not checked:
                raise LedgerError("UNTRUSTED_LEDGER_FILE")
        # SQLite is only used on the explicitly selected existing local directory.
        connection = sqlite3.connect(path, timeout=2.0, isolation_level=None)
        if _file_identity(path) != identity:
            connection.close()
            raise LedgerError("LEDGER_REPLACED")
        try:
            mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
            if mode.lower() != "delete":
                raise LedgerError("LEDGER_JOURNAL_UNAVAILABLE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA busy_timeout=2000")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("CREATE TABLE IF NOT EXISTS requests ("
                               "request_key TEXT PRIMARY KEY, plan_sha TEXT NOT NULL, "
                               "phase TEXT NOT NULL CHECK(phase IN ('RESERVED','RECORDED')), "
                               "artifact_sha TEXT)")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise LedgerError("LEDGER_VERSION_MISMATCH")
            connection.execute("PRAGMA user_version=1")
            connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
            connection.execute("COMMIT")
            return connection
        except BaseException:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            connection.close()
            raise
    except LedgerError:
        raise
    except (sqlite3.Error, OSError, ValueError):
        raise LedgerError("LEDGER_UNAVAILABLE") from None


def _transaction(connection, operation):
    try:
        connection.execute("BEGIN IMMEDIATE")
        result = operation(connection)
        connection.execute("COMMIT")
        return result
    except BaseException:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise


def reserve(root: str | Path, request_id: str, plan_sha256: str) -> dict:
    """Reserve a request once; any replay fails closed for actual publication."""
    request_key = _validate(request_id, plan_sha256)
    directory = _directory(root)
    try:
        with closing(_connect(directory)) as connection:
            def operation(db):
                found = db.execute("SELECT plan_sha,phase FROM requests WHERE request_key=?",
                                   (request_key,)).fetchone()
                if found is not None:
                    if found[0] != plan_sha256:
                        raise LedgerError("REQUEST_PLAN_CONFLICT")
                    return "REPLAY_REQUIRES_MANUAL_REVIEW" if found[1] == "RESERVED" else "RECORDED_REQUIRES_ARTIFACT_VERIFICATION"
                count = db.execute("SELECT count(*) FROM requests").fetchone()[0]
                if count >= MAX_REQUESTS:
                    raise LedgerError("LEDGER_CAPACITY_EXCEEDED")
                db.execute("INSERT INTO requests(request_key,plan_sha,phase,artifact_sha) VALUES(?,?,'RESERVED',NULL)",
                           (request_key, plan_sha256))
                return "RESERVED_NOT_EXECUTED"
            status = _transaction(connection, operation)
        return {"status": status, "archive_executed": False,
                "ready_for_customer_data": False, "exactly_once_verified": False}
    except LedgerError:
        raise
    except sqlite3.Error:
        raise LedgerError("LEDGER_UNAVAILABLE") from None


def record_artifact(root: str | Path, request_id: str, plan_sha256: str,
                    artifact_sha256: str) -> dict:
    """Record caller-supplied digest; independent artifact verification is mandatory."""
    request_key = _validate(request_id, plan_sha256)
    if type(artifact_sha256) is not str or DIGEST.fullmatch(artifact_sha256) is None:
        raise LedgerError("INVALID_ARTIFACT_DIGEST")
    directory = _directory(root)
    try:
        with closing(_connect(directory, create=False)) as connection:
            def operation(db):
                found = db.execute("SELECT plan_sha,phase,artifact_sha FROM requests WHERE request_key=?",
                                   (request_key,)).fetchone()
                if found is None:
                    raise LedgerError("UNRESERVED_REQUEST")
                if found[0] != plan_sha256:
                    raise LedgerError("REQUEST_PLAN_CONFLICT")
                if found[1] == "RECORDED":
                    if found[2] != artifact_sha256:
                        raise LedgerError("ARTIFACT_DIGEST_CONFLICT")
                    return "PREVIOUSLY_RECORDED_UNVERIFIED"
                if found[1] != "RESERVED":
                    raise LedgerError("LEDGER_STATE_INVALID")
                db.execute("UPDATE requests SET phase='RECORDED',artifact_sha=? WHERE request_key=?",
                           (artifact_sha256, request_key))
                return "RECORDED_UNVERIFIED"
            status = _transaction(connection, operation)
        return {"status": status, "independent_artifact_verification": False,
                "ready_for_customer_data": False, "exactly_once_verified": False}
    except LedgerError:
        raise
    except sqlite3.Error:
        raise LedgerError("LEDGER_UNAVAILABLE") from None
