"""Synthetic-only tests for read-only CAS retention planning."""
from __future__ import annotations

from contextlib import closing, redirect_stderr
import hashlib
import io
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import compressed_cas, retention_preview
from dbvora.archive.safe_zip import create_snapshot
from tests.fixtures.make_sqlite import create_fixture


class RetentionPreviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dbvora-cas-retention-test-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.db = create_fixture(root / "source.sqlite")
        self.snapshots = root / "snapshots"
        self.chunks = root / "chunks"
        self.manifests = root / "manifests"
        for folder in (self.snapshots, self.chunks, self.manifests):
            folder.mkdir()
        self.snapshot = Path(create_snapshot(self.db, self.snapshots)["snapshot_path"])
        self.first = self._create(self.snapshot)

    def _create(self, snapshot):
        return compressed_cas.create_compressed(
            snapshot, self.chunks, self.manifests,
            synthetic_only=True, accept_plaintext=True)

    def _add_changed_generation(self):
        with closing(sqlite3.connect(self.db)) as con:
            con.execute("CREATE TABLE synthetic_generation_2(id INTEGER PRIMARY KEY)")
            con.commit()
        snapshot = Path(create_snapshot(self.db, self.snapshots)["snapshot_path"])
        return self._create(snapshot)

    def _preview(self, keep=1):
        return retention_preview.preview(
            self.chunks, self.manifests, keep_generations=keep,
            synthetic_only=True, accept_plaintext=True)

    def _tree_bytes(self):
        return {
            folder.name + "/" + path.name: path.read_bytes()
            for folder in (self.chunks, self.manifests)
            for path in folder.iterdir()
            if path.is_file() and not path.is_symlink()
        }

    def test_healthy_preview_suggests_old_manifest_and_estimates_unique_bytes(self):
        second = self._add_changed_generation()
        old = self.manifests / self.first["manifest_name"]
        new = self.manifests / second["manifest_name"]
        os.utime(old, ns=(1_000_000_000, 1_000_000_000))
        os.utime(new, ns=(2_000_000_000, 2_000_000_000))
        before = self._tree_bytes()
        report = self._preview(keep=1)
        self.assertEqual(report["status"], "PREVIEW_READY")
        self.assertFalse(report["generation_order_trusted"])
        self.assertEqual(report["ordering_basis"], "filesystem_mtime_ns_untrusted")
        self.assertEqual(report["retention_suggestions"], [self.first["manifest_name"]])
        self.assertEqual(report["retained_preview_manifest_names"], [second["manifest_name"]])
        first_doc = compressed_cas._parse_manifest(old.read_bytes())
        second_doc = compressed_cas._parse_manifest(new.read_bytes())
        old_only_chunks = set(first_doc["chunks"]) - set(second_doc["chunks"])
        expected = old.stat().st_size + sum(
            (self.chunks / (key + ".cz")).stat().st_size for key in old_only_chunks)
        self.assertEqual(report["estimated_reclaimable_bytes"], expected)
        self.assertFalse(report["automatic_deletion"])
        self.assertFalse(report["deletion_enabled"])
        self.assertTrue(report["inventory_stable_during_preview"])
        self.assertEqual(before, self._tree_bytes())

    def test_orphan_is_listed_but_forces_hold_and_no_suggestion(self):
        payload = b"synthetic orphan only"
        name = hashlib.sha256(payload).hexdigest() + ".cz"
        orphan = self.chunks / name
        orphan.write_bytes(payload)
        before = self._tree_bytes()
        report = self._preview()
        self.assertEqual(report["status"], "HOLD_MANUAL_REVIEW")
        self.assertEqual(report["unreferenced_chunk_names"], [name])
        self.assertEqual(report["retention_suggestions"], [])
        self.assertIsNone(report["estimated_reclaimable_bytes"])
        self.assertEqual(before, self._tree_bytes())

    def test_missing_chunk_holds_without_suggesting_any_removal(self):
        record = compressed_cas._parse_manifest(
            (self.manifests / self.first["manifest_name"]).read_bytes())
        (self.chunks / (record["chunks"][0] + ".cz")).unlink()
        before = self._tree_bytes()
        report = self._preview()
        self.assertEqual(report["status"], "HOLD_DAMAGED_OR_MISSING")
        self.assertEqual(report["retention_suggestions"], [])
        self.assertIsNone(report["estimated_reclaimable_bytes"])
        self.assertEqual(before, self._tree_bytes())

    def test_equal_mtimes_hold_ambiguous_order_without_suggestions(self):
        second = self._add_changed_generation()
        for name in (self.first["manifest_name"], second["manifest_name"]):
            os.utime(self.manifests / name, ns=(3_000_000_000, 3_000_000_000))
        before = self._tree_bytes()
        report = self._preview(keep=1)
        self.assertEqual(report["status"], "HOLD_AMBIGUOUS_ORDER")
        self.assertEqual(report["retention_suggestions"], [])
        self.assertIsNone(report["estimated_reclaimable_bytes"])
        self.assertEqual(before, self._tree_bytes())

    def test_mutation_during_preview_holds_and_never_proposes_removal(self):
        real_audit = retention_preview.cas_audit.audit
        orphan = self.chunks / (hashlib.sha256(b"changed during preview").hexdigest() + ".cz")

        def mutate_after_audit(*args, **kwargs):
            result = real_audit(*args, **kwargs)
            orphan.write_bytes(b"synthetic mutation")
            return result

        with patch.object(retention_preview.cas_audit, "audit", side_effect=mutate_after_audit):
            report = self._preview()
        self.assertEqual(report["status"], "HOLD_STORE_CHANGED")
        self.assertFalse(report["inventory_stable_during_preview"])
        self.assertEqual(report["retention_suggestions"], [])
        self.assertTrue(orphan.exists())

    def test_required_ack_and_safe_cli_errors_do_not_leak_paths(self):
        with self.assertRaisesRegex(retention_preview.RetentionPreviewError,
                                   "SYNTHETIC_ONLY_REQUIRED"):
            retention_preview.preview(self.chunks, self.manifests,
                                      keep_generations=1,
                                      accept_plaintext=True)
        secret = "C:\\client-secret\\database.sqlite"
        with redirect_stderr(io.StringIO()) as output:
            code = retention_preview.main([
                "--chunk-dir", secret, "--manifest-dir", str(self.manifests),
                "--keep-generations", "1", "--accept-plaintext"])
        self.assertEqual(code, 2)
        self.assertNotIn(secret, output.getvalue())
        with self.assertRaisesRegex(retention_preview.RetentionPreviewError,
                                   "INVALID_KEEP_GENERATIONS"):
            retention_preview.preview(self.chunks, self.manifests,
                                      keep_generations=0, synthetic_only=True,
                                      accept_plaintext=True)


if __name__ == "__main__":
    unittest.main()
