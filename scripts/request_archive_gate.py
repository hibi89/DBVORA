"""Synthetic-only archive/ledger integration evidence, never a customer backup.

This exercise generates its own temporary SQLite fixture, invokes the existing
archive CLI, independently compares file hashes after restore, and verifies
that a replayed request does not trigger a second archive. No scheduling,
customer path input, deletion of published artifacts or automatic resume.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile

from dbvora.archive.request_ledger import LedgerError, record_artifact, reserve
from scripts.synthetic_cli_gate import GateFailure, _generated_file, _invoke
from tests.fixtures.make_sqlite import create_fixture

REQUEST_ID = "synthetic-archive-request-0001"
PLAN_SHA = hashlib.sha256(b"dbvora.synthetic-request-zip-v1").hexdigest()
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


def _expect(condition: bool, code: str) -> None:
    if condition is not True:
        raise GateFailure(code)


def _digest(path: Path, *, max_bytes: int = 512 * 1024 * 1024) -> str:
    """Independent bounded file digest; refuse linked or mutable files."""
    import os
    import stat
    try:
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > max_bytes or before.st_size < 1):
            raise GateFailure("UNSAFE_SYNTHETIC_ARTIFACT")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            identity = (before.st_dev, before.st_ino, before.st_size,
                        before.st_mtime_ns, before.st_ctime_ns)
            check = (opened.st_dev, opened.st_ino, opened.st_size,
                     opened.st_mtime_ns, opened.st_ctime_ns)
            if identity != check:
                raise GateFailure("SYNTHETIC_ARTIFACT_CHANGED")
            h = hashlib.sha256()
            count = 0
            with os.fdopen(fd, "rb", closefd=False) as handle:
                while block := handle.read(1024 * 1024):
                    count += len(block)
                    if count > max_bytes:
                        raise GateFailure("UNSAFE_SYNTHETIC_ARTIFACT")
                    h.update(block)
            after = path.lstat()
            final = (after.st_dev, after.st_ino, after.st_size,
                     after.st_mtime_ns, after.st_ctime_ns)
            if final != identity or os.fstat(fd).st_size != count:
                raise GateFailure("SYNTHETIC_ARTIFACT_CHANGED")
            return h.hexdigest()
        finally:
            os.close(fd)
    except GateFailure:
        raise
    except (OSError, ValueError):
        raise GateFailure("SYNTHETIC_ARTIFACT_UNREADABLE") from None


def _reserve_first(folder: Path, *, request_id: str = REQUEST_ID, plan_sha: str = PLAN_SHA) -> None:
    result = reserve(folder, request_id, plan_sha)
    _expect(result.get("status") == "RESERVED_NOT_EXECUTED"
            and result.get("archive_executed") is False
            and result.get("exactly_once_verified") is False,
            "REQUEST_RESERVATION_NOT_NEW")


def run_gate(*, interrupt_after_reserve: bool = False) -> dict:
    """Exercise actual offline CLI against a generated, disposable SQLite DB.

    The injected interruption does not emulate power loss; it merely verifies
    that a reserved-but-incomplete request is held rather than blindly rerun.
    """
    with tempfile.TemporaryDirectory(prefix="dbvora-request-synthetic-") as location:
        root = Path(location)
        source_dir, snap_dir, archive_dir, restored_dir, ledger_dir = (
            root / name for name in ("source", "snap", "archive", "restored", "ledger")
        )
        for folder in (source_dir, snap_dir, archive_dir, restored_dir, ledger_dir):
            folder.mkdir()
        source = create_fixture(source_dir / "synthetic.sqlite")
        before = (_digest(source), source.stat().st_mtime_ns, source.stat().st_size)
        _reserve_first(ledger_dir)
        if interrupt_after_reserve:
            replay = reserve(ledger_dir, REQUEST_ID, PLAN_SHA)
            _expect(replay["status"] == "REPLAY_REQUIRES_MANUAL_REVIEW",
                    "PENDING_REQUEST_WAS_NOT_HELD")
            _expect(not any(snap_dir.iterdir()) and not any(archive_dir.iterdir()),
                    "PENDING_REQUEST_CREATED_ARTIFACT")
            return {"status": "PASS_PENDING_REPLAY_HELD_SYNTHETIC_ONLY",
                    "checks": 2, "archive_executed": False,
                    "ready_for_customer_data": False, "exactly_once_verified": False}

        snapshot = _invoke("snapshot", "--source", str(source), "--output-dir",
                           str(snap_dir), "--synthetic-only", "--accept-plaintext")
        snapshot_path = _generated_file(snap_dir, snapshot["snapshot_path"], "sqlite")
        snapshot_sha = _digest(snapshot_path)
        _expect(snapshot_sha == snapshot["snapshot_sha256"], "SNAPSHOT_SHA_MISMATCH")
        archive = _invoke("archive", "--snapshot", str(snapshot_path), "--output-dir",
                          str(archive_dir), "--codec", "zip", "--synthetic-only", "--accept-plaintext")
        archive_path = _generated_file(archive_dir, archive["archive_path"], "zip")
        actual_archive_sha = _digest(archive_path)
        _expect(actual_archive_sha == archive["archive_sha256"]
                and archive["snapshot_sha256"] == snapshot_sha, "ARCHIVE_SHA_MISMATCH")
        restored = _invoke("restore", "--archive", str(archive_path),
                           "--output-dir", str(restored_dir), "--synthetic-only",
                           "--accept-plaintext")
        restored_path = _generated_file(restored_dir, restored["restored_path"], "sqlite")
        _expect(_digest(restored_path) == snapshot_sha == restored["restored_sha256"],
                "RESTORE_SHA_MISMATCH")
        # A valid SQLite result is checked independently of the CLI's JSON.
        with closing(sqlite3.connect(restored_path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
            _expect(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                    "RESTORED_SQLITE_CORRUPT")
        recorded = record_artifact(ledger_dir, REQUEST_ID, PLAN_SHA, actual_archive_sha)
        _expect(recorded["status"] == "RECORDED_UNVERIFIED"
                and recorded["independent_artifact_verification"] is False,
                "LEDGER_IMPROPER_SUCCESS_CLAIM")
        replay = reserve(ledger_dir, REQUEST_ID, PLAN_SHA)
        _expect(replay["status"] == "RECORDED_REQUIRES_ARTIFACT_VERIFICATION",
                "RECORDED_REQUEST_WAS_NOT_HELD")
        _expect((_digest(source), source.stat().st_mtime_ns, source.stat().st_size) == before,
                "ORIGINAL_SOURCE_CHANGED")
        _expect(len(list(archive_dir.glob("dbvora-*.zip"))) == 1,
                "DUPLICATE_ARCHIVE_WAS_PUBLISHED")
        _expect(not any(p.name.endswith(".part") for p in root.rglob("*")),
                "ORPHAN_STAGING_FILE")
        return {"status": "PASS_SYNTHETIC_REQUEST_AND_ZIP_ONLY",
                "checks": 9, "archive_executed": True,
                "replay_held": True, "zip_restore_content_verified": True,
                "ledger_artifact_state": "RECORDED_UNVERIFIED",
                "ready_for_customer_data": False,
                "exactly_once_verified": False, "windows_ntfs_verified": False}


def main() -> int:
    try:
        report = run_gate()
    except (GateFailure, LedgerError, OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        safe_code = (str(error) if isinstance(error, (GateFailure, LedgerError))
                     and re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", str(error)) else "GATE_FAILED")
        report = {"status": "FAIL_CLOSED", "error_code": safe_code,
                  "ready_for_customer_data": False, "exactly_once_verified": False}
    except Exception:
        report = {"status": "FAIL_CLOSED", "error_code": "UNEXPECTED_GATE_FAILURE",
                  "ready_for_customer_data": False, "exactly_once_verified": False}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS_SYNTHETIC_REQUEST_AND_ZIP_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
