"""Repeated synthetic-only ZIP/ZSTD/CAS comparison and restore checks."""
import unittest
from scripts.benchmark_synthetic_archives import verify, STATUS


class BenchmarkSyntheticArchivesTests(unittest.TestCase):
    def test_three_trials_restore_both_generations_for_all_available_formats(self):
        data = verify()
        self.assertEqual(data["status"], STATUS, data)
        self.assertEqual(data["checks"] >= 20, True)
        self.assertTrue(data["same_synthetic_workload"])
        self.assertEqual(data["generation_count"], 2)
        self.assertEqual(data["benchmark_trials_per_method"], 3)
        self.assertTrue(data["both_generations_restored"])
        self.assertTrue(data["second_generation_reused_blocks"])
        self.assertTrue(data["compressed_generations_restored"])
        self.assertTrue(data["compressed_second_reused_blocks"])
        self.assertTrue(data["source_unchanged_during_archiving"])
        self.assertTrue(data["no_universal_compression_claim"])
        self.assertEqual(data["timing_scope"],
                         "3_trial_medians_two_generations_wall_clock_only")
        self.assertEqual(set(data["timings_ns"]), {
            "zip_write_ns", "raw_write_ns", "zlib_write_ns",
            "zip_restore_ns", "raw_restore_ns", "zlib_restore_ns"})
        if data["zstd"] == "passed":
            self.assertTrue(data["zstd_generations_restored"])
            self.assertEqual(set(data["zstd_timings_ns"]), {"zstd_write_ns", "zstd_restore_ns"})
        else:
            self.assertEqual(data["zstd"], "skipped_no_local_codec")
            self.assertEqual(data["zstd_timings_ns"], {})
        methods = data["benchmarks"]
        expected = {"zip", "raw_cas", "compressed_cas"}
        if data["zstd"] == "passed":
            expected.add("zstd")
        self.assertEqual(set(methods), expected)
        self.assertEqual(len(data["trial_orders"]), 3)
        self.assertNotEqual(data["trial_orders"][0], data["trial_orders"][1])
        for method, summary in methods.items():
            with self.subTest(method=method):
                self.assertEqual(summary["trial_count"], 3)
                self.assertEqual(summary["generation_count"], 2)
                self.assertTrue(summary["restore_sha256_verified"])
                self.assertEqual(summary["artifact_bytes"]["sample_count"], 3)
                self.assertGreater(summary["artifact_bytes"]["median"], 0)
                for metric in ("artifact_bytes", "create_wall_ns", "restore_wall_ns"):
                    series = summary[metric]
                    self.assertEqual(len(series["samples"]), 3)
                    self.assertGreater(series["min"], 0)
                    self.assertLessEqual(series["min"], series["median"])
                    self.assertGreaterEqual(series["max"], series["median"])
        metrics = data["metrics"]
        self.assertGreater(metrics["two_zip_archives_bytes"], 0)
        self.assertGreater(metrics["cas_total_stored_bytes"], 0)
        self.assertGreater(metrics["compressed_cas_total_stored_bytes"], 0)
        if data["zstd"] == "passed":
            self.assertGreater(metrics["zstd_archives_bytes"], 0)
        self.assertFalse(data["ready_for_customer_data"])

    def test_invalid_trial_count_and_report_redacts_payloads_and_paths(self):
        self.assertEqual(verify(2)["error_code"], "INVALID_TRIAL_COUNT")
        data = verify()
        output = repr(data)
        self.assertNotIn("NOT_FOR_SCHEMA_OUTPUT", output)
        self.assertNotIn("SECOND_GENERATION_CHANGED_SYNTHETIC_BYTE", output)
        self.assertNotIn("dbvora-two-gen-benchmark-", output)
        self.assertEqual(data["environment"]["machine"] is not None, True)
        self.assertTrue(data["environment"]["os"])
        self.assertEqual(data["cache_policy"],
                         "OS caches are not cleared; method order rotates across trials.")
