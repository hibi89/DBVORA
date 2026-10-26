"""Offline synthetic release-gate decision logic (processes mocked)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import verify_release_gate as gate


class VerificationGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='dbvora-gate-unit-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for file in gate.REQUIRED:
            target = self.root / file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
        self.root_patch = patch.object(gate, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def responses(self, *, tests=156, checks=8, zstd='passed', customer_ready=False):
        return [
            (0, '', f'Ran {tests} tests in 1.000s\nOK'),
            (0, json.dumps({'status': 'PASS_SYNTHETIC_ONLY',
                            'check_count': checks, 'optional_zstd': zstd,
                            'ready_for_customer_data': customer_ready}), ''),
            (0, '', ''),
            (0, '# tests 1\n# pass 1\n# fail 0\n', ''),
            (0, json.dumps({'archive_publish_test': 'passed_on_temporary_filesystem',
                            'ready_for_customer_data': False}), ''),
        ]

    def test_full_mocked_gate_synthetic_pass_not_customer_release(self):
        with patch.object(gate, '_run', side_effect=self.responses()), patch.object(gate.shutil, 'which', return_value='tool'):
            report = gate.verify()
        self.assertEqual(report['status'], 'PASS_SYNTHETIC_ENVIRONMENT_ONLY')
        self.assertFalse(report['ready_for_customer_data'])
        self.assertEqual(len(report['steps']), 6)

    def test_incomplete_checkout_fails_before_execution(self):
        (self.root / 'dbvora/archive/safe_zip.py').unlink()
        with patch.object(gate, '_run') as runner:
            report = gate.verify()
        runner.assert_not_called()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['steps'][0]['error'], 'INCOMPLETE_SOURCE_CHECKOUT')

    def test_155_tests_is_not_enough(self):
        with patch.object(gate, '_run', side_effect=self.responses(tests=155)), patch.object(gate.shutil, 'which', return_value='tool'):
            report = gate.verify()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['steps'][1]['discovered_tests'], 155)

    def test_unsigned_customer_ready_claim_causes_failure(self):
        with patch.object(gate, '_run', side_effect=self.responses(customer_ready=True)), patch.object(gate.shutil, 'which', return_value='tool'):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_missing_zstd_is_explicit_supported_skip(self):
        with patch.object(gate, '_run', side_effect=self.responses(checks=7, zstd='skipped_no_local_codec')):
            with patch.object(gate.shutil, 'which', side_effect=lambda cmd: None if cmd == 'zstd' else '/usr/bin/node'):
                report = gate.verify()
        self.assertEqual(report['status'], 'PASS_SYNTHETIC_ENVIRONMENT_ONLY')

    def test_present_zstd_cannot_be_silently_skipped(self):
        with patch.object(gate, '_run', side_effect=self.responses(checks=7, zstd='skipped_no_local_codec')):
            with patch.object(gate.shutil, 'which', return_value='tool'):
                self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_one_optional_zstd_skip_is_allowed_only_without_binary(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=7)
        mocked[0] = (0, '', 'test_zstd_roundtrip_when_optional_codec_exists (test_archive_cli.ArchiveCliTests.test_zstd_roundtrip_when_optional_codec_exists) ... skipped \'optional external zstd executable unavailable\'\nRan 156 tests in 1.000s\nOK (skipped=1)')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', side_effect=lambda name: None if name == 'zstd' else '/usr/bin/node'
        ):
            self.assertEqual(gate.verify()['status'], 'PASS_SYNTHETIC_ENVIRONMENT_ONLY')

    def test_any_skip_with_zstd_installed_fails_closed(self):
        mocked = self.responses()
        mocked[0] = (0, '', 'Ran 156 tests in 1.000s\nOK (skipped=1)')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(gate.shutil, 'which', return_value='tool'):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertEqual(result['steps'][1]['skipped_tests'], 1)

    def test_more_than_one_skip_without_zstd_fails_closed(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=7)
        mocked[0] = (0, '', 'Ran 156 tests in 1.000s\nOK (skipped=2)')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', side_effect=lambda name: None if name == 'zstd' else '/usr/bin/node'
        ):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_node_exit_zero_without_tap_test_evidence_is_rejected(self):
        mocked = self.responses()
        mocked[3] = (0, 'ok', '')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(gate.shutil, 'which', return_value='tool'):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertEqual(result['steps'][4]['step'], 'node_dom')
        self.assertEqual(result['steps'][4]['status'], 'FAIL')

    def test_unrelated_skip_rejected_even_without_zstd(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=7)
        mocked[0] = (0, '', "test_backup (test_safety.Safety.test_backup) ... skipped 'bad reason'\nRan 156 tests in 1.000s\nOK (skipped=1)")
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', side_effect=lambda name: None if name == 'zstd' else '/usr/bin/node'
        ):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_skip_summary_without_identity_line_rejected(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=7)
        mocked[0] = (0, '', 'Ran 156 tests in 1.000s\nOK (skipped=1)')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', side_effect=lambda name: None if name == 'zstd' else '/usr/bin/node'
        ):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_skip_identity_from_named_case_only(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=7)
        mocked[0] = (0, '', "test_zstd_roundtrip_when_optional_codec_exists (test_archive_cli.ArchiveCliTests.test_zstd_roundtrip_when_optional_codec_exists) ... skipped 'wrong reason'\nRan 156 tests in 1.000s\nOK (skipped=1)")
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', side_effect=lambda name: None if name == 'zstd' else '/usr/bin/node'
        ):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_timeout_and_missing_output_fails_closed(self):
        bad = self.responses()
        bad[0] = (-1, '', '')
        bad[1] = (-1, '', '')
        with patch.object(gate, '_run', side_effect=bad), patch.object(gate.shutil, 'which', return_value='tool'):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')


if __name__ == '__main__':
    unittest.main()
