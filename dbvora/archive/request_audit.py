"""Read-only, fail-closed reconciliation of a local archive request ledger.

Never retries, mutates, approves, deletes, or authenticates an archive. The caller
supplies a trusted local ledger directory and an independent recovery catalog
produced by inspect_recovery_catalog. Synthetic-only preview, not a release.
"""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote

LEDGER_NAME = '.dbvora-request-ledger-v1.sqlite'
APPLICATION_ID = 0x44425652
MAX_LEDGER_BYTES = 32 * 1024 * 1024
MAX_REQUESTS = 10000
DIGEST = re.compile(r'[a-f0-9]{64}\Z', re.ASCII)
KNOWN_PHASES = {'RESERVED', 'RECORDED'}
REQUIRED_COLUMNS = ('request_key', 'plan_sha', 'phase', 'artifact_sha')


class AuditError(ValueError):
    """Only stable codes, never filesystem paths or connection details."""


def _safe_dir(directory: str | Path) -> Path:
    import stat
    if not isinstance(directory, (str, Path)):
        raise AuditError('INVALID_DIRECTORY')
    folder = Path(directory)
    if not folder.is_absolute():
        raise AuditError('INVALID_DIRECTORY')
    try:
        for entry in (folder, *folder.parents):
            info = entry.lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise AuditError('UNSAFE_DIRECTORY')
    except AuditError:
        raise
    except OSError:
        raise AuditError('DIRECTORY_UNAVAILABLE') from None
    return folder


def _identity(path: Path) -> tuple[int, int, int, int, int]:
    import stat
    try:
        s = path.lstat()
    except OSError:
        raise AuditError('LEDGER_UNAVAILABLE') from None
    if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1 or not 100 <= s.st_size <= MAX_LEDGER_BYTES:
        raise AuditError('UNSAFE_LEDGER')
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def _read_ledger(directory: Path) -> list[tuple[str, str | None]]:
    path = directory / LEDGER_NAME
    initial = _identity(path)
    # A concurrent active writer or unexpected journal mode requires manual review.
    for sidecar in ('-wal', '-shm', '-journal'):
        if (directory / (LEDGER_NAME + sidecar)).exists():
            raise AuditError('LEDGER_ACTIVE')
    uri = 'file:' + quote(str(path), safe='/') + '?mode=ro'
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=2)) as con:
            con.execute('PRAGMA query_only=ON')
            if con.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID:
                raise AuditError('UNTRUSTED_LEDGER')
            if con.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise AuditError('UNTRUSTED_LEDGER')
            columns = tuple(row[1] for row in con.execute('PRAGMA table_info(requests)'))
            if columns != REQUIRED_COLUMNS:
                raise AuditError('UNTRUSTED_LEDGER')
            if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise AuditError('INVALID_LEDGER')
            rows = con.execute('SELECT request_key,plan_sha,phase,artifact_sha '
                               'FROM requests ORDER BY request_key LIMIT ?', (MAX_REQUESTS + 1,)).fetchall()
    except AuditError:
        raise
    except (sqlite3.Error, OSError, ValueError, TypeError):
        raise AuditError('INVALID_LEDGER') from None
    if _identity(path) != initial:
        raise AuditError('LEDGER_CHANGED')
    if len(rows) > MAX_REQUESTS:
        raise AuditError('LEDGER_LIMIT')
    seen = set()
    state = []
    for key, plan, phase, artifact in rows:
        if (type(key) is not str or not DIGEST.fullmatch(key)
                or type(plan) is not str or not DIGEST.fullmatch(plan)
                or phase not in KNOWN_PHASES or key in seen):
            raise AuditError('INVALID_LEDGER')
        if phase == 'RESERVED':
            if artifact is not None:
                raise AuditError('INVALID_LEDGER')
            state.append((phase, None))
        else:
            if type(artifact) is not str or not DIGEST.fullmatch(artifact):
                raise AuditError('INVALID_LEDGER')
            state.append((phase, artifact))
        seen.add(key)
    return state


