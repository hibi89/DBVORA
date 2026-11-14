"""Synthetic-only measured two-generation ZIP/CAS size proof."""
from __future__ import annotations

import unittest
from scripts.benchmark_synthetic_archives import verify, STATUS


class BenchmarkSyntheticArchivesTests(unittest.TestCase):
    def test_bytes_are_observed_and_both_archive_formats_restore(self):
        data = verify()
        self.assertEqual(data["status"], STATUS)
        self.assertEqual(data["checks"], 9)
        self.assertTrue(data["same_synthetic_workload"])
        self.assertTrue(data["both_generations_restored"])
        self.assertTrue(data["second_generation_reused_blocks"])
        self.assertTrue(data["source_unchanged_during_archiving"])
        self.assertTrue(data["no_universal_compression_claim"])
        self.assertFalse(data["ready_for_customer_data"])
        metrics = data["metrics"]
        self.assertGreater(metrics["two_zip_archives_bytes"], 0)
        self.assertGreater(metrics["cas_total_stored_bytes"], 0)
        self.assertGreater(metrics["cas_second_reused_chunks"], 0)
        self.assertEqual(metrics["cas_minus_zip_bytes"],
                         metrics["cas_total_stored_bytes"] - metrics["two_zip_archives_bytes"])

    def test_no_raw_payload_or_source_paths_in_aggregate(self):
        data = verify()
        output = repr(data)
        self.assertNotIn("NOT_FOR_SCHEMA_OUTPUT", output)
        self.assertNotIn("SECOND_GENERATION_CHANGED_SYNTHETIC_BYTE", output)
        self.assertNotIn("dbvora-two-gen-benchmark-", output)
