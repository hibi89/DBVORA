"""Offline HTML self-test must be synthetic, path-free and fail closed."""
import unittest
from unittest.mock import patch

from dbvora import offline_selftest as selftest


class OfflineSelftestTests(unittest.TestCase):
    def test_real_synthetic_html_report(self):
        report = selftest.verify()
        self.assertEqual(report['status'], 'PASS_SYNTHETIC_OFFLINE_HTML_ONLY', report)
        self.assertEqual(report['checks_passed'], 9)
        self.assertFalse(report['ready_for_customer_data'])
        self.assertFalse(report['windows_ntfs_durability_verified'])
        self.assertFalse(report['native_file_browser_verified'])

    def test_export_error_fails_without_paths(self):
        with patch.object(selftest, 'export', side_effect=RuntimeError('SECRET_TEST_PATH')):
            report = selftest.verify()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['error_code'], 'SYNTHETIC_CHECK_FAILED')
        self.assertNotIn('SECRET_TEST_PATH', str(report))

    def test_unexpected_output_filename_is_rejected(self):
        with patch.object(selftest, 'export', return_value={'filename': '../escape.html'}):
            report = selftest.verify()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['error_code'], 'SYNTHETIC_CHECK_FAILED')

    def test_missing_output_filename_is_rejected(self):
        with patch.object(selftest, 'export', return_value={}):
            self.assertEqual(selftest.verify()['status'], 'FAIL_CLOSED')


if __name__ == '__main__':
    unittest.main()
