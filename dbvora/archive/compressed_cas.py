"""Versioned zlib compressed CAS v2 for DBVORA synthetic SQLite snapshots.

Independent from raw CAS v1. No customers, retention, deletion, signing,
encryption or physical power-loss certification.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import zlib

from dbvora.archive.incremental_cas import _directories, CHUNK_BYTES
from dbvora.archive.request_service import _snapshot_source
from dbvora.archive.safe_zip import (
    ArchiveError, MAX_SNAPSHOT_BYTES, _staging_file, _sync_staged_file,
    _sync_directory, _publish_new, _publish_new_ntfs, _hash_file, _integrity_check,
)

CONTRACT = "dbvora.synthetic-cas-zlib.v2"
MAGIC = b"DBVORA-CASZ2\x00"
MAX_STORED_BYTES = CHUNK_BYTES + 256
MAX_MANIFEST = 512 * 1024
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
MANIFEST = re.compile(r"dbvora-[a-f0-9]{32}\.json\Z")


class CompressedCasError(ValueError):
    """Fixed path-free error code."""


def _read(root: Path, key: str) -> bytes:
    if type(key) is not str or DIGEST.fullmatch(key) is None:
        raise CompressedCasError("INVALID_CHUNK_ID")
    path = root / (key + ".cz")
    try:
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                path.is_symlink() or not len(MAGIC) < before.st_size <= MAX_STORED_BYTES):
            raise CompressedCasError("INVALID_CHUNK_FILE")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
                     getattr(os, "O_BINARY", 0))
        try:
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino, opened.st_size) != (
                    before.st_dev, before.st_ino, before.st_size):
                raise CompressedCasError("CHUNK_REPLACED")
            blob = os.read(fd, MAX_STORED_BYTES + 1)
            after = os.fstat(fd)
            named = path.lstat()
            expected = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != expected
                    or (named.st_dev, named.st_ino, named.st_size, named.st_mtime_ns) != expected):
                raise CompressedCasError("CHUNK_CHANGED")
        finally:
            os.close(fd)
        if len(blob) != before.st_size or not blob.startswith(MAGIC):
            raise CompressedCasError("INVALID_CHUNK_MAGIC")
        inflater = zlib.decompressobj()
        raw = inflater.decompress(blob[len(MAGIC):], CHUNK_BYTES + 1)
        if (not 1 <= len(raw) <= CHUNK_BYTES or not inflater.eof
                or inflater.unconsumed_tail or inflater.unused_data or inflater.flush()):
            raise CompressedCasError("INVALID_COMPRESSED_CHUNK")
        if hashlib.sha256(raw).hexdigest() != key:
            raise CompressedCasError("CHUNK_HASH_MISMATCH")
        return raw
    except CompressedCasError:
        raise
    except (OSError, ValueError, zlib.error):
        raise CompressedCasError("CHUNK_UNAVAILABLE") from None


def _write_staged_exact(staged: Path, payload: bytes) -> None:
    """Refuse publication when a staged write is short or its bytes differ.

    Python file writes may report fewer bytes without an exception. The
    immutable CAS manifest must never be published from such a staging file.
    """
    written = staged.write_bytes(payload)
    if written != len(payload) or staged.read_bytes() != payload:
        raise CompressedCasError("STAGED_WRITE_UNVERIFIED")


def _put(root: Path, raw: bytes) -> tuple[str, bool]:
    key = hashlib.sha256(raw).hexdigest()
    final = root / (key + ".cz")
    if os.path.lexists(final):
        if _read(root, key) != raw:
            raise CompressedCasError("CHUNK_COLLISION")
        return key, False
    data = MAGIC + zlib.compress(raw, level=6)
    if len(data) > MAX_STORED_BYTES:
        raise CompressedCasError("COMPRESSED_CHUNK_TOO_LARGE")
    staged = _staging_file(root)
    try:
        _write_staged_exact(staged, data)
        _sync_staged_file(staged)
        if os.name == "nt":
            _publish_new_ntfs(staged, root, final)
        else:
            try:
                os.link(staged, final, follow_symlinks=False)
            except FileExistsError:
                if _read(root, key) != raw:
                    raise CompressedCasError("CHUNK_COLLISION")
                return key, False
            _sync_directory(root)
            # POSIX new hardlink has two names until staging is removed.
            staged.unlink(missing_ok=True)
            _sync_directory(root)
        if _read(root, key) != raw:
            raise CompressedCasError("CHUNK_VERIFICATION_FAILED")
        return key, True
    except CompressedCasError:
        raise
    except (OSError, ArchiveError):
        raise CompressedCasError("CHUNK_PUBLISH_UNVERIFIED") from None
    finally:
        staged.unlink(missing_ok=True)


def create_compressed(snapshot_path: str | Path, chunk_dir: str | Path,
                      manifest_dir: str | Path, *, synthetic_only=False,
                      accept_plaintext=False) -> dict:
    if synthetic_only is not True:
        raise CompressedCasError("SYNTHETIC_ONLY_REQUIRED")
    if accept_plaintext is not True:
        raise CompressedCasError("PLAINTEXT_ACK_REQUIRED")
    try:
        source, sha, identity = _snapshot_source(snapshot_path)
        chunks, manifests = _directories(source, chunk_dir, manifest_dir)
        names, new_count, reused, total, new_bytes = [], 0, 0, 0, 0
        with source.open("rb") as stream:
            while True:
                raw = stream.read(CHUNK_BYTES)
                if not raw:
                    break
                total += len(raw)
                if total > MAX_SNAPSHOT_BYTES or len(names) >= (
                        MAX_SNAPSHOT_BYTES + CHUNK_BYTES - 1) // CHUNK_BYTES:
                    raise CompressedCasError("SOURCE_TOO_LARGE")
                key, fresh = _put(chunks, raw)
                names.append(key)
                new_count += int(fresh)
                reused += int(not fresh)
                if fresh:
                    new_bytes += (chunks / (key + ".cz")).stat().st_size
        now = source.stat()
        if ((now.st_dev, now.st_ino, now.st_size, now.st_mtime_ns, now.st_ctime_ns)
                != identity or total < 100 or _hash_file(source)[0] != sha):
            raise CompressedCasError("SOURCE_CHANGED")
        doc = {"contract": CONTRACT, "codec": "zlib-6",
               "chunk_bytes": CHUNK_BYTES, "snapshot_sha256": sha,
               "snapshot_size_bytes": total, "chunks": names}
        encoded = (json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if len(encoded) > MAX_MANIFEST:
            raise CompressedCasError("MANIFEST_LIMIT")
        staged = _staging_file(manifests)
        try:
            _write_staged_exact(staged, encoded)
            published = _publish_new(staged, manifests, ".json")
        finally:
            staged.unlink(missing_ok=True)
        return {"status": "PUBLISHED_COMPRESSED_SYNTHETIC_ONLY",
                "manifest_name": published.name, "snapshot_sha256": sha,
                "source_bytes": total, "chunks": len(names),
                "new_chunks": new_count, "reused_chunks": reused,
                "new_compressed_bytes": new_bytes,
                "compressed": True, "signed": False, "encrypted": False,
                "automatic_deletion": False, "power_loss_verified": False,
                "ready_for_customer_data": False}
    except CompressedCasError:
        raise
    except (ArchiveError, OSError, ValueError):
        raise CompressedCasError("COMPRESSED_CREATE_FAILED") from None


def _parse_manifest(payload: bytes) -> dict:
    def pairs_unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise CompressedCasError("DUPLICATE_MANIFEST_KEY")
            result[key] = value
        return result
    try:
        doc = json.loads(payload, object_pairs_hook=pairs_unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except CompressedCasError:
        raise
    except (ValueError, TypeError, UnicodeError):
        raise CompressedCasError("INVALID_MANIFEST") from None
    if (type(doc) is not dict or set(doc) != {
            "contract", "codec", "chunk_bytes", "snapshot_sha256",
            "snapshot_size_bytes", "chunks"} or doc["contract"] != CONTRACT
            or doc["codec"] != "zlib-6" or doc["chunk_bytes"] != CHUNK_BYTES):
        raise CompressedCasError("INVALID_MANIFEST")
    size, names = doc["snapshot_size_bytes"], doc["chunks"]
    if (type(size) is not int or not 100 <= size <= MAX_SNAPSHOT_BYTES
            or type(names) is not list or
            len(names) != (size + CHUNK_BYTES - 1) // CHUNK_BYTES
            or type(doc["snapshot_sha256"]) is not str
            or DIGEST.fullmatch(doc["snapshot_sha256"]) is None
            or any(type(k) is not str or DIGEST.fullmatch(k) is None for k in names)):
        raise CompressedCasError("INVALID_MANIFEST")
    return doc


def _read_manifest_unchanged(source: Path) -> bytes:
    """Read one bounded immutable manifest via an identity-checked file descriptor.

    A manifest substituted after the initial lstat must not be accepted even
    if an attacker preserves its size and modification timestamp.
    """
    before = source.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or source.is_symlink() or not 0 < before.st_size <= MAX_MANIFEST):
        raise CompressedCasError("UNSAFE_MANIFEST")
    identity = (before.st_dev, before.st_ino, before.st_size,
                before.st_mtime_ns, before.st_ctime_ns)
    fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
                 getattr(os, "O_BINARY", 0))
    try:
        opened = os.fstat(fd)
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or
                (opened.st_dev, opened.st_ino, opened.st_size,
                 opened.st_mtime_ns, opened.st_ctime_ns) != identity):
            raise CompressedCasError("MANIFEST_CHANGED")
        parts, remaining = [], MAX_MANIFEST + 1
        while remaining:
            part = os.read(fd, remaining)
            if not part:
                break
            parts.append(part)
            remaining -= len(part)
        raw = b"".join(parts)
        after = os.fstat(fd)
        named = source.lstat()
        for item in (after, named):
            if (not stat.S_ISREG(item.st_mode) or item.st_nlink != 1 or
                    (item.st_dev, item.st_ino, item.st_size,
                     item.st_mtime_ns, item.st_ctime_ns) != identity):
                raise CompressedCasError("MANIFEST_CHANGED")
    finally:
        os.close(fd)
    if len(raw) != before.st_size:
        raise CompressedCasError("MANIFEST_CHANGED")
    return raw


def restore_compressed(manifest_path: str | Path, chunk_dir: str | Path,
                       output_dir: str | Path, *, synthetic_only=False,
                       accept_plaintext=False) -> dict:
    if synthetic_only is not True:
        raise CompressedCasError("SYNTHETIC_ONLY_REQUIRED")
    if accept_plaintext is not True:
        raise CompressedCasError("PLAINTEXT_ACK_REQUIRED")
    if not isinstance(manifest_path, (str, Path)) or not Path(manifest_path).is_absolute():
        raise CompressedCasError("INVALID_MANIFEST_PATH")
    source = Path(manifest_path)
    if MANIFEST.fullmatch(source.name) is None:
        raise CompressedCasError("INVALID_MANIFEST_PATH")
    try:
        chunks, output = _directories(source, chunk_dir, output_dir)
        doc = _parse_manifest(_read_manifest_unchanged(source))
        staged = _staging_file(output)
        try:
            length, digest = 0, hashlib.sha256()
            with staged.open("wb") as writer:
                for key in doc["chunks"]:
                    raw = _read(chunks, key)
                    length += len(raw)
                    if length > doc["snapshot_size_bytes"]:
                        raise CompressedCasError("RESTORE_LIMIT")
                    writer.write(raw)
                    digest.update(raw)
                writer.flush()
                os.fsync(writer.fileno())
            if (length != doc["snapshot_size_bytes"]
                    or digest.hexdigest() != doc["snapshot_sha256"]):
                raise CompressedCasError("RESTORE_HASH_MISMATCH")
            _integrity_check(staged)
            final = _publish_new(staged, output, ".sqlite")
            return {"status": "RESTORED_COMPRESSED_SYNTHETIC_ONLY",
                    "restored_name": final.name,
                    "restored_sha256": digest.hexdigest(),
                    "restored_bytes": length,
                    "sqlite_integrity": "ok",
                    "signed": False, "encrypted": False,
                    "power_loss_verified": False,
                    "ready_for_customer_data": False}
        finally:
            staged.unlink(missing_ok=True)
    except CompressedCasError:
        raise
    except (ArchiveError, OSError, ValueError):
        raise CompressedCasError("COMPRESSED_RESTORE_FAILED") from None
