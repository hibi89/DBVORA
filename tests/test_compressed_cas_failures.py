"""Synthetic-only fault injection. Never uses or deletes actual customer data."""
from __future__ import annotations
from contextlib import closing
import errno
import hashlib
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import compressed_cas as cas
from dbvora.archive.safe_zip import ArchiveError, create_snapshot
from tests.fixtures.make_sqlite import create_fixture


class CompressedCasFailureTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dbvora-cas-fault-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.source = create_fixture(root / "synthetic.sqlite")
        self.snap, self.chunks, self.manifests, self.output = (
            root / part for part in ("snap", "chunks", "manifests", "output"))
        for directory in (self.snap, self.chunks, self.manifests, self.output):
            directory.mkdir()
        self.snapshot = Path(create_snapshot(self.source, self.snap)["snapshot_path"])
        self.original_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.original_mtime = self.source.stat().st_mtime_ns

    def create(self, snapshot=None):
        return cas.create_compressed(
            snapshot or self.snapshot, self.chunks, self.manifests,
            synthetic_only=True, accept_plaintext=True)

    def restore(self, item):
        return cas.restore_compressed(
            self.manifests / item["manifest_name"], self.chunks, self.output,
            synthetic_only=True, accept_plaintext=True)

    def check_source(self):
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.original_hash)
        self.assertEqual(self.source.stat().st_mtime_ns, self.original_mtime)

    def test_enospc_before_first_chunk_does_not_publish_manifest(self):
        with patch.object(cas, "_sync_staged_file", side_effect=OSError(errno.ENOSPC, "synthetic")):
            with self.assertRaisesRegex(cas.CompressedCasError, "CHUNK_PUBLISH_UNVERIFIED"):
                self.create()
        self.assertEqual(list(self.manifests.iterdir()), [])
        self.assertEqual(list(self.chunks.glob("*.cz")), [])
        self.check_source()

    def test_new_generation_enospc_preserves_old_restorable_generation(self):
        first = self.create()
        with closing(sqlite3.connect(self.source)) as conn:
            conn.execute("CREATE TABLE injected_delta(id INTEGER PRIMARY KEY, content BLOB)")
            conn.execute("INSERT INTO injected_delta VALUES (1, ?)", (bytes(range(256)) * 300,))
            conn.commit()
        second = Path(create_snapshot(self.source, self.snap)["snapshot_path"])
        existing = sorted(p.name for p in self.manifests.iterdir())
        with patch.object(cas, "_sync_staged_file", side_effect=OSError(errno.ENOSPC, "synthetic")):
            with self.assertRaises(cas.CompressedCasError):
                self.create(second)
        self.assertEqual(existing, sorted(p.name for p in self.manifests.iterdir()))
        self.assertEqual(self.restore(first)["restored_sha256"], first["snapshot_sha256"])

    def test_manifest_publish_failure_preserves_prior_manifest(self):
        first = self.create()
        manifest = self.manifests / first["manifest_name"]
        payload = manifest.read_bytes()
        with patch.object(cas, "_publish_new", side_effect=ArchiveError("INJECTED_FAILED", "synthetic")):
            with self.assertRaisesRegex(cas.CompressedCasError, "COMPRESSED_CREATE_FAILED"):
                self.create()
        self.assertEqual(manifest.read_bytes(), payload)
        self.assertEqual(len(list(self.manifests.glob("dbvora-*.json"))), 1)
        self.assertEqual(self.restore(first)["restored_sha256"], first["snapshot_sha256"])
        self.check_source()

    def test_source_hash_change_before_manifest_publication_holds(self):
        with patch.object(cas, "_hash_file", return_value=("f" * 64, 0)):
            with self.assertRaisesRegex(cas.CompressedCasError, "SOURCE_CHANGED"):
                self.create()
        self.assertEqual(list(self.manifests.glob("*.json")), [])
        self.check_source()

    def test_restore_fsync_enospc_retains_last_successful_file(self):
        saved = self.create()
        good = self.restore(saved)
        previous = self.output / good["restored_name"]
        digest = hashlib.sha256(previous.read_bytes()).hexdigest()
        with patch.object(cas.os, "fsync", side_effect=OSError(errno.ENOSPC, "synthetic")):
            with self.assertRaisesRegex(cas.CompressedCasError, "COMPRESSED_RESTORE_FAILED"):
                self.restore(saved)
        self.assertEqual(len(list(self.output.glob("dbvora-*.sqlite"))), 1)
        self.assertEqual(hashlib.sha256(previous.read_bytes()).hexdigest(), digest)
        self.check_source()

    def test_restore_publish_failure_preserves_previous_good_result(self):
        saved = self.create()
        good = self.restore(saved)
        previous = self.output / good["restored_name"]
        digest = hashlib.sha256(previous.read_bytes()).hexdigest()
        with patch.object(cas, "_publish_new", side_effect=ArchiveError("INJECTED_FAILED", "synthetic")):
            with self.assertRaisesRegex(cas.CompressedCasError, "COMPRESSED_RESTORE_FAILED"):
                self.restore(saved)
        self.assertEqual(len(list(self.output.glob("dbvora-*.sqlite"))), 1)
        self.assertEqual(hashlib.sha256(previous.read_bytes()).hexdigest(), digest)
        self.check_source()

    def test_missing_chunk_fails_closed_without_erasing_manifest(self):
        saved = self.create()
        manifest = self.manifests / saved["manifest_name"]
        entry = cas._parse_manifest(manifest.read_bytes())
        (self.chunks / (entry["chunks"][0] + ".cz")).unlink()
        with self.assertRaisesRegex(cas.CompressedCasError, "CHUNK_UNAVAILABLE"):
            self.restore(saved)
        self.assertTrue(manifest.is_file())
        self.assertEqual(list(self.output.glob("dbvora-*.sqlite")), [])
        self.check_source()

    def test_hardlinked_chunk_is_refused_without_migration(self):
        saved = self.create()
        entry = cas._parse_manifest(
            (self.manifests / saved["manifest_name"]).read_bytes())
        chunk = self.chunks / (entry["chunks"][0] + ".cz")
        linked = self.chunks / "synthetic-other-link"
        try:
            os.link(chunk, linked)
        except (OSError, NotImplementedError):
            self.skipTest("hardlink not supported by temporary test filesystem")
        with self.assertRaisesRegex(cas.CompressedCasError, "INVALID_CHUNK_FILE"):
            self.restore(saved)
        self.assertTrue(linked.exists())
        self.assertEqual(list(self.output.glob("dbvora-*.sqlite")), [])
        self.check_source()


if __name__ == "__main__":
    unittest.main()
