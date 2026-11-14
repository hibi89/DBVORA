"""Opt-in request ledger exercises only temp folder and synthetic digests."""
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from unittest.mock import patch
import os
from dbvora.archive import request_ledger
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

def _reserve_process(folder: str, barrier, result_queue):
    try:
        barrier.wait(timeout=30)
        status = reserve(folder, ID, PLAN)["status"]
    except BaseException as exc:
        status = ("ERROR", type(exc).__name__, getattr(exc, "code", ""))
    result_queue.put(status)


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

    def test_multiprocess_reservations_only_one_new_request(self):
        seed_plan = hashlib.sha256(b"synthetic seed request").hexdigest()
        reserve(self.folder, "request-2026-0000", seed_plan)
        context = multiprocessing.get_context("spawn")
        barrier = context.Barrier(4)
        result_queue = context.Queue()
        processes = [
            context.Process(target=_reserve_process,
                            args=(str(self.folder), barrier, result_queue))
            for _ in range(4)
        ]
        try:
            for process in processes:
                process.start()
            statuses = [result_queue.get(timeout=45) for _ in processes]
            for process in processes:
                process.join(timeout=10)
            self.assertTrue(all(not process.is_alive() for process in processes))
            self.assertTrue(all(process.exitcode == 0 for process in processes))
            self.assertEqual(statuses.count("RESERVED_NOT_EXECUTED"), 1)
            self.assertEqual(statuses.count("REPLAY_REQUIRES_MANUAL_REVIEW"), 3)
            with closing(sqlite3.connect(self.folder / LEDGER_NAME)) as connection:
                count = connection.execute("SELECT count(*) FROM requests").fetchone()[0]
            self.assertEqual(count, 2)
            self.assertEqual(list(self.folder.glob("dbvora-*.zip")), [])
            self.assertEqual(list(self.folder.glob("dbvora-*.json")), [])
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                if process.pid is not None:
                    process.join(timeout=5)
            result_queue.close()
            result_queue.join_thread()

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

    def test_record_missing_ledger_race_never_creates_new_file(self):
        # Simulate a positive exists check followed by an absent file.
        # This used to cause the record-only path to create a fresh ledger.
        path = self.folder / LEDGER_NAME
        with patch.object(Path, "exists", return_value=True):
            with self.assertRaises(LedgerError):
                record_artifact(self.folder, ID, PLAN, ARTIFACT)
        self.assertFalse(path.exists())

    def test_record_existing_reservation_never_requests_os_create(self):
        reserve(self.folder, ID, PLAN)
        actual_open = os.open
        def deny_create(file, flags, *args, **kwargs):
            if flags & os.O_CREAT:
                self.fail("record-only path attempted OS-level file create")
            return actual_open(file, flags, *args, **kwargs)
        with patch.object(request_ledger.os, "open", side_effect=deny_create):
            result = record_artifact(self.folder, ID, PLAN, ARTIFACT)
        self.assertEqual(result["status"], "RECORDED_UNVERIFIED")

    def test_record_only_sqlite_connect_race_never_creates_replacement(self):
        reserve(self.folder, ID, PLAN)
        ledger_path = self.folder / LEDGER_NAME
        raw_connect = sqlite3.connect
        def remove_before_write(database, *args, **kwargs):
            # sqlite3.connect has a keyword argument named uri=True; do not
            # shadow it in this test seam, or no deletion race is exercised.
            if isinstance(database, str) and database.endswith('?mode=rw'):
                ledger_path.unlink()
            return raw_connect(database, *args, **kwargs)
        with patch.object(request_ledger.sqlite3, 'connect', side_effect=remove_before_write):
            with self.assertRaisesRegex(LedgerError, 'LEDGER_UNAVAILABLE'):
                record_artifact(self.folder, ID, PLAN, ARTIFACT)
        self.assertFalse(ledger_path.exists())

    def test_missing_output_is_not_created(self):
        with self.assertRaisesRegex(LedgerError, "LEDGER_DIRECTORY_UNAVAILABLE"):
            reserve(self.folder / "missing", ID, PLAN)
        self.assertFalse((self.folder / "missing").exists())

if __name__=="__main__":
    unittest.main()
