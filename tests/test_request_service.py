"""Full original-engine request service tests; OS-temp generated SQLite only."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from contextlib import closing
import hashlib
import sqlite3
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import request_service as service
from dbvora.archive.safe_zip import ArchiveError, create_snapshot
from tests.fixtures.make_sqlite import create_fixture


def _archive_once_process(snapshot, output, ledger, barrier, result_queue):
    try:
        barrier.wait(timeout=30)
        result = service.archive_once(
            snapshot, output, ledger, "synthetic-request-0001",
            synthetic_only=True, accept_plaintext=True,
        )
        result_queue.put(("PUBLISHED", result["artifact_name"],
                         result["artifact_sha256"], result["snapshot_sha256"]))
    except service.RequestServiceError as exc:
        result_queue.put(("HOLD", exc.code))
    except BaseException as exc:
        result_queue.put(("ERROR", type(exc).__name__))


class RequestServiceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dbvora-request-service-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.original = create_fixture(self.root / "source.sqlite")
        self.original_id = (hashlib.sha256(self.original.read_bytes()).hexdigest(),
                            self.original.stat().st_mtime_ns)
        self.snap_dir, self.output, self.ledger = (self.root / p for p in ("snap", "archive", "ledger"))
        for p in (self.snap_dir, self.output, self.ledger):
            p.mkdir()
        self.snapshot = Path(create_snapshot(self.original, self.snap_dir)["snapshot_path"])

    def go(self, req="synthetic-request-0001", **kwargs):
        return service.archive_once(self.snapshot, self.output, self.ledger, req,
                                    synthetic_only=True, accept_plaintext=True, **kwargs)

    def test_zip_restored_content_and_ledger_recorded_without_success_claim(self):
        report = self.go()
        self.assertEqual(report["status"], "RECORDED_UNVERIFIED")
        self.assertTrue(report["independently_restored_content_verified"])
        self.assertFalse(report["exactly_once_verified"])
        self.assertFalse(report["ready_for_customer_data"])
        self.assertTrue((self.output / report["artifact_name"]).is_file())
        self.assertEqual((hashlib.sha256(self.original.read_bytes()).hexdigest(),
                          self.original.stat().st_mtime_ns), self.original_id)

    def test_exact_request_replay_does_not_publish_second_zip(self):
        self.go()
        files = sorted(x.name for x in self.output.iterdir())
        with self.assertRaisesRegex(service.RequestServiceError, "REQUEST_REPLAY_HELD"):
            self.go()
        self.assertEqual(files, sorted(x.name for x in self.output.iterdir()))

    def test_conflicting_request_plan_does_not_publish(self):
        self.go()
        with self.assertRaisesRegex(service.RequestServiceError, "REQUEST_PLAN_CONFLICT"):
            self.go(codec="zstd", level=3)
        self.assertEqual(len(list(self.output.glob("dbvora-*.zip"))), 1)

    def test_reservation_stays_held_after_injected_failure(self):
        with patch.object(service, "make_zip_archive", side_effect=ArchiveError("PUBLISH_FAILED", "simulated")):
            with self.assertRaisesRegex(service.RequestServiceError, "PUBLISH_FAILED"):
                self.go()
        with self.assertRaisesRegex(service.RequestServiceError, "REQUEST_REPLAY_HELD"):
            self.go()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_no_required_acknowledgement_does_not_create_ledger(self):
        for flags in (dict(synthetic_only=False, accept_plaintext=True),
                      dict(synthetic_only=True, accept_plaintext=False)):
            with self.assertRaises(service.RequestServiceError):
                service.archive_once(self.snapshot, self.output, self.ledger,
                                     "synthetic-request-0001", **flags)
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertEqual(list(self.ledger.iterdir()), [])

    def test_invalid_codec_and_level_do_not_reserve(self):
        for x in (dict(codec="brotli"), dict(codec="zip", level=3), dict(codec="zstd", level=True)):
            with self.assertRaises(service.RequestServiceError):
                self.go(**x)
        self.assertEqual(list(self.ledger.iterdir()), [])

    def test_invalid_request_id_fails_closed(self):
        with self.assertRaisesRegex(service.RequestServiceError, "INVALID_REQUEST_ID"):
            self.go(req="../private")
        self.assertEqual(list(self.output.iterdir()), [])

    def test_ledger_must_not_be_snapshot_or_archive_directory(self):
        for folder in (self.snap_dir, self.output):
            with self.assertRaisesRegex(service.RequestServiceError, "SEPARATE_DIRECTORY_REQUIRED"):
                service.archive_once(self.snapshot, self.output, folder,
                                     "synthetic-request-0001", synthetic_only=True,
                                     accept_plaintext=True)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_source_must_be_dbvora_generated_snapshot(self):
        with self.assertRaisesRegex(service.RequestServiceError, "GENERATED_SNAPSHOT_REQUIRED"):
            service.archive_once(self.original, self.output, self.ledger,
                                 "synthetic-request-0001", synthetic_only=True,
                                 accept_plaintext=True)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_mutated_archive_before_independent_check_stays_unverified(self):
        actual = service.make_zip_archive
        def corrupt(source, folder):
            result = actual(source, folder)
            with Path(result["archive_path"]).open("ab") as stream:
                stream.write(b"garbage")
            return result
        with patch.object(service, "make_zip_archive", side_effect=corrupt):
            with self.assertRaises(service.RequestServiceError):
                self.go()
        with self.assertRaisesRegex(service.RequestServiceError, "REQUEST_REPLAY_HELD"):
            self.go()

    def test_parallel_requests_exactly_one_new_authorization(self):
        def once(_):
            try:
                return self.go()["status"]
            except service.RequestServiceError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=3) as pool:
            result = list(pool.map(once, range(3)))
        self.assertEqual(result.count("RECORDED_UNVERIFIED"), 1)
        self.assertEqual(result.count("REQUEST_REPLAY_HELD"), 2)
        self.assertEqual(len(list(self.output.glob("dbvora-*.zip"))), 1)

    def test_multiprocess_same_request_publishes_only_one_zip(self):
        from dbvora.archive.request_ledger import LEDGER_NAME, reserve

        seed = hashlib.sha256(b"synthetic seed plan").hexdigest()
        reserve(self.ledger, "synthetic-seed-0001", seed)
        context = multiprocessing.get_context("spawn")
        barrier = context.Barrier(3)
        result_queue = context.Queue()
        processes = [
            context.Process(
                target=_archive_once_process,
                args=(str(self.snapshot), str(self.output), str(self.ledger),
                      barrier, result_queue),
            )
            for _ in range(3)
        ]
        try:
            for process in processes:
                process.start()
            outcomes = [result_queue.get(timeout=45) for _ in processes]
            for process in processes:
                process.join(timeout=10)
            self.assertTrue(all(not process.is_alive() for process in processes))
            self.assertTrue(all(process.exitcode == 0 for process in processes))
            published = [item for item in outcomes if item[0] == "PUBLISHED"]
            held = [item for item in outcomes if item == ("HOLD", "REQUEST_REPLAY_HELD")]
            errors = [item for item in outcomes if item[0] == "ERROR"]
            self.assertEqual(errors, [])
            self.assertEqual(len(published), 1)
            self.assertEqual(len(held), 2)
            _, name, artifact_sha, snapshot_sha = published[0]
            archives = list(self.output.glob("dbvora-*.zip"))
            self.assertEqual([item.name for item in archives], [name])
            self.assertEqual(hashlib.sha256(archives[0].read_bytes()).hexdigest(), artifact_sha)
            self.assertEqual(snapshot_sha, hashlib.sha256(self.snapshot.read_bytes()).hexdigest())
            with closing(sqlite3.connect(self.ledger / LEDGER_NAME)) as connection:
                recorded = connection.execute(
                    "SELECT phase,artifact_sha FROM requests WHERE artifact_sha IS NOT NULL"
                ).fetchall()
            self.assertEqual(recorded, [("RECORDED", artifact_sha)])
            self.assertEqual(
                (hashlib.sha256(self.original.read_bytes()).hexdigest(),
                 self.original.stat().st_mtime_ns),
                self.original_id,
            )
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                if process.pid is not None:
                    process.join(timeout=5)
            result_queue.close()
            result_queue.join_thread()

    @unittest.skipUnless(shutil.which("zstd"), "optional installed ZSTD codec unavailable")
    def test_zstd_archive_independent_restore(self):
        result = self.go(codec="zstd", level=3)
        self.assertTrue(result["artifact_name"].endswith(".dbvz"))
        self.assertTrue(result["independently_restored_content_verified"])
        self.assertFalse(result["windows_ntfs_verified"])

    def test_unknown_existing_ledger_not_mutated(self):
        from dbvora.archive.request_ledger import LEDGER_NAME
        p = self.ledger / LEDGER_NAME
        with closing(sqlite3.connect(p)) as db:
            db.execute("CREATE TABLE customer_secret(value TEXT)")
            db.execute("INSERT INTO customer_secret VALUES('sentinel')")
            db.commit()
        before = p.read_bytes()
        with self.assertRaisesRegex(service.RequestServiceError, "UNTRUSTED_LEDGER_FILE"):
            self.go()
        self.assertEqual(before, p.read_bytes())


class RequestServiceAdditionalFaultTests(unittest.TestCase):
    """Reuse synthetic fixture scaffolding without inheriting the old test cases."""

    setUp = RequestServiceTests.setUp
    go = RequestServiceTests.go

    def test_publish_succeeds_but_ledger_record_failure_never_autoretries(self):
        from dbvora.archive.request_ledger import LedgerError
        with patch.object(service.request_ledger, 'record_artifact',
                          side_effect=LedgerError('LEDGER_UNAVAILABLE')):
            with self.assertRaisesRegex(service.RequestServiceError, 'LEDGER_UNAVAILABLE'):
                self.go()
        self.assertEqual(len(list(self.output.glob('dbvora-*.zip'))), 1)
        with self.assertRaisesRegex(service.RequestServiceError, 'REQUEST_REPLAY_HELD'):
            self.go()

    def test_output_symlink_is_rejected_without_touching_target(self):
        target = self.root / 'real-out'
        target.mkdir()
        link = self.root / 'aliased-out'
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('local symlink creation unavailable')
        with self.assertRaisesRegex(service.RequestServiceError, 'BAD_DESTINATION'):
            service.archive_once(self.snapshot, link, self.ledger,
                                 'synthetic-request-0001', synthetic_only=True,
                                 accept_plaintext=True)
        self.assertEqual(list(target.iterdir()), [])

    def test_postarchive_snapshot_mutation_is_detected_and_held(self):
        original = service.make_zip_archive
        def create_then_mutate(source, output):
            result = original(source, output)
            with closing(sqlite3.connect(source)) as db:
                db.execute('CREATE TABLE extra(id INTEGER)')
                db.commit()
            return result
        with patch.object(service, 'make_zip_archive', side_effect=create_then_mutate):
            with self.assertRaisesRegex(service.RequestServiceError, 'POST_ARCHIVE_VERIFICATION_FAILED'):
                self.go()
        with self.assertRaisesRegex(service.RequestServiceError, 'REQUEST_PLAN_CONFLICT'):
            self.go()
        self.assertEqual(len(list(self.output.glob('dbvora-*.zip'))), 1)

    def test_filesystem_errors_do_not_leak_local_paths(self):
        secret = '/home/private/example.sqlite'
        with patch.object(service, 'make_zip_archive', side_effect=OSError(secret)):
            with self.assertRaises(service.RequestServiceError) as problem:
                self.go()
        self.assertEqual(problem.exception.code, 'OPERATION_FAILED')
        self.assertNotIn(secret, str(problem.exception))


if __name__ == "__main__":
    unittest.main()
