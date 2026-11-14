"""Persisted daily/weekly slot behavior across child-process restarts.

All files are test-owned synthetic artifacts. No OS scheduler is installed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.fixtures.make_sqlite import create_fixture


ROOT = Path(__file__).resolve().parents[1]


class SlotRestartTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dbvora-slot-restart-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = create_fixture(self.root / "synthetic.sqlite")
        self.snapshot_dir = self.root / "snapshots"
        self.archive_dir = self.root / "archives"
        self.ledger_dir = self.root / "ledger"
        for folder in (self.snapshot_dir, self.archive_dir, self.ledger_dir):
            folder.mkdir()
        stat = self.source.stat()
        self.source_before = (hashlib.sha256(self.source.read_bytes()).hexdigest(),
                              stat.st_size, stat.st_mtime_ns)

    def run_cli(self, period: str, utc_day: str) -> subprocess.CompletedProcess:
        command = [
            sys.executable, "-m", "dbvora.archive.daily_synthetic",
            "--source", str(self.source),
            "--snapshot-dir", str(self.snapshot_dir),
            "--archive-dir", str(self.archive_dir),
            "--ledger-dir", str(self.ledger_dir),
            "--job-id", "restart01", "--utc-day", utc_day,
            "--period", period, "--synthetic-only", "--accept-plaintext",
        ]
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", timeout=60, check=False)

    def assert_source_unchanged(self):
        current = self.source.stat()
        self.assertEqual(self.source_before,
                         (hashlib.sha256(self.source.read_bytes()).hexdigest(),
                          current.st_size, current.st_mtime_ns))

    def test_daily_crash_reservation_holds_after_process_restart_then_next_day_runs(self):
        crash_code = """
import os
import sys
from unittest.mock import patch
from dbvora.archive import daily_synthetic
source, snapshot_dir, archive_dir, ledger_dir = sys.argv[1:5]
def crash_before_snapshot(*args, **kwargs):
    os._exit(86)
with patch.object(daily_synthetic, "create_snapshot", side_effect=crash_before_snapshot):
    daily_synthetic.run_daily(
        source, snapshot_dir, archive_dir, ledger_dir,
        job_id="restart01", utc_day="2026-11-14",
        synthetic_only=True, accept_plaintext=True)
"""
        crashed = subprocess.run(
            [sys.executable, "-c", crash_code, str(self.source),
             str(self.snapshot_dir), str(self.archive_dir), str(self.ledger_dir)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            timeout=60, check=False)
        self.assertEqual(crashed.returncode, 86)
        self.assertEqual(list(self.snapshot_dir.iterdir()), [])
        self.assertEqual(list(self.archive_dir.iterdir()), [])

        restarted_same_slot = self.run_cli("daily", "2026-11-14")
        self.assertEqual(restarted_same_slot.returncode, 2)
        self.assertIn("DAILY_SLOT_HELD_FOR_MANUAL_REVIEW", restarted_same_slot.stderr)
        self.assertNotIn(str(self.source), restarted_same_slot.stdout + restarted_same_slot.stderr)
        self.assertEqual(list(self.snapshot_dir.iterdir()), [])
        self.assertEqual(list(self.archive_dir.iterdir()), [])

        next_slot = self.run_cli("daily", "2026-11-15")
        self.assertEqual(next_slot.returncode, 0, next_slot.stderr)
        report = json.loads(next_slot.stdout)["result"]
        self.assertEqual(report["status"], "RECORDED_UNVERIFIED_REQUIRES_OWNER_REVIEW")
        self.assertFalse(report["scheduler_installed"])
        self.assertEqual(len(list(self.snapshot_dir.glob("dbvora-*.sqlite"))), 1)
        self.assertEqual(len(list(self.archive_dir.glob("dbvora-*.zip"))), 1)
        self.assert_source_unchanged()

    def test_weekly_slot_persists_across_process_restart_and_resumes_next_iso_week(self):
        first = self.run_cli("weekly", "2026-11-09")
        self.assertEqual(first.returncode, 0, first.stderr)
        first_result = json.loads(first.stdout)["result"]
        self.assertEqual(first_result["period_start_utc"], "2026-11-09")

        restarted_same_week = self.run_cli("weekly", "2026-11-15")
        self.assertEqual(restarted_same_week.returncode, 2)
        self.assertIn("DAILY_SLOT_HELD_FOR_MANUAL_REVIEW", restarted_same_week.stderr)
        self.assertNotIn(str(self.source), restarted_same_week.stderr)
        self.assertEqual(len(list(self.archive_dir.glob("*.zip"))), 1)

        next_week = self.run_cli("weekly", "2026-11-16")
        self.assertEqual(next_week.returncode, 0, next_week.stderr)
        next_result = json.loads(next_week.stdout)["result"]
        self.assertEqual(next_result["period_start_utc"], "2026-11-16")
        self.assertNotEqual(first_result["artifact_name"], next_result["artifact_name"])
        self.assertEqual(len(list(self.archive_dir.glob("*.zip"))), 2)
        self.assertEqual(len(list(self.snapshot_dir.glob("dbvora-*.sqlite"))), 2)
        self.assert_source_unchanged()


if __name__ == "__main__":
    unittest.main()
