"""Portable developer-preview self-test: real synthetic ZIP/ZSTD recovery and audit.

Runs from a source ZIP extracted with an existing Python 3.11+. Generates all
sources/output under a disposable OS temp folder; no external DB path accepted.
Never authorizes customer backups, hardware durability or archive replay.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import sys
import tempfile

from dbvora.archive.request_service import RequestServiceError, archive_once
from dbvora.archive.request_audit import AuditError, inspect_and_reconcile
from dbvora.archive.review_html import ReviewError, publish
from dbvora.archive.safe_zip import ArchiveError, create_snapshot, restore_zip_archive
from dbvora.archive.zstd_archive import restore_zstd_archive


class SelftestError(ValueError):
    """Safe, fixed synthetic regression failure code."""


def _require(value: bool, reason: str) -> None:
    if value is not True:
        raise SelftestError(reason)


def _signature(path: Path) -> tuple[str, int, int]:
    before = path.lstat()
    _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and 100 <= before.st_size <= 32 * 1024 * 1024,
             'UNSAFE_SYNTHETIC_FILE')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    after = path.lstat()
    _require((before.st_dev, before.st_ino, before.st_size,
              before.st_mtime_ns, before.st_ctime_ns) ==
             (after.st_dev, after.st_ino, after.st_size,
              after.st_mtime_ns, after.st_ctime_ns),
             'SYNTHETIC_FILE_CHANGED')
    return digest.hexdigest(), before.st_size, before.st_mtime_ns


def _fixture(path: Path) -> None:
    # Fully generated; no fixture from tests/, customer path, env or network.
    with closing(sqlite3.connect(path)) as db:
        db.executescript('''
            PRAGMA foreign_keys=ON;
            CREATE TABLE synthetic_parent(id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE synthetic_child(id INTEGER PRIMARY KEY,
                parent_id INTEGER REFERENCES synthetic_parent(id));
            INSERT INTO synthetic_parent VALUES (1, 'synthetic-only');
            INSERT INTO synthetic_child VALUES (2, 1);
        ''')
        db.commit()


def _codec(codec: str, root: Path) -> int:
    root.mkdir()
    dirs = {name: root / name for name in
            ('source', 'snapshot', 'archive', 'ledger', 'restored', 'review')}
    for folder in dirs.values():
        folder.mkdir()
    source = dirs['source'] / 'fixture.sqlite'
    _fixture(source)
    baseline = _signature(source)
    snap_path = Path(create_snapshot(source, dirs['snapshot'])['snapshot_path'])
    snap_digest = _signature(snap_path)
    request = 'portable-synthetic-check-0001'
    opts = dict(codec=codec, synthetic_only=True, accept_plaintext=True)
    if codec == 'zstd':
        opts['level'] = 3
    completed = archive_once(snap_path, dirs['archive'], dirs['ledger'], request, **opts)
    _require(completed['status'] == 'RECORDED_UNVERIFIED' and
             completed['independently_restored_content_verified'] is True and
             completed['ready_for_customer_data'] is False and
             completed['exactly_once_verified'] is False,
             'REQUEST_STATUS_INVALID')
    archive = dirs['archive'] / completed['artifact_name']
    _require(archive.is_file() and archive.parent == dirs['archive'], 'ARCHIVE_NOT_PUBLISHED')

    # Actual extraction outside the source and outside the archive; byte-exact.
    result = (restore_zip_archive if codec == 'zip' else restore_zstd_archive)(archive, dirs['restored'])
    restored = Path(result['restored_path'])
    _require(_signature(restored)[0] == snap_digest[0] == result['restored_sha256'],
             'RESTORE_SHA_MISMATCH')
    with closing(sqlite3.connect(restored.as_uri() + '?mode=ro&immutable=1', uri=True)) as con:
        _require(con.execute('PRAGMA integrity_check').fetchone() == ('ok',), 'RESTORED_SQLITE_INVALID')

    evidence = inspect_and_reconcile(dirs['ledger'], dirs['archive'], synthetic_only=True)
    _require(evidence['request_count'] == 1 and
             evidence['counts']['RECORDED_MATCH_REVIEW_REQUIRED'] == 1 and
             evidence['may_resume_archive'] is False,
             'MATCH_NOT_HELD_FOR_REVIEW')
    result = publish(evidence, dirs['review'], synthetic_only=True,
                     accept_plaintext_summary=True)
    html = (dirs['review'] / result['report_name']).read_text(encoding='utf-8')
    _require('복구 승인 아님' in html and '<script' not in html and
             'http://' not in html and result['may_resume_archive'] is False,
             'REPORT_UNSAFE')
    try:
        archive_once(snap_path, dirs['archive'], dirs['ledger'], request, **opts)
    except RequestServiceError as error:
        _require(error.code == 'REQUEST_REPLAY_HELD', 'REQUEST_REPLAY_NOT_HELD')
    else:
        raise SelftestError('REQUEST_REPLAY_SUCCEEDED')
    _require(len(list(dirs['archive'].iterdir())) == 1, 'DUPLICATE_ARCHIVE')

    # Destructively perturb ONLY one generated disposable archive, never an original.
    with archive.open('r+b') as file:
        head = file.read(1)
        _require(len(head) == 1, 'EMPTY_SYNTHETIC_ARCHIVE')
        file.seek(0)
        file.write(bytes([head[0] ^ 0xFF]))
        file.flush()
    damaged = inspect_and_reconcile(dirs['ledger'], dirs['archive'], synthetic_only=True)
    _require(damaged['counts']['RECORDED_MATCH_REVIEW_REQUIRED'] == 0 and
             damaged['counts']['RECORDED_NOT_VERIFIED'] == 1 and
             damaged['may_resume_archive'] is False,
             'CORRUPTION_NOT_HELD')
    _require(_signature(source) == baseline and _signature(snap_path) == snap_digest,
             'SOURCE_CHANGED')
    return 11


def verify() -> dict:
    # No arguments, outside paths, DSNs or network are consumed.
    report = {'contract': 'dbvora.portable-synthetic-review.v1',
              'status': 'FAIL_CLOSED', 'scope': 'OS_TEMP_SYNTHETIC_ONLY',
              'zip': 'not_run', 'zstd': 'not_run', 'checks': 0,
              'customer_ready': False, 'exactly_once_verified': False,
              'windows_ntfs_durability_verified': False,
              'hardware_power_loss_verified': False}
    try:
        with tempfile.TemporaryDirectory(prefix='dbvora-portable-review-') as directory:
            temp = Path(directory)
            report['checks'] += _codec('zip', temp / 'zip')
            report['zip'] = 'passed'
            if shutil.which('zstd') is not None:
                report['checks'] += _codec('zstd', temp / 'zstd')
                report['zstd'] = 'passed'
            else:
                report['zstd'] = 'skipped_no_local_codec'
        report['status'] = 'PASS_SYNTHETIC_PREVIEW_ONLY'
    except (SelftestError, ArchiveError, RequestServiceError, ReviewError, AuditError,
            OSError, ValueError, TypeError, KeyError, sqlite3.Error) as error:
        import re
        code = error.code if hasattr(error, 'code') else str(error)
        report['error_code'] = code if re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}', code) else 'PREVIEW_CHECK_FAILED'
    except Exception:
        report['error_code'] = 'UNEXPECTED_PREVIEW_FAILURE'
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse
    class Parser(argparse.ArgumentParser):
        def error(self, message):
            raise SelftestError('NO_USER_INPUT_ALLOWED')
    try:
        parser = Parser(description='Run disposable local synthetic ZIP/ZSTD review self-test')
        parser.parse_args(argv)
        report = verify()
    except SelftestError:
        report = {'status': 'FAIL_CLOSED', 'error_code': 'NO_USER_INPUT_ALLOWED',
                  'customer_ready': False, 'windows_ntfs_durability_verified': False}
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report['status'] == 'PASS_SYNTHETIC_PREVIEW_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
