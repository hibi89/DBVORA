"""Real-engine synthetic-only snapshot -> ZIP/ZSTD -> audit -> offline HTML regression.

No caller-supplied DB paths, no customer archive/ledger data, no network, no
replay, no automatic approval. A pass never certifies power-loss durability.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

from dbvora.archive.request_service import archive_once, RequestServiceError
from dbvora.archive.request_audit import inspect_and_reconcile, AuditError
from dbvora.archive.review_html import publish, ReviewError
from dbvora.archive.safe_zip import ArchiveError, create_snapshot
from tests.fixtures.make_sqlite import create_fixture

_SAFE = re.compile(r'[A-Z][A-Z0-9_]{0,63}\Z', re.ASCII)


class GateError(ValueError):
    """Only fixed codes are allowed to reach public output."""


def _check(condition: bool, reason: str) -> None:
    if condition is not True:
        raise GateError(reason)


def _fingerprint(path: Path) -> tuple[str, int, int]:
    import stat
    info = path.lstat()
    _check(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size < 512*1024*1024,
           'UNSAFE_SYNTHETIC_FILE')
    content = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            content.update(block)
    after = path.lstat()
    _check((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size,
                                   after.st_mtime_ns, after.st_ctime_ns),
           'SYNTHETIC_FILE_CHANGED')
    return content.hexdigest(), info.st_size, info.st_mtime_ns


def _assert_report(data: dict, *, expected_match: int, expected_missing: int,
                   expected_interrupted: int = 0) -> None:
    counts = data['counts']
    _check(data['inspection_mode'] == 'read_only_human_review_only' and
           counts['RECORDED_MATCH_REVIEW_REQUIRED'] == expected_match and
           counts['RECORDED_NOT_VERIFIED'] == expected_missing and
           counts['INTERRUPTED_REVIEW_REQUIRED'] == expected_interrupted and
           counts['DUPLICATE_ARTIFACT_REVIEW_REQUIRED'] == 0 and
           data['may_resume_archive'] is False and
           data['ready_for_customer_data'] is False and
           data['exactly_once_verified'] is False and
           data['power_loss_verified'] is False,
           'AUDIT_COUNTS_OR_SAFETY_INVALID')


def _attempt(codec: str, root: Path) -> dict:
    root.mkdir()
    paths = {name: root / name for name in ('source', 'snap', 'archive', 'ledger', 'review')}
    for directory in paths.values():
        directory.mkdir()
    src = create_fixture(paths['source'] / 'generated.sqlite')
    orig = _fingerprint(src)
    snapshot = Path(create_snapshot(src, paths['snap'])['snapshot_path'])
    snap = _fingerprint(snapshot)
    args = {'codec': codec, 'synthetic_only': True, 'accept_plaintext': True}
    if codec == 'zstd':
        args['level'] = 3
    report = archive_once(snapshot, paths['archive'], paths['ledger'],
                          'synthetic-review-gate-request-01', **args)
    _check(report['status'] == 'RECORDED_UNVERIFIED' and
           report['independently_restored_content_verified'] is True and
           report['exactly_once_verified'] is False and
           report['ready_for_customer_data'] is False,
           'REQUEST_RESULT_NOT_REVIEW_ONLY')
    published = paths['archive'] / report['artifact_name']
    _check(published.is_file() and published.suffix == ('.zip' if codec == 'zip' else '.dbvz') and
           _fingerprint(snapshot) == snap and _fingerprint(src) == orig,
           'ARCHIVE_OR_ORIGINAL_CHANGED')

    audit = inspect_and_reconcile(paths['ledger'], paths['archive'], synthetic_only=True)
    _assert_report(audit, expected_match=1, expected_missing=0)
    html = publish(audit, paths['review'], synthetic_only=True,
                   accept_plaintext_summary=True)
    page = (paths['review'] / html['report_name']).read_text(encoding='utf-8')
    _check('복구 승인 아님' in page and '<script' not in page and
           '<iframe' not in page and 'http://' not in page and
           html['customer_ready'] is False,
           'HTML_REVIEW_INVALID')

    try:
        archive_once(snapshot, paths['archive'], paths['ledger'],
                     'synthetic-review-gate-request-01', **args)
    except RequestServiceError as exc:
        _check(exc.code == 'REQUEST_REPLAY_HELD', 'REPLAY_NOT_HELD')
    else:
        raise GateError('REPLAY_WAS_NOT_BLOCKED')
    _check(len(list(paths['archive'].glob('dbvora-*'))) == 1, 'SECOND_ARCHIVE_CREATED')

    # Corrupt only a generated disposable artifact. No customer/ledger source path
    # is accepted by this gate; the existing archive must no longer match.
    with published.open('r+b') as stream:
        stream.seek(0)
        first = stream.read(1)
        _check(len(first) == 1, 'SYNTHETIC_ARCHIVE_EMPTY')
        stream.seek(0)
        stream.write(bytes([first[0] ^ 0xFF]))
        stream.flush()
    corrupt = inspect_and_reconcile(paths['ledger'], paths['archive'], synthetic_only=True)
    _assert_report(corrupt, expected_match=0, expected_missing=1)
    _check(_fingerprint(snapshot) == snap and _fingerprint(src) == orig,
           'ORIGINAL_CHANGED_AFTER_CORRUPTION')
    return {'archive_executed': True, 'verified_then_corruption_held': True,
            'replay_held': True, 'offline_report_new_only': True,
            'source_unchanged': True, 'checks': 8}


def run() -> dict:
    """No input filenames; every source and output is generated inside OS temp."""
    with tempfile.TemporaryDirectory(prefix='dbvora-review-gate-') as temp:
        parent = Path(temp)
        zip_result = _attempt('zip', parent / 'zip')
        zstd_status = 'skipped_no_local_codec'
        checks = zip_result['checks']
        if shutil.which('zstd') is not None:
            zstd = _attempt('zstd', parent / 'zstd')
            _check(zstd['verified_then_corruption_held'] is True, 'ZSTD_AUDIT_FAILED')
            zstd_status = 'passed'
            checks += zstd['checks']
    return {'status': 'PASS_SYNTHETIC_ARCHIVE_REVIEW_ONLY',
            'checks': checks, 'zip': 'passed', 'optional_zstd': zstd_status,
            'replay_held': True, 'content_corruption_detected': True,
            'offline_html_written': True, 'source_unchanged': True,
            'customer_ready': False, 'exactly_once_verified': False,
            'power_loss_verified': False, 'windows_ntfs_verified': False}


def main() -> int:
    try:
        result = run()
    except (ArchiveError, RequestServiceError, AuditError, ReviewError,
            GateError, OSError, KeyError, TypeError, ValueError) as error:
        key = error.code if isinstance(error, (ArchiveError, RequestServiceError)) else str(error)
        result = {'status': 'FAIL_CLOSED', 'error_code': key if _SAFE.fullmatch(key) else 'GATE_FAILED',
                  'customer_ready': False, 'exactly_once_verified': False,
                  'power_loss_verified': False, 'windows_ntfs_verified': False}
    except Exception:
        result = {'status': 'FAIL_CLOSED', 'error_code': 'UNEXPECTED_GATE_FAILURE',
                  'customer_ready': False, 'exactly_once_verified': False,
                  'power_loss_verified': False, 'windows_ntfs_verified': False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'PASS_SYNTHETIC_ARCHIVE_REVIEW_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