def reconcile_requests(ledger_directory: str | Path, recovery_catalog: dict,
                       *, synthetic_only: bool = False) -> dict:
    """Cross-check hashes with a previously independent read-only catalog.

    This is evidence for HUMAN review only. A matching SHA is never permission
    to resume work, and never establishes cryptographic authorship or fsync.
    """
    if synthetic_only is not True:
        raise AuditError('SYNTHETIC_ONLY_REQUIRED')
    if type(recovery_catalog) is not dict or recovery_catalog.get('contract_version') != 'p1-c3.audit.v1' or recovery_catalog.get('complete') is not True or recovery_catalog.get('inspection_mode') != 'read_only_no_cleanup':
        raise AuditError('UNTRUSTED_CATALOG')
    records = recovery_catalog.get('records')
    if type(records) is not list or len(records) > 250:
        raise AuditError('UNTRUSTED_CATALOG')
    verified = {}
    for item in records:
        if type(item) is not dict:
            raise AuditError('UNTRUSTED_CATALOG')
        if item.get('kind') not in ('sqlite', 'zip', 'dbvz', 'temporary'):
            raise AuditError('UNTRUSTED_CATALOG')
        if item.get('kind') not in ('zip', 'dbvz') or item.get('status') != 'CONTENT_VERIFIED_PUBLISH_UNPROVEN':
            continue
        digest = item.get('artifact_sha256')
        if type(digest) is not str or DIGEST.fullmatch(digest) is None:
            raise AuditError('UNTRUSTED_CATALOG')
        verified[digest] = verified.get(digest, 0) + 1
    ledger = _read_ledger(_safe_dir(ledger_directory))
    breakdown = {'INTERRUPTED_REVIEW_REQUIRED': 0,
                 'RECORDED_MATCH_REVIEW_REQUIRED': 0,
                 'RECORDED_NOT_VERIFIED': 0,
                 'DUPLICATE_ARTIFACT_REVIEW_REQUIRED': 0}
    matched = set()
    for phase, digest in ledger:
        if phase == 'RESERVED':
            breakdown['INTERRUPTED_REVIEW_REQUIRED'] += 1
        elif verified.get(digest, 0) == 1:
            breakdown['RECORDED_MATCH_REVIEW_REQUIRED'] += 1
            matched.add(digest)
        elif verified.get(digest, 0) > 1:
            breakdown['DUPLICATE_ARTIFACT_REVIEW_REQUIRED'] += 1
        else:
            breakdown['RECORDED_NOT_VERIFIED'] += 1
    return {'contract_version': 'dbvora.synthetic.request-reconcile.v1',
            'inspection_mode': 'read_only_human_review_only',
            'request_count': len(ledger), 'counts': breakdown,
            'unmatched_verified_archive_count': sum(n for k, n in verified.items() if k not in matched),
            'may_resume_archive': False, 'exactly_once_verified': False,
            'authenticity_verified': False, 'power_loss_verified': False,
            'ready_for_customer_data': False}


def inspect_and_reconcile(ledger_directory: str | Path, archive_directory: str | Path,
                          *, synthetic_only: bool = False) -> dict:
    """Run real independent archive recovery inspection before ledger comparison.

    No mutation or external traffic. Caller must still explicitly approve a
    synthetic-only inspection; both directories must already exist locally.
    """
    if synthetic_only is not True:
        raise AuditError('SYNTHETIC_ONLY_REQUIRED')
    from dbvora.archive.recovery_catalog import inspect_recovery_catalog
    return reconcile_requests(ledger_directory,
                              inspect_recovery_catalog(_safe_dir(archive_directory)),
                              synthetic_only=True)


def main(argv=None) -> int:
    import argparse
    import json
    import sys
    from dbvora.archive.safe_zip import ArchiveError

    class Parser(argparse.ArgumentParser):
        def error(self, _message):
            raise AuditError('INVALID_ARGUMENT')

    parser = Parser(prog='python -m dbvora.archive.request_audit',
                    description='Read-only synthetic archive/ledger reconciliation; no retries')
    parser.add_argument('--ledger-dir', required=True)
    parser.add_argument('--archive-dir', required=True)
    parser.add_argument('--synthetic-only', action='store_true')
    try:
        args = parser.parse_args(argv)
        result = inspect_and_reconcile(args.ledger_dir, args.archive_dir,
                                       synthetic_only=args.synthetic_only)
        print(json.dumps({'ok': True, 'result': result}, sort_keys=True))
        return 0
    except (AuditError, ArchiveError) as exc:
        code = str(exc) if isinstance(exc, AuditError) else exc.code
    except (OSError, ValueError, TypeError, sqlite3.Error):
        code = 'INSPECTION_FAILED'
    except Exception:
        code = 'UNEXPECTED_FAILURE'
    # Intentionally no raw exception/path/SQL/secret output.
    print(json.dumps({'ok': False, 'error': {'code': code}}, sort_keys=True), file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
