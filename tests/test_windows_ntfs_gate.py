"""Synthetic Windows NTFS gate *decision logic*; no Windows execution implied."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from scripts import windows_ntfs_gate as gate


class WindowsNtfsGateTests(unittest.TestCase):
    def kw(self, **override):
        good = dict(platform_name='Windows', python_version=(3, 11), filesystem='NTFS',
                    preflight_fn=lambda: {
                        'archive_publish_test': 'passed_on_temporary_filesystem',
                        'ready_for_customer_data': False,
                        'writes_outside_os_temporary_folder': False},
                    release_fn=lambda: {
                        'status': 'PASS_SYNTHETIC_ENVIRONMENT_ONLY',
                        'ready_for_customer_data': False,
                        'steps': [{'step': p, 'status': 'PASS'} for p in gate._REQUIRED_STEPS]})
        good.update(override)
        return good

    def test_synthetic_pass_is_not_customer_or_powerloss_ready(self):
        report = gate.verify_windows_ntfs(**self.kw())
        self.assertEqual(report['status'], 'PASS_WINDOWS_NTFS_SYNTHETIC_ONLY')
        self.assertFalse(report['ready_for_customer_data'])
        self.assertFalse(report['hardware_power_loss_verified'])
        self.assertTrue(report['windows_host_verified'])
        self.assertEqual(len(report['steps']), 5)

    def test_linux_requires_real_windows_host_before_any_probe(self):
        touched = []
        result = gate.verify_windows_ntfs(**self.kw(platform_name='Linux', preflight_fn=lambda: touched.append(1)))
        self.assertEqual(result['reason'], 'WINDOWS_HOST_REQUIRED')
        self.assertEqual(touched, [])

    def test_python_312_rejected_without_file_write(self):
        touched = []
        result = gate.verify_windows_ntfs(**self.kw(python_version=(3, 12), preflight_fn=lambda: touched.append(1)))
        self.assertEqual(result['reason'], 'PYTHON_3_11_REQUIRED')
        self.assertFalse(touched)

    def test_non_ntfs_temp_volume_rejected_without_probe(self):
        touched = []
        result = gate.verify_windows_ntfs(**self.kw(filesystem='ReFS', preflight_fn=lambda: touched.append(1)))
        self.assertEqual(result['reason'], 'NTFS_TEMP_VOLUME_REQUIRED')
        self.assertFalse(touched)

    def test_directory_fsync_failure_blocks_promotion(self):
        failed = lambda: dict(archive_publish_test='unsupported_or_failed',
                              ready_for_customer_data=False,
                              writes_outside_os_temporary_folder=False)
        report = gate.verify_windows_ntfs(**self.kw(preflight_fn=failed))
        self.assertEqual(report['reason'], 'DURABILITY_NOT_PROVEN_FAIL_CLOSED')
        self.assertEqual(len(report['steps']), 4)

    def test_preflight_customer_ready_flag_is_rejected(self):
        unexpected = lambda: dict(archive_publish_test='passed_on_temporary_filesystem',
                                  ready_for_customer_data=True,
                                  writes_outside_os_temporary_folder=False)
        report = gate.verify_windows_ntfs(**self.kw(preflight_fn=unexpected))
        self.assertEqual(report['status'], 'BLOCKED_UNVERIFIED')

    def test_preflight_external_write_flag_is_rejected(self):
        unexpected = lambda: dict(archive_publish_test='passed_on_temporary_filesystem',
                                  ready_for_customer_data=False,
                                  writes_outside_os_temporary_folder=True)
        self.assertEqual(gate.verify_windows_ntfs(**self.kw(preflight_fn=unexpected))['status'], 'BLOCKED_UNVERIFIED')

    def test_missing_or_forged_gate_steps_rejected(self):
        for bad in ({'status': 'PASS_SYNTHETIC_ENVIRONMENT_ONLY', 'ready_for_customer_data': False, 'steps': []},
                    {'status': 'PASS_SYNTHETIC_ENVIRONMENT_ONLY', 'ready_for_customer_data': False,
                     'steps': [{'step': p, 'status': 'PASS'} for p in gate._REQUIRED_STEPS[:-1]]},
                    {'status': 'PASS_SYNTHETIC_ENVIRONMENT_ONLY', 'ready_for_customer_data': True,
                     'steps': [{'step': p, 'status': 'PASS'} for p in gate._REQUIRED_STEPS]}):
            with self.subTest(bad=bad):
                self.assertEqual(gate.verify_windows_ntfs(**self.kw(release_fn=lambda: bad))['status'], 'BLOCKED_UNVERIFIED')

    def test_exception_in_durability_probe_fails_sanitized(self):
        def broken():
            raise OSError('private files path should never be printed')
        report = gate.verify_windows_ntfs(**self.kw(preflight_fn=broken))
        self.assertNotIn('private files', json.dumps(report))
        self.assertEqual(report['reason'], 'DURABILITY_NOT_PROVEN_FAIL_CLOSED')

    def test_exception_in_release_gate_fails_sanitized(self):
        def broken():
            raise RuntimeError('private files path should never be printed')
        report = gate.verify_windows_ntfs(**self.kw(release_fn=broken))
        self.assertNotIn('private files', json.dumps(report))
        self.assertEqual(report['reason'], 'REGRESSION_OR_SYNTHETIC_GATE_FAILED')

    def test_running_main_on_linux_fails_closed_without_paths(self):
        with patch.object(gate, 'verify_windows_ntfs', return_value={
            'status': 'BLOCKED_UNVERIFIED', 'ready_for_customer_data': False,
            'reason': 'WINDOWS_HOST_REQUIRED'}):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = gate.main()
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(output.getvalue())['ready_for_customer_data'])


if __name__ == '__main__':
    unittest.main()
