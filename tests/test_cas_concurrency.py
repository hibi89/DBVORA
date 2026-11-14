"""Deterministic synthetic CAS zlib v2 publish/restore concurrency regressions.

All deliberate races are confined to temporary synthetic SQLite snapshots.
These tests neither access customer files nor install background jobs.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
import zlib
from unittest.mock import patch

from dbvora.archive import cas_audit, compressed_cas as cas
from dbvora.archive.safe_zip import create_snapshot
from tests.fixtures.make_sqlite import create_fixture


class CompressedCasConcurrencyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dbvora-concurrent-synthetic-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.database = create_fixture(root / "synthetic.sqlite")
        self.snapshots, self.chunks, self.manifests, self.output = (
            root / name for name in ("snapshots", "chunks", "manifests", "output"))
        for directory in (self.snapshots, self.chunks, self.manifests, self.output):
            directory.mkdir()
        self.snapshot = self.take_snapshot()

    def take_snapshot(self):
        return Path(create_snapshot(self.database, self.snapshots)["snapshot_path"])

    def publish(self):
        return cas.create_compressed(
            self.snapshot, self.chunks, self.manifests,
            synthetic_only=True, accept_plaintext=True)

    def restore(self, record):
        return cas.restore_compressed(
            self.manifests / record["manifest_name"], self.chunks, self.output,
            synthetic_only=True, accept_plaintext=True)

    def test_two_writers_race_same_new_chunk_keep_old_generation_and_no_stages(self):
        old = self.publish()
        old_bytes = (self.manifests / old["manifest_name"]).read_bytes()
        old_source_hash = hashlib.sha256(self.database.read_bytes()).hexdigest()
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute(
                "INSERT INTO events (category, content) VALUES (?, ?)",
                ("synthetic", "changed-for-race-" + "R" * 1500))
            connection.commit()
        self.snapshot = self.take_snapshot()
        expected_hash = hashlib.sha256(self.snapshot.read_bytes()).hexdigest()

        # Ensure both threads have already observed the target new chunk as
        # absent by rendezvousing at the first chunk staging allocation.
        original_staging = cas._staging_file
        barrier = threading.Barrier(2, timeout=20)
        gate = threading.Lock()
        entered = [0]

        def rendezvous_staging(directory):
            if Path(directory) == self.chunks:
                with gate:
                    index = entered[0]
                    entered[0] += 1
                if index < 2:
                    barrier.wait()
            return original_staging(directory)

        def worker(_index):
            try:
                return ("PUBLISHED", self.publish())
            except cas.CompressedCasError as exc:
                return ("HOLD", str(exc))

        with patch.object(cas, "_staging_file", side_effect=rendezvous_staging):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(worker, range(2)))
        self.assertEqual(entered[0] >= 2, True)
        published = [value for state, value in results if state == "PUBLISHED"]
        rejected = [value for state, value in results if state == "HOLD"]
        self.assertGreaterEqual(len(published), 1)
        self.assertEqual(len(published) + len(rejected), 2)
        # POSIX can verify and reuse the winner, while NTFS may fail closed
        # on a no-replace race. A loser must not report an unverified success.
        self.assertTrue(all(value in {
            "CHUNK_PUBLISH_UNVERIFIED", "CHUNK_UNAVAILABLE",
            "INVALID_CHUNK_FILE", "CHUNK_CHANGED"} for value in rejected))
        self.assertEqual((self.manifests / old["manifest_name"]).read_bytes(), old_bytes)
        self.assertEqual(self.restore(old)["restored_sha256"], old["snapshot_sha256"])
        self.assertEqual(
            cas_audit.audit(self.chunks, self.manifests,
                            synthetic_only=True)["status"],
            "PASS_SYNTHETIC_CAS_AUDIT_ONLY")
        for item in published:
            self.assertEqual(item["snapshot_sha256"], expected_hash)
            self.assertEqual(self.restore(item)["restored_sha256"], expected_hash)
        for directory in (self.chunks, self.manifests, self.output):
            self.assertEqual(list(directory.glob(".dbvora-incomplete-*.part")), [])
        self.assertNotEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(),
                            old_source_hash)

    def test_simultaneous_restore_publishes_two_distinct_checked_outputs(self):
        stored = self.publish()
        before = (self.manifests / stored["manifest_name"]).read_bytes()
        with ThreadPoolExecutor(max_workers=2) as pool:
            restored = list(pool.map(lambda _: self.restore(stored), range(2)))
        self.assertEqual(len({item["restored_name"] for item in restored}), 2)
        for item in restored:
            self.assertEqual(item["restored_sha256"], stored["snapshot_sha256"])
            file = self.output / item["restored_name"]
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),
                             stored["snapshot_sha256"])
        self.assertEqual((self.manifests / stored["manifest_name"]).read_bytes(),
                         before)
        self.assertEqual(list(self.output.glob(".dbvora-incomplete-*.part")), [])

    def test_existing_mismatched_chunk_never_overwritten_or_referenced(self):
        old = self.publish()
        before = (self.manifests / old["manifest_name"]).read_bytes()
        raw = b"SYNTHETIC_COLLISION_" * 100
        digest = hashlib.sha256(raw).hexdigest()
        poison = self.chunks / (digest + ".cz")
        poison_blob = cas.MAGIC + zlib.compress(b"DIFFERENT_DATA" * 90)
        poison.write_bytes(poison_blob)
        with self.assertRaisesRegex(cas.CompressedCasError,
                                    "CHUNK_HASH_MISMATCH"):
            cas._put(self.chunks, raw)
        self.assertEqual(poison.read_bytes(), poison_blob)
        self.assertEqual((self.manifests / old["manifest_name"]).read_bytes(),
                         before)
        self.assertEqual(self.restore(old)["restored_sha256"], old["snapshot_sha256"])


if __name__ == "__main__":
    unittest.main()
