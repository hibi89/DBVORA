"""Offline, opt-in verification of DBVORA's real CLI on synthetic SQLite.

Run from checkout: python -m scripts.synthetic_cli_gate
Only creates files inside an OS-managed temporary directory. This is NOT a
customer database readiness certificate or a full regression test suite.
"""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

from dbvora.archive_cli import main as archive_cli_main
from tests.fixtures.make_sqlite import create_fixture


class GateFailure(Exception):
    """Safe failure marker; no sensitive source paths are printed."""


def _invoke(*args):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = archive_cli_main(list(args))
    try:
        payload = json.loads(stdout.getvalue() if exit_code == 0 else stderr.getvalue())
    except (ValueError, TypeError):
        raise GateFailure('INVALID_CLI_JSON') from None
    if exit_code != 0 or payload.get('ok') is not True:
        code = payload.get('error', {}).get('code', 'UNKNOWN')
        if not isinstance(code, str) or not code.replace('_', '').isalnum():
            code = 'UNKNOWN'
        raise GateFailure('CLI_' + code)
    return payload['result']


def _check(condition, code):
    if not condition:
        raise GateFailure(code)


def run_gate(*, include_zstd=True):
    """Run genuine library calls end-to-end, then report only synthetic hashes."""
    result = {
        'contract': 'dbvora.synthetic-cli-gate.v1',
        'environment': {'platform': sys.platform,
                        'python': '.'.join(map(str, sys.version_info[:3])),
                        'sqlite': sqlite3.sqlite_version},
        'scope': 'OS_TEMP_SYNTHETIC_ONLY',
        'ready_for_customer_data': False,
        'checks': [],
        'optional_zstd': 'not_requested' if not include_zstd else 'not_run',
    }
    with tempfile.TemporaryDirectory(prefix='dbvora-synthetic-gate-') as root:
        root = Path(root)
        src_dir = root / 'src'
        snap_dir = root / 'snap'
        arc_dir = root / 'archives'
        restore_dir = root / 'restored'
        for folder in (src_dir, snap_dir, arc_dir, restore_dir):
            folder.mkdir()
        original = create_fixture(src_dir / 'fixture.sqlite')
        before = (hashlib.sha256(original.read_bytes()).hexdigest(),
                  original.stat().st_mtime_ns, original.stat().st_size)

        snapshot = _invoke('snapshot', '--source', str(original),
                           '--output-dir', str(snap_dir), '--synthetic-only',
                           '--accept-plaintext')
        snap_path = snap_dir / snapshot['snapshot_path']
        _check(snap_path.is_file(), 'SNAPSHOT_ABSENT')
        result['checks'].append('sqlite_online_snapshot')

        archive = _invoke('archive', '--snapshot', str(snap_path),
                          '--output-dir', str(arc_dir), '--codec', 'zip',
                          '--synthetic-only', '--accept-plaintext')
        zip_path = arc_dir / archive['archive_path']
        _check(zip_path.is_file(), 'ZIP_ABSENT')
        _check(archive['snapshot_sha256'] == snapshot['snapshot_sha256'], 'ZIP_SHA_MISMATCH')
        result['checks'].append('zip_archive_verified')

        receipt = _invoke('receipt', '--artifact', str(zip_path),
                          '--synthetic-only', '--accept-unsigned')
        _check(receipt['authentication'] == 'unsigned_untrusted', 'RECEIPT_AUTH_MISREPORTED')
        result['checks'].append('unsigned_receipt_recorded')

        restored = _invoke('restore', '--archive', str(zip_path),
                           '--output-dir', str(restore_dir), '--synthetic-only',
                           '--accept-plaintext')
        restored_path = restore_dir / restored['restored_path']
        restored_sha = hashlib.sha256(restored_path.read_bytes()).hexdigest()
        _check(restored_sha == snapshot['snapshot_sha256'], 'RESTORE_SHA_MISMATCH')
        result['checks'].append('independent_zip_restore_sha256')

        catalog = _invoke('audit', '--output-dir', str(arc_dir))
        entries = {item['name']: item['status'] for item in catalog['records']}
        _check(entries.get(zip_path.name) == 'RECORDED_AND_CONTENT_VERIFIED_UNSIGNED',
               'RECEIPT_AUDIT_FAILED')
        result['checks'].append('read_only_receipt_audit')

        if include_zstd:
            if shutil.which('zstd') is None:
                result['optional_zstd'] = 'skipped_no_local_codec'
            else:
                zstd_archive = _invoke('archive', '--snapshot', str(snap_path),
                                       '--output-dir', str(arc_dir), '--codec', 'zstd',
                                       '--level', '3', '--synthetic-only', '--accept-plaintext')
                zstd_path = arc_dir / zstd_archive['archive_path']
                recovered = _invoke('restore', '--archive', str(zstd_path),
                                    '--output-dir', str(restore_dir), '--synthetic-only',
                                    '--accept-plaintext')
                _check(recovered['restored_sha256'] == snapshot['snapshot_sha256'],
                       'ZSTD_RESTORE_SHA_MISMATCH')
                result['optional_zstd'] = 'passed'
                result['checks'].append('optional_zstd_restore_sha256')

        after = (hashlib.sha256(original.read_bytes()).hexdigest(),
                 original.stat().st_mtime_ns, original.stat().st_size)
        _check(before == after, 'ORIGINAL_CHANGED')
        result['checks'].append('original_sha_mtime_size_unchanged')
        _check(not any(path.name.endswith('.part') for path in root.rglob('*')),
               'INCOMPLETE_STAGING_FOUND')
        result['checks'].append('no_incomplete_staging_files')
    result['status'] = 'PASS_SYNTHETIC_ONLY'
    result['check_count'] = len(result['checks'])
    return result


def main():
    try:
        report = run_gate()
    except (GateFailure, OSError, ValueError, KeyError, TypeError) as exc:
        report = {'contract': 'dbvora.synthetic-cli-gate.v1', 'status': 'FAIL',
                  'error_code': str(exc) if isinstance(exc, GateFailure) else 'GATE_FAILED',
                  'ready_for_customer_data': False}
    except Exception:
        report = {'contract': 'dbvora.synthetic-cli-gate.v1', 'status': 'FAIL',
                  'error_code': 'UNEXPECTED_GATE_ERROR', 'ready_for_customer_data': False}
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report['status'] == 'PASS_SYNTHETIC_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
