"""Synthetic-only multi-generation CAS v2 recovery and orphan safety tests.

These are temporary disposable SQLite fixtures, not customer backup tests.
No automatic cleanup of retained chunks or generations is permitted.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import cas_audit, compressed_cas as cas
from dbvora.archive.safe_zip import ArchiveError, create_snapshot
from tests.fixtures.make_sqlite import create_fixture


class CasGenerationLifecycleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dbvora-cas-lifecycle-synthetic-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.db = create_fixture(root / "synthetic.sqlite")
        self.snapshots, self.chunks, self.manifests, self.restored = (
            root / name for name in ("snapshots", "chunks", "manifests", "restored"))
        for directory in (self.snapshots, self.chunks, self.manifests, self.restored):
            directory.mkdir()
        self.source = self.snapshot()

    def snapshot(self):
        return Path(create_snapshot(self.db, self.snapshots)["snapshot_path"])

    def append_synthetic_event(self, serial):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("INSERT INTO events(category, content) VALUES (?, ?)",
                         ("synthetic", f"generation-{serial}-" + "x" * 1200))
            conn.commit()
        self.source = self.snapshot()

    def publish(self):
        return cas.create_compressed(
            self.source, self.chunks, self.manifests,
            synthetic_only=True, accept_plaintext=True)

    def restore(self, saved):
        report = cas.restore_compressed(
            self.manifests / saved["manifest_name"], self.chunks,
            self.restored, synthetic_only=True, accept_plaintext=True)
        restored = self.restored / report["restored_name"]
        self.assertEqual(hashlib.sha256(restored.read_bytes()).hexdigest(),
                         saved["snapshot_sha256"])
        return report

    def inspect(self):
        return cas_audit.audit(self.chunks, self.manifests, synthetic_only=True)

    def keys(self, saved):
        payload = (self.manifests / saved["manifest_name"]).read_bytes()
        return set(cas._parse_manifest(payload)["chunks"])

    def test_four_generations_replay_changed_snapshot_out_of_order_restore(self):
        first = self.publish()
        replay = self.publish()
        self.assertEqual(replay["new_chunks"], 0)
        self.assertEqual(replay["reused_chunks"], first["chunks"])
        self.append_synthetic_event(2)
        second = self.publish()
        self.append_synthetic_event(3)
        third = self.publish()
        snapshots = [first, replay, second, third]
        self.assertEqual(len({s["manifest_name"] for s in snapshots}), 4)
        self.assertEqual(len({s["snapshot_sha256"] for s in snapshots}), 3)
        before = sorted(p.name for p in self.chunks.iterdir())
        audit = self.inspect()
        self.assertEqual(audit["status"], "PASS_SYNTHETIC_CAS_AUDIT_ONLY")
        self.assertEqual(audit["verified_generation_count"], 4)
        self.assertEqual(audit["invalid_generation_count"], 0)
        self.assertEqual(audit["unreferenced_chunk_count"], 0)
        self.assertFalse(audit["automatic_deletion"])
        self.assertFalse(audit["new_files_created"])
        for saved in (third, first, second, replay):
            self.restore(saved)
        self.assertEqual(before, sorted(p.name for p in self.chunks.iterdir()))

    def test_latest_unique_corrupt_chunk_holds_but_old_restore_survives(self):
        old = self.publish()
        self.append_synthetic_event(2)
        newest = self.publish()
        only_new = self.keys(newest) - self.keys(old)
        self.assertTrue(only_new, "new synthetic generation must have unique content")
        broken = self.chunks / (sorted(only_new)[0] + ".cz")
        broken.write_bytes(b"disposable-synthetic-corruption")
        audit = self.inspect()
        self.assertEqual(audit["status"], "HOLD_DAMAGED_OR_MISSING")
        self.assertEqual(audit["verified_generation_count"], 1)
        self.assertEqual(audit["invalid_generation_count"], 1)
        self.restore(old)
        with self.assertRaises(cas.CompressedCasError):
            self.restore(newest)
        self.assertEqual(len(list(self.restored.glob("dbvora-*.sqlite"))), 1)
        self.assertTrue((self.manifests / newest["manifest_name"]).exists())

    def test_failed_new_manifest_is_manual_hold_not_auto_gc(self):
        old = self.publish()
        payload = (self.manifests / old["manifest_name"]).read_bytes()
        self.append_synthetic_event(2)
        with patch.object(cas, "_publish_new",
                          side_effect=ArchiveError("INJECTED_FAILURE", "synthetic")):
            with self.assertRaisesRegex(cas.CompressedCasError,
                                        "COMPRESSED_CREATE_FAILED"):
                self.publish()
        self.assertEqual(sorted(p.name for p in self.manifests.iterdir()),
                         [old["manifest_name"]])
        self.assertEqual((self.manifests / old["manifest_name"]).read_bytes(), payload)
        report = self.inspect()
        self.assertEqual(report["verified_generation_count"], 1)
        self.assertEqual(report["status"], "HOLD_MANUAL_REVIEW")
        self.assertGreater(report["unreferenced_chunk_count"], 0)
        self.restore(old)
        self.assertFalse(report["automatic_deletion"])
        self.assertFalse(report["new_files_created"])


if __name__ == "__main__":
    unittest.main()
