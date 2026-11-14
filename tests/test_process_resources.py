"""Actual local process, OS RAM and local volume provenance tests."""
from __future__ import annotations
from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from dbvora import process_resources as p


class ProcessResourcesTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="dbvora-process-only-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)

    def test_measures_real_process_counters_not_remote_db_metrics(self):
        first = p.observe(self.root)
        sum(x * x for x in range(40000))
        second = p.observe(self.root)
        self.assertEqual(second["contract"], p.CONTRACT)
        self.assertGreaterEqual(second["process_cpu_time_ns"], first["process_cpu_time_ns"])
        self.assertGreaterEqual(second["sample_monotonic_ns"], first["sample_monotonic_ns"])
        self.assertIsNone(second["database_server_cpu_percent"])
        self.assertIsNone(second["database_server_ram_bytes"])
        self.assertEqual(second["disk"]["status"], "measured")
        self.assertLessEqual(second["disk"]["free_bytes"], second["disk"]["total_bytes"])
        self.assertNotIn(str(self.root), str(second))
        self.assertFalse(second["ready_for_customer_data"])

    def test_ram_never_estimates_unavailable(self):
        report = p.observe(self.root)["ram"]
        self.assertIn(report["status"], ("measured", "unavailable"))
        if report["status"] == "measured":
            self.assertIs(type(report["resident_bytes"]), int)
            self.assertGreater(report["resident_bytes"], 0)
        else:
            self.assertIsNone(report["resident_bytes"])
            self.assertEqual(report["source"], "unavailable")

    def test_real_two_samples_compare_local_process_only(self):
        before = p.observe(self.root)
        sum(x * x for x in range(40000))
        # On Windows two instantaneous calls may share one native monotonic
        # clock tick. This is a live two-sample test, so allow real time to pass.
        time.sleep(0.1)
        after = p.observe(self.root)
        # Path-free Windows diagnostic if a native clock/RAM field is outside
        # the expected provenance range. Never print customer directories.
        diagnostic = {
            "pid_types": [type(item["process_id"]).__name__ for item in (before, after)],
            "instance_id_pattern": [bool(p._ID.fullmatch(item["process_instance_id"])) for item in (before, after)],
            "clock_in_range": [0 <= item["sample_monotonic_ns"] <= p._MAX_COUNTER for item in (before, after)],
            "cpu_in_range": [0 <= item["process_cpu_time_ns"] <= p._MAX_COUNTER for item in (before, after)],
            "ram_source": [item["ram"]["source"] for item in (before, after)],
            "ram_status": [item["ram"]["status"] for item in (before, after)],
        }
        self.assertTrue(p._valid_comparable_sample(before), diagnostic)
        self.assertTrue(p._valid_comparable_sample(after), diagnostic)
        trend = p.compare_local_samples(before, after)
        self.assertEqual(trend["contract"], p.TREND_CONTRACT)
        self.assertEqual(trend["status"], "measured_two_samples_only_no_forecast", trend)
        self.assertGreater(trend["elapsed_ns"], 0)
        self.assertGreaterEqual(trend["process_cpu_delta_ns"], 0)
        self.assertIsNone(trend["database_server_cpu_percent"])
        self.assertIsNone(trend["database_server_ram_bytes"])
        self.assertEqual(trend["scope"], "same_python_process_only_not_database_server")
        self.assertFalse(trend["ready_for_customer_data"])
        self.assertNotIn(str(self.root), str(trend))
        if trend["resident_ram_status"] == "measured":
            self.assertIs(type(trend["resident_ram_delta_bytes"]), int)
        else:
            self.assertIsNone(trend["resident_ram_delta_bytes"])

    def test_two_sample_calculation_uses_raw_cpu_and_memory_deltas_not_percent(self):
        first = p.observe(self.root)
        second = copy.deepcopy(first)
        second["sample_monotonic_ns"] += 1_000_000_000
        second["process_cpu_time_ns"] += 125_000_000
        first["ram"] = {"status": "measured", "resident_bytes": 400_000,
                        "source": "linux_proc_self_statm_resident_bytes",
                        "scope": "current_python_process_not_database_server"}
        second["ram"] = {**first["ram"], "resident_bytes": 398_000}
        trend = p.compare_local_samples(first, second)
        self.assertEqual(trend["status"], "measured_two_samples_only_no_forecast", trend)
        self.assertEqual(trend["elapsed_ns"], 1_000_000_000)
        self.assertEqual(trend["process_cpu_delta_ns"], 125_000_000)
        self.assertEqual(trend["resident_ram_delta_bytes"], -2_000)
        self.assertNotIn("process_cpu_percent", trend)

    def test_different_process_or_session_cannot_form_trend(self):
        first = p.observe(self.root)
        second = copy.deepcopy(first)
        second["sample_monotonic_ns"] += 1
        second["process_id"] += 1
        self.assertEqual(p.compare_local_samples(first, second)["reason"],
                         "different_python_process")
        second["process_id"] = first["process_id"]
        second["process_instance_id"] = "a" * 32 if first["process_instance_id"] != "a" * 32 else "b" * 32
        self.assertEqual(p.compare_local_samples(first, second)["reason"],
                         "different_python_process")

    def test_invalid_time_or_cpu_counter_never_creates_false_trend(self):
        first = p.observe(self.root)
        later = copy.deepcopy(first)
        self.assertEqual(p.compare_local_samples(first, later)["reason"],
                         "non_increasing_monotonic_clock")
        later["sample_monotonic_ns"] += 1
        later["process_cpu_time_ns"] -= 1
        self.assertEqual(p.compare_local_samples(first, later)["reason"],
                         "process_cpu_counter_decreased")
        later["process_cpu_time_ns"] = True
        self.assertEqual(p.compare_local_samples(first, later)["reason"],
                         "invalid_or_legacy_observation")

    def test_missing_identity_legacy_and_untrusted_fields_unavailable(self):
        a = p.observe(self.root)
        b = copy.deepcopy(a)
        b["sample_monotonic_ns"] += 1
        a.pop("process_instance_id")
        trend = p.compare_local_samples(a, b)
        self.assertEqual(trend["status"], "unavailable")
        self.assertIsNone(trend["process_cpu_delta_ns"])
        a = p.observe(self.root)
        a["database_server_cpu_percent"] = 88
        self.assertEqual(p.compare_local_samples(a, b)["reason"],
                         "invalid_or_legacy_observation")

    def test_missing_ram_sample_stays_unavailable_while_cpu_delta_valid(self):
        a = p.observe(self.root)
        b = copy.deepcopy(a)
        b["sample_monotonic_ns"] += 100
        b["process_cpu_time_ns"] += 12
        b["ram"] = {"status": "unavailable", "resident_bytes": None, "source": "unavailable",
                    "scope": "current_python_process_not_database_server"}
        trend = p.compare_local_samples(a, b)
        self.assertEqual(trend["status"], "measured_two_samples_only_no_forecast")
        self.assertEqual(trend["process_cpu_delta_ns"], 12)
        self.assertEqual(trend["resident_ram_status"], "unavailable")
        self.assertIsNone(trend["resident_ram_delta_bytes"])

    def test_relative_missing_and_symlink_paths_are_rejected(self):
        for path in (".", str(self.root / "missing")):
            with self.subTest(path=path), self.assertRaisesRegex(
                    p.ResourceError, "INVALID_LOCAL_DIRECTORY"):
                p.observe(path)
        target = self.root / "link"
        try:
            target.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks cannot be created on this runner")
        with self.assertRaisesRegex(p.ResourceError, "SYMLINK_LOCAL_DIRECTORY"):
            p.observe(target)

    def test_missing_ram_disk_cannot_be_faked(self):
        with patch.object(p, "_ram", return_value=(None, "unavailable")), patch.object(
                p.shutil, "disk_usage", side_effect=OSError("synthetic")):
            r = p.observe(self.root)
        self.assertEqual(r["ram"]["status"], "unavailable")
        self.assertEqual(r["disk"]["status"], "unavailable")
        self.assertIsNone(r["database_server_ram_bytes"])

    def test_bad_cli_path_and_option_do_not_echo_secret(self):
        secret = "C:\\secret\\customer.sqlite"
        for args in (["--local-dir", secret], ["--bogus", secret]):
            with io.StringIO() as stream, redirect_stderr(stream):
                self.assertEqual(p.main(args), 2)
                self.assertNotIn(secret, stream.getvalue())

    def test_cli_bounded_two_sample_mode_produces_honest_delta(self):
        # Do not mock away the interval: Windows clock resolution can make
        # consecutive instantaneous observations have equal timestamps.
        with io.StringIO() as stream, redirect_stdout(stream):
            code = p.main(["--local-dir", str(self.root), "--sample-interval-ms", "100"])
            report = json.loads(stream.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(report["report"]["contract"], "dbvora.local-process-trend-cli.v1")
        self.assertEqual(report["report"]["comparison"]["status"],
                         "measured_two_samples_only_no_forecast")
        self.assertIsNone(report["report"]["comparison"]["database_server_cpu_percent"])
        self.assertNotIn(str(self.root), str(report))

    def test_cli_rejects_unsafe_or_unbounded_sampling_without_sleep(self):
        for interval in ("0", "99", "5001", "-2", "C:/very_private/secret"):
            with self.subTest(interval=interval), patch.object(p.time, "sleep") as sleeper:
                with io.StringIO() as stream, redirect_stderr(stream):
                    code = p.main(["--local-dir", str(self.root),
                                   "--sample-interval-ms", interval])
                    raw = stream.getvalue()
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(raw)["error_code"],
                                 "INVALID_ARGUMENT" if "secret" in interval else "INVALID_SAMPLE_INTERVAL")
                self.assertNotIn(interval, raw)
                sleeper.assert_not_called()

    def test_actual_cli_reports_only_scoped_metrics(self):
        with io.StringIO() as stream, redirect_stdout(stream):
            self.assertEqual(p.main(["--local-dir", str(self.root)]), 0)
            raw = stream.getvalue()
        self.assertNotIn(str(self.root), raw)
        result = json.loads(raw)
        self.assertTrue(result["ok"])
        self.assertFalse(result["report"]["automatic_actions"])


if __name__ == "__main__":
    unittest.main()
