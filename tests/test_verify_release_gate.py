"""Offline synthetic release-gate decision logic (processes mocked)."""
import json
import subprocess
import sys
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

    def responses(self, *, tests=290, checks=8, zstd='passed', customer_ready=False):
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

    def test_289_tests_is_not_enough(self):
        with patch.object(gate, '_run', side_effect=self.responses(tests=289)), patch.object(gate.shutil, 'which', return_value='tool'):
            report = gate.verify()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['steps'][1]['discovered_tests'], 289)

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
        mocked[0] = (0, '', 'test_zstd_roundtrip_when_optional_codec_exists (test_archive_cli.ArchiveCliTests.test_zstd_roundtrip_when_optional_codec_exists) ... skipped \'optional external zstd executable unavailable\'\nRan 290 tests in 1.000s\nOK (skipped=1)')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', side_effect=lambda name: None if name == 'zstd' else '/usr/bin/node'
        ):
            self.assertEqual(gate.verify()['status'], 'PASS_SYNTHETIC_ENVIRONMENT_ONLY')

    def test_any_skip_with_zstd_installed_fails_closed(self):
        mocked = self.responses()
        mocked[0] = (0, '', 'Ran 290 tests in 1.000s\nOK (skipped=1)')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(gate.shutil, 'which', return_value='tool'):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertEqual(result['steps'][1]['skipped_tests'], 1)

    def test_more_than_one_skip_without_zstd_fails_closed(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=7)
        mocked[0] = (0, '', 'Ran 290 tests in 1.000s\nOK (skipped=2)')
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
        mocked[0] = (0, '', "test_backup (test_safety.Safety.test_backup) ... skipped 'bad reason'\nRan 290 tests in 1.000s\nOK (skipped=1)")
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', side_effect=lambda name: None if name == 'zstd' else '/usr/bin/node'
        ):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_skip_summary_without_identity_line_rejected(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=7)
        mocked[0] = (0, '', 'Ran 290 tests in 1.000s\nOK (skipped=1)')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', side_effect=lambda name: None if name == 'zstd' else '/usr/bin/node'
        ):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_skip_identity_from_named_case_only(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=7)
        mocked[0] = (0, '', "test_zstd_roundtrip_when_optional_codec_exists (test_archive_cli.ArchiveCliTests.test_zstd_roundtrip_when_optional_codec_exists) ... skipped 'wrong reason'\nRan 290 tests in 1.000s\nOK (skipped=1)")
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


    def test_run_decodes_utf8_process_output_on_cp949_hosts(self):
        # This reproduces UTF-8 TAP output regardless of Python's Windows locale.
        command = [sys.executable, '-c',
                   "import sys; sys.stdout.buffer.write('✓'.encode('utf-8')); "
                   "sys.stderr.buffer.write('⚠'.encode('utf-8'))"]
        self.assertEqual(gate._run(command), (0, '✓', '⚠'))

    def test_run_invalid_utf8_fails_closed_without_traceback(self):
        invalid = subprocess.CompletedProcess(['node'], 0, b'\xff', b'')
        with patch.object(gate.subprocess, 'run', return_value=invalid):
            self.assertEqual(gate._run(['node']), (-1, '', ''))

    def test_run_missing_output_stream_fails_closed(self):
        missing = subprocess.CompletedProcess(['node'], 0, None, b'')
        with patch.object(gate.subprocess, 'run', return_value=missing):
            self.assertEqual(gate._run(['node']), (-1, '', ''))

    def test_run_forces_python_utf8_and_preserves_inherited_environment(self):
        completed = subprocess.CompletedProcess(['node'], 0, b'ok', b'')
        with patch.dict(gate.os.environ, {'DBVORA_SENTINEL': 'keep', 'PYTHONIOENCODING': 'cp949'}):
            with patch.object(gate.subprocess, 'run', return_value=completed) as child:
                self.assertEqual(gate._run(['node']), (0, 'ok', ''))
        child_env = child.call_args.kwargs['env']
        self.assertEqual(child_env['PYTHONIOENCODING'], 'utf-8')
        self.assertEqual(child_env['DBVORA_SENTINEL'], 'keep')

    def test_windows_failed_unittest_reports_ids_and_skip_count_without_tracebacks(self):
        mocked = self.responses()
        mocked[0] = (1, '', "test_archive_failure (test_safe_zip.ZipTests.test_archive_failure) ... FAIL\n"
                     "FAIL: test_archive_failure (test_safe_zip.ZipTests.test_archive_failure)\n"
                     "Traceback secret C:\\\\customer\\\\source.sqlite\n"
                     "Ran 290 tests in 1.0s\nFAILED (failures=1, skipped=1)")
        with patch.object(gate, '_run', side_effect=mocked), patch.object(gate.shutil, 'which', return_value='tool'):
            step = gate.verify()['steps'][1]
        self.assertEqual(step['status'], 'FAIL')
        self.assertEqual(step['skipped_tests'], 1)
        self.assertEqual(step['failed_test_ids'], ['test_safe_zip.ZipTests.test_archive_failure'])
        self.assertNotIn('customer', str(step))

    def test_real_cli_gate_reports_fixed_error_code_only(self):
        mocked = self.responses()
        mocked[1] = (2, json.dumps({'status':'FAIL','error_code':'CLI_PUBLISH_FAILED'}), '')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(gate.shutil, 'which', return_value='tool'):
            step = gate.verify()['steps'][2]
        self.assertEqual(step['status'], 'FAIL')
        self.assertEqual(step['error_code'], 'CLI_PUBLISH_FAILED')

    def test_unsafe_cli_error_code_is_replaced_not_echoed(self):
        mocked = self.responses()
        mocked[1] = (2, json.dumps({'status':'FAIL','error_code':'C:\\\\private\\\\db.sqlite'}), '')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(gate.shutil, 'which', return_value='tool'):
            step = gate.verify()['steps'][2]
        self.assertEqual(step['error_code'], 'NOT_REPORTED')
        self.assertNotIn('private', str(step))

    def test_node_tap_failure_has_only_numeric_counts(self):
        mocked = self.responses()
        mocked[3] = (1, '# tests 1\n# pass 0\n# fail 1\n', '')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(gate.shutil, 'which', return_value='tool'):
            step = gate.verify()['steps'][4]
        self.assertEqual(step['status'], 'FAIL')
        self.assertEqual(step['tap'], {'tests':1,'passed':0,'failed':1})
        self.assertEqual(step['error_code'], 'NODE_TEST_FAILED')

    def test_filesystem_failure_reports_archive_code(self):
        mocked = self.responses()
        mocked[4] = (0, json.dumps({'archive_publish_test':'unsupported_or_failed',
                                     'failure_code':'PUBLISH_FAILED','ready_for_customer_data':False}), '')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(gate.shutil, 'which', return_value='tool'):
            step = gate.verify()['steps'][5]
        self.assertEqual(step['status'], 'FAIL')
        self.assertEqual(step['error_code'], 'PUBLISH_FAILED')
        self.assertEqual(step['publish_test'], 'unsupported_or_failed')

    def test_node_reporter_forced_tap_even_when_windows_defaults_differ(self):
        calls = []
        scripted = self.responses()
        def capture(command, timeout=180):
            calls.append(command)
            return scripted[len(calls)-1]
        with patch.object(gate, '_run', side_effect=capture), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            report = gate.verify()
        self.assertEqual(report['steps'][4]['status'], 'PASS')
        self.assertEqual(calls[3], ['node', '--test-reporter=tap', '--test',
                                    'tests/test_ui_dom.cjs'])

    def test_skip_ids_are_sanitized_without_reasons_or_paths(self):
        mocked = self.responses()
        mocked[0] = (1, '', "test_missing_symlink (test_safety.FileSafety.test_missing_symlink) ... skipped 'C:\\private\\bad'\n"
                     "Ran 290 tests in 1.0s\nFAILED (errors=1, skipped=1)")
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            step = gate.verify()['steps'][1]
        self.assertEqual(step['skipped_test_ids'], ['test_safety.FileSafety.test_missing_symlink'])
        self.assertEqual(step['skipped_tests'], 1)
        self.assertNotIn('private', str(step))

if __name__ == '__main__':
    unittest.main()
