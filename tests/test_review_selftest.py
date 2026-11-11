"""Portable self-contained review test: no external fixtures or customer input."""
from contextlib import closing, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import review_selftest as selftest


class PortableReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='dbvora-portable-selftest-case-')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)

    def test_real_zip_and_zstd_selfcheck(self):
        report = selftest.verify()
        self.assertEqual(report['status'], 'PASS_SYNTHETIC_PREVIEW_ONLY', report)
        self.assertEqual(report['zip'], 'passed')
        self.assertIn(report['zstd'], ('passed', 'skipped_no_local_codec'))
        self.assertEqual(report['checks'], 22 if report['zstd'] == 'passed' else 11)
        self.assertFalse(report['customer_ready'])
        self.assertFalse(report['hardware_power_loss_verified'])
        self.assertFalse(report['windows_ntfs_durability_verified'])
        self.assertFalse(report['exactly_once_verified'])

    def test_zip_only_when_optional_codec_missing(self):
        with patch.object(selftest.shutil, 'which', return_value=None):
            report = selftest.verify()
        self.assertEqual(report['status'], 'PASS_SYNTHETIC_PREVIEW_ONLY')
        self.assertEqual(report['zstd'], 'skipped_no_local_codec')
        self.assertEqual(report['checks'], 11)

    def test_real_generated_fixture_is_consistent_sqlite(self):
        source = self.base / 'fixture.sqlite'
        selftest._fixture(source)
        with closing(sqlite3.connect(source)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone(), ('ok',))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM synthetic_parent').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM synthetic_child').fetchone()[0], 1)

    def test_signature_does_not_accept_short_file(self):
        p = self.base / 'short'
        p.write_bytes(b'secret')
        with self.assertRaisesRegex(selftest.SelftestError, 'UNSAFE_SYNTHETIC_FILE'):
            selftest._signature(p)

    def test_signature_detects_source_content_change(self):
        p = self.base / 'data'
        p.write_bytes(b'X' * 256)
        before = selftest._signature(p)
        p.write_bytes(b'Y' * 256)
        self.assertNotEqual(before, selftest._signature(p))

    def test_symlink_file_rejected(self):
        source = self.base / 'real'
        source.write_bytes(b'X' * 200)
        link = self.base / 'link'
        try:
            link.symlink_to(source)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unsupported')
        with self.assertRaisesRegex(selftest.SelftestError, 'UNSAFE_SYNTHETIC_FILE'):
            selftest._signature(link)

    def test_cli_disallows_customer_paths(self):
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = selftest.main(['--db', '/secret/customer.sqlite'])
        self.assertEqual(exit_code, 1)
        self.assertIn('NO_USER_INPUT_ALLOWED', out.getvalue())
        self.assertNotIn('/secret/customer', out.getvalue())

    def test_cli_no_arguments_returns_safe_summary(self):
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = selftest.main([])
        data = json.loads(out.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(data['status'], 'PASS_SYNTHETIC_PREVIEW_ONLY')
        self.assertNotIn(str(self.base), out.getvalue())
        self.assertFalse(data['customer_ready'])

    def test_fake_positive_without_restored_artifact_rejected(self):
        with patch.object(selftest, 'restore_zip_archive', side_effect=selftest.SelftestError('RESTORE_BLOCKED')):
            report = selftest.verify()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['error_code'], 'RESTORE_BLOCKED')
        self.assertFalse(report['customer_ready'])

    def test_fake_positive_without_archive_creation_rejected(self):
        with patch.object(selftest, 'archive_once', side_effect=RuntimeError('private/password')):
            report = selftest.verify()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['error_code'], 'UNEXPECTED_PREVIEW_FAILURE')
        self.assertNotIn('password', json.dumps(report))

    def test_missing_local_zstd_only_downgrades_optional_codec(self):
        with patch.object(selftest.shutil, 'which', return_value=None):
            result = selftest.verify()
        self.assertEqual(result['zip'], 'passed')
        self.assertEqual(result['zstd'], 'skipped_no_local_codec')
        self.assertEqual(result['status'], 'PASS_SYNTHETIC_PREVIEW_ONLY')

    def test_bad_restore_is_not_reinterpreted_as_hardware_ready(self):
        with patch.object(selftest, 'archive_once', side_effect=selftest.SelftestError('BAD_ARCHIVE')):
            result = selftest.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertFalse(result['hardware_power_loss_verified'])
        self.assertFalse(result['windows_ntfs_durability_verified'])

    def test_never_leak_os_errors_into_output(self):
        with patch.object(selftest, 'create_snapshot', side_effect=OSError('C:\\private\\customer.sqlite')):
            result = selftest.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertNotIn('C:\\\\private', json.dumps(result))
        self.assertNotIn('customer.sqlite', json.dumps(result))

    def test_expected_name_for_output_contract(self):
        report = selftest.verify()
        self.assertEqual(report['contract'], 'dbvora.portable-synthetic-review.v1')
        self.assertEqual(report['scope'], 'OS_TEMP_SYNTHETIC_ONLY')


if __name__ == '__main__':
    unittest.main()
