"""Bounded immutable block reuse + independent restore of DBVORA synthetic SQLite snapshots.

Not a customer archive, encrypted vault, signed proof, automatic retention,
power-loss certified chain or permission to delete older generations.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

from dbvora.archive.request_service import _snapshot_source
from dbvora.archive.safe_zip import (
    ArchiveError, MAX_SNAPSHOT_BYTES, _directory, _integrity_check,
    _hash_file, _staging_file, _sync_staged_file, _sync_directory,
    _publish_new, _publish_new_ntfs,
)

CHUNK_BYTES = 64 * 1024
MAX_CHUNKS = (MAX_SNAPSHOT_BYTES + CHUNK_BYTES - 1) // CHUNK_BYTES
MAX_MANIFEST_BYTES = 512 * 1024
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
MANIFEST = re.compile(r"dbvora-[a-f0-9]{32}\.json\Z")
CONTRACT = "dbvora.synthetic-incremental-blocks.v1"


class IncrementalError(ValueError):
    """Error code only, never files, data, DSNs or paths."""


def _directories(source: Path, first, second):
    try:
        a, b = _directory(first), _directory(second)
        if (a == b or source.parent in (a, b) or
                any(x == source or x in source.parents for x in (a, b))):
            raise IncrementalError("SEPARATE_DIRECTORIES_REQUIRED")
        return a, b
    except ArchiveError:
        raise IncrementalError("INVALID_OUTPUT_DIRECTORY") from None


def _read_chunk(root: Path, digest: str) -> bytes:
    file = root / (digest + ".chunk")
    if DIGEST.fullmatch(digest) is None:
        raise IncrementalError("INVALID_CHUNK_DIGEST")
    try:
        before = file.lstat()
        if (not stat.S_ISREG(before.st_mode) or file.is_symlink() or
                before.st_nlink != 1 or not 1 <= before.st_size <= CHUNK_BYTES):
            raise IncrementalError("UNSAFE_CHUNK")
        fd = os.open(file, os.O_RDONLY | getattr(os, "O_BINARY", 0) |
                     getattr(os, "O_NOFOLLOW", 0))
        try:
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino, opened.st_size) != (
                    before.st_dev, before.st_ino, before.st_size):
                raise IncrementalError("CHUNK_REPLACED")
            data = os.read(fd, CHUNK_BYTES + 1)
            after = os.fstat(fd)
            named = file.lstat()
            if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
                    before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) or (
                    named.st_dev, named.st_ino, named.st_size, named.st_mtime_ns) != (
                    before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                raise IncrementalError("CHUNK_CHANGED")
        finally:
            os.close(fd)
        if len(data) != before.st_size or hashlib.sha256(data).hexdigest() != digest:
            raise IncrementalError("CHUNK_CORRUPT")
        return data
    except IncrementalError:
        raise
    except OSError:
        raise IncrementalError("CHUNK_UNAVAILABLE") from None


def _write_chunk(root: Path, data: bytes) -> tuple[str, bool]:
    digest = hashlib.sha256(data).hexdigest()
    final = root / (digest + ".chunk")
    if os.path.lexists(final):
        if _read_chunk(root, digest) != data:
            raise IncrementalError("CHUNK_COLLISION")
        return digest, False
    staged = _staging_file(root)
    try:
        staged.write_bytes(data)
        _sync_staged_file(staged)
        try:
            if os.name == "nt":
                # Never convert an unverified native publish failure to success.
                _publish_new_ntfs(staged, root, final)
            else:
                try:
                    os.link(staged, final, follow_symlinks=False)
                except FileExistsError:
                    if _read_chunk(root, digest) != data:
                        raise IncrementalError("CHUNK_COLLISION")
                    return digest, False
                _sync_directory(root)
                # A newly-linked POSIX inode has nlink=2 until the staging
                # name goes away. Verify it only after nlink returns to 1.
                staged.unlink(missing_ok=True)
                _sync_directory(root)
        except ArchiveError:
            raise IncrementalError("CHUNK_PUBLISH_UNVERIFIED") from None
        if _read_chunk(root, digest) != data:
            raise IncrementalError("CHUNK_VERIFY_FAILED")
        return digest, True
    except IncrementalError:
        raise
    except (OSError, ArchiveError):
        raise IncrementalError("CHUNK_WRITE_FAILED") from None
    finally:
        staged.unlink(missing_ok=True)


def create_incremental(snapshot_path: str | Path, chunk_dir: str | Path,
                       manifest_dir: str | Path, *, synthetic_only=False,
                       accept_plaintext=False) -> dict:
    if synthetic_only is not True:
        raise IncrementalError("SYNTHETIC_ONLY_REQUIRED")
    if accept_plaintext is not True:
        raise IncrementalError("PLAINTEXT_ACK_REQUIRED")
    try:
        snapshot, sha, before = _snapshot_source(snapshot_path)
        chunks, manifests = _directories(snapshot, chunk_dir, manifest_dir)
        names, total, fresh, reused, written = [], 0, 0, 0, 0
        with snapshot.open("rb") as stream:
            while True:
                block = stream.read(CHUNK_BYTES)
                if not block:
                    break
                total += len(block)
                if total > MAX_SNAPSHOT_BYTES or len(names) >= MAX_CHUNKS:
                    raise IncrementalError("TOO_LARGE")
                digest, new = _write_chunk(chunks, block)
                names.append(digest)
                fresh += int(new)
                reused += int(not new)
                written += len(block) if new else 0
        stat_now = snapshot.stat()
        after = (stat_now.st_dev, stat_now.st_ino, stat_now.st_size,
                 stat_now.st_mtime_ns, stat_now.st_ctime_ns)
        if after != before or not 100 <= total <= MAX_SNAPSHOT_BYTES or _hash_file(snapshot)[0] != sha:
            raise IncrementalError("SOURCE_CHANGED")
        record = {"contract": CONTRACT, "chunk_bytes": CHUNK_BYTES,
                  "snapshot_sha256": sha, "snapshot_size_bytes": total,
                  "chunks": names}
        encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if len(encoded) > MAX_MANIFEST_BYTES:
            raise IncrementalError("MANIFEST_TOO_LARGE")
        staged = _staging_file(manifests)
        try:
            staged.write_bytes(encoded)
            published = _publish_new(staged, manifests, ".json")
        finally:
            staged.unlink(missing_ok=True)
        return {
            "status": "PUBLISHED_INCREMENTAL_SYNTHETIC_ONLY",
            "manifest_name": published.name, "snapshot_sha256": sha,
            "source_bytes": total, "chunks": len(names),
            "new_chunks": fresh, "reused_chunks": reused,
            "new_stored_bytes": written, "source_unchanged": True,
            "signed": False, "encrypted": False,
            "automatic_deletion": False, "power_loss_verified": False,
            "ready_for_customer_data": False,
        }
    except IncrementalError:
        raise
    except (ArchiveError, OSError, ValueError):
        raise IncrementalError("INCREMENTAL_CREATE_FAILED") from None


def _strict_manifest(raw: bytes) -> dict:
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise IncrementalError("DUPLICATE_KEY")
            obj[key] = value
        return obj
    try:
        obj = json.loads(raw, object_pairs_hook=unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except IncrementalError:
        raise
    except (ValueError, UnicodeError, TypeError):
        raise IncrementalError("INVALID_MANIFEST") from None
    if (type(obj) is not dict
            or set(obj) != {"contract", "chunk_bytes", "snapshot_sha256",
                            "snapshot_size_bytes", "chunks"}
            or obj["contract"] != CONTRACT or obj["chunk_bytes"] != CHUNK_BYTES):
        raise IncrementalError("INVALID_MANIFEST")
    size, names = obj["snapshot_size_bytes"], obj["chunks"]
    if (type(size) is not int or not 100 <= size <= MAX_SNAPSHOT_BYTES
            or type(names) is not list or len(names) != (size + CHUNK_BYTES - 1) // CHUNK_BYTES
            or len(names) > MAX_CHUNKS or type(obj["snapshot_sha256"]) is not str
            or DIGEST.fullmatch(obj["snapshot_sha256"]) is None
            or any(type(x) is not str or DIGEST.fullmatch(x) is None for x in names)):
        raise IncrementalError("INVALID_MANIFEST")
    return obj


def restore_incremental(manifest_path: str | Path, chunk_dir: str | Path,
                        output_dir: str | Path, *, synthetic_only=False,
                        accept_plaintext=False) -> dict:
    if synthetic_only is not True:
        raise IncrementalError("SYNTHETIC_ONLY_REQUIRED")
    if accept_plaintext is not True:
        raise IncrementalError("PLAINTEXT_ACK_REQUIRED")
    if not isinstance(manifest_path, (str, Path)) or not Path(manifest_path).is_absolute():
        raise IncrementalError("INVALID_MANIFEST_PATH")
    manifest = Path(manifest_path)
    if MANIFEST.fullmatch(manifest.name) is None:
        raise IncrementalError("INVALID_MANIFEST_PATH")
    try:
        chunks, output = _directories(manifest, chunk_dir, output_dir)
        before = manifest.lstat()
        if (not stat.S_ISREG(before.st_mode) or manifest.is_symlink()
                or before.st_nlink != 1 or before.st_size > MAX_MANIFEST_BYTES):
            raise IncrementalError("UNSAFE_MANIFEST")
        raw = manifest.read_bytes()
        if (len(raw) != before.st_size
                or manifest.stat().st_mtime_ns != before.st_mtime_ns):
            raise IncrementalError("MANIFEST_CHANGED")
        parsed = _strict_manifest(raw)
        staged = _staging_file(output)
        try:
            total = 0
            h = hashlib.sha256()
            with staged.open("wb") as dest:
                for sha in parsed["chunks"]:
                    data = _read_chunk(chunks, sha)
                    total += len(data)
                    if total > parsed["snapshot_size_bytes"]:
                        raise IncrementalError("SIZE_MISMATCH")
                    dest.write(data)
                    h.update(data)
                dest.flush()
                os.fsync(dest.fileno())
            if total != parsed["snapshot_size_bytes"] or h.hexdigest() != parsed["snapshot_sha256"]:
                raise IncrementalError("DIGEST_MISMATCH")
            _integrity_check(staged)
            result = _publish_new(staged, output, ".sqlite")
            return {
                "status": "RESTORED_INCREMENTAL_SYNTHETIC_ONLY",
                "restored_name": result.name, "restored_sha256": h.hexdigest(),
                "restored_bytes": total, "sqlite_integrity": "ok",
                "customer_ready": False, "power_loss_verified": False,
                "signed": False, "encrypted": False,
            }
        finally:
            staged.unlink(missing_ok=True)
    except IncrementalError:
        raise
    except (ArchiveError, OSError, ValueError):
        raise IncrementalError("INCREMENTAL_RESTORE_FAILED") from None
