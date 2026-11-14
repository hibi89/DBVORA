"""Synthetic-only compressed CAS v2; raw CAS v1 compatibility retained."""
from __future__ import annotations

from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zlib

from dbvora.archive import compressed_cas as v2, incremental_cas as v1
from dbvora.archive.safe_zip import create_snapshot
from tests.fixtures.make_sqlite import create_fixture


class CompressedCasTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dbvora-cas-zlib-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.db = create_fixture(root / "source.sqlite")
        self.snap, self.chunks, self.manifests, self.restored = [
            root / x for x in ("snap", "chunks", "manifests", "restored")]
        for d in (self.snap, self.chunks, self.manifests, self.restored):
            d.mkdir()
        self.source = Path(create_snapshot(self.db, self.snap)["snapshot_path"])
        self.before = hashlib.sha256(self.db.read_bytes()).hexdigest()

    def create(self, src=None):
        return v2.create_compressed(src or self.source, self.chunks, self.manifests,
                                    synthetic_only=True, accept_plaintext=True)

    def restore(self, report):
        return v2.restore_compressed(self.manifests / report["manifest_name"],
                                     self.chunks, self.restored,
                                     synthetic_only=True, accept_plaintext=True)

    def test_roundtrip_and_compression_is_real(self):
        first = self.create()
        self.assertGreater(first["new_chunks"], 0)
        self.assertLess(first["new_compressed_bytes"], first["source_bytes"])
        result = self.restore(first)
        self.assertEqual(result["restored_sha256"], first["snapshot_sha256"])
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), self.before)
        self.assertFalse(result["ready_for_customer_data"])

    def test_replay_reuses_chunks_and_keeps_distinct_manifests(self):
        one = self.create()
        two = self.create()
        self.assertEqual(two["new_chunks"], 0)
        self.assertEqual(two["reused_chunks"], one["chunks"])
        self.assertNotEqual(one["manifest_name"], two["manifest_name"])
        self.assertEqual(self.restore(one)["restored_sha256"],
                         self.restore(two)["restored_sha256"])

    def test_changed_snapshot_keeps_old_independent_restore(self):
        old = self.create()
        with closing(sqlite3.connect(self.db)) as con:
            con.execute("CREATE TABLE synthetic_added(id INTEGER PRIMARY KEY)")
            con.commit()
        newer_snapshot = Path(create_snapshot(self.db, self.snap)["snapshot_path"])
        new = self.create(newer_snapshot)
        self.assertNotEqual(new["snapshot_sha256"], old["snapshot_sha256"])
        self.assertEqual(self.restore(old)["restored_sha256"], old["snapshot_sha256"])
        self.assertEqual(self.restore(new)["restored_sha256"], new["snapshot_sha256"])

    def test_corrupt_chunk_and_bomb_both_rejected(self):
        one = self.create()
        doc = v2._parse_manifest((self.manifests / one["manifest_name"]).read_bytes())
        target = self.chunks / (doc["chunks"][0] + ".cz")
        target.write_bytes(b"corrupted")
        with self.assertRaises(v2.CompressedCasError):
            self.restore(one)
        target.write_bytes(v2.MAGIC + zlib.compress(b"X" * (v2.CHUNK_BYTES * 8)))
        with self.assertRaises(v2.CompressedCasError):
            self.restore(one)
        self.assertEqual(list(self.restored.iterdir()), [])

    def test_raw_v1_still_remains_independent(self):
        root = self.snap.parent
        old_chunks, old_manifests = root / "v1c", root / "v1m"
        old_chunks.mkdir()
        old_manifests.mkdir()
        old = v1.create_incremental(self.source, old_chunks, old_manifests,
                                    synthetic_only=True, accept_plaintext=True)
        with self.assertRaisesRegex(v2.CompressedCasError, "INVALID_MANIFEST"):
            v2.restore_compressed(old_manifests / old["manifest_name"], old_chunks,
                                  self.restored, synthetic_only=True, accept_plaintext=True)
        self.assertTrue((old_manifests / old["manifest_name"]).exists())

    def test_missing_ack_creates_no_new_chunks(self):
        with self.assertRaisesRegex(v2.CompressedCasError, "SYNTHETIC_ONLY_REQUIRED"):
            v2.create_compressed(self.source, self.chunks, self.manifests,
                                 accept_plaintext=True)
        with self.assertRaisesRegex(v2.CompressedCasError, "PLAINTEXT_ACK_REQUIRED"):
            v2.create_compressed(self.source, self.chunks, self.manifests,
                                 synthetic_only=True)
        self.assertEqual(list(self.chunks.iterdir()), [])

    def test_duplicate_manifest_key_does_not_publish(self):
        record = self.create()
        (self.manifests / record["manifest_name"]).write_bytes(
            b'{"contract":"x","contract":"y"}')
        with self.assertRaisesRegex(v2.CompressedCasError, "DUPLICATE_MANIFEST_KEY"):
            self.restore(record)
        self.assertEqual(list(self.restored.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
