"""Isolated synthetic fixtures for read-only ledger reconciliation."""
from __future__ import annotations

from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from dbvora.archive.request_audit import AuditError, LEDGER_NAME, APPLICATION_ID, reconcile_requests


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def catalog(*digests):
    return {'contract_version': 'p1-c3.audit.v1', 'complete': True,
            'inspection_mode': 'read_only_no_cleanup',
            'records': [{'kind': 'zip', 'status': 'CONTENT_VERIFIED_PUBLISH_UNPROVEN',
                         'artifact_sha256': d} for d in digests]}


class RequestReconcileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.ledger = self.folder / LEDGER_NAME

    def create_ledger(self, items=()):
        with closing(sqlite3.connect(self.ledger)) as db:
            db.execute(f'PRAGMA application_id={APPLICATION_ID}')
            db.execute('PRAGMA user_version=1')
            db.execute('CREATE TABLE requests (request_key TEXT PRIMARY KEY, plan_sha TEXT NOT NULL, '
                       "phase TEXT NOT NULL CHECK(phase IN ('RESERVED','RECORDED')), artifact_sha TEXT)")
            db.executemany('INSERT INTO requests VALUES (?,?,?,?)', items)
            db.commit()

    def run_audit(self, audit=None):
        return reconcile_requests(self.folder, catalog() if audit is None else audit, synthetic_only=True)

    def test_empty_ledger_is_review_only(self):
        self.create_ledger()
        first = self.ledger.read_bytes()
        result = self.run_audit()
        self.assertEqual(result['request_count'], 0)
        self.assertFalse(result['may_resume_archive'])
        self.assertEqual(first, self.ledger.read_bytes())

    def test_reserved_is_never_assumed_to_have_executed(self):
        self.create_ledger([(sha('id'), sha('plan'), 'RESERVED', None)])
        self.assertEqual(self.run_audit()['counts']['INTERRUPTED_REVIEW_REQUIRED'], 1)

    def test_recorded_digest_matches_verified_catalog_but_not_authenticity(self):
        digest = sha('archive')
        self.create_ledger([(sha('id'), sha('plan'), 'RECORDED', digest)])
        r = self.run_audit(catalog(digest))
        self.assertEqual(r['counts']['RECORDED_MATCH_REVIEW_REQUIRED'], 1)
        self.assertFalse(r['authenticity_verified'])
        self.assertFalse(r['exactly_once_verified'])

    def test_missing_archive_refuses_falsely_verified_state(self):
        self.create_ledger([(sha('id'), sha('plan'), 'RECORDED', sha('missing'))])
        self.assertEqual(self.run_audit()['counts']['RECORDED_NOT_VERIFIED'], 1)

    def test_duplicate_verified_artifact_needs_manual_review(self):
        digest = sha('archive')
        self.create_ledger([(sha('id'), sha('plan'), 'RECORDED', digest)])
        self.assertEqual(self.run_audit(catalog(digest, digest))['counts']['DUPLICATE_ARTIFACT_REVIEW_REQUIRED'], 1)

    def test_same_archive_claimed_by_two_requests_is_ambiguous(self):
        digest = sha('shared')
        self.create_ledger([(sha('one'), sha('plan1'), 'RECORDED', digest),
                            (sha('two'), sha('plan2'), 'RECORDED', digest)])
        result = self.run_audit(catalog(digest))
        self.assertEqual(result['counts']['RECORDED_MATCH_REVIEW_REQUIRED'], 0)
        self.assertEqual(result['counts']['DUPLICATE_ARTIFACT_REVIEW_REQUIRED'], 2)

    def test_unmatched_verified_archive_not_assumed_approved(self):
        self.create_ledger()
        self.assertEqual(self.run_audit(catalog(sha('orphan')))['unmatched_verified_archive_count'], 1)

    def test_wrong_schema_rejected_without_write(self):
        with closing(sqlite3.connect(self.ledger)) as db:
            db.execute('CREATE TABLE secret (value TEXT)')
            db.commit()
        before = self.ledger.read_bytes()
        with self.assertRaisesRegex(AuditError, 'UNTRUSTED_LEDGER'):
            self.run_audit()
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_invalid_record_digest_fails_closed(self):
        self.create_ledger([(sha('id'), sha('plan'), 'RECORDED', 'bad-sha')])
        with self.assertRaisesRegex(AuditError, 'INVALID_LEDGER'):
            self.run_audit()

    def test_untrusted_recovery_catalog_rejected(self):
        self.create_ledger()
        with self.assertRaisesRegex(AuditError, 'UNTRUSTED_CATALOG'):
            self.run_audit({'records': [], 'complete': True})

    def test_missing_ledger_does_not_create_new_one(self):
        with self.assertRaisesRegex(AuditError, 'LEDGER_UNAVAILABLE'):
            self.run_audit()
        self.assertFalse(self.ledger.exists())

    def test_symlink_ledger_rejected(self):
        target = self.folder / 'customer.txt'
        target.write_text('private')
        try:
            self.ledger.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        with self.assertRaisesRegex(AuditError, 'UNSAFE_LEDGER'):
            self.run_audit()
        self.assertEqual(target.read_text(), 'private')

    def test_non_synthetic_mode_rejected(self):
        with self.assertRaisesRegex(AuditError, 'SYNTHETIC_ONLY_REQUIRED'):
            reconcile_requests(self.folder, catalog())

    def test_active_journal_blocks_audit(self):
        self.create_ledger()
        (self.folder / (LEDGER_NAME + '-journal')).write_bytes(b'incomplete')
        with self.assertRaisesRegex(AuditError, 'LEDGER_ACTIVE'):
            self.run_audit()

    def test_no_source_paths_or_request_ids_in_report(self):
        self.create_ledger([(sha('private-id'), sha('private-plan'), 'RESERVED', None)])
        r = str(self.run_audit())
        self.assertNotIn(str(self.folder), r)
        self.assertNotIn('private-id', r)


class RequestAuditCliTests(unittest.TestCase):
    def test_missing_ack_fails_before_file_access(self):
        from dbvora.archive.request_audit import AuditError, inspect_and_reconcile
        with self.assertRaisesRegex(AuditError, 'SYNTHETIC_ONLY_REQUIRED'):
            inspect_and_reconcile('/not/call/ledger', '/not/call/archive')

    def test_invalid_command_never_prints_argument_path(self):
        import io
        from contextlib import redirect_stderr
        from unittest.mock import patch
        from dbvora.archive import request_audit
        from types import ModuleType
        fake_zip = ModuleType('dbvora.archive.safe_zip')
        fake_zip.ArchiveError = type('ArchiveError', (Exception,), {})
        stderr = io.StringIO()
        with patch.dict('sys.modules', {'dbvora.archive.safe_zip': fake_zip}), redirect_stderr(stderr):
            result = request_audit.main(['--unrecognized-secret', 'private-dsn=password'])
        self.assertEqual(result, 2)
        self.assertNotIn('private-dsn', stderr.getvalue())
        self.assertIn('INVALID_ARGUMENT', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
