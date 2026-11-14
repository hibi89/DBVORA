"""Opt-in synthetic-only daily archive execution primitive.

This is NOT an installed scheduler, customer backup service, incremental
chain, automatic retry, cleanup, expiration, deletion or crash certification.
The OS may invoke this command on a future date *only* after owner approval.
The immutable date/job key reserves BEFORE snapshot creation, so an
ambiguous interrupted run is HELD for manual review, not silently retried.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys

from dbvora.archive import request_ledger, request_service
from dbvora.archive.safe_zip import ArchiveError, _directory, _hash_file, create_snapshot
from dbvora.connectors.sqlite_reader import validate_path
from dbvora.errors import InventoryError

JOB_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,19}\Z", re.ASCII)


class DailyArchiveError(ValueError):
    """Fixed public error code without source path or data."""


def _verified_day(day: str) -> str:
    if type(day) is not str or not re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", day):
        raise DailyArchiveError("INVALID_UTC_DAY")
    try:
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("invalid date")
    except ValueError:
        raise DailyArchiveError("INVALID_UTC_DAY") from None
    return day


def run_daily(source: str | Path, snapshot_dir: str | Path,
              archive_dir: str | Path, ledger_dir: str | Path,
              *, job_id: str, utc_day: str, codec: str = "zip",
              zstd_level: int | None = None, synthetic_only: bool = False,
              accept_plaintext: bool = False) -> dict:
    """Make one synthetically authorized immutable snapshot+archive per slot.

    An entire job/day slot cannot be retried after *any* post-reservation
    exception; the owner must inspect the immutable artifacts and ledger.
    """
    if synthetic_only is not True:
        raise DailyArchiveError("SYNTHETIC_ONLY_REQUIRED")
    if accept_plaintext is not True:
        raise DailyArchiveError("PLAINTEXT_ACK_REQUIRED")
    if type(job_id) is not str or JOB_ID.fullmatch(job_id) is None:
        raise DailyArchiveError("INVALID_JOB_ID")
    day = _verified_day(utc_day)
    if codec not in ("zip", "zstd") or (codec == "zip" and zstd_level is not None) or (
        codec == "zstd" and (type(zstd_level) is not int or zstd_level not in (1, 3, 9))
    ):
        raise DailyArchiveError("INVALID_CODEC_OR_LEVEL")
    try:
        # Every directory must pre-exist and be an absolute non-symlink path.
        snap, archive, ledger = (
            _directory(snapshot_dir), _directory(archive_dir),
            request_ledger._directory(ledger_dir)
        )
        if not isinstance(source, (str, Path)) or not Path(source).is_absolute():
            raise DailyArchiveError("INVALID_SOURCE")
        original, _, _ = validate_path(Path(source))
        resolved = [x.resolve(strict=True) for x in (snap, archive, ledger)]
        if (len(set(resolved)) != 3 or original.parent.resolve(strict=True) in resolved
                or any(item == original or item in original.parents for item in resolved)):
            raise DailyArchiveError("SEPARATE_DIRECTORIES_REQUIRED")
        # Fail safely if source is replaced or modified, before and after run.
        stat_before = original.stat()
        identity = (stat_before.st_dev, stat_before.st_ino, stat_before.st_size,
                    stat_before.st_mtime_ns, stat_before.st_ctime_ns)
        source_digest = _hash_file(original)[0]
    except (ArchiveError, request_ledger.LedgerError, InventoryError, OSError):
        raise DailyArchiveError("INVALID_SOURCE_OR_DESTINATION") from None

    request_id = "daily-" + job_id + "-" + day.replace("-", "")
    archive_request_id = "archive-" + job_id + "-" + day.replace("-", "")
    # Digest includes full local paths only as private hash input; the ledger
    # and JSON response never serialize paths, DSNs or source file contents.
    canonical = {
        "contract": "dbvora.synthetic.daily-v1", "source": str(original),
        "archive_dir": str(archive), "snapshot_dir": str(snap),
        "job_id": job_id, "day": day, "codec": codec, "level": zstd_level,
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True,
                            separators=(",", ":")).encode("utf-8")).hexdigest()
    try:
        reservation = request_ledger.reserve(ledger, request_id, digest)
    except request_ledger.LedgerError as exc:
        raise DailyArchiveError(str(exc)) from None
    if reservation.get("status") != "RESERVED_NOT_EXECUTED":
        raise DailyArchiveError("DAILY_SLOT_HELD_FOR_MANUAL_REVIEW")
    # After this point NEVER retry automatically; a crash may leave an
    # intact snapshot/archive that the next invocation must not overwrite.
    try:
        published = create_snapshot(original, snap)
        snapshot = Path(published["snapshot_path"])
        result = request_service.archive_once(
            snapshot, archive, ledger, archive_request_id,
            codec=codec, level=zstd_level, synthetic_only=True,
            accept_plaintext=True,
        )
        observed = original.stat()
        after_identity = (observed.st_dev, observed.st_ino, observed.st_size,
                          observed.st_mtime_ns, observed.st_ctime_ns)
        if after_identity != identity or _hash_file(original)[0] != source_digest:
            raise DailyArchiveError("SOURCE_CHANGED_REQUIRES_MANUAL_REVIEW")
        if (result.get("status") != "RECORDED_UNVERIFIED"
                or result.get("independently_restored_content_verified") is not True):
            raise DailyArchiveError("ARCHIVE_REQUIRES_MANUAL_REVIEW")
        marked = request_ledger.record_artifact(
            ledger, request_id, digest, result["artifact_sha256"]
        )
        if marked.get("status") != "RECORDED_UNVERIFIED":
            raise DailyArchiveError("DAILY_LEDGER_NOT_RECORDED")
        return {
            "contract": "dbvora.synthetic.daily-v1",
            "status": "RECORDED_UNVERIFIED_REQUIRES_OWNER_REVIEW",
            "utc_day": day, "job_id": job_id,
            "snapshot_name": snapshot.name,
            "artifact_name": result["artifact_name"],
            "artifact_sha256": result["artifact_sha256"],
            "source_unchanged": True, "independently_restored_content_verified": True,
            "automatic_retries": False, "automatic_deletion": False,
            "scheduler_installed": False, "incremental_archive_verified": False,
            "exactly_once_verified": False, "ready_for_customer_data": False,
        }
    except DailyArchiveError:
        raise
    except (ArchiveError, request_service.RequestServiceError,
            request_ledger.LedgerError) as exc:
        # Fixed codes only; never reveal original paths or exception chains.
        raise DailyArchiveError(getattr(exc, "code", str(exc))) from None
    except Exception:
        raise DailyArchiveError("DAILY_ATTEMPT_FAILED_REQUIRES_MANUAL_REVIEW") from None


def run_weekly(source: str | Path, snapshot_dir: str | Path,
               archive_dir: str | Path, ledger_dir: str | Path,
               *, job_id: str, utc_day: str, codec: str = "zip",
               zstd_level: int | None = None, synthetic_only: bool = False,
               accept_plaintext: bool = False) -> dict:
    """One immutable ISO-week UTC slot, reusing the existing daily ledger.

    Only the calendar key changes. No scheduler is installed and no automatic
    retry, deletion, promotion or customer-data connection is performed.
    """
    day = _verified_day(utc_day)
    if type(job_id) is not str or JOB_ID.fullmatch(job_id) is None or len(job_id) > 18:
        raise DailyArchiveError("INVALID_WEEKLY_JOB_ID")
    today = date.fromisoformat(day)
    monday = (today - timedelta(days=today.weekday())).isoformat()
    result = run_daily(
        source, snapshot_dir, archive_dir, ledger_dir,
        job_id="w-" + job_id, utc_day=monday, codec=codec, zstd_level=zstd_level,
        synthetic_only=synthetic_only, accept_plaintext=accept_plaintext,
    )
    return {**result, "period": "weekly", "selected_utc_day": day,
            "period_start_utc": monday, "job_id": job_id}


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse.error normally echoes the supplied invalid option value,
        # which could itself be a local path or secret. Never echo it.
        raise DailyArchiveError("INVALID_ARGUMENT")


def main(argv: list[str] | None = None) -> int:
    parser = _SafeArgumentParser(description="Synthetic-only explicit UTC date-slot archive attempt; no scheduler installed")
    parser.add_argument("--source", required=True)
    parser.add_argument("--snapshot-dir", required=True)
    parser.add_argument("--archive-dir", required=True)
    parser.add_argument("--ledger-dir", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--utc-day", required=True)
    parser.add_argument("--codec", choices=("zip", "zstd"), default="zip")
    parser.add_argument("--period", choices=("daily", "weekly"), default="daily")
    parser.add_argument("--zstd-level", type=int)
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--accept-plaintext", action="store_true")
    # argparse normally echoes raw bad user flags including private source
    # paths. Use parse_known_args and redact on malformed invocations.
    try:
        args, rest = parser.parse_known_args(argv)
        if rest:
            raise DailyArchiveError("INVALID_ARGUMENT")
        method = run_weekly if args.period == "weekly" else run_daily
        output = method(
            args.source, args.snapshot_dir, args.archive_dir, args.ledger_dir,
            job_id=args.job_id, utc_day=args.utc_day, codec=args.codec,
            zstd_level=args.zstd_level, synthetic_only=args.synthetic_only,
            accept_plaintext=args.accept_plaintext,
        )
        print(json.dumps({"ok": True, "result": output}, sort_keys=True))
        return 0
    except DailyArchiveError as exc:
        code = str(exc)
    except SystemExit:
        code = "INVALID_ARGUMENT"
    except Exception:
        code = "UNEXPECTED_FAILURE"
    print(json.dumps({"ok": False, "error_code": code}, sort_keys=True), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
