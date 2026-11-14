"""Synthetic zlib CAS v2 abrupt child-exit staging acceptance.

Only a spawned child writing in a disposable TemporaryDirectory is terminated
with os._exit. This is NOT a physical power cut, fsync durability guarantee,
automatic recovery, or a customer-data test.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import multiprocessing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import cas_audit, compressed_cas as cas
from dbvora.archive.safe_zip import create_snapshot
from tests.fixtures.make_sqlite import create_fixture


EXIT_CHUNK = 86
EXIT_MANIFEST = 87


def _crash_writer(snapshot, chunks, manifests, stage):
    """In a separate spawned process, die after a deliberately partial write."""
    original = cas._write_staged_exact

    def interrupted_write(staged, payload):
        is_chunk = payload.startswith(cas.MAGIC)
        inject = (stage == "chunk" and is_chunk) or (
            stage == "manifest" and not is_chunk)
        if inject:
            # write_bytes closes/flushed its file before os._exit; the
            # deliberately incomplete .part is left for read-only audit.
            staged.write_bytes(payload[:max(1, len(payload) // 3)])
            os._exit(EXIT_CHUNK if is_chunk else EXIT_MANIFEST)
        return original(staged, payload)

    with patch.object(cas, "_write_staged_exact", side_effect=interrupted_write):
        cas.create_compressed(
            Path(snapshot), Path(chunks), Path(manifests),
            synthetic_only=True, accept_plaintext=True)
    # If no intended hook fired, fail instead of passing as a crash.
    os._exit(1)


class CompressedCasAbruptExitTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(
            prefix="dbvora-abrupt-child-synthetic-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.database = create_fixture(root / "synthetic.sqlite")
        self.snapshots, self.chunks, self.manifests, self.outputs = (
            root / name for name in ("snapshots", "chunks", "manifests", "outputs"))
        for folder in (self.snapshots, self.chunks, self.manifests, self.outputs):
            folder.mkdir()
        self.snapshot = self.take_snapshot()

    def take_snapshot(self):
        return Path(create_snapshot(self.database, self.snapshots)["snapshot_path"])

    @staticmethod
    def fingerprint(path):
        info = path.stat()
        return hashlib.sha256(path.read_bytes()).hexdigest(), info.st_mtime_ns

    def publish(self):
        return cas.create_compressed(
            self.snapshot, self.chunks, self.manifests,
            synthetic_only=True, accept_plaintext=True)

    def restore(self, saved):
        record = cas.restore_compressed(
            self.manifests / saved["manifest_name"], self.chunks,
            self.outputs, synthetic_only=True, accept_plaintext=True)
        self.assertEqual(record["restored_sha256"], saved["snapshot_sha256"])
        restored = self.outputs / record["restored_name"]
        self.assertEqual(self.fingerprint(restored)[0], saved["snapshot_sha256"])
        with closing(sqlite3.connect(restored)) as conn:
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_child_exit_during_chunk_staging_preserves_old_generation(self):
        self.check_interrupted_staging("chunk")

    def test_child_exit_during_manifest_staging_holds_orphans(self):
        self.check_interrupted_staging("manifest")

    def check_interrupted_staging(self, stage):
        old = self.publish()
        old_manifest = self.manifests / old["manifest_name"]
        old_bytes = old_manifest.read_bytes()
        old_chunk_names = {p.name for p in self.chunks.glob("*.cz")}
        before_source = self.fingerprint(self.database)

        # A new snapshot must contain at least one chunk not present in old.
        with closing(sqlite3.connect(self.database)) as conn:
            conn.execute(
                "INSERT INTO events(category, content) VALUES (?, ?)",
                ("synthetic", "interrupted-" + stage + "-" + "R" * 2200))
            conn.commit()
        self.snapshot = self.take_snapshot()
        new_db = self.fingerprint(self.database)
        new_snapshot = self.fingerprint(self.snapshot)
        self.assertNotEqual(new_db, before_source)
        self.assertNotEqual(new_snapshot[0], old["snapshot_sha256"])
        new_blob = self.snapshot.read_bytes()
        new_keys = {
            hashlib.sha256(new_blob[n:n + cas.CHUNK_BYTES]).hexdigest() + ".cz"
            for n in range(0, len(new_blob), cas.CHUNK_BYTES)
        } - old_chunk_names
        self.assertTrue(new_keys, "PRECONDITION_REQUIRES_NEW_CHUNK")

        context = multiprocessing.get_context("spawn")
        worker = context.Process(
            target=_crash_writer, args=(
                str(self.snapshot), str(self.chunks), str(self.manifests), stage))
        try:
            worker.start()
            worker.join(timeout=30)
            self.assertFalse(worker.is_alive(), "CHILD_PROCESS_TIMEOUT")
            self.assertEqual(
                worker.exitcode,
                EXIT_CHUNK if stage == "chunk" else EXIT_MANIFEST,
                "INTENDED_STAGE_CRASH_NOT_REACHED")
        finally:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
            if worker.is_alive():
                worker.kill()
                worker.join(timeout=5)

        # A partially written stage must not become a verified chunk/manifest.
        stages = sorted((self.chunks if stage == "chunk" else self.manifests)
                        .glob(".dbvora-incomplete-*.part"))
        self.assertEqual(len(stages), 1, "ABRUPT_EXIT_STAGE_NOT_RETAINED")
        self.assertGreater(stages[0].stat().st_size, 0)
        self.assertEqual(
            sorted(p.name for p in self.manifests.glob("dbvora-*.json")),
            [old["manifest_name"]], "UNVERIFIED_MANIFEST_PUBLISHED")
        self.assertEqual(old_manifest.read_bytes(), old_bytes)
        self.assertEqual(self.fingerprint(self.database), new_db)
        self.assertEqual(self.fingerprint(self.snapshot), new_snapshot)

        created_new = {p.name for p in self.chunks.glob("*.cz")} - old_chunk_names
        if stage == "chunk":
            self.assertEqual(created_new, set(),
                             "PARTIAL_CHUNK_WAS_PUBLISHED")
        else:
            self.assertTrue(created_new & new_keys,
                            "MANIFEST_CRASH_REQUIRES_PUBLISHED_NEW_CHUNK")
        report = cas_audit.audit(self.chunks, self.manifests, synthetic_only=True)
        self.assertEqual(report["status"], "HOLD_MANUAL_REVIEW")
        self.assertEqual(report["verified_generation_count"], 1)
        self.assertEqual(report["invalid_generation_count"], 0)
        self.assertEqual(report["missing_chunk_count"], 0)
        self.assertGreaterEqual(report["unrecognized_file_count"], 1)
        self.assertEqual(report["unreferenced_chunk_count"] > 0,
                         stage == "manifest")
        self.assertFalse(report["automatic_deletion"])
        self.assertFalse(report["new_files_created"])

        # Inspection is read-only and never removes suspicious artifacts.
        names_before = [
            sorted(p.name for p in folder.iterdir())
            for folder in (self.chunks, self.manifests)]
        self.assertEqual(
            cas_audit.audit(self.chunks, self.manifests, synthetic_only=True),
            report)
        self.assertEqual(names_before, [
            sorted(p.name for p in folder.iterdir())
            for folder in (self.chunks, self.manifests)])
        self.restore(old)
        self.assertEqual(old_manifest.read_bytes(), old_bytes)
        self.assertEqual(self.fingerprint(self.snapshot), new_snapshot)
        self.assertEqual(stages[0].exists(), True)


if __name__ == "__main__":
    unittest.main()
