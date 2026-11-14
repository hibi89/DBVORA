"""Synthetic-only daily archive reservation and source preservation regressions."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import daily_synthetic, request_service
from dbvora.archive.safe_zip import ArchiveError
from tests.fixtures.make_sqlite import create_fixture


class DailySyntheticTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory(prefix="dbvora-daily-synthetic-")
        self.addCleanup(holder.cleanup)
        self.base = Path(holder.name)
        self.source = create_fixture(self.base / "synthetic.sqlite")
        self.dirs = [self.base / name for name in ("snapshots", "archives", "ledger")]
        for folder in self.dirs:
            folder.mkdir()
        self.before = (hashlib.sha256(self.source.read_bytes()).digest(),
                       self.source.stat().st_mtime_ns)

    def run_once(self, **params):
        settings = {"job_id": "test01", "utc_day": "2026-11-14",
                    "synthetic_only": True, "accept_plaintext": True}
        settings.update(params)
        return daily_synthetic.run_daily(self.source, *self.dirs, **settings)

    def test_first_daily_slot_writes_single_verified_archival_attempt(self):
        report = self.run_once()
        self.assertEqual(report["status"], "RECORDED_UNVERIFIED_REQUIRES_OWNER_REVIEW")
        self.assertTrue(report["independently_restored_content_verified"])
        self.assertTrue(report["source_unchanged"])
        self.assertFalse(report["scheduler_installed"])
        self.assertFalse(report["ready_for_customer_data"])
        self.assertFalse(report["incremental_archive_verified"])
        self.assertEqual(len(list(self.dirs[0].glob("dbvora-*.sqlite"))), 1)
        self.assertEqual(len(list(self.dirs[1].glob("dbvora-*.zip"))), 1)
        self.assertEqual(self.before, (hashlib.sha256(self.source.read_bytes()).digest(),
                                       self.source.stat().st_mtime_ns))

    def test_replay_holds_before_new_snapshot_or_archive(self):
        self.run_once()
        existing = [sorted(x.name for x in folder.iterdir()) for folder in self.dirs]
        with self.assertRaisesRegex(daily_synthetic.DailyArchiveError,
                                    "DAILY_SLOT_HELD_FOR_MANUAL_REVIEW"):
            self.run_once()
        self.assertEqual(existing, [sorted(x.name for x in folder.iterdir())
                                    for folder in self.dirs])

    def test_changed_plan_same_slot_is_denied(self):
        self.run_once()
        with self.assertRaisesRegex(daily_synthetic.DailyArchiveError,
                                    "REQUEST_PLAN_CONFLICT"):
            self.run_once(codec="zstd", zstd_level=3)

    def test_new_calendar_day_creates_new_archive_without_deletion(self):
        self.run_once()
        later = self.run_once(utc_day="2026-11-15")
        self.assertTrue((self.dirs[1] / later["artifact_name"]).is_file())
        self.assertEqual(len(list(self.dirs[1].glob("dbvora-*.zip"))), 2)

    def test_no_explicit_ack_does_not_write_anything(self):
        for kwargs in (dict(synthetic_only=False), dict(accept_plaintext=False)):
            with self.assertRaises(daily_synthetic.DailyArchiveError):
                self.run_once(**kwargs)
        self.assertTrue(all(not list(folder.iterdir()) for folder in self.dirs))

    def test_invalid_job_date_codec_do_not_reserve(self):
        for kwargs in (dict(job_id="../escape"), dict(utc_day="2026-02-30"),
                       dict(utc_day="today"), dict(codec="unknown"),
                       dict(codec="zip", zstd_level=3), dict(codec="zstd", zstd_level=True)):
            with self.subTest(kwargs=kwargs), self.assertRaises(daily_synthetic.DailyArchiveError):
                self.run_once(**kwargs)
        self.assertEqual(list(self.dirs[2].iterdir()), [])

    def test_same_or_source_folder_refused_before_ledger(self):
        with self.assertRaisesRegex(daily_synthetic.DailyArchiveError,
                                    "SEPARATE_DIRECTORIES_REQUIRED"):
            daily_synthetic.run_daily(self.source, self.dirs[0], self.dirs[0], self.dirs[2],
                                      job_id="job", utc_day="2026-11-14",
                                      synthetic_only=True, accept_plaintext=True)
        with self.assertRaisesRegex(daily_synthetic.DailyArchiveError,
                                    "SEPARATE_DIRECTORIES_REQUIRED"):
            daily_synthetic.run_daily(self.source, self.base, self.dirs[1], self.dirs[2],
                                      job_id="job", utc_day="2026-11-14",
                                      synthetic_only=True, accept_plaintext=True)
        self.assertTrue(all(not list(folder.iterdir()) for folder in self.dirs))

    def test_failed_publication_slot_remains_reserved_without_retry(self):
        with patch.object(request_service, "make_zip_archive",
                          side_effect=ArchiveError("PUBLISH_FAILED", "injected")):
            with self.assertRaisesRegex(daily_synthetic.DailyArchiveError, "PUBLISH_FAILED"):
                self.run_once()
        self.assertEqual(len(list(self.dirs[1].iterdir())), 0)
        before_snapshots = sorted(x.name for x in self.dirs[0].iterdir())
        with self.assertRaisesRegex(daily_synthetic.DailyArchiveError,
                                    "DAILY_SLOT_HELD_FOR_MANUAL_REVIEW"):
            self.run_once()
        self.assertEqual(before_snapshots, sorted(x.name for x in self.dirs[0].iterdir()))

    def test_parallel_identical_slot_exactly_one_attempt(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.run_once) for _ in range(2)]
            values = []
            for job in futures:
                try:
                    values.append(job.result())
                except daily_synthetic.DailyArchiveError as exc:
                    values.append(str(exc))
        self.assertEqual(sum(isinstance(item, dict) for item in values), 1)
        self.assertEqual(len(list(self.dirs[1].glob("dbvora-*.zip"))), 1)

    def test_results_do_not_contain_original_path_or_row_content(self):
        r = self.run_once()
        serialized = str(r)
        self.assertNotIn(str(self.base), serialized)
        self.assertNotIn("NOT_FOR_SCHEMA_OUTPUT", serialized)


if __name__ == "__main__":
    unittest.main()
