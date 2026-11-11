"""Offline-only synthetic review HTML safety, UX, publishing and CLI tests."""
from contextlib import closing, redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from dbvora.archive import review_html
from dbvora.archive.request_audit import LEDGER_NAME, APPLICATION_ID


def fixture_summary():
    return dict(contract_version='dbvora.synthetic.request-reconcile.v1',
                inspection_mode='read_only_human_review_only', request_count=3,
                counts=dict(INTERRUPTED_REVIEW_REQUIRED=1,
                            RECORDED_MATCH_REVIEW_REQUIRED=1,
                            RECORDED_NOT_VERIFIED=1,
                            DUPLICATE_ARTIFACT_REVIEW_REQUIRED=0),
                unmatched_verified_archive_count=2,
                may_resume_archive=False, exactly_once_verified=False,
                authenticity_verified=False, power_loss_verified=False,
                ready_for_customer_data=False)


class ReviewHtmlTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='dbvora-html-test-')
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)

    def publish(self, data=None, **kw):
        return review_html.publish(data if data is not None else fixture_summary(), self.folder,
                                   synthetic_only=True, accept_plaintext_summary=True, **kw)

    def test_html_has_korean_accessible_table_and_manual_disclaimer(self):
        text = review_html.render(fixture_summary()).decode()
        for phrase in ('lang="ko"', '<caption>', '복구 승인 아님', '중단된 요청',
                       '원장에 없는', '자동 정리', "default-src 'none'"):
            self.assertIn(phrase, text)

    def test_html_never_includes_row_data_or_filenames(self):
        report = review_html.render(fixture_summary()).decode()
        for value in ('private_db.sqlite', 'password=', '<script', 'fetch(', 'onclick=', 'http:'):
            self.assertNotIn(value, report)

    def test_no_script_and_no_remote_resources(self):
        text = review_html.render(fixture_summary()).decode()
        for marker in ('<script', '<link', '<iframe', '<img', '<form', 'https://', 'src='):
            self.assertNotIn(marker, text)

    def test_publish_creates_new_file_without_overwrite(self):
        original = (self.folder / 'existing.html')
        original.write_bytes(b'preserve-me')
        result = self.publish()
        self.assertEqual(result['status'], 'LOCAL_SYNTHETIC_REVIEW_ONLY')
        self.assertTrue((self.folder / result['report_name']).exists())
        self.assertEqual(original.read_bytes(), b'preserve-me')
        self.assertFalse(result['may_resume_archive'])

    def test_two_reports_have_separate_names(self):
        self.assertNotEqual(self.publish()['report_name'], self.publish()['report_name'])

    def test_synthetic_ack_required(self):
        with self.assertRaisesRegex(review_html.ReviewError, 'SYNTHETIC_ONLY_REQUIRED'):
            review_html.publish(fixture_summary(), self.folder, accept_plaintext_summary=True)

    def test_plaintext_ack_required(self):
        with self.assertRaisesRegex(review_html.ReviewError, 'PLAINTEXT_SUMMARY_ACK_REQUIRED'):
            review_html.publish(fixture_summary(), self.folder, synthetic_only=True)

    def test_invalid_summary_extra_field_fails_closed(self):
        data = fixture_summary()
        data['customer_sql'] = 'select private'
        with self.assertRaisesRegex(review_html.ReviewError, 'INVALID_REVIEW_SUMMARY'):
            review_html.render(data)

    def test_invalid_count_total_fails_closed(self):
        data = fixture_summary()
        data['request_count'] = 2
        with self.assertRaisesRegex(review_html.ReviewError, 'INVALID_REVIEW_SUMMARY'):
            review_html.render(data)

    def test_bool_not_treated_as_integer(self):
        data = fixture_summary()
        data['counts']['RECORDED_MATCH_REVIEW_REQUIRED'] = True
        with self.assertRaisesRegex(review_html.ReviewError, 'INVALID_REVIEW_SUMMARY'):
            review_html.render(data)

    def test_positive_recovery_claim_rejected(self):
        data = fixture_summary()
        data['may_resume_archive'] = True
        with self.assertRaisesRegex(review_html.ReviewError, 'UNSAFE_REVIEW_SUMMARY'):
            review_html.render(data)

    def test_invalid_scope_rejected(self):
        data = fixture_summary()
        data['inspection_mode'] = 'automated_recovery'
        with self.assertRaisesRegex(review_html.ReviewError, 'INVALID_REVIEW_SUMMARY'):
            review_html.render(data)

    def test_negative_count_rejected(self):
        data = fixture_summary()
        data['counts']['RECORDED_NOT_VERIFIED'] = -1
        with self.assertRaisesRegex(review_html.ReviewError, 'INVALID_REVIEW_SUMMARY'):
            review_html.render(data)

    def test_over_bound_rejected(self):
        data = fixture_summary()
        data['unmatched_verified_archive_count'] = 251
        with self.assertRaisesRegex(review_html.ReviewError, 'INVALID_REVIEW_SUMMARY'):
            review_html.render(data)

    def test_output_directory_must_exist_and_be_absolute(self):
        for bad in ('relative', self.folder / 'missing'):
            with self.assertRaises(review_html.ReviewError):
                review_html.publish(fixture_summary(), bad, synthetic_only=True,
                                    accept_plaintext_summary=True)

    def test_output_symlink_rejected(self):
        alias = self.folder / 'alias'
        try:
            alias.symlink_to(self.folder, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlink unavailable')
        with self.assertRaisesRegex(review_html.ReviewError, 'UNSAFE_OUTPUT'):
            review_html.publish(fixture_summary(), alias, synthetic_only=True,
                                accept_plaintext_summary=True)

    def test_created_report_is_mode_0600_on_posix(self):
        import os, stat
        if os.name != 'posix':
            self.skipTest('posix permission only')
        report = self.folder / self.publish()['report_name']
        self.assertEqual(stat.S_IMODE(report.stat().st_mode), 0o600)

    def test_file_content_is_deterministic_despite_random_file_name(self):
        a = self.folder / self.publish()['report_name']
        b = self.folder / self.publish()['report_name']
        self.assertEqual(hashlib.sha256(a.read_bytes()).hexdigest(),
                         hashlib.sha256(b.read_bytes()).hexdigest())

    def test_cli_requires_synthetic_before_reading_private_files(self):
        fake_zip = ModuleType('dbvora.archive.safe_zip')
        fake_zip.ArchiveError = type('ArchiveError', (Exception,), {})
        stderr = io.StringIO()
        with patch.dict('sys.modules', {'dbvora.archive.safe_zip': fake_zip}), redirect_stderr(stderr):
            code = review_html.main(['--ledger-dir', '/private/db', '--archive-dir', '/secret',
                                     '--output-dir', '/secret'])
        self.assertEqual(code, 2)
        self.assertIn('SYNTHETIC_ONLY_REQUIRED', stderr.getvalue())
        self.assertNotIn('/private', stderr.getvalue())

    def test_cli_real_ledger_with_fake_catalog_writes_separate_html(self):
        # A genuine SQLite ledger is read. Only the recovery catalog is injected.
        import sys
        from dbvora.archive.request_audit import reconcile_requests
        d = self.folder / 'ledger'
        a = self.folder / 'archives'
        o = self.folder / 'review'
        for folder in (d, a, o):
            folder.mkdir()
        ledger = d / LEDGER_NAME
        with closing(sqlite3.connect(ledger)) as con:
            con.execute(f'PRAGMA application_id={APPLICATION_ID}')
            con.execute('PRAGMA user_version=1')
            con.execute('CREATE TABLE requests (request_key TEXT PRIMARY KEY, plan_sha TEXT NOT NULL, '
                        "phase TEXT NOT NULL CHECK(phase IN ('RESERVED','RECORDED')), artifact_sha TEXT)")
            con.execute('INSERT INTO requests VALUES(?,?,?,NULL)',
                        (hashlib.sha256(b'request').hexdigest(), hashlib.sha256(b'plan').hexdigest(), 'RESERVED'))
            con.commit()
        audit_fixture = {'contract_version': 'p1-c3.audit.v1', 'complete': True,
                         'inspection_mode': 'read_only_no_cleanup', 'records': []}
        fake_catalog = ModuleType('dbvora.archive.recovery_catalog')
        fake_catalog.inspect_recovery_catalog = lambda _path: audit_fixture
        fake_zip = ModuleType('dbvora.archive.safe_zip')
        fake_zip.ArchiveError = type('ArchiveError', (Exception,), {})
        stdout, stderr = io.StringIO(), io.StringIO()
        before = ledger.read_bytes()
        with patch.dict(sys.modules, {'dbvora.archive.recovery_catalog': fake_catalog,
                                      'dbvora.archive.safe_zip': fake_zip}), \
             redirect_stdout(stdout), redirect_stderr(stderr):
            result = review_html.main(['--ledger-dir', str(d), '--archive-dir', str(a),
                                       '--output-dir', str(o), '--synthetic-only',
                                       '--accept-plaintext-summary'])
        self.assertEqual(result, 0, stderr.getvalue())
        report = json.loads(stdout.getvalue())['result']
        self.assertFalse(report['customer_ready'])
        self.assertIn('중단된 요청', (o / report['report_name']).read_text())
        self.assertEqual(before, ledger.read_bytes())
        self.assertEqual(len(list(a.iterdir())), 0)

    def test_cli_rejects_nested_output_within_archive_directory(self):
        subdir = self.folder / 'nested'
        subdir.mkdir()
        fake_zip = ModuleType('dbvora.archive.safe_zip')
        fake_zip.ArchiveError = type('ArchiveError', (Exception,), {})
        stderr = io.StringIO()
        with patch.dict('sys.modules', {'dbvora.archive.safe_zip': fake_zip}), redirect_stderr(stderr):
            code = review_html.main(['--ledger-dir', str(self.folder), '--archive-dir', str(self.folder),
                                     '--output-dir', str(subdir), '--synthetic-only',
                                     '--accept-plaintext-summary'])
        self.assertEqual(code, 2)
        self.assertIn('SEPARATE_OUTPUT_REQUIRED', stderr.getvalue())

    def test_cli_rejects_ledger_as_output_dir(self):
        fake_zip = ModuleType('dbvora.archive.safe_zip')
        fake_zip.ArchiveError = type('ArchiveError', (Exception,), {})
        stderr = io.StringIO()
        with patch.dict('sys.modules', {'dbvora.archive.safe_zip': fake_zip}), redirect_stderr(stderr):
            code = review_html.main(['--ledger-dir', str(self.folder), '--archive-dir', str(self.folder),
                                     '--output-dir', str(self.folder), '--synthetic-only',
                                     '--accept-plaintext-summary'])
        self.assertEqual(code, 2)
        self.assertIn('SEPARATE_OUTPUT_REQUIRED', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
