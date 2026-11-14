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

    def responses(self, *, tests=668, checks=10, zstd='passed',
                  customer_ready=False, resource_unavailable=False):
        def series(value):
            return {"sample_count": 3, "median": value, "min": value,
                    "max": value, "samples": [value, value, value]}

        resource_scopes = {
            "process_cpu_time_delta_ns":
                "current_python_process_cpu_time_delta_ns_not_cpu_percent",
            "sampled_max_rss_bytes":
                "sampled_boundary_max_current_python_process_not_peak",
            "volume_free_bytes_delta":
                "shared_containing_volume_free_byte_delta_not_per_process_io",
        }
        resource_fields = {
            "create_process_cpu_time_delta_ns": ("create", "process_cpu_time_delta_ns"),
            "restore_process_cpu_time_delta_ns": ("restore", "process_cpu_time_delta_ns"),
            "create_sampled_max_rss_bytes": ("create", "sampled_max_rss_bytes"),
            "restore_sampled_max_rss_bytes": ("restore", "sampled_max_rss_bytes"),
            "create_volume_free_bytes_delta": ("create", "volume_free_bytes_delta"),
            "restore_volume_free_bytes_delta": ("restore", "volume_free_bytes_delta"),
        }

        def resource_item(metric, value):
            scope = resource_scopes[metric]
            if resource_unavailable:
                result = {"status": "unavailable", "value": None, "scope": scope}
                if metric == "sampled_max_rss_bytes":
                    result.update({"boundary_sample_count": 2,
                                   "available_boundary_sample_count": 0,
                                   "source": "unavailable"})
                if metric == "volume_free_bytes_delta":
                    result["source"] = "unavailable"
                return result
            result = {"status": "measured", "value": value, "scope": scope}
            if metric == "sampled_max_rss_bytes":
                result.update({"boundary_sample_count": 2,
                               "available_boundary_sample_count": 2,
                               "source": "synthetic_fixture"})
            if metric == "volume_free_bytes_delta":
                result["source"] = "shutil_disk_usage_explicit_local_volume"
            return result

        def method(name, stored):
            trials = []
            for _ in range(3):
                measurements = {
                    operation: {
                        metric: resource_item(metric, {
                            "process_cpu_time_delta_ns": 1000,
                            "sampled_max_rss_bytes": 2048,
                            "volume_free_bytes_delta": -7,
                        }[metric])
                        for metric in resource_scopes
                    }
                    for operation in ("create", "restore")
                }
                trials.append({
                    "artifact_bytes": stored, "create_wall_ns": 1000000,
                    "restore_wall_ns": 1000001,
                    "restore_sha256_verified": True,
                    "second_generation_reused_chunks": 1 if name in
                        ("raw_cas", "compressed_cas") else None,
                    "generation_count": 2,
                    "resource_measurements": measurements,
                })
            resource_metrics = {}
            for field, (operation, metric) in resource_fields.items():
                value = (None if resource_unavailable else {
                    "process_cpu_time_delta_ns": 1000,
                    "sampled_max_rss_bytes": 2048,
                    "volume_free_bytes_delta": -7,
                }[metric])
                values = [value, value, value]
                resource_metrics[field] = {
                    "status": "unavailable" if resource_unavailable else "measured",
                    "sample_count": 3,
                    "available_sample_count": 0 if resource_unavailable else 3,
                    "median": value, "min": value, "max": value,
                    "samples": values, "scope": resource_scopes[metric],
                }
            return {
                "trial_count": 3, "generation_count": 2,
                "options": name + " synthetic options",
                "trials": trials,
                "artifact_bytes": series(stored),
                "create_wall_ns": series(1000000),
                "restore_wall_ns": series(1000001),
                "resource_metrics": resource_metrics,
                "restore_sha256_verified": True,
                **({"second_generation_reused_chunks": True}
                   if name in ("raw_cas", "compressed_cas") else {}),
            }

        benchmark_methods = {
            "zip": method("zip", 10),
            "raw_cas": method("raw_cas", 20),
            "compressed_cas": method("compressed_cas", 12),
        }
        zstd_bytes = None
        zstd_delta = None
        zstd_times = {}
        zstd_status = "skipped_no_local_codec"
        zstd_restored = False
        if zstd == "passed":
            benchmark_methods["zstd"] = method("zstd", 9)
            zstd_bytes = 9
            zstd_delta = -1
            zstd_times = {"zstd_write_ns": 1000002, "zstd_restore_ns": 1000003}
            zstd_status = "passed"
            zstd_restored = True
        benchmark_metrics = {
            "first_snapshot_bytes": 1000, "second_snapshot_bytes": 1001,
            "benchmark_trials_per_method": 3, "two_zip_archives_bytes": 10,
            "zstd_archives_bytes": zstd_bytes, "zstd_minus_zip_bytes": zstd_delta,
            "cas_total_stored_bytes": 20, "cas_minus_zip_bytes": 10,
            "compressed_cas_total_stored_bytes": 12,
            "compressed_cas_minus_zip_bytes": 2,
        }
        return [
            (0, '', f'Ran {tests} tests in 1.000s\nOK'),
            (0, json.dumps({'status': 'PASS_SYNTHETIC_ONLY',
                            'check_count': checks, 'optional_zstd': zstd,
                            'ready_for_customer_data': customer_ready}), ''),
            (0, '', ''),
            (0, '# tests 1\n# pass 1\n# fail 0\n', ''),
            (0, json.dumps({'archive_publish_test': 'passed_on_temporary_filesystem',
                            'ready_for_customer_data': False}), ''),
            (0, json.dumps({'status': 'PASS_SYNTHETIC_REQUEST_AND_ZIP_ONLY',
                            'checks': 9, 'archive_executed': True,
                            'replay_held': True, 'zip_restore_content_verified': True,
                            'ledger_artifact_state': 'RECORDED_UNVERIFIED',
                            'ready_for_customer_data': False, 'exactly_once_verified': False,
                            'windows_ntfs_verified': False}), ''),
            (0, json.dumps({'status': 'PASS_SYNTHETIC_ARCHIVE_REVIEW_ONLY',
                            'checks': 16 if zstd == 'passed' else 8,
                            'zip': 'passed', 'optional_zstd': zstd,
                            'replay_held': True, 'content_corruption_detected': True,
                            'offline_html_written': True, 'source_unchanged': True,
                            'customer_ready': False, 'exactly_once_verified': False,
                            'power_loss_verified': False, 'windows_ntfs_verified': False}), ''),
            (0, json.dumps({'status': 'PASS_SYNTHETIC_PORTABLE_ONLY',
                            'checks': 4, 'zip_sha256': 'a' * 64,
                            'ready_for_customer_data': False,
                            'signed': False, 'windows_ntfs_verified': False}), ''),
            (0, json.dumps({'status': 'PASS_SYNTHETIC_PG_ONLY', 'checks': 6,
                            'real_pg_connected': False,
                            'ready_for_customer_data': False,
                            'automatic_actions': False}), ''),
            (0, json.dumps({'status': 'PASS_SYNTHETIC_INCREMENTAL_CLI_ONLY',
                            'checks': 12, 'source_unchanged': True,
                            'independent_restore_verified': True,
                            'second_generation_reused_chunks': True,
                            'tampered_chunk_rejected': True,
                            'compressed_independent_restore_verified': True,
                            'compressed_second_generation_reused_chunks': True,
                            'compressed_tamper_rejected': True,
                            'format_mismatch_rejected': True,
                            'customer_ready': False, 'power_loss_verified': False,
                            'automatic_deletion': False}), ''),
            (0, json.dumps({
                "status": "PASS_SYNTHETIC_STORAGE_COMPARISON_ONLY",
                "checks": 29,
                "timing_scope": "3_trial_medians_two_generations_wall_clock_only",
                "resource_measurement_policy": {
                    "observer": "dbvora.process_resources.observe",
                    "sampling": "before_and_after_each_create_or_restore_operation",
                    "process_cpu_scope":
                        "current_python_process_cpu_time_delta_ns_not_cpu_percent",
                    "resident_memory_scope":
                        "sampled_boundary_max_current_python_process_not_peak",
                    "volume_free_space_scope":
                        "shared_containing_volume_free_byte_delta_not_per_process_io",
                    "unavailable_policy": "record_unavailable_or_partial_without_substitution",
                    "process_disk_io_scope":
                        "unavailable_not_measured_volume_delta_is_shared_host_volume_signal",
                    "external_child_process_cpu_and_rss":
                        "not_included_in_current_python_process_metrics",
                },
                "creation_timing_scope":
                    "API call wall time; API self-verification may be included.",
                "restore_timing_scope":
                    "Independent restore API plus restored-file SHA-256 check.",
                "cache_policy":
                    "OS caches are not cleared; method order rotates across trials.",
                "timings_ns": {
                    "zip_write_ns": 1000000, "raw_write_ns": 1000001,
                    "zlib_write_ns": 1000002, "zip_restore_ns": 1000003,
                    "raw_restore_ns": 1000004, "zlib_restore_ns": 1000005,
                },
                "zstd_timings_ns": zstd_times,
                "benchmarks": benchmark_methods,
                "environment": {
                    "os": "Linux", "os_release": "6.0", "machine": "x86_64",
                    "processor": "synthetic", "logical_cpu_count": 2,
                    "python": "3.11.0", "sqlite": "3.46.1",
                    "zstd_cli": "available" if zstd == "passed" else "unavailable",
                    "zstd_cli_version": "1.5.6" if zstd == "passed" else None,
                },
                "trial_orders": [["zip", "raw_cas", "compressed_cas"],
                                 ["raw_cas", "compressed_cas", "zip"],
                                 ["compressed_cas", "zip", "raw_cas"]],
                "benchmark_trials_per_method": 3, "generation_count": 2,
                "zstd": zstd_status, "zstd_generations_restored": zstd_restored,
                "same_synthetic_workload": True,
                "both_generations_restored": True,
                "compressed_generations_restored": True,
                "compressed_second_reused_blocks": True,
                "second_generation_reused_blocks": True,
                "source_unchanged_during_archiving": True,
                "no_universal_compression_claim": True,
                "ready_for_customer_data": False,
                "metrics": benchmark_metrics,
            }), ''),
        ]

    def test_full_mocked_gate_synthetic_pass_not_customer_release(self):
        with patch.object(gate, '_run', side_effect=self.responses()), patch.object(gate.shutil, 'which', return_value='tool'):
            report = gate.verify()
        self.assertEqual(report['status'], 'PASS_SYNTHETIC_ENVIRONMENT_ONLY')
        self.assertFalse(report['ready_for_customer_data'])
        self.assertEqual(len(report['steps']), 12)

    def test_benchmark_gate_accepts_explicit_unavailable_resources(self):
        mocked = self.responses(resource_unavailable=True)
        with patch.object(gate, "_run", side_effect=mocked), patch.object(
                gate.shutil, "which", return_value="tool"):
            report = gate.verify()
        self.assertEqual(report["status"], "PASS_SYNTHETIC_ENVIRONMENT_ONLY")
        for resource in report["steps"][-1]["benchmarks"]["zip"]["resource_metrics"].values():
            self.assertEqual(resource["status"], "unavailable")
            self.assertIsNone(resource["median"])

    def test_benchmark_gate_rejects_fabricated_unavailable_resource_value(self):
        mocked = self.responses(resource_unavailable=True)
        code, output, error = mocked[-1]
        benchmark = json.loads(output)
        benchmark["benchmarks"]["zip"]["resource_metrics"][
            "create_process_cpu_time_delta_ns"]["median"] = 1
        mocked[-1] = (code, json.dumps(benchmark), error)
        with patch.object(gate, "_run", side_effect=mocked), patch.object(
                gate.shutil, "which", return_value="tool"):
            report = gate.verify()
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertEqual(report["steps"][-1]["status"], "FAIL")

    def test_benchmark_gate_rejects_fewer_than_three_trials(self):
        mocked = self.responses()
        code, output, error = mocked[-1]
        benchmark = json.loads(output)
        benchmark["benchmark_trials_per_method"] = 2
        mocked[-1] = (code, json.dumps(benchmark), error)
        with patch.object(gate, "_run", side_effect=mocked), patch.object(
                gate.shutil, "which", return_value="tool"):
            report = gate.verify()
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertEqual(report["steps"][-1]["step"], "synthetic_archive_size_comparison")
        self.assertEqual(report["steps"][-1]["status"], "FAIL")

    def test_incomplete_checkout_fails_before_execution(self):
        (self.root / 'dbvora/archive/safe_zip.py').unlink()
        with patch.object(gate, '_run') as runner:
            report = gate.verify()
        runner.assert_not_called()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['steps'][0]['error'], 'INCOMPLETE_SOURCE_CHECKOUT')

    def test_668_test_baseline_rejects_incomplete_synthetic_suite(self):
        with patch.object(gate, '_run', side_effect=self.responses(tests=667)), patch.object(
                gate.shutil, 'which', return_value='tool'):
            report = gate.verify()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['steps'][1]['discovered_tests'], 667)

    def test_354_tests_is_not_enough(self):
        with patch.object(gate, '_run', side_effect=self.responses(tests=354)), patch.object(gate.shutil, 'which', return_value='tool'):
            report = gate.verify()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['steps'][1]['discovered_tests'], 354)

    def test_unsigned_customer_ready_claim_causes_failure(self):
        with patch.object(gate, '_run', side_effect=self.responses(customer_ready=True)), patch.object(gate.shutil, 'which', return_value='tool'):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_missing_zstd_is_explicit_supported_skip(self):
        with patch.object(gate, '_run', side_effect=self.responses(checks=9, zstd='skipped_no_local_codec')):
            with patch.object(gate.shutil, 'which', side_effect=lambda cmd: None if cmd == 'zstd' else '/usr/bin/node'):
                report = gate.verify()
        self.assertEqual(report['status'], 'PASS_SYNTHETIC_ENVIRONMENT_ONLY')

    def test_present_zstd_cannot_be_silently_skipped(self):
        with patch.object(gate, '_run', side_effect=self.responses(checks=9, zstd='skipped_no_local_codec')):
            with patch.object(gate.shutil, 'which', return_value='tool'):
                self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_one_optional_zstd_skip_is_allowed_only_without_binary(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=9)
        mocked[0] = (0, '', 'test_zstd_roundtrip_when_optional_codec_exists (test_archive_cli.ArchiveCliTests.test_zstd_roundtrip_when_optional_codec_exists) ... skipped \'optional external zstd executable unavailable\'\nRan 668 tests in 1.000s\nOK (skipped=1)')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', side_effect=lambda name: None if name == 'zstd' else '/usr/bin/node'
        ):
            self.assertEqual(gate.verify()['status'], 'PASS_SYNTHETIC_ENVIRONMENT_ONLY')

    def test_any_skip_with_zstd_installed_fails_closed(self):
        mocked = self.responses()
        mocked[0] = (0, '', 'Ran 668 tests in 1.000s\nOK (skipped=1)')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(gate.shutil, 'which', return_value='tool'):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertEqual(result['steps'][1]['skipped_tests'], 1)

    def test_more_than_one_skip_without_zstd_fails_closed(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=9)
        mocked[0] = (0, '', 'Ran 668 tests in 1.000s\nOK (skipped=2)')
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
        mocked = self.responses(zstd='skipped_no_local_codec', checks=9)
        mocked[0] = (0, '', "test_backup (test_safety.Safety.test_backup) ... skipped 'bad reason'\nRan 668 tests in 1.000s\nOK (skipped=1)")
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', side_effect=lambda name: None if name == 'zstd' else '/usr/bin/node'
        ):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_skip_summary_without_identity_line_rejected(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=9)
        mocked[0] = (0, '', 'Ran 668 tests in 1.000s\nOK (skipped=1)')
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', side_effect=lambda name: None if name == 'zstd' else '/usr/bin/node'
        ):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_skip_identity_from_named_case_only(self):
        mocked = self.responses(zstd='skipped_no_local_codec', checks=9)
        mocked[0] = (0, '', "test_zstd_roundtrip_when_optional_codec_exists (test_archive_cli.ArchiveCliTests.test_zstd_roundtrip_when_optional_codec_exists) ... skipped 'wrong reason'\nRan 668 tests in 1.000s\nOK (skipped=1)")
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
                     "Ran 668 tests in 1.0s\nFAILED (failures=1, skipped=1)")
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
                     "Ran 668 tests in 1.0s\nFAILED (errors=1, skipped=1)")
        with patch.object(gate, '_run', side_effect=mocked), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            step = gate.verify()['steps'][1]
        self.assertEqual(step['skipped_test_ids'], ['test_safety.FileSafety.test_missing_symlink'])
        self.assertEqual(step['skipped_tests'], 1)
        self.assertNotIn('private', str(step))

    def test_request_replay_gate_rejects_success_without_real_replay_evidence(self):
        responses = self.responses()
        responses[5] = (0, json.dumps({
            'status': 'PASS_SYNTHETIC_REQUEST_AND_ZIP_ONLY', 'checks': 9,
            'archive_executed': True, 'replay_held': False,
            'zip_restore_content_verified': True, 'ledger_artifact_state': 'RECORDED_UNVERIFIED',
            'ready_for_customer_data': False, 'exactly_once_verified': False,
            'windows_ntfs_verified': False}), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            report = gate.verify()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['steps'][6]['status'], 'FAIL')

    def test_request_gate_rejects_spurious_customer_release_claim(self):
        responses = self.responses()
        responses[5] = (0, json.dumps({
            'status': 'PASS_SYNTHETIC_REQUEST_AND_ZIP_ONLY', 'checks': 9,
            'archive_executed': True, 'replay_held': True,
            'zip_restore_content_verified': True, 'ledger_artifact_state': 'RECORDED_UNVERIFIED',
            'ready_for_customer_data': True, 'exactly_once_verified': False,
            'windows_ntfs_verified': False}), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_recovery_review_gate_rejects_missing_corruption_evidence(self):
        responses = self.responses()
        failing = json.loads(responses[6][1])
        failing['content_corruption_detected'] = False
        responses[6] = (0, json.dumps(failing), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            report = gate.verify()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertEqual(report['steps'][7]['step'], 'synthetic_recovery_review')
        self.assertEqual(report['steps'][7]['status'], 'FAIL')

    def test_recovery_review_gate_rejects_customer_ready_claim(self):
        responses = self.responses()
        falsified = json.loads(responses[6][1])
        falsified['customer_ready'] = True
        responses[6] = (0, json.dumps(falsified), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            report = gate.verify()
        self.assertEqual(report['status'], 'FAIL_CLOSED')
        self.assertFalse(report['ready_for_customer_data'])

    def test_trusted_portable_zip_gate_is_mandatory(self):
        responses = self.responses()
        reports = json.loads(responses[7][1])
        reports["checks"] = 3
        responses[7] = (0, json.dumps(reports), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            answer = gate.verify()
        self.assertEqual(answer['status'], 'FAIL_CLOSED')
        self.assertEqual(answer['steps'][8]['step'], 'trusted_portable_zip_e2e')
        self.assertEqual(answer['steps'][8]['status'], 'FAIL')

    def test_trusted_portable_gate_rejects_false_customer_release(self):
        responses = self.responses()
        report = json.loads(responses[7][1])
        report["ready_for_customer_data"] = True
        responses[7] = (0, json.dumps(report), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            self.assertEqual(gate.verify()['status'], 'FAIL_CLOSED')

    def test_trusted_portable_gate_rejects_bad_digest(self):
        responses = self.responses()
        report = json.loads(responses[7][1])
        report["zip_sha256"] = 'C:\\\\private\\\\file.zip'
        responses[7] = (0, json.dumps(report), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            step = gate.verify()['steps'][8]
        self.assertEqual(step['status'], 'FAIL')
        self.assertIsNone(step['zip_sha256'])
        self.assertNotIn('private', str(step))


    def test_pg_synthetic_end_to_end_is_mandatory(self):
        responses = self.responses()
        current = json.loads(responses[8][1])
        current['checks'] = 5
        responses[8] = (0, json.dumps(current), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertEqual(result['steps'][-3]['step'], 'synthetic_pg_to_offline_html')
        self.assertEqual(result['steps'][-3]['status'], 'FAIL')

    def test_pg_gate_rejects_false_real_postgres_connection(self):
        responses = self.responses()
        current = json.loads(responses[8][1])
        current['real_pg_connected'] = True
        responses[8] = (0, json.dumps(current), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
            gate.shutil, 'which', return_value='tool'
        ):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertEqual(result['steps'][-3]['status'], 'FAIL')

    def test_pg_gate_rejects_automatic_actions_or_customer_claim(self):
        for change in ('automatic_actions', 'ready_for_customer_data'):
            with self.subTest(change=change):
                responses = self.responses()
                current = json.loads(responses[8][1])
                current[change] = True
                responses[8] = (0, json.dumps(current), '')
                with patch.object(gate, '_run', side_effect=responses), patch.object(
                    gate.shutil, 'which', return_value='tool'
                ):
                    result = gate.verify()
                self.assertEqual(result['status'], 'FAIL_CLOSED')

    def test_incremental_cli_mandatory_gate_rejects_missing_reuse(self):
        responses = self.responses()
        report = json.loads(responses[9][1])
        report['second_generation_reused_chunks'] = False
        responses[9] = (0, json.dumps(report), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
                gate.shutil, 'which', return_value='tool'):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertEqual(result['steps'][-2]['step'], 'synthetic_incremental_cli_roundtrip')
        self.assertEqual(result['steps'][-2]['status'], 'FAIL')

    def test_incremental_cli_gate_rejects_any_claim_of_customer_ready(self):
        responses = self.responses()
        report = json.loads(responses[9][1])
        report['customer_ready'] = True
        responses[9] = (0, json.dumps(report), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
                gate.shutil, 'which', return_value='tool'):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertEqual(result['steps'][-2]['status'], 'FAIL')


    def test_size_comparison_requires_real_two_generation_restore(self):
        responses = self.responses()
        measured = json.loads(responses[10][1])
        measured['both_generations_restored'] = False
        responses[10] = (0, json.dumps(measured), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
                gate.shutil, 'which', return_value='tool'):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertEqual(result['steps'][-1]['step'], 'synthetic_archive_size_comparison')
        self.assertEqual(result['steps'][-1]['status'], 'FAIL')

    def test_size_comparison_does_not_accept_falsified_savings_claim(self):
        responses = self.responses()
        measured = json.loads(responses[10][1])
        measured['metrics']['cas_minus_zip_bytes'] = -10000000
        responses[10] = (0, json.dumps(measured), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
                gate.shutil, 'which', return_value='tool'):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertIsNone(result['steps'][-1]['metrics'])


    def test_benchmark_must_report_actual_positive_wall_clock_samples(self):
        responses = self.responses()
        report = json.loads(responses[10][1])
        report['timings_ns']['zlib_restore_ns'] = -1
        responses[10] = (0, json.dumps(report), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
                gate.shutil, 'which', return_value='tool'):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')
        self.assertEqual(result['steps'][-1]['status'], 'FAIL')
        self.assertIsNone(result['steps'][-1]['timings_ns'])

    def test_benchmark_does_not_accept_claimed_multi_sample_precision(self):
        responses = self.responses()
        report = json.loads(responses[10][1])
        report['timing_scope'] = 'generalized_performance_guarantee'
        responses[10] = (0, json.dumps(report), '')
        with patch.object(gate, '_run', side_effect=responses), patch.object(
                gate.shutil, 'which', return_value='tool'):
            result = gate.verify()
        self.assertEqual(result['status'], 'FAIL_CLOSED')

if __name__ == '__main__':
    unittest.main()
