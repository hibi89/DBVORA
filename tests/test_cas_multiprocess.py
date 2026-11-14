"""Spawned *separate processes* exercising synthetic-only zlib CAS v2 races.

No customer files, network, scheduling, shared-memory database, or auto deletion.
The process rendezvous happens AFTER both writers see a new CAS chunk absent.
Not a physical power-cut / network filesystem durability certification.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import multiprocessing
from pathlib import Path
import queue
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import cas_audit, compressed_cas as cas
from dbvora.archive.safe_zip import create_snapshot
from tests.fixtures.make_sqlite import create_fixture


def _spawn_publish(snapshot, chunks, manifests, barrier, replies):
    """Child process; patching remains private to this process."""
    original_staging = cas._staging_file
    entered = 0

    def first_new_chunk_stage(directory):
        nonlocal entered
        if not entered:
            entered = 1
            # Both processes have already passed the same missing-chunk check.
            barrier.wait(timeout=20)
        return original_staging(directory)

    try:
        with patch.object(cas, "_staging_file", side_effect=first_new_chunk_stage):
            report = cas.create_compressed(
                Path(snapshot), Path(chunks), Path(manifests),
                synthetic_only=True, accept_plaintext=True)
        replies.put(("PUBLISHED", entered, report))
    except cas.CompressedCasError as exc:
        replies.put(("HOLD", entered, str(exc)))
    except BaseException as exc:
        replies.put(("UNEXPECTED", entered, type(exc).__name__))


def _spawn_restore(manifest, chunks, outputs, barrier, replies):
    """Distinct process, same immutable manifest, same output directory."""
    try:
        barrier.wait(timeout=20)
        report = cas.restore_compressed(
            Path(manifest), Path(chunks), Path(outputs),
            synthetic_only=True, accept_plaintext=True)
        replies.put(("RESTORED", 1, report))
    except BaseException as exc:
        replies.put(("UNEXPECTED", 0, type(exc).__name__))


class CompressedCasMultiprocessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(
            prefix="dbvora-separate-process-synthetic-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.db = create_fixture(root / "synthetic.sqlite")
        self.snapshots, self.chunks, self.manifests, self.outputs = (
            root / name for name in ("snapshots", "chunks", "manifests", "outputs"))
        for folder in (self.snapshots, self.chunks, self.manifests, self.outputs):
            folder.mkdir()
        self.snapshot = self.take_snapshot()

    def take_snapshot(self):
        return Path(create_snapshot(self.db, self.snapshots)["snapshot_path"])

    @staticmethod
    def fingerprint(path):
        info = path.stat()
        return hashlib.sha256(path.read_bytes()).hexdigest(), info.st_mtime_ns

    def publish(self):
        return cas.create_compressed(
            self.snapshot, self.chunks, self.manifests,
            synthetic_only=True, accept_plaintext=True)

    def restore(self, saved):
        report = cas.restore_compressed(
            self.manifests / saved["manifest_name"],
            self.chunks, self.outputs,
            synthetic_only=True, accept_plaintext=True)
        restored = self.outputs / report["restored_name"]
        self.assertEqual(self.fingerprint(restored)[0], saved["snapshot_sha256"])

    def spawn_pair(self, target, args):
        # Force "spawn" even on Linux so the test truly has independent Python
        # interpreters. No thread-only race masquerades as multiprocess proof.
        ctx = multiprocessing.get_context("spawn")
        barrier, replies = ctx.Barrier(2, timeout=20), ctx.Queue()
        workers = [ctx.Process(target=target, args=(*args, barrier, replies))
                   for _ in range(2)]
        try:
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=35)
            self.assertTrue(all(not worker.is_alive() for worker in workers),
                            "SYNTHETIC_CHILD_PROCESS_TIMEOUT")
            self.assertEqual([worker.exitcode for worker in workers], [0, 0],
                             "SYNTHETIC_CHILD_PROCESS_EXIT")
            try:
                return [replies.get(timeout=5) for _ in workers]
            except queue.Empty:
                self.fail("SYNTHETIC_CHILD_RESULT_MISSING")
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join(timeout=5)
                if worker.is_alive():
                    worker.kill()
                    worker.join(timeout=5)
            replies.close()
            replies.join_thread()

    def test_two_processes_compete_for_new_chunk_without_losing_old_snapshot(self):
        old = self.publish()
        old_manifest = self.manifests / old["manifest_name"]
        old_manifest_bytes = old_manifest.read_bytes()
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("INSERT INTO events(category, content) VALUES (?, ?)",
                         ("synthetic", "process-change-" + "P" * 1500))
            conn.commit()
        self.snapshot = self.take_snapshot()
        db_before = self.fingerprint(self.db)
        snapshot_before = self.fingerprint(self.snapshot)
        self.assertNotEqual(snapshot_before[0], old["snapshot_sha256"])
        blocks = self.snapshot.read_bytes()
        missing = [
            hashlib.sha256(blocks[n:n + cas.CHUNK_BYTES]).hexdigest()
            for n in range(0, len(blocks), cas.CHUNK_BYTES)
            if not (self.chunks / (
                hashlib.sha256(blocks[n:n + cas.CHUNK_BYTES]).hexdigest()
                + ".cz")).exists()
        ]
        self.assertTrue(missing, "RACE_PRECONDITION_NO_NEW_CHUNK")
        results = self.spawn_pair(
            _spawn_publish, (str(self.snapshot), str(self.chunks), str(self.manifests)))
        self.assertTrue(all(item[1] == 1 for item in results),
                        "RACE_PRECONDITION_NOT_SYNCHRONIZED")
        published = [item[2] for item in results if item[0] == "PUBLISHED"]
        held = [item[2] for item in results if item[0] == "HOLD"]
        self.assertGreaterEqual(len(published), 1, results)
        self.assertEqual(len(published) + len(held), 2, results)
        self.assertTrue(all(code in {
            "CHUNK_PUBLISH_UNVERIFIED", "CHUNK_UNAVAILABLE",
            "INVALID_CHUNK_FILE", "CHUNK_CHANGED"} for code in held), held)
        self.assertEqual(self.fingerprint(self.db), db_before)
        self.assertEqual(self.fingerprint(self.snapshot), snapshot_before)
        self.assertEqual(old_manifest.read_bytes(), old_manifest_bytes)
        self.restore(old)
        for report in published:
            self.assertEqual(report["snapshot_sha256"], snapshot_before[0])
            self.restore(report)
        audit = cas_audit.audit(self.chunks, self.manifests, synthetic_only=True)
        self.assertEqual(audit["status"], "PASS_SYNTHETIC_CAS_AUDIT_ONLY")
        for folder in (self.chunks, self.manifests, self.outputs):
            self.assertEqual(list(folder.glob(".dbvora-incomplete-*.part")), [])

    def test_two_processes_restore_same_manifest_to_distinct_verified_outputs(self):
        saved = self.publish()
        manifest = self.manifests / saved["manifest_name"]
        manifest_before = self.fingerprint(manifest)
        db_before = self.fingerprint(self.db)
        results = self.spawn_pair(
            _spawn_restore, (str(manifest), str(self.chunks), str(self.outputs)))
        self.assertEqual([r[0] for r in results], ["RESTORED", "RESTORED"], results)
        names = [r[2]["restored_name"] for r in results]
        self.assertEqual(len(set(names)), 2)
        for name in names:
            result = self.outputs / name
            self.assertEqual(self.fingerprint(result)[0], saved["snapshot_sha256"])
            with closing(sqlite3.connect(result)) as conn:
                self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0],
                                 "ok")
        self.assertEqual(self.fingerprint(self.db), db_before)
        self.assertEqual(self.fingerprint(manifest), manifest_before)
        self.assertEqual(list(self.outputs.glob(".dbvora-incomplete-*.part")), [])


if __name__ == "__main__":
    unittest.main()
