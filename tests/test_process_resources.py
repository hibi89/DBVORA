"""Actual local process, OS RAM and local volume provenance tests."""
from __future__ import annotations
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
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
