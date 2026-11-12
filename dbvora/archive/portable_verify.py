"""Verify SHA-256 of an already extracted, unsigned DBVORA developer ZIP.

No input paths, database data, network, repair or automatic execution. This
checks accidental mutation, NOT author identity: an attacker can forge both
source and the unsigned manifest. Use an authenticated channel for originals.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

MAX_MANIFEST_BYTES = 64 * 1024
MAX_MEMBERS = 100
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
_DIGEST = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)
_ROOT_FILES = {'scripts/build_portable.py', 'pyproject.toml', 'README_PORTABLE.txt',
               'run_dbvora_windows.cmd', 'run_dbvora_unix.sh',
               'check_dbvora_windows.cmd', 'check_dbvora_unix.sh',
               'export_dbvora_map_windows.cmd', 'export_dbvora_map_unix.sh',
               'check_dbvora_archive_windows.cmd', 'check_dbvora_archive_unix.sh',
               'verify_dbvora_portable_windows.cmd', 'verify_dbvora_portable_unix.sh'}
_REQUIRED = {'dbvora/archive/portable_verify.py', 'dbvora/archive/review_selftest.py',
             'dbvora/archive/request_ledger.py', 'dbvora/archive/request_service.py',
             'dbvora/archive/request_audit.py', 'dbvora/archive/review_html.py',
             'scripts/build_portable.py', 'pyproject.toml',
             'verify_dbvora_portable_windows.cmd', 'verify_dbvora_portable_unix.sh'}


class PortableVerifyError(ValueError):
    """Stable fixed error code, never a caller path or source text."""


def _valid_name(name: str) -> bool:
    if type(name) is not str or not 1 <= len(name) <= 220 or '\\' in name:
        return False
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != name or any(
            not p or p == '.' or p.startswith('.') for p in path.parts):
        return False
    if name in _ROOT_FILES:
        return True
    return name.startswith('dbvora/') and path.suffix in ('.py', '.js', '.html', '.css')


def _safe_root(root: Path) -> None:
    if not isinstance(root, Path) or not root.is_absolute():
        raise PortableVerifyError('INVALID_PACKAGE_ROOT')
    try:
        for ancestor in (root, *root.parents):
            if not stat.S_ISDIR(ancestor.lstat().st_mode):
                raise PortableVerifyError('UNSAFE_PACKAGE_ROOT')
    except OSError:
        raise PortableVerifyError('PACKAGE_ROOT_UNAVAILABLE') from None


def _read_regular(root: Path, name: str, max_bytes: int) -> bytes:
    path = root / name
    try:
        for ancestor in (path.parent, *path.parents):
            if not stat.S_ISDIR(ancestor.lstat().st_mode):
                raise PortableVerifyError('UNSAFE_PACKAGE_ENTRY')
            if ancestor == root:
                break
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > max_bytes:
            raise PortableVerifyError('UNSAFE_PACKAGE_ENTRY')
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) |
                             getattr(os, 'O_BINARY', 0))
        try:
            opened = os.fstat(descriptor)
            if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns,
                opened.st_ctime_ns) != (before.st_dev, before.st_ino, before.st_size,
                                        before.st_mtime_ns, before.st_ctime_ns):
                raise PortableVerifyError('PACKAGE_ENTRY_CHANGED')
            with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                data = stream.read(max_bytes + 1)
            current = path.lstat()
            after = os.fstat(descriptor)
            identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if identity(current) != identity(before) or identity(after) != identity(before) or len(data) != before.st_size:
                raise PortableVerifyError('PACKAGE_ENTRY_CHANGED')
            return data
        finally:
            os.close(descriptor)
    except PortableVerifyError:
        raise
    except (OSError, ValueError):
        raise PortableVerifyError('PACKAGE_ENTRY_UNAVAILABLE') from None


def verify(root: Path | None = None) -> dict:
    """Internal optional root is only for tests; CLI accepts no external root."""
    folder = root if root is not None else Path(__file__).absolute().parents[2]
    _safe_root(folder)
    raw = _read_regular(folder, 'MANIFEST.sha256.json', MAX_MANIFEST_BYTES)
    try:
        manifest = json.loads(raw)
    except (UnicodeError, TypeError, ValueError):
        raise PortableVerifyError('INVALID_PACKAGE_MANIFEST') from None
    if (type(manifest) is not dict or set(manifest) != {'format', 'unsigned', 'files'}
            or manifest['format'] != 'dbvora-portable-dev-v1' or manifest['unsigned'] is not True):
        raise PortableVerifyError('INVALID_PACKAGE_MANIFEST')
    files = manifest['files']
    if (type(files) is not dict or not _REQUIRED.issubset(files)
            or not 1 <= len(files) <= MAX_MEMBERS):
        raise PortableVerifyError('INVALID_PACKAGE_MANIFEST')
    total = 0
    for name, evidence in files.items():
        if not _valid_name(name) or type(evidence) is not dict or set(evidence) != {'sha256', 'bytes'}:
            raise PortableVerifyError('INVALID_PACKAGE_MANIFEST')
        size, sha = evidence['bytes'], evidence['sha256']
        if (type(size) is not int or not 0 <= size <= MAX_FILE_BYTES
                or type(sha) is not str or not _DIGEST.fullmatch(sha)):
            raise PortableVerifyError('INVALID_PACKAGE_MANIFEST')
        total += size
        if total > MAX_TOTAL_BYTES:
            raise PortableVerifyError('PACKAGE_TOO_LARGE')
        bytes_on_disk = _read_regular(folder, name, MAX_FILE_BYTES)
        if len(bytes_on_disk) != size or hashlib.sha256(bytes_on_disk).hexdigest() != sha:
            raise PortableVerifyError('PACKAGE_DIGEST_MISMATCH')
    # Reject unexpected additional executable source files, while tolerating
    # Python's generated __pycache__ bytecode and platform resource metadata.
    visited = 0
    for path in folder.rglob('*'):
        visited += 1
        if visited > 500:
            raise PortableVerifyError('PACKAGE_ENTRY_LIMIT')
        try:
            relative = path.relative_to(folder)
            if path.is_symlink():
                raise PortableVerifyError('UNSAFE_PACKAGE_ENTRY')
            # Bytecode is tolerated only inside Python's generated cache.
            # A loose .pyc or an unlisted OS/startup script is executable
            # material and must not be silently covered by an unsigned report.
            if '__pycache__' in relative.parts and path.suffix == '.pyc':
                continue
            executable = {'.py', '.pyc', '.pyw', '.pth', '.js', '.html',
                          '.css', '.cmd', '.bat', '.ps1', '.sh', '.exe',
                          '.dll', '.pyd', '.so', '.com', '.vbs'}
            if (path.is_file() and path.suffix.lower() in executable
                    and relative.as_posix() not in files):
                raise PortableVerifyError('UNLISTED_PACKAGE_SOURCE')
        except PortableVerifyError:
            raise
        except (OSError, ValueError):
            raise PortableVerifyError('UNSAFE_PACKAGE_ENTRY') from None
    return {'status': 'PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY',
            'source_files_verified': len(files), 'total_source_bytes': total,
            'signed': False, 'publisher_authenticity_verified': False,
            'customer_ready': False, 'windows_ntfs_durability_verified': False}


def main(argv: list[str] | None = None) -> int:
    import argparse
    class Parser(argparse.ArgumentParser):
        def error(self, message):
            raise PortableVerifyError('NO_USER_INPUT_ALLOWED')
    try:
        parser = Parser(description='Verify extracted unsigned developer preview only')
        parser.parse_args(argv)
        result = verify()
    except PortableVerifyError as error:
        result = {'status': 'FAIL_CLOSED', 'error_code': str(error),
                  'signed': False, 'customer_ready': False}
    except Exception:
        result = {'status': 'FAIL_CLOSED', 'error_code': 'UNEXPECTED_PACKAGE_FAILURE',
                  'signed': False, 'customer_ready': False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
