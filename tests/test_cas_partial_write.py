"""Synthetic-only staged short-write injection for compressed CAS v2.

No customer file is opened. Tests operate in temporary SQLite fixtures.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import compressed_cas as cas
from dbvora.archive.safe_zip import create_snapshot
from tests.fixtures.make_sqlite import create_fixture


class CasPartialWriteTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="dbvora-cas-short-write-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.database = create_fixture(root / "synthetic.sqlite")
        self.snapshot_dir = root / "snapshots"
        self.chunks = root / "chunks"
        self.manifests = root / "manifests"
        self.restored = root / "restored"
        for directory in (self.snapshot_dir, self.chunks, self.manifests, self.restored):
            directory.mkdir()
        self.snapshot = Path(
            create_snapshot(self.database, self.snapshot_dir)["snapshot_path"])
        self.database_sha = hashlib.sha256(self.database.read_bytes()).hexdigest()
        self.snapshot_sha = hashlib.sha256(self.snapshot.read_bytes()).hexdigest()

    def create(self):
        return cas.create_compressed(
            self.snapshot, self.chunks, self.manifests,
            synthetic_only=True, accept_plaintext=True)

    def restore(self, saved):
        return cas.restore_compressed(
            self.manifests / saved["manifest_name"], self.chunks,
            self.restored, synthetic_only=True, accept_plaintext=True)

    def assert_sources_unchanged(self):
        self.assertEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(),
                         self.database_sha)
        self.assertEqual(hashlib.sha256(self.snapshot.read_bytes()).hexdigest(),
                         self.snapshot_sha)

    def test_partial_chunk_write_never_publishes_file_or_manifest(self):
        write = Path.write_bytes

        def short_write(path, payload):
            return write(path, payload[:len(payload) // 2])

        with patch.object(Path, "write_bytes", short_write):
            with self.assertRaisesRegex(cas.CompressedCasError,
                                        "STAGED_WRITE_UNVERIFIED"):
                self.create()
        self.assertEqual(list(self.chunks.iterdir()), [])
        self.assertEqual(list(self.manifests.iterdir()), [])
        self.assert_sources_unchanged()

    def test_partial_manifest_write_keeps_previous_generation_restorable(self):
        old = self.create()
        before = (self.manifests / old["manifest_name"]).read_bytes()
        write = Path.write_bytes

        injected = [0]

        def short_manifest(path, payload):
            # Identify manifest bytes by contract, not OS-dependent Path
            # identity/casing. A non-firing injection must never pass silently.
            if cas.CONTRACT.encode("ascii") in payload:
                injected[0] += 1
                return write(path, payload[:len(payload) // 2])
            return write(path, payload)

        with patch.object(Path, "write_bytes", short_manifest):
            with self.assertRaisesRegex(cas.CompressedCasError,
                                        "STAGED_WRITE_UNVERIFIED"):
                self.create()
        self.assertEqual(injected[0], 1)
        self.assertEqual([x.name for x in self.manifests.iterdir()],
                         [old["manifest_name"]])
        self.assertEqual((self.manifests / old["manifest_name"]).read_bytes(),
                         before)
        self.assertEqual(self.restore(old)["restored_sha256"],
                         old["snapshot_sha256"])
        self.assertEqual(list(self.chunks.glob(".dbvora-incomplete-*.part")), [])
        self.assert_sources_unchanged()

    def test_lying_full_length_write_is_caught_by_readback(self):
        write = Path.write_bytes

        def falsely_complete(path, payload):
            write(path, payload[:len(payload) // 2])
            return len(payload)

        with patch.object(Path, "write_bytes", falsely_complete):
            with self.assertRaisesRegex(cas.CompressedCasError,
                                        "STAGED_WRITE_UNVERIFIED"):
                self.create()
        self.assertEqual(list(self.chunks.iterdir()), [])
        self.assertEqual(list(self.manifests.iterdir()), [])
        self.assert_sources_unchanged()


if __name__ == "__main__":
    unittest.main()
