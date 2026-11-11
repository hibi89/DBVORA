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
import re
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

from dbvora.archive_cli import main as archive_cli_main
from dbvora.archive.request_ledger import reserve, record_artifact
from tests.fixtures.make_sqlite import create_fixture


class GateFailure(Exception):
    """Safe failure marker; no sensitive source paths are printed."""


GENERATED = re.compile(r'^dbvora-[a-f0-9]{32}\.(sqlite|zip|dbvz)$')


def _generated_file(directory: Path, name: str, suffix: str, *, expected_sha=None) -> Path:
    """Inspect only exact generated basenames in the caller's temporary directory."""
    if type(name) is not str or not (match := GENERATED.fullmatch(name)) or match.group(1) != suffix:
        raise GateFailure('INVALID_GENERATED_FILENAME')
    target = directory / name
    if target.is_symlink() or not target.is_file():
        raise GateFailure('EXPECTED_ARTIFACT_MISSING')
    if expected_sha is not None:
        if not isinstance(expected_sha, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha):
            raise GateFailure('BAD_EXPECTED_SHA')
        try:
            actual_sha = hashlib.sha256(target.read_bytes()).hexdigest()
        except OSError:
            raise GateFailure('ARTIFACT_UNREADABLE') from None
        if actual_sha != expected_sha:
            raise GateFailure('INDEPENDENT_FILE_SHA_MISMATCH')
    return target


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



def _reserve_new_request(ledger_dir: Path, request_id: str, plan_sha: str) -> None:
    """Fail closed BEFORE invoking archive_cli when a request is not new."""
    entry = reserve(ledger_dir, request_id, plan_sha)
    _check(entry.get('status') == 'RESERVED_NOT_EXECUTED'
           and entry.get('archive_executed') is False
           and entry.get('exactly_once_verified') is False,
           'REQUEST_RESERVATION_FAILED')


def _record_then_hold_replay(ledger_dir: Path, request_id: str,
                             plan_sha: str, archive_sha: str) -> None:
    """Record *unverified* digest after caller has independently verified ZIP."""
    record = record_artifact(ledger_dir, request_id, plan_sha, archive_sha)
    _check(record.get('status') == 'RECORDED_UNVERIFIED'
           and record.get('independent_artifact_verification') is False,
           'LEDGER_RECORD_UNVERIFIED')
    replay = reserve(ledger_dir, request_id, plan_sha)
    _check(replay.get('status') == 'RECORDED_REQUIRES_ARTIFACT_VERIFICATION'
           and replay.get('exactly_once_verified') is False,
           'REPLAY_NOT_HELD')

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
        ledger_dir = root / 'request_ledger'
        ledger_dir.mkdir()
        original = create_fixture(src_dir / 'fixture.sqlite')
        before = (hashlib.sha256(original.read_bytes()).hexdigest(),
                  original.stat().st_mtime_ns, original.stat().st_size)

        request_id = 'synthetic-request-zip-0001'
        plan_sha = hashlib.sha256(b'dbvora.synthetic-archive-request.v1').hexdigest()
        _reserve_new_request(ledger_dir, request_id, plan_sha)
        result['checks'].append('request_reserved_before_any_archive_execution')

        snapshot = _invoke('snapshot', '--source', str(original),
                           '--output-dir', str(snap_dir), '--synthetic-only',
                           '--accept-plaintext')
        snap_path = _generated_file(snap_dir, snapshot['snapshot_path'], 'sqlite',
                                    expected_sha=snapshot['snapshot_sha256'])
        result['checks'].append('sqlite_online_snapshot')

        archive = _invoke('archive', '--snapshot', str(snap_path),
                          '--output-dir', str(arc_dir), '--codec', 'zip',
                          '--synthetic-only', '--accept-plaintext')
        zip_path = _generated_file(arc_dir, archive['archive_path'], 'zip',
                                   expected_sha=archive['archive_sha256'])
        _check(archive['snapshot_sha256'] == snapshot['snapshot_sha256'], 'ZIP_SHA_MISMATCH')
        result['checks'].append('zip_archive_verified')

        receipt = _invoke('receipt', '--artifact', str(zip_path),
                          '--synthetic-only', '--accept-unsigned')
        _check(receipt['authentication'] == 'unsigned_untrusted', 'RECEIPT_AUTH_MISREPORTED')
        result['checks'].append('unsigned_receipt_recorded')

        restored = _invoke('restore', '--archive', str(zip_path),
                           '--output-dir', str(restore_dir), '--synthetic-only',
                           '--accept-plaintext')
        _generated_file(restore_dir, restored['restored_path'], 'sqlite',
                        expected_sha=snapshot['snapshot_sha256'])
        result['checks'].append('independent_zip_restore_sha256')

        catalog = _invoke('audit', '--output-dir', str(arc_dir))
        entries = {item['name']: item['status'] for item in catalog['records']}
        _check(entries.get(zip_path.name) == 'RECORDED_AND_CONTENT_VERIFIED_UNSIGNED',
               'RECEIPT_AUDIT_FAILED')
        result['checks'].append('read_only_receipt_audit')

        # ZIP hash was independently checked above; the ledger itself still
        # stores a caller-supplied, unsigned and unverified digest.
        _record_then_hold_replay(ledger_dir, request_id, plan_sha,
                                 archive['archive_sha256'])
        _check(len(list(arc_dir.glob('dbvora-*.zip'))) == 1,
               'REPLAY_CREATED_DUPLICATE_ARCHIVE')
        result['checks'].append('recorded_request_replay_held_without_duplicate')

        if include_zstd:
            if shutil.which('zstd') is None:
                result['optional_zstd'] = 'skipped_no_local_codec'
            else:
                zstd_archive = _invoke('archive', '--snapshot', str(snap_path),
                                       '--output-dir', str(arc_dir), '--codec', 'zstd',
                                       '--level', '3', '--synthetic-only', '--accept-plaintext')
                zstd_path = _generated_file(arc_dir, zstd_archive['archive_path'], 'dbvz',
                                            expected_sha=zstd_archive['archive_sha256'])
                recovered = _invoke('restore', '--archive', str(zstd_path),
                                    '--output-dir', str(restore_dir), '--synthetic-only',
                                    '--accept-plaintext')
                _generated_file(restore_dir, recovered['restored_path'], 'sqlite',
                                expected_sha=snapshot['snapshot_sha256'])
                _check(recovered['restored_sha256'] == snapshot['snapshot_sha256'],
                       'ZSTD_REPORTED_SHA_MISMATCH')
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
