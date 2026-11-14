"""User-confirmed synthetic-only daily/weekly slot and CLI redaction tests."""
from __future__ import annotations

from contextlib import redirect_stderr
import hashlib
import io
from pathlib import Path
import tempfile
import unittest

from dbvora.archive import daily_synthetic as daily
from tests.fixtures.make_sqlite import create_fixture


class WeeklyArchiveTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dbvora-weekly-synthetic-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = create_fixture(self.root / "source.sqlite")
        self.snap, self.archive, self.ledger = (
            self.root / name for name in ("snap", "archives", "ledger"))
        for folder in (self.snap, self.archive, self.ledger):
            folder.mkdir()
        self.before_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def call(self, day, *, weekly=True, job_id="synthetic01", **kwargs):
        method = daily.run_weekly if weekly else daily.run_daily
        return method(
            self.source, self.snap, self.archive, self.ledger,
            job_id=job_id, utc_day=day, synthetic_only=True,
            accept_plaintext=True, **kwargs)

    def test_same_utc_iso_week_replay_is_held_with_one_archive(self):
        first = self.call("2026-11-09")
        self.assertEqual(first["period"], "weekly")
        self.assertEqual(first["period_start_utc"], "2026-11-09")
        with self.assertRaisesRegex(daily.DailyArchiveError, "DAILY_SLOT_HELD_FOR_MANUAL_REVIEW"):
            self.call("2026-11-15")
        self.assertEqual(len(list(self.archive.glob("dbvora-*.zip"))), 1)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.before_hash)

    def test_next_utc_iso_week_creates_second_artifact_without_deletion(self):
        first = self.call("2026-11-09")
        second = self.call("2026-11-16")
        self.assertNotEqual(first["artifact_name"], second["artifact_name"])
        self.assertEqual(second["period_start_utc"], "2026-11-16")
        self.assertEqual(len(list(self.archive.glob("dbvora-*.zip"))), 2)

    def test_calendar_year_rollover_uses_iso_monday_not_year_number(self):
        a = self.call("2026-12-31")
        self.assertEqual(a["period_start_utc"], "2026-12-28")
        with self.assertRaisesRegex(daily.DailyArchiveError, "DAILY_SLOT_HELD_FOR_MANUAL_REVIEW"):
            self.call("2027-01-01")
        self.assertEqual(len(list(self.archive.glob("dbvora-*.zip"))), 1)

    def test_daily_and_weekly_have_separate_ledger_keys_and_no_clobber(self):
        a = self.call("2026-11-14", weekly=False)
        b = self.call("2026-11-14", weekly=True)
        self.assertNotEqual(a["artifact_name"], b["artifact_name"])
        self.assertEqual(len(list(self.archive.glob("dbvora-*.zip"))), 2)

    def test_invalid_period_id_ack_or_codec_cannot_publish(self):
        for job in ("", "x" * 19, "with spaces", "../bad"):
            with self.subTest(job=job), self.assertRaises(daily.DailyArchiveError):
                self.call("2026-11-14", job_id=job)
        for params in ({"synthetic_only": False}, {"accept_plaintext": False}):
            with self.subTest(params=params), self.assertRaises(daily.DailyArchiveError):
                daily.run_weekly(
                    self.source, self.snap, self.archive, self.ledger,
                    job_id="testjob", utc_day="2026-11-14",
                    **params)
        self.assertEqual(list(self.archive.iterdir()), [])

    def test_bad_cli_choice_never_echoes_private_bad_value(self):
        secret = "C:\\Users\\customer\\private.sqlite"
        with io.StringIO() as err, redirect_stderr(err):
            status = daily.main([
                "--source", secret, "--snapshot-dir", str(self.snap),
                "--archive-dir", str(self.archive), "--ledger-dir", str(self.ledger),
                "--job-id", "example01", "--utc-day", "2026-11-14",
                "--period", secret, "--synthetic-only", "--accept-plaintext",
            ])
            out = err.getvalue()
        self.assertEqual(status, 2)
        self.assertIn('"error_code": "INVALID_ARGUMENT"', out)
        self.assertNotIn(secret, out)
        self.assertEqual(list(self.archive.iterdir()), [])

    def test_explicit_weekly_cli_uses_only_synthetic_source(self):
        with io.StringIO() as err, redirect_stderr(err):
            # This is a valid ISO weekly slot, no OS task is installed.
            status = daily.main([
                "--source", str(self.source),
                "--snapshot-dir", str(self.snap), "--archive-dir", str(self.archive),
                "--ledger-dir", str(self.ledger), "--job-id", "my-weekly-job",
                "--utc-day", "2026-11-14", "--period", "weekly",
                "--synthetic-only", "--accept-plaintext",
            ])
        self.assertEqual(status, 0)
        self.assertEqual(len(list(self.archive.glob("dbvora-*.zip"))), 1)


if __name__ == "__main__":
    unittest.main()
