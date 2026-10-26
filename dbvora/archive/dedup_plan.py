"""Bounded, read-only byte-identical chunk reuse estimator; not a backup.

This is an experimental C2 *planner* only. It never creates a content store,
archive, restore chain, retention rule, or assertion of crash durability.
Reports intentionally exclude original filesystem paths and data chunks.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

MAX_FILES = 8
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MIN_CHUNK_BYTES = 4096
MAX_CHUNK_BYTES = 1024 * 1024
DEFAULT_CHUNK_BYTES = 64 * 1024


class DedupPlanError(Exception):
    """Fixed public error code without input paths or bytes."""


def _fingerprint(st) -> tuple[int, int, int, int, int]:
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _safe_open(path: Path):
    if not isinstance(path, Path) or not path.is_absolute():
        raise DedupPlanError('INVALID_SOURCE')
    try:
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise DedupPlanError('UNSAFE_SOURCE')
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise DedupPlanError('UNSAFE_SOURCE')
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(path, flags)
        try:
            current = os.fstat(fd)
            if not stat.S_ISREG(current.st_mode) or _fingerprint(current) != _fingerprint(before):
                raise DedupPlanError('SOURCE_CHANGED')
            return os.fdopen(fd, 'rb', buffering=0), current
        except BaseException:
            os.close(fd)
            raise
    except DedupPlanError:
        raise
    except (OSError, ValueError):
        raise DedupPlanError('SOURCE_UNAVAILABLE') from None


def _same_chunk(first, offset: int, current: bytes) -> bool:
    saved = first.tell()
    try:
        first.seek(offset)
        return first.read(len(current)) == current
    finally:
        first.seek(saved)


def plan(paths: list[Path], *, chunk_bytes: int = DEFAULT_CHUNK_BYTES) -> dict:
    """Estimate byte-exact reusable fixed-size chunks across explicit files.

    SHA-256 is a lookup accelerator, never proof of byte identity: a candidate
    reuse is counted only after comparing its bytes to the earlier occurrence.
    Original file handles remain read-only and are checked before/after scan.
    """
    if (not isinstance(paths, list) or not 1 <= len(paths) <= MAX_FILES
            or not all(isinstance(p, Path) for p in paths)):
        raise DedupPlanError('INVALID_INPUT')
    if (type(chunk_bytes) is not int or chunk_bytes < MIN_CHUNK_BYTES
            or chunk_bytes > MAX_CHUNK_BYTES or chunk_bytes & (chunk_bytes - 1)):
        raise DedupPlanError('INVALID_CHUNK_SIZE')
    with ExitStack() as stack:
        open_files = []
        before_stats = []
        total_size = 0
        identifiers = set()
        for path in paths:
            reader, before = _safe_open(path)
            stack.enter_context(reader)
            identity = (before.st_dev, before.st_ino)
            if identity in identifiers:
                raise DedupPlanError('DUPLICATE_SOURCE')
            identifiers.add(identity)
            if before.st_size > MAX_FILE_BYTES or total_size + before.st_size > MAX_TOTAL_BYTES:
                raise DedupPlanError('SOURCE_TOO_LARGE')
            total_size += before.st_size
            open_files.append(reader)
            before_stats.append(before)
        # digest -> [(file index, absolute byte offset)]; only positions retained.
        # In the astronomically unlikely case of a hash collision, compare bytes.
        known: dict[tuple[int, bytes], list[tuple[int, int]]] = {}
        unique_bytes = reused_bytes = unique_chunks = reused_chunks = 0
        items = []
        for index, reader in enumerate(open_files):
            per_reused = per_chunks = 0
            while True:
                position = reader.tell()
                part = reader.read(chunk_bytes)
                if not part:
                    break
                per_chunks += 1
                key = (len(part), hashlib.sha256(part).digest())
                occurrences = known.get(key, ())
                reused = False
                for first_index, first_offset in occurrences:
                    if _same_chunk(open_files[first_index], first_offset, part):
                        reused = True
                        break
                if reused:
                    reused_chunks += 1
                    reused_bytes += len(part)
                    per_reused += len(part)
                else:
                    unique_chunks += 1
                    unique_bytes += len(part)
                    known.setdefault(key, []).append((index, position))
            items.append({'input_index': index, 'size_bytes': before_stats[index].st_size,
                          'chunks_scanned': per_chunks, 'reusable_bytes': per_reused})
        for reader, before in zip(open_files, before_stats):
            if _fingerprint(os.fstat(reader.fileno())) != _fingerprint(before):
                raise DedupPlanError('SOURCE_CHANGED')
        if unique_bytes + reused_bytes != total_size:
            raise DedupPlanError('INTERNAL_INVARIANT')
        return {'status': 'CANDIDATE_REUSE_ESTIMATE_ONLY', 'mode': 'read_only_fixed_chunks',
                'chunk_bytes': chunk_bytes, 'files_scanned': len(paths),
                'source_total_bytes': total_size, 'estimated_unique_bytes': unique_bytes,
                'candidate_reusable_bytes': reused_bytes, 'unique_chunks': unique_chunks,
                'reused_chunks': reused_chunks, 'files': items,
                'content_store_created': False, 'independent_restore_verified': False,
                'windows_ntfs_durability_verified': False, 'ready_for_customer_data': False}


def synthetic_selfcheck() -> dict:
    """Demonstrate reuse only with disposable non-customer fixture bytes."""
    with tempfile.TemporaryDirectory(prefix='dbvora-dedup-synthetic-') as tmp:
        root = Path(tmp)
        paths = [root / f'input_{i}.bin' for i in range(3)]
        chunks = [b'A' * 4096, b'B' * 4096, b'C' * 4096]
        paths[0].write_bytes(chunks[0] + chunks[1])
        paths[1].write_bytes(chunks[0] + chunks[2])
        paths[2].write_bytes(chunks[1] + chunks[2])
        report = plan(paths, chunk_bytes=4096)
        if (report['candidate_reusable_bytes'] != 12288
                or report['estimated_unique_bytes'] != 12288
                or report['unique_chunks'] != 3 or report['reused_chunks'] != 3):
            raise DedupPlanError('SYNTHETIC_ASSERTION_FAILED')
        return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Synthetic-only, no-customer-file dedup planning demo')
    parser.add_argument('--synthetic', action='store_true', required=True)
    args = parser.parse_args(argv)
    try:
        report = synthetic_selfcheck()
    except DedupPlanError as error:
        report = {'status': 'FAIL_CLOSED', 'error_code': str(error),
                  'ready_for_customer_data': False}
    print(json.dumps(report, sort_keys=True))
    return int(report['status'] != 'CANDIDATE_REUSE_ESTIMATE_ONLY')


if __name__ == '__main__':
    raise SystemExit(main())
