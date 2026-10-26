"""Build/verify an unsigned local developer-preview source ZIP, never customer data.

From repository: python -m scripts.build_portable --output /absolute/existing/folder
After extraction: python -m scripts.build_portable --verify /absolute/file.zip
Requires Python >=3.11; UI requires separately installed local FastAPI+Uvicorn.
NOT a Windows/NTFS backup durability certification, installer or signed release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
_STAMP = (2020, 1, 1, 0, 0, 0)
_ALLOWED_SUFFIXES = {'.py', '.js', '.html', '.css'}
_REQUIRED = {
    'dbvora/__init__.py', 'dbvora/__main__.py', 'dbvora/serve.py',
    'dbvora/api.py', 'dbvora/archive/safe_zip.py',
    'dbvora/web/index.html', 'dbvora/web/app.js',
    'dbvora/web/style.css', 'scripts/build_portable.py',
    'pyproject.toml', 'README_PORTABLE.txt', 'run_dbvora_windows.cmd',
    'run_dbvora_unix.sh', 'dbvora/export_html.py',
    'export_dbvora_map_windows.cmd', 'export_dbvora_map_unix.sh',
    'dbvora/offline_selftest.py', 'dbvora/archive/dedup_plan.py', 'check_dbvora_windows.cmd',
    'check_dbvora_unix.sh',
}


class PortableError(Exception):
    """Fixed error codes; no source or output paths returned to callers."""
    pass


def _read_safe(source: Path) -> bytes:
    try:
        root = source.resolve(strict=True)
        if root != source or any(p.is_symlink() for p in (source, *source.parents)):
            raise PortableError('UNSAFE_SOURCE')
        info = source.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
            raise PortableError('UNSAFE_SOURCE')
        data = source.read_bytes()
        after = source.lstat()
        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
        ) or len(data) != info.st_size:
            raise PortableError('SOURCE_CHANGED')
        return data
    except OSError:
        raise PortableError('SOURCE_UNAVAILABLE') from None


def _version(root: Path) -> str:
    try:
        config = tomllib.loads(_read_safe(root / 'pyproject.toml').decode('utf-8'))
        version = config['project']['version']
    except (KeyError, ValueError, UnicodeDecodeError):
        raise PortableError('INVALID_PROJECT_VERSION') from None
    if not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise PortableError('INVALID_PROJECT_VERSION')
    return version


def _contents(root: Path) -> dict[str, bytes]:
    root = root.resolve(strict=True)
    files: dict[str, bytes] = {}
    for base in ('dbvora',):
        folder = root / base
        if not folder.is_dir() or folder.is_symlink():
            raise PortableError('SOURCE_UNAVAILABLE')
        for source in sorted(folder.rglob('*')):
            if source.is_symlink():
                raise PortableError('UNSAFE_SOURCE')
            if source.is_dir():
                continue
            if source.suffix not in _ALLOWED_SUFFIXES:
                # Do not package .pyc, SQLite files, archives, keys or hidden files.
                continue
            name = source.relative_to(root).as_posix()
            if any(part.startswith('.') for part in PurePosixPath(name).parts):
                continue
            files[name] = _read_safe(source)
    files['scripts/build_portable.py'] = _read_safe(root / 'scripts' / 'build_portable.py')
    files['pyproject.toml'] = _read_safe(root / 'pyproject.toml')
    files['README_PORTABLE.txt'] = (
        'DBVORA LOCAL DEVELOPER PREVIEW (unsigned / no customer readiness)\n'
        'This is a source ZIP, NOT a standalone installer or bundled Python.\n'
        'NO-PIP OFFLINE MAP: use installed Python 3.11+ without FastAPI.\n'
        'SYNTHETIC-ONLY SELF-CHECK (no customer file, no pip):\n'
        '  Windows: check_dbvora_windows.cmd (or py -3.11 -m dbvora.offline_selftest)\n'
        '  Linux/macOS: sh check_dbvora_unix.sh\n'
        '  This does NOT certify NTFS durability or native browser opening.\n'
        '  py -3 -m dbvora.export_html --db \"C:\\absolute\\synthetic.sqlite\" --out \"C:\\existing\\folder\"\n'
        '  Then open the generated dbvora-map-*.html in your browser.\n'
        '  Or run export_dbvora_map_windows.cmd with TWO quoted arguments.\n'
        '  Linux/macOS: python3 -m dbvora.export_html --db /abs/test.sqlite --out /abs/dir\n'
        'Requirements: Python 3.11+ installed; FastAPI and Uvicorn for viewer.\n'
        'Unzip to a local folder. In that folder, run:\n'
        '  py -3.11 -m pip install ".[ui]"  (may require package network download)\n'
        '  run_dbvora_windows.cmd "C:\\absolute\\synthetic.sqlite"\n'
        'or on Linux/macOS: python3 -m pip install ".[ui]"\n'
        '  sh run_dbvora_unix.sh "/absolute/synthetic.sqlite"\n'
        'Inventory without UI: py -3.11 -m dbvora inspect "C:\\absolute\\synthetic.sqlite"\n'
        'Only use explicitly authorized synthetic/test DBs. Never use customer data\n'
        'until native Windows/NTFS archive durability and packaging are certified.\n'
        'ZIP checksum manifest is unsigned; it detects accidental corruption,\n'
        'NOT a malicious actor capable of replacing ZIP + manifest together.\n'
        'No automatic archiving, remote telemetry, web server exposure or deletion.\n'
    ).encode('utf-8')
    files['run_dbvora_windows.cmd'] = (
        '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
        'if "%~1"=="" (echo Provide one absolute synthetic SQLite path. 1>&2 & exit /b 2)\r\n'
        'py -3.11 -m dbvora.serve --db "%~1"\r\n'
        'exit /b %ERRORLEVEL%\r\n'
    ).encode('ascii')
    files['run_dbvora_unix.sh'] = (
        '#!/bin/sh\nset -eu\n'
        'if [ "$#" -ne 1 ]; then echo "Provide one absolute synthetic SQLite path" >&2; exit 2; fi\n'
        'cd "$(dirname "$0")"\nexec python3 -m dbvora.serve --db "$1"\n'
    ).encode('utf-8')
    files['check_dbvora_windows.cmd'] = (
        '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
        'if not "%~1"=="" (echo No arguments: synthetic-only self-check. 1>&2 & exit /b 2)\r\n'
        'py -3.11 -m dbvora.offline_selftest\r\n'
        'exit /b %ERRORLEVEL%\r\n'
    ).encode('ascii')
    files['check_dbvora_unix.sh'] = (
        '#!/bin/sh\nset -eu\n'
        'if [ "$#" -ne 0 ]; then echo "No arguments: synthetic-only self-check" >&2; exit 2; fi\n'
        'cd "$(dirname "$0")"\n'
        'exec python3 -m dbvora.offline_selftest\n'
    ).encode('utf-8')
    files['export_dbvora_map_windows.cmd'] = (
        '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
        'if "%~1"=="" goto usage\r\n'
        'if "%~2"=="" goto usage\r\n'
        'py -3 -m dbvora.export_html --db "%~1" --out "%~2"\r\n'
        'exit /b %ERRORLEVEL%\r\n'
        ':usage\r\necho Provide an absolute synthetic SQLite file and existing output folder. 1>&2\r\n'
        'exit /b 2\r\n'
    ).encode('ascii')
    files['export_dbvora_map_unix.sh'] = (
        '#!/bin/sh\nset -eu\n'
        'if [ "$#" -ne 2 ]; then echo "Provide a synthetic SQLite file and existing output folder" >&2; exit 2; fi\n'
        'cd "$(dirname "$0")"\n'
        'exec python3 -m dbvora.export_html --db "$1" --out "$2"\n'
    ).encode('utf-8')
    if not _REQUIRED.issubset(files):
        raise PortableError('INCOMPLETE_SOURCE')
    if sum(map(len, files.values())) > MAX_TOTAL_BYTES:
        raise PortableError('TOO_LARGE')
    return files


def _member(name: str, payload: bytes) -> tuple[zipfile.ZipInfo, bytes]:
    item = zipfile.ZipInfo(name, date_time=_STAMP)
    item.compress_type = zipfile.ZIP_DEFLATED
    item.create_system = 3
    item.external_attr = (0o644 << 16)
    return item, payload


def _zip_bytes(root: Path) -> bytes:
    import io
    source = _contents(root)
    manifest = {
        'format': 'dbvora-portable-dev-v1', 'unsigned': True,
        'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                  for name, data in sorted(source.items())},
    }
    source['MANIFEST.sha256.json'] = (json.dumps(manifest, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as zf:
        for name, data in sorted(source.items()):
            info, payload = _member(name, data)
            zf.writestr(info, payload)
    return out.getvalue()


def verify_zip(archive: Path) -> dict:
    """Strict integrity/shape scan. Manifest is not an authenticity signature."""
    try:
        if archive.is_symlink() or not archive.is_file() or archive.stat().st_size > MAX_TOTAL_BYTES:
            raise PortableError('INVALID_ARCHIVE')
        with zipfile.ZipFile(archive) as zf:
            infos = zf.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)) or len(names) > 100 or 'MANIFEST.sha256.json' not in names:
                raise PortableError('INVALID_MEMBERS')
            for info in infos:
                p = PurePosixPath(info.filename)
                if (p.is_absolute() or '..' in p.parts or '\\' in info.filename
                    or not info.filename or info.is_dir() or info.file_size > MAX_FILE_BYTES
                    or (info.external_attr >> 16 & 0o170000) == 0o120000):
                    raise PortableError('INVALID_MEMBERS')
            if sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
                raise PortableError('TOO_LARGE')
            parsed = json.loads(zf.read('MANIFEST.sha256.json'))
            if parsed.get('format') != 'dbvora-portable-dev-v1' or parsed.get('unsigned') is not True:
                raise PortableError('INVALID_MANIFEST')
            catalog = parsed.get('files')
            if not isinstance(catalog, dict) or set(catalog) != set(names) - {'MANIFEST.sha256.json'}:
                raise PortableError('INVALID_MANIFEST')
            if not _REQUIRED.issubset(catalog):
                raise PortableError('INVALID_MANIFEST')
            for info in infos:
                if info.filename == 'MANIFEST.sha256.json':
                    continue
                item = catalog[info.filename]
                if not isinstance(item, dict) or set(item) != {'sha256', 'bytes'}:
                    raise PortableError('INVALID_MANIFEST')
                if type(item['bytes']) is not int or item['bytes'] != info.file_size:
                    raise PortableError('INVALID_MANIFEST')
                digest = item['sha256']
                if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
                    raise PortableError('INVALID_MANIFEST')
                if hashlib.sha256(zf.read(info)).hexdigest() != digest:
                    raise PortableError('CHECKSUM_MISMATCH')
        return {'status': 'PASS_UNSIGNED_SOURCE_INTEGRITY_ONLY', 'files': len(catalog),
                'ready_for_customer_data': False, 'signed': False}
    except (OSError, ValueError, TypeError, zipfile.BadZipFile, KeyError, RuntimeError):
        raise PortableError('INVALID_ARCHIVE') from None


def build(output: Path, *, root: Path = ROOT) -> Path:
    if not output.is_absolute() or output.is_symlink() or not output.is_dir():
        raise PortableError('INVALID_OUTPUT')
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise PortableError('INVALID_OUTPUT')
    archive_name = f'dbvora-dev-preview-{_version(root)}.zip'
    archive = output / archive_name
    if archive.exists() or archive.is_symlink():
        raise PortableError('ALREADY_EXISTS')
    data = _zip_bytes(root)
    # Stage and verify before publishing under an exclusive new name.
    fd, staging = tempfile.mkstemp(prefix='.dbvora-bundle-', suffix='.part', dir=output)
    staged = Path(staging)
    try:
        with os.fdopen(fd, 'wb') as dst:
            dst.write(data)
            dst.flush()
            os.fsync(dst.fileno())
        verify_zip(staged)
        try:
            os.link(staged, archive, follow_symlinks=False)
        except FileExistsError:
            raise PortableError('ALREADY_EXISTS') from None
        except OSError:
            raise PortableError('PUBLISH_FAILED') from None
        return archive
    finally:
        staged.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Offline unsigned DBVORA source developer preview')
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--output', help='Existing absolute directory for new ZIP')
    modes.add_argument('--verify', help='Existing archive to independently verify')
    args = parser.parse_args(argv)
    try:
        if args.output:
            path = build(Path(args.output))
            report = verify_zip(path)
            report['archive_name'] = path.name
            report['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            report = verify_zip(Path(args.verify))
    except PortableError as error:
        report = {'status': 'FAIL_CLOSED', 'error_code': str(error),
                  'ready_for_customer_data': False}
    print(json.dumps(report, sort_keys=True))
    return 0 if report['status'] == 'PASS_UNSIGNED_SOURCE_INTEGRITY_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
