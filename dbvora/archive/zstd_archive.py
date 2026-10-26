"""Offline ZSTD CLI compression for validated standalone SQLite snapshots.

Single-file DBVZSTD1 envelope: 8-byte magic + 4-byte JSON length + manifest
+ ZSTD frame. The manifest is *not authenticated*; this is not a secure backup.
Uses an optional locally installed official zstd executable; no network calls.
"""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

from dbvora.archive.safe_zip import (
    ArchiveError, MAX_ARCHIVE_BYTES, MAX_SNAPSHOT_BYTES, CHUNK_SIZE,
    _directory, _hash_file, _integrity_check, _publish_new, _staging_file,
)
from dbvora.connectors.sqlite_reader import validate_path
from dbvora.errors import InventoryError

MAGIC = b"DBVZSTD1"
MAX_MANIFEST_BYTES = 4096
ALLOWED_LEVELS = (1, 3, 9)


def _cli() -> str:
    binary = shutil.which("zstd")
    if not binary:
        raise ArchiveError("CODEC_UNAVAILABLE", "The local ZSTD command is not installed.")
    return binary


def _zstd_pipe(source: Path, output: Path, *, level: int | None = None) -> int:
    """Run trusted local CLI without shell; bound expanded output and time."""
    cmd = [_cli(), "-q", "-c"]
    if level is None:
        cmd.insert(1, "-d")
    else:
        cmd.append(f"-{level}")
    proc = None
    try:
        with source.open("rb") as inp, output.open("wb") as out:
            proc = subprocess.Popen(cmd, stdin=inp, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            written = 0
            try:
                while True:
                    chunk = proc.stdout.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > (MAX_SNAPSHOT_BYTES if level is None else MAX_ARCHIVE_BYTES):
                        raise ArchiveError("TOO_LARGE", "ZSTD output exceeds the prototype size limit.")
                    out.write(chunk)
                if proc.wait(timeout=120) != 0:
                    raise ArchiveError("CODEC_FAILED", "The local ZSTD codec rejected the artifact.")
                out.flush()
                os.fsync(out.fileno())
                return written
            finally:
                if proc.stdout is not None:
                    proc.stdout.close()
                if proc.poll() is None:
                    proc.kill()
                proc.wait()
    except ArchiveError:
        raise
    except (OSError, subprocess.SubprocessError):
        raise ArchiveError("CODEC_FAILED", "The local ZSTD operation failed safely.") from None


def _source(path: str | Path) -> Path:
    try:
        checked, size, _ = validate_path(path)
    except (InventoryError, OSError, TypeError, ValueError):
        raise ArchiveError("INVALID_SOURCE", "A valid standalone SQLite snapshot is required.") from None
    if size > MAX_SNAPSHOT_BYTES:
        raise ArchiveError("TOO_LARGE", "The snapshot exceeds the prototype size limit.")
    _integrity_check(checked)
    return checked


def _archive_path(path: str | Path) -> Path:
    if not isinstance(path, (str, Path)) or not str(path):
        raise ArchiveError("INVALID_ARCHIVE", "An absolute ZSTD archive path is required.")
    candidate = Path(path)
    if not candidate.is_absolute() or any(p.is_symlink() for p in (candidate, *candidate.parents)):
        raise ArchiveError("INVALID_ARCHIVE", "An absolute regular archive file is required.")
    try:
        stat = candidate.stat()
        if not candidate.is_file():
            raise ArchiveError("INVALID_ARCHIVE", "An absolute regular archive file is required.")
        if stat.st_size > MAX_ARCHIVE_BYTES or stat.st_size < len(MAGIC) + 4:
            raise ArchiveError("INVALID_ARCHIVE", "Archive size outside supported limits.")
        return candidate.resolve(strict=True)
    except OSError:
        raise ArchiveError("INVALID_ARCHIVE", "The ZSTD archive cannot be read.") from None


def _manifest(raw: bytes) -> dict:
    try:
        obj = json.loads(raw.decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError()
        if (obj.get("format") != "dbvora-zstd-v1" or obj.get("codec") != "zstd"
            or type(obj.get("level")) is not int or obj["level"] not in ALLOWED_LEVELS
            or type(obj.get("snapshot_size_bytes")) is not int
            or not 100 <= obj["snapshot_size_bytes"] <= MAX_SNAPSHOT_BYTES
            or type(obj.get("frame_size_bytes")) is not int
            or not 1 <= obj["frame_size_bytes"] <= MAX_ARCHIVE_BYTES
            or not all(isinstance(obj.get(key), str) and len(obj[key]) == 64
                       and all(c in "0123456789abcdef" for c in obj[key])
                       for key in ("snapshot_sha256", "frame_sha256"))):
            raise ValueError()
        return obj
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise ArchiveError("BAD_MANIFEST", "ZSTD archive manifest validation failed.") from None


def _verify_to_temp(archive: Path, extracted_frame: Path, restored: Path) -> dict:
    """Verify bounded envelope and frame first, then independently decompress and SHA-check."""
    try:
        with archive.open("rb") as src:
            if src.read(len(MAGIC)) != MAGIC:
                raise ArchiveError("INVALID_ARCHIVE", "ZSTD archive header is invalid.")
            length_bytes = src.read(4)
            if len(length_bytes) != 4:
                raise ArchiveError("INVALID_ARCHIVE", "ZSTD archive header is incomplete.")
            length = struct.unpack(">I", length_bytes)[0]
            if length < 2 or length > MAX_MANIFEST_BYTES:
                raise ArchiveError("BAD_MANIFEST", "ZSTD manifest exceeds the size limit.")
            raw = src.read(length)
            if len(raw) != length:
                raise ArchiveError("INVALID_ARCHIVE", "ZSTD manifest is truncated.")
            meta = _manifest(raw)
            h = hashlib.sha256()
            n = 0
            with extracted_frame.open("wb") as out:
                for block in iter(lambda: src.read(CHUNK_SIZE), b""):
                    n += len(block)
                    if n > MAX_ARCHIVE_BYTES or n > meta["frame_size_bytes"]:
                        raise ArchiveError("TOO_LARGE", "Compressed ZSTD frame exceeds the size limit.")
                    h.update(block)
                    out.write(block)
                out.flush()
                os.fsync(out.fileno())
            if n != meta["frame_size_bytes"] or h.hexdigest() != meta["frame_sha256"]:
                raise ArchiveError("HASH_MISMATCH", "The compressed ZSTD frame checksum did not match.")
        size = _zstd_pipe(extracted_frame, restored)
        digest, observed_size = _hash_file(restored)
        if size != meta["snapshot_size_bytes"] or observed_size != size or digest != meta["snapshot_sha256"]:
            raise ArchiveError("HASH_MISMATCH", "The restored SQLite snapshot does not match the manifest.")
        _integrity_check(restored)
        return {"restored_sha256": digest, "restored_size_bytes": size, "sqlite_integrity": "ok"}
    except ArchiveError:
        raise
    except (OSError, struct.error):
        raise ArchiveError("INVALID_ARCHIVE", "ZSTD archive could not be verified.") from None


def create_zstd_archive(snapshot_path: str | Path, output_dir: str | Path, *, level: int = 3) -> dict:
    """Create and self-restore a new ZSTD archive from a standalone SQLite snapshot."""
    if type(level) is not int or level not in ALLOWED_LEVELS:
        raise ArchiveError("INVALID_LEVEL", "Supported ZSTD compression levels are 1, 3, and 9.")
    output = _directory(output_dir)
    snapshot = _source(snapshot_path)
    sha, size = _hash_file(snapshot)
    frame, envelope, extraction, dry_run = (_staging_file(output) for _ in range(4))
    try:
        compressed = _zstd_pipe(snapshot, frame, level=level)
        frame_sha, verified_length = _hash_file(frame, limit=MAX_ARCHIVE_BYTES)
        if compressed != verified_length:
            raise ArchiveError("CODEC_FAILED", "ZSTD frame size changed during inspection.")
        meta = {"format": "dbvora-zstd-v1", "codec": "zstd", "level": level,
                "snapshot_size_bytes": size, "snapshot_sha256": sha,
                "frame_size_bytes": compressed, "frame_sha256": frame_sha,
                "created_at_utc": datetime.now(timezone.utc).isoformat()}
        raw = json.dumps(meta, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(raw) > MAX_MANIFEST_BYTES:
            raise ArchiveError("BAD_MANIFEST", "ZSTD manifest exceeds size limit.")
        with envelope.open("wb") as dest, frame.open("rb") as inp:
            dest.write(MAGIC)
            dest.write(struct.pack(">I", len(raw)))
            dest.write(raw)
            shutil.copyfileobj(inp, dest, CHUNK_SIZE)
            dest.flush()
            os.fsync(dest.fileno())
        check = _verify_to_temp(envelope, extraction, dry_run)
        if check["restored_sha256"] != sha:
            raise ArchiveError("HASH_MISMATCH", "ZSTD self-restore failed.")
        archive_sha, archive_bytes = _hash_file(envelope, limit=MAX_ARCHIVE_BYTES)
        published = _publish_new(envelope, output, ".dbvz")
        return {"archive_path": str(published), "archive_sha256": archive_sha,
                "archive_size_bytes": archive_bytes, "snapshot_sha256": sha,
                "snapshot_size_bytes": size, "level": level,
                "verification": "independent_restore_ok"}
    except ArchiveError:
        raise
    except OSError:
        raise ArchiveError("STORAGE_FAILED", "ZSTD archive creation failed safely.") from None
    finally:
        for path in (frame, envelope, extraction, dry_run):
            path.unlink(missing_ok=True)


def restore_zstd_archive(archive_path: str | Path, output_dir: str | Path) -> dict:
    """Validate frame, checksum and SQLite integrity, publish only NEW restore file."""
    output = _directory(output_dir)
    archive = _archive_path(archive_path)
    extraction, restored = _staging_file(output), _staging_file(output)
    try:
        result = _verify_to_temp(archive, extraction, restored)
        result["restored_path"] = str(_publish_new(restored, output, ".sqlite"))
        return result
    finally:
        extraction.unlink(missing_ok=True)
        restored.unlink(missing_ok=True)
