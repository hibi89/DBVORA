"""Synthetic content-addressed incremental actual independent restore regression."""
from __future__ import annotations

from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from dbvora.archive.safe_zip import create_snapshot
from dbvora.archive import incremental_cas as cas
from tests.fixtures.make_sqlite import create_fixture


class IncrementalCasTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory(prefix="dbvora-inc-")
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        self.db = create_fixture(self.root / "original.sqlite")
        self.snap, self.chunks, self.manifest, self.restored = [
            self.root / x for x in ("snapshots", "chunks", "manifests", "restored")]
        for folder in (self.snap, self.chunks, self.manifest, self.restored):
            folder.mkdir()
        self.source = Path(create_snapshot(self.db, self.snap)["snapshot_path"])
        self.before = hashlib.sha256(self.db.read_bytes()).hexdigest()

    def save(self, source=None):
        return cas.create_incremental(source or self.source, self.chunks, self.manifest,
                                      synthetic_only=True, accept_plaintext=True)

    def restore(self, record):
        return cas.restore_incremental(self.manifest / record["manifest_name"],
                                       self.chunks, self.restored,
                                       synthetic_only=True, accept_plaintext=True)

    def test_new_store_roundtrip(self):
        report = self.save()
        self.assertGreater(report["new_chunks"], 0)
        self.assertEqual(report["new_chunks"], report["chunks"])
        restored = self.restore(report)
        self.assertEqual(restored["status"], "RESTORED_INCREMENTAL_SYNTHETIC_ONLY")
        self.assertEqual(restored["restored_sha256"], report["snapshot_sha256"])
        self.assertFalse(report["ready_for_customer_data"])
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), self.before)

    def test_second_snapshot_reuses_all_existing_content(self):
        one = self.save()
        two = self.save()
        self.assertEqual(two["new_chunks"], 0)
        self.assertEqual(two["reused_chunks"], one["chunks"])
        self.assertNotEqual(one["manifest_name"], two["manifest_name"])
        self.assertEqual(self.restore(two)["restored_sha256"], one["snapshot_sha256"])

    def test_changed_fixture_preserves_both_versions(self):
        old = self.save()
        with closing(sqlite3.connect(self.db)) as db:
            db.execute("CREATE TABLE added_table(id INTEGER PRIMARY KEY)")
            db.commit()
        new_snapshot = Path(create_snapshot(self.db, self.snap)["snapshot_path"])
        new = self.save(new_snapshot)
        self.assertNotEqual(old["snapshot_sha256"], new["snapshot_sha256"])
        self.assertEqual(self.restore(old)["restored_sha256"], old["snapshot_sha256"])
        self.assertEqual(self.restore(new)["restored_sha256"], new["snapshot_sha256"])

    def test_corrupt_or_missing_chunk_denies_restore_without_new_sqlite(self):
        report = self.save()
        manifest = cas._strict_manifest((self.manifest / report["manifest_name"]).read_bytes())
        first = self.chunks / (manifest["chunks"][0] + ".chunk")
        first.write_bytes(b"tampered")
        with self.assertRaises(cas.IncrementalError):
            self.restore(report)
        first.unlink()
        with self.assertRaises(cas.IncrementalError):
            self.restore(report)
        self.assertEqual(list(self.restored.iterdir()), [])

    def test_duplicate_json_property_rejected(self):
        report = self.save()
        (self.manifest / report["manifest_name"]).write_text(
            '{"contract":"a","contract":"b"}', encoding="utf-8")
        with self.assertRaises(cas.IncrementalError):
            self.restore(report)

    def test_acknowledgment_and_separate_directories_required(self):
        with self.assertRaisesRegex(cas.IncrementalError, "SYNTHETIC_ONLY_REQUIRED"):
            cas.create_incremental(self.source, self.chunks, self.manifest,
                                   accept_plaintext=True)
        with self.assertRaisesRegex(cas.IncrementalError, "PLAINTEXT_ACK_REQUIRED"):
            cas.create_incremental(self.source, self.chunks, self.manifest,
                                   synthetic_only=True)
        with self.assertRaisesRegex(cas.IncrementalError, "SEPARATE_DIRECTORIES_REQUIRED"):
            cas.create_incremental(self.source, self.snap, self.manifest,
                                   synthetic_only=True, accept_plaintext=True)
        self.assertEqual(list(self.chunks.iterdir()), [])

    def test_manifest_never_contains_customer_paths_or_rows(self):
        record = self.save()
        text = (self.manifest / record["manifest_name"]).read_text(encoding="utf-8")
        self.assertNotIn(str(self.db), text)
        self.assertNotIn(str(self.root), text)
        self.assertNotIn("NOT_FOR_SCHEMA_OUTPUT", text)
        self.assertFalse(record["automatic_deletion"])


if __name__ == "__main__":
    unittest.main()
