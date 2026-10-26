"""Conservative SQLite snapshot + ZIP baseline; writes only new artifacts.

No archive operations are exposed through the web API. Every input is an
explicitly selected local file or pre-existing output directory. Files named
in this module are all generated, never arbitrary ZIP paths.
"""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
import tempfile
import uuid
import zipfile

from dbvora.connectors.sqlite_reader import read_only_connection, validate_path
from dbvora.errors import InventoryError

CHUNK_SIZE = 1024 * 1024
MAX_SNAPSHOT_BYTES = 512 * 1024 * 1024  # conservative prototype limit, not a performance claim
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MANIFEST_NAME = "manifest.json"
PAYLOAD_NAME = "snapshot.sqlite"
HEX_SHA = re.compile(r"^[0-9a-f]{64}$")


class ArchiveError(Exception):
    """Error with a fixed public message; no customer path or record content."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _directory(path: str | Path) -> Path:
    if not isinstance(path, (str, Path)) or not str(path):
        raise ArchiveError("BAD_DESTINATION", "An existing absolute output directory is required.")
    target = Path(path)
    if not target.is_absolute():
        raise ArchiveError("BAD_DESTINATION", "An existing absolute output directory is required.")
    for item in (target, *target.parents):
        if item.is_symlink():
            raise ArchiveError("BAD_DESTINATION", "Symlink output locations are not supported.")
    try:
        details = target.stat()
        if not stat.S_ISDIR(details.st_mode):
            raise ArchiveError("BAD_DESTINATION", "An existing output directory is required.")
        return target.resolve(strict=True)
    except OSError:
        raise ArchiveError("BAD_DESTINATION", "The output directory is unavailable.") from None


def _hash_file(path: Path, *, limit: int = MAX_SNAPSHOT_BYTES) -> tuple[str, int]:
    hashed = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            size += len(chunk)
            if size > limit:
                raise ArchiveError("TOO_LARGE", "The artifact exceeds the prototype size limit.")
            hashed.update(chunk)
    return hashed.hexdigest(), size


def _staging_file(directory: Path) -> Path:
    try:
        fd, name = tempfile.mkstemp(prefix=".dbvora-incomplete-", suffix=".part", dir=directory)
        os.close(fd)
    except OSError:
        raise ArchiveError("STORAGE_FAILED", "Could not create a temporary artifact safely.") from None
    return Path(name)


def _staging_files(directory: Path, count: int) -> tuple[Path, ...]:
    """Allocate a group; failure on any later tempfile removes earlier ones."""
    staged = []
    try:
        for _ in range(count):
            staged.append(_staging_file(directory))
        return tuple(staged)
    except BaseException:
        for path in staged:
            path.unlink(missing_ok=True)
        raise


def _sync_directory(directory: Path) -> None:
    """Sync parent metadata when OS/filesystem supports directory fsync.

    Deliberately fail closed on unsupported systems; Windows not validated yet.
    """
    fd = None
    try:
        fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("not a directory")
        os.fsync(fd)
    except OSError:
        raise ArchiveError("DURABILITY_UNAVAILABLE", "Directory sync was not confirmed on this filesystem.") from None
    finally:
        if fd is not None:
            os.close(fd)


def _sync_staged_file(staged: Path) -> None:
    fd = None
    try:
        fd = os.open(staged, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        info = os.fstat(fd)
        by_name = staged.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                (info.st_dev, info.st_ino) != (by_name.st_dev, by_name.st_ino)):
            raise OSError("unexpected staging file")
        os.fsync(fd)
    except OSError:
        raise ArchiveError("PUBLISH_FAILED", "Staged artifact could not be flushed safely.") from None
    finally:
        if fd is not None:
            os.close(fd)


def _publish_new(staged: Path, directory: Path, suffix: str) -> Path:
    """New-name hardlink publish, after file fsync and before directory fsync.

    A failed directory sync removes only the new link. It cannot prove all
    sudden-power-loss guarantees (hardware/filesystem dependent).
    """
    _sync_staged_file(staged)
    final = directory / ("dbvora-" + uuid.uuid4().hex + suffix)
    linked = False
    try:
        os.link(staged, final, follow_symlinks=False)
        linked = True
        _sync_directory(directory)
        return final
    except (OSError, ArchiveError):
        if linked:
            try:
                final.unlink(missing_ok=True)
                _sync_directory(directory)
            except (OSError, ArchiveError):
                # Cleanup may be incomplete: never claim the new file is valid.
                pass
        raise ArchiveError("PUBLISH_FAILED", "Artifact publication could not be verified.") from None


_TEMP_NAME = re.compile(r"^\.dbvora-incomplete-[a-z0-9_]{8}\.part$")


def inspect_stale_temps(output_dir: str | Path, *, older_than_seconds: int = 86400) -> list[str]:
    """Read-only inventory of probable orphan temp filenames; never auto-delete.

    Caller must ensure no active writer before any explicit removal operation.
    """
    if type(older_than_seconds) is not int or older_than_seconds < 3600:
        raise ArchiveError("INVALID_AGE", "Minimum orphan age is one hour.")
    directory = _directory(output_dir)
    cutoff = time.time() - older_than_seconds
    candidates = []
    for path in directory.iterdir():
        if not _TEMP_NAME.fullmatch(path.name):
            continue
        try:
            info = path.lstat()
            if (stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
                    info.st_mtime < cutoff and
                    (not hasattr(os, "getuid") or info.st_uid == os.getuid())):
                candidates.append(path.name)
        except OSError:
            continue
    return sorted(candidates)


def cleanup_stale_temps(output_dir: str | Path, *, older_than_seconds: int = 86400,
                        confirm: bool = False) -> list[str]:
    """Explicit-only orphan cleanup; never called automatically during backup.

    This feature is limited to POSIX dirfd APIs. It is not a concurrency-proof
    filesystem sandbox; caller must coordinate with all other active writers.
    """
    if confirm is not True:
        raise ArchiveError("CONFIRM_REQUIRED", "Explicit cleanup confirmation is required.")
    directory = _directory(output_dir)
    if os.name != "posix" or os.unlink not in os.supports_dir_fd or os.stat not in os.supports_dir_fd:
        raise ArchiveError("RECOVERY_UNSUPPORTED", "Safe scoped cleanup is not supported here.")
    # dir_fd anchors name resolution to the inspected directory.
    fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    removed = []
    try:
        for name in inspect_stale_temps(directory, older_than_seconds=older_than_seconds):
            try:
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                        info.st_mtime >= time.time() - older_than_seconds or
                        (hasattr(os, "getuid") and info.st_uid != os.getuid())):
                    continue
                os.unlink(name, dir_fd=fd)
                removed.append(name)
            except (FileNotFoundError, PermissionError):
                continue
        if removed:
            _sync_directory(directory)
        return removed
    finally:
        os.close(fd)


def _integrity_check(path: Path) -> None:
    try:
        # A finished, closed, standalone snapshot can be opened immutable.
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True, timeout=0.5)) as con:
            rows = con.execute("PRAGMA integrity_check").fetchall()
        if rows != [("ok",)]:
            raise ArchiveError("CORRUPT_SQLITE", "The recovered SQLite database failed integrity validation.")
    except sqlite3.Error:
        raise ArchiveError("CORRUPT_SQLITE", "The recovered SQLite database failed integrity validation.") from None


def create_snapshot(source_path: str | Path, output_dir: str | Path) -> dict:
    """SQLite online backup -> validated new standalone snapshot (never source overwrite)."""
    output = _directory(output_dir)
    try:
        source, size, _ = validate_path(source_path)
    except InventoryError:
        raise ArchiveError("INVALID_SOURCE", "A readable SQLite database is required.") from None
    if size > MAX_SNAPSHOT_BYTES:
        raise ArchiveError("TOO_LARGE", "The source exceeds the prototype size limit.")
    staged = _staging_file(output)
    try:
        try:
            with read_only_connection(source) as src:
                with closing(sqlite3.connect(staged, timeout=1.0)) as dest:
                    src.backup(dest, pages=64, sleep=0.01)
        except (sqlite3.Error, InventoryError):
            raise ArchiveError("BACKUP_FAILED", "SQLite online snapshot failed safely.") from None
        _integrity_check(staged)
        sha, length = _hash_file(staged)
        published = _publish_new(staged, output, ".sqlite")
        return {"snapshot_path": str(published), "snapshot_sha256": sha, "snapshot_size_bytes": length,
                "sqlite_integrity": "ok", "source_write_performed": False}
    except OSError:
        raise ArchiveError("STORAGE_FAILED", "Snapshot storage operation failed.") from None
    finally:
        staged.unlink(missing_ok=True)


def _unpack_verified(archive: Path, staged: Path) -> dict:
    """Check ZIP members, manifest, byte limit, SHA and SQLite integrity."""
    try:
        if archive.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ArchiveError("TOO_LARGE", "The archive exceeds the prototype size limit.")
        with zipfile.ZipFile(archive, mode="r", allowZip64=False) as zf:
            members = zf.infolist()
            if [entry.filename for entry in members] != [PAYLOAD_NAME, MANIFEST_NAME]:
                raise ArchiveError("INVALID_ARCHIVE", "Archive member layout is invalid.")
            data_info, manifest_info = members
            if (data_info.file_size > MAX_SNAPSHOT_BYTES or data_info.file_size < 100
                    or manifest_info.file_size > 4096 or manifest_info.file_size < 2
                    or data_info.compress_type != zipfile.ZIP_DEFLATED
                    or manifest_info.compress_type != zipfile.ZIP_STORED
                    or any(member.is_dir() or member.flag_bits & 0x1 for member in members)):
                raise ArchiveError("INVALID_ARCHIVE", "Archive member properties are invalid.")
            manifest = json.loads(zf.read(MANIFEST_NAME).decode("utf-8"))
            sha = manifest.get("snapshot_sha256") if isinstance(manifest, dict) else None
            size = manifest.get("snapshot_size_bytes") if isinstance(manifest, dict) else None
            if (not isinstance(sha, str) or not HEX_SHA.fullmatch(sha)
                    or type(size) is not int or size != data_info.file_size
                    or manifest.get("format") != "dbvora-zip-v1"
                    or manifest.get("codec") != "zip-deflate"):
                raise ArchiveError("BAD_MANIFEST", "Archive manifest validation failed.")
            digest = hashlib.sha256()
            count = 0
            with zf.open(data_info) as inp, staged.open("wb") as out:
                for chunk in iter(lambda: inp.read(CHUNK_SIZE), b""):
                    count += len(chunk)
                    if count > MAX_SNAPSHOT_BYTES:
                        raise ArchiveError("TOO_LARGE", "The expanded payload exceeds the prototype limit.")
                    digest.update(chunk)
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            if count != size or digest.hexdigest() != sha:
                raise ArchiveError("HASH_MISMATCH", "Restored snapshot checksum mismatch.")
        _integrity_check(staged)
        return {"restored_sha256": sha, "restored_size_bytes": size, "sqlite_integrity": "ok"}
    except ArchiveError:
        raise
    except (OSError, ValueError, TypeError, UnicodeError, KeyError, RuntimeError,
            zipfile.BadZipFile, zipfile.LargeZipFile, json.JSONDecodeError):
        raise ArchiveError("INVALID_ARCHIVE", "Archive bytes could not be verified.") from None


def make_zip_archive(snapshot_path: str | Path, output_dir: str | Path) -> dict:
    """ZIP baseline; independent dry-run restore BEFORE publishing archive."""
    output = _directory(output_dir)
    try:
        snapshot, size, _ = validate_path(snapshot_path)
    except InventoryError:
        raise ArchiveError("INVALID_SOURCE", "A readable SQLite snapshot is required.") from None
    if size > MAX_SNAPSHOT_BYTES:
        raise ArchiveError("TOO_LARGE", "The snapshot exceeds the prototype size limit.")
    _integrity_check(snapshot)
    sha, length = _hash_file(snapshot)
    manifest = {"format": "dbvora-zip-v1", "codec": "zip-deflate", "snapshot_sha256": sha,
                "snapshot_size_bytes": length, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    staged, dry_run = _staging_files(output, 2)
    try:
        with zipfile.ZipFile(staged, "w", allowZip64=False) as zf:
            zf.write(snapshot, arcname=PAYLOAD_NAME, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
            zf.writestr(MANIFEST_NAME, json.dumps(manifest, sort_keys=True), compress_type=zipfile.ZIP_STORED)
        check = _unpack_verified(staged, dry_run)
        if check["restored_sha256"] != sha:
            raise ArchiveError("HASH_MISMATCH", "Archive self-verification failed.")
        archive_sha, compressed_size = _hash_file(staged, limit=MAX_ARCHIVE_BYTES)
        published = _publish_new(staged, output, ".zip")
        return {"archive_path": str(published), "archive_sha256": archive_sha,
                "archive_size_bytes": compressed_size, "snapshot_sha256": sha,
                "snapshot_size_bytes": length, "verification": "independent_restore_ok"}
    except ArchiveError:
        raise
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile):
        raise ArchiveError("ARCHIVE_FAILED", "ZIP archive creation failed safely.") from None
    finally:
        staged.unlink(missing_ok=True)
        dry_run.unlink(missing_ok=True)


def restore_zip_archive(archive_path: str | Path, output_dir: str | Path) -> dict:
    """Verify and restore to a NEW standalone SQLite file, never overwrite."""
    output = _directory(output_dir)
    if not isinstance(archive_path, (str, Path)) or not Path(archive_path).is_absolute():
        raise ArchiveError("INVALID_ARCHIVE", "An absolute archive path is required.")
    archive = Path(archive_path)
    for item in (archive, *archive.parents):
        if item.is_symlink():
            raise ArchiveError("INVALID_ARCHIVE", "Symlink archive paths are not supported.")
    if not archive.is_file():
        raise ArchiveError("INVALID_ARCHIVE", "A regular ZIP archive is required.")
    staged = _staging_file(output)
    try:
        verified = _unpack_verified(archive, staged)
        restored = _publish_new(staged, output, ".sqlite")
        return {"restored_path": str(restored), **verified}
    finally:
        staged.unlink(missing_ok=True)
