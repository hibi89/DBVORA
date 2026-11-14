"""P1-C3: verify saved artifacts after a process restart, without changing them.

All potentially sensitive bytes are copied into a *separate temporary directory*
first and verified there. Nothing under the inspected output directory is written,
restored, removed or renamed. Checksums are not signatures or an authenticity proof.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

from dbvora.archive.safe_zip import (
    ArchiveError, MAX_ARCHIVE_BYTES, MAX_SNAPSHOT_BYTES, _directory,
    _hash_file, _integrity_check, _unpack_verified, _TEMP_NAME,
)
from dbvora.archive.zstd_archive import _verify_to_temp

PUBLISHED = re.compile(r"^dbvora-[a-f0-9]{32}\.(sqlite|zip|dbvz)$")
MAX_ENTRIES = 250
MAX_DIRECTORY_ENTRIES = 5000
COPY_CHUNK = 1024 * 1024


def _snapshot_metadata(path: Path):
    """Return identity/times for a regular, non-symlink, single-link artifact."""
    value = path.lstat()
    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
        raise ArchiveError("UNSAFE_ENTRY", "Artifact is not a standalone regular file.")
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _stable_copy(source: Path, destination: Path, maximum: int) -> tuple[str, int]:
    """Never follow final symlinks; refuse mutable/replaced source during copy."""
    first = _snapshot_metadata(source)
    if first[2] > maximum:
        raise ArchiveError("TOO_LARGE", "Artifact exceeds inspection size limit.")
    fd = None
    try:
        fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino, opened.st_size,
                opened.st_mtime_ns, opened.st_ctime_ns) != first:
            raise ArchiveError("RACE_DETECTED", "Artifact changed while being inspected.")
        digest = hashlib.sha256()
        size = 0
        with os.fdopen(fd, "rb", closefd=False) as read, destination.open("wb") as write:
            for block in iter(lambda: read.read(COPY_CHUNK), b""):
                size += len(block)
                if size > maximum:
                    raise ArchiveError("TOO_LARGE", "Artifact grew beyond inspection size limit.")
                digest.update(block)
                write.write(block)
        after_fd = os.fstat(fd)
        current = _snapshot_metadata(source)
        after = (after_fd.st_dev, after_fd.st_ino, after_fd.st_size,
                 after_fd.st_mtime_ns, after_fd.st_ctime_ns)
        if after != first or current != first or size != first[2]:
            raise ArchiveError("RACE_DETECTED", "Artifact changed while being inspected.")
        return digest.hexdigest(), size
    except ArchiveError:
        raise
    except OSError:
        raise ArchiveError("INSPECTION_FAILED", "Unable to read artifact safely.") from None
    finally:
        if fd is not None:
            os.close(fd)


def _verify_one(path: Path, suffix: str, directory: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="dbvora-check-") as temp:
        base = Path(temp)
        frozen = base / ("source." + suffix)
        maximum = MAX_SNAPSHOT_BYTES if suffix == "sqlite" else MAX_ARCHIVE_BYTES
        digest, size = _stable_copy(path, frozen, maximum)
        if suffix == "sqlite":
            _integrity_check(frozen)
            evidence = "standalone_sqlite_integrity_check"
            restored_sha = digest
        elif suffix == "zip":
            result = _unpack_verified(frozen, base / "restored.sqlite")
            evidence = "zip_manifest_sha256_and_restored_sqlite_integrity"
            restored_sha = result["restored_sha256"]
        elif suffix == "dbvz":
            result = _verify_to_temp(frozen, base / "frame.zst", base / "restored.sqlite")
            evidence = "zstd_frame_and_restored_sqlite_sha256_integrity"
            restored_sha = result["restored_sha256"]
        else:
            raise ArchiveError("UNSUPPORTED_FORMAT", "Unsupported artifact type.")
        # The verifier has never observed the original writer's fsync or commit.
        return {
            "status": "CONTENT_VERIFIED_PUBLISH_UNPROVEN",
            "bytes": size,
            "artifact_sha256": digest,
            "snapshot_sha256": restored_sha,
            "evidence": evidence,
        }



def inspect_recovery_artifact(archive_path: str | Path) -> dict:
    """Read-only content preview for one generated ZIP/ZSTD archive."""
    if not isinstance(archive_path, (str, Path)) or not str(archive_path):
        raise ArchiveError("INVALID_ARCHIVE", "Select an absolute DBVORA archive.")
    target = Path(archive_path)
    if not target.is_absolute():
        raise ArchiveError("INVALID_ARCHIVE", "Select an absolute DBVORA archive.")
    match = PUBLISHED.fullmatch(target.name)
    if match is None or match.group(1) not in ("zip", "dbvz"):
        raise ArchiveError("UNSUPPORTED_FORMAT", "Select a generated ZIP or ZSTD archive.")
    folder = _directory(target.parent)
    path = folder / target.name
    suffix = match.group(1)
    record = {
        "name": path.name,
        "kind": suffix,
        "authentication": "unsigned_untrusted",
        "publication_durability": "unknown_no_persisted_commit_evidence",
    }
    try:
        record.update(_verify_one(path, suffix, folder))
    except ArchiveError as exc:
        record.update({"status": "FAILED_REVIEW", "error_code": exc.code})
    except (OSError, ValueError):
        record.update({"status": "FAILED_REVIEW", "error_code": "INSPECTION_FAILED"})
    return record


def inspect_recovery_catalog(output_dir: str | Path, *, max_entries: int = MAX_ENTRIES) -> dict:
    """Read-only post-restart audit; never infers atomic/durable publication.

    Recognized names must be DBVORA-generated-style names. Nonmatching names,
    symlinks and directories aren't opened or followed. No cleanup is performed.
    """
    if type(max_entries) is not int or not 1 <= max_entries <= MAX_ENTRIES:
        raise ArchiveError("CATALOG_LIMIT", "Unsupported maximum number of entries.")
    folder = _directory(output_dir)
    try:
        items = []
        for item in folder.iterdir():
            if len(items) >= MAX_DIRECTORY_ENTRIES:
                raise ArchiveError("CATALOG_LIMIT", "Directory contains too many files for safe inventory.")
            items.append(item)
        items.sort(key=lambda item: item.name)
    except OSError:
        raise ArchiveError("INSPECTION_FAILED", "Unable to enumerate the archive directory.") from None
    accepted = [(p, match.group(1)) for p in items if (match := PUBLISHED.fullmatch(p.name))]
    incomplete = [p for p in items if _TEMP_NAME.fullmatch(p.name)]
    if len(accepted) + len(incomplete) > max_entries:
        raise ArchiveError("CATALOG_LIMIT", "Archive inventory exceeds the review limit.")
    records = []
    for file, suffix in accepted:
        entry = {"name": file.name, "kind": suffix,
                 "authentication": "unsigned_untrusted",
                 "publication_durability": "unknown_no_persisted_commit_evidence"}
        try:
            entry.update(_verify_one(file, suffix, folder))
        except ArchiveError as exc:
            entry.update({"status": "FAILED_REVIEW", "error_code": exc.code})
        except (OSError, ValueError):
            entry.update({"status": "FAILED_REVIEW", "error_code": "INSPECTION_FAILED"})
        records.append(entry)
    for file in incomplete:
        try:
            temp_info = file.lstat()
            state = "UNPUBLISHED_OR_ACTIVE" if stat.S_ISREG(temp_info.st_mode) else "UNSAFE_TEMP_ENTRY"
        except OSError:
            state = "UNSAFE_TEMP_ENTRY"
        records.append({"name": file.name, "kind": "temporary",
                        "status": state, "removal": "not_performed"})
    return {
        "contract_version": "p1-c3.audit.v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "inspection_mode": "read_only_no_cleanup",
        "records": sorted(records, key=lambda item: item["name"]),
        "ignored_entry_count": len(items) - len(accepted) - len(incomplete),
        "complete": True,
    }
