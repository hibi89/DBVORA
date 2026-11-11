"""Opt-in, synthetic-only archive request service (prototype, not customer-ready).

Uses the existing local archive engine and P3 reservation ledger; never schedules,
retries, deletes, uploads or overwrites an original. A recorded request digest is
not proof of exactly-once execution or power-loss durability.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat

from dbvora.archive import request_ledger
from dbvora.archive.recovery_catalog import PUBLISHED, _verify_one
from dbvora.archive.safe_zip import (
    ArchiveError, _directory, _hash_file, _integrity_check, make_zip_archive,
)
from dbvora.archive.zstd_archive import create_zstd_archive
from dbvora.connectors.sqlite_reader import validate_path
from dbvora.errors import InventoryError


class RequestServiceError(Exception):
    """Bounded, source-path-free public outcome."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _snapshot_identity(source: Path) -> tuple[int, int, int, int, int]:
    try:
        info = source.lstat()
    except OSError:
        raise RequestServiceError("SNAPSHOT_UNAVAILABLE") from None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RequestServiceError("UNSAFE_SNAPSHOT")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _snapshot_source(path: str | Path) -> tuple[Path, str, tuple[int, int, int, int, int]]:
    if not isinstance(path, (str, Path)) or not Path(path).is_absolute():
        raise RequestServiceError("GENERATED_SNAPSHOT_REQUIRED")
    candidate = Path(path)
    match = PUBLISHED.fullmatch(candidate.name)
    if match is None or match.group(1) != "sqlite":
        raise RequestServiceError("GENERATED_SNAPSHOT_REQUIRED")
    try:
        source, _, _ = validate_path(candidate)
        before = _snapshot_identity(source)
        _integrity_check(source)
        sha, _ = _hash_file(source)
        if _snapshot_identity(source) != before:
            raise RequestServiceError("SNAPSHOT_CHANGED")
        return source, sha, before
    except InventoryError:
        raise RequestServiceError("INVALID_SNAPSHOT") from None
    except ArchiveError as exc:
        raise RequestServiceError(exc.code) from None
    except (OSError, ValueError, TypeError):
        raise RequestServiceError("SNAPSHOT_UNAVAILABLE") from None


def archive_once(snapshot_path: str | Path, archive_directory: str | Path,
                 ledger_directory: str | Path, request_id: str, *, codec: str = "zip",
                 level: int | None = None, synthetic_only: bool = False,
                 accept_plaintext: bool = False) -> dict:
    """One synthetic reservation and archive attempt; all repeats fail closed.

    The independently verified published artifact is recorded as an *unverified*
    ledger digest, intentionally. Successful content inspection is not a signed
    receipt or a physical crash-durability assertion.
    """
    if synthetic_only is not True:
        raise RequestServiceError("SYNTHETIC_ONLY_REQUIRED")
    if accept_plaintext is not True:
        raise RequestServiceError("PLAINTEXT_ACK_REQUIRED")
    if codec not in ("zip", "zstd"):
        raise RequestServiceError("UNSUPPORTED_CODEC")
    if codec == "zip" and level is not None:
        raise RequestServiceError("UNSUPPORTED_LEVEL")
    if codec == "zstd" and (type(level) is not int or level not in (1, 3, 9)):
        raise RequestServiceError("UNSUPPORTED_LEVEL")
    try:
        output = _directory(archive_directory)
        ledger = request_ledger._directory(ledger_directory)
    except ArchiveError as exc:
        raise RequestServiceError(exc.code) from None
    except request_ledger.LedgerError as exc:
        raise RequestServiceError(str(exc)) from None

    source, sha, before = _snapshot_source(snapshot_path)
    if ledger.resolve() in (output.resolve(), source.parent.resolve()) or output == source.parent:
        raise RequestServiceError("SEPARATE_DIRECTORY_REQUIRED")
    plan = {
        "contract": "dbvora.synthetic.archive-once.v1", "snapshot_sha256": sha,
        "codec": codec, "level": level, "destination": str(output),
    }
    plan_sha = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    try:
        reserved = request_ledger.reserve(ledger, request_id, plan_sha)
    except request_ledger.LedgerError as exc:
        raise RequestServiceError(str(exc)) from None
    if reserved.get("status") != "RESERVED_NOT_EXECUTED":
        # No retry or implicit use of a previously published artifact.
        raise RequestServiceError("REQUEST_REPLAY_HELD")
    try:
        if codec == "zip":
            created = make_zip_archive(source, output)
        else:
            created = create_zstd_archive(source, output, level=level)
        path = Path(created["archive_path"])
        expected_kind = "zip" if codec == "zip" else "dbvz"
        if path.parent != output or not (m := PUBLISHED.fullmatch(path.name)) or m.group(1) != expected_kind:
            raise RequestServiceError("INVALID_PUBLISHED_ARTIFACT")
        independent = _verify_one(path, expected_kind, output)
        if (independent["artifact_sha256"] != created["archive_sha256"]
                or independent["snapshot_sha256"] != sha
                or created["snapshot_sha256"] != sha
                or _snapshot_identity(source) != before
                or _hash_file(source)[0] != sha):
            raise RequestServiceError("POST_ARCHIVE_VERIFICATION_FAILED")
        recorded = request_ledger.record_artifact(ledger, request_id, plan_sha,
                                                  independent["artifact_sha256"])
        if recorded["status"] != "RECORDED_UNVERIFIED":
            raise RequestServiceError("LEDGER_RECORD_NOT_NEW")
        return {
            "status": "RECORDED_UNVERIFIED", "artifact_name": path.name,
            "artifact_sha256": independent["artifact_sha256"], "snapshot_sha256": sha,
            "independently_restored_content_verified": True,
            "new_archive_created": True, "request_replay_held": True,
            "ready_for_customer_data": False, "exactly_once_verified": False,
            "windows_ntfs_verified": False, "power_loss_verified": False,
        }
    except ArchiveError as exc:
        # Leave RESERVED until an owner has independently reviewed any leftover
        # published artifact. Never turn a failed operation into an auto retry.
        raise RequestServiceError(exc.code) from None
    except request_ledger.LedgerError as exc:
        raise RequestServiceError(str(exc)) from None
    except (OSError, ValueError, TypeError):
        raise RequestServiceError("OPERATION_FAILED") from None
