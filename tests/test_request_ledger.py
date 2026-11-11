"""Opt-in request ledger exercises only temp folder and synthetic digests."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from dbvora.archive.request_ledger import LedgerError, LEDGER_NAME, record_artifact, reserve

ID = "request-2026-0001"
PLAN = hashlib.sha256(b"synthetic plan").hexdigest()
OTHER = hashlib.sha256(b"another plan").hexdigest()
ARTIFACT = hashlib.sha256(b"synthetic archive").hexdigest()

class RequestLedgerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="dbvora-request-ledger-")
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)

    def test_first_reservation_does_not_execute_archive(self):
        result = reserve(self.folder, ID, PLAN)
        self.assertEqual(result["status"], "RESERVED_NOT_EXECUTED")
        self.assertFalse(result["archive_executed"])
        self.assertFalse(result["exactly_once_verified"])
        self.assertTrue((self.folder / LEDGER_NAME).is_file())

    def test_duplicate_reservation_blocks_rerun(self):
        reserve(self.folder, ID, PLAN)
        self.assertEqual(reserve(self.folder, ID, PLAN)["status"], "REPLAY_REQUIRES_MANUAL_REVIEW")

    def test_conflicting_plan_is_rejected(self):
        reserve(self.folder, ID, PLAN)
        with self.assertRaisesRegex(LedgerError, "REQUEST_PLAN_CONFLICT"):
            reserve(self.folder, ID, OTHER)

    def test_cannot_record_without_reservation(self):
        with self.assertRaisesRegex(LedgerError, "UNRESERVED_REQUEST"):
            record_artifact(self.folder, ID, PLAN, ARTIFACT)

    def test_recorded_digest_is_not_verified(self):
        reserve(self.folder, ID, PLAN)
        result = record_artifact(self.folder, ID, PLAN, ARTIFACT)
        self.assertEqual(result["status"], "RECORDED_UNVERIFIED")
        self.assertFalse(result["independent_artifact_verification"])
        self.assertEqual(reserve(self.folder, ID, PLAN)["status"], "RECORDED_REQUIRES_ARTIFACT_VERIFICATION")

    def test_repeated_same_record_is_stable(self):
        reserve(self.folder, ID, PLAN)
        record_artifact(self.folder, ID, PLAN, ARTIFACT)
        self.assertEqual(record_artifact(self.folder, ID, PLAN, ARTIFACT)["status"], "PREVIOUSLY_RECORDED_UNVERIFIED")

    def test_changed_record_digest_is_rejected(self):
        reserve(self.folder, ID, PLAN)
        record_artifact(self.folder, ID, PLAN, ARTIFACT)
        with self.assertRaisesRegex(LedgerError, "ARTIFACT_DIGEST_CONFLICT"):
            record_artifact(self.folder, ID, PLAN, OTHER)

    def test_restart_retains_reservation(self):
        reserve(self.folder, ID, PLAN)
        self.assertEqual(reserve(self.folder, ID, PLAN)["status"], "REPLAY_REQUIRES_MANUAL_REVIEW")

    def test_no_plain_request_id_stored(self):
        reserve(self.folder, ID, PLAN)
        with closing(sqlite3.connect(self.folder / LEDGER_NAME)) as c:
            values = c.execute("SELECT request_key, plan_sha, phase FROM requests").fetchone()
        self.assertNotEqual(values[0], ID)
        self.assertEqual(values[1], PLAN)
        self.assertEqual(values[2], "RESERVED")

    def test_parallel_reservations_only_one_new(self):
        with ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(lambda _: reserve(self.folder, ID, PLAN)["status"], range(4)))
        self.assertEqual(results.count("RESERVED_NOT_EXECUTED"), 1)
        self.assertEqual(results.count("REPLAY_REQUIRES_MANUAL_REVIEW"), 3)

    def test_invalid_ids_and_digests_are_rejected(self):
        for bad_id in ("x", "../a/b/c", "열쇠-12345678", "", None):
            with self.assertRaises(LedgerError):
                reserve(self.folder, bad_id, PLAN)
        for bad_sha in ("ABC" * 21 + "X", "", None):
            with self.assertRaises(LedgerError):
                reserve(self.folder, ID, bad_sha)

    def test_symlink_file_is_refused(self):
        outside = self.folder / "outside.bin"
        outside.write_bytes(b"never touch")
        (self.folder / LEDGER_NAME).symlink_to(outside)
        with self.assertRaisesRegex(LedgerError, "UNSAFE_LEDGER_FILE"):
            reserve(self.folder, ID, PLAN)
        self.assertEqual(outside.read_bytes(), b"never touch")

    def test_existing_unknown_sqlite_is_never_mutated(self):
        db = self.folder / LEDGER_NAME
        with closing(sqlite3.connect(db)) as conn:
            conn.execute("CREATE TABLE customer_secret(secret TEXT)")
            conn.execute("INSERT INTO customer_secret VALUES('sentinel')")
            conn.commit()
        original = db.read_bytes()
        with self.assertRaisesRegex(LedgerError, "UNTRUSTED_LEDGER_FILE"):
            reserve(self.folder, ID, PLAN)
        self.assertEqual(db.read_bytes(), original)

    def test_relative_output_is_rejected(self):
        with self.assertRaisesRegex(LedgerError, "INVALID_LEDGER_DIRECTORY"):
            reserve("relative-path", ID, PLAN)

    def test_missing_output_is_not_created(self):
        with self.assertRaisesRegex(LedgerError, "LEDGER_DIRECTORY_UNAVAILABLE"):
            reserve(self.folder / "missing", ID, PLAN)
        self.assertFalse((self.folder / "missing").exists())

if __name__=="__main__":
    unittest.main()
