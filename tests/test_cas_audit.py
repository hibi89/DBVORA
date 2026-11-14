"""Read-only, bounded synthetic zlib CAS inventory: valid, missing, orphan, attack."""
from __future__ import annotations
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from dbvora.archive import cas_audit, compressed_cas
from dbvora.archive.safe_zip import create_snapshot
from tests.fixtures.make_sqlite import create_fixture


class CasAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="dbvora-cas-audit-test-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.db = create_fixture(root / "fixture.sqlite")
        self.snap, self.chunks, self.manifests = (
            root / name for name in ("snap", "chunks", "manifests"))
        for p in (self.snap, self.chunks, self.manifests):
            p.mkdir()
        self.snapshot = Path(create_snapshot(self.db, self.snap)["snapshot_path"])
        self.saved = compressed_cas.create_compressed(
            self.snapshot, self.chunks, self.manifests,
            synthetic_only=True, accept_plaintext=True)
        self.manifest = self.manifests / self.saved["manifest_name"]
        self.manifest_bytes = self.manifest.read_bytes()

    def inspect(self):
        return cas_audit.audit(self.chunks, self.manifests, synthetic_only=True)

    def test_valid_store_verifies_full_snapshot_without_creating_files(self):
        before = sorted(p.name for p in self.chunks.iterdir())
        report = self.inspect()
        self.assertEqual(report["status"], "PASS_SYNTHETIC_CAS_AUDIT_ONLY")
        self.assertEqual(report["verified_generation_count"], 1)
        self.assertGreater(report["referenced_unique_chunks"], 0)
        self.assertFalse(report["automatic_deletion"])
        self.assertFalse(report["new_files_created"])
        self.assertEqual(self.manifest.read_bytes(), self.manifest_bytes)
        self.assertEqual(before, sorted(p.name for p in self.chunks.iterdir()))

    def test_repeated_manifest_reuses_same_content_without_orphans(self):
        compressed_cas.create_compressed(
            self.snapshot, self.chunks, self.manifests,
            synthetic_only=True, accept_plaintext=True)
        r = self.inspect()
        self.assertEqual(r["verified_generation_count"], 2)
        self.assertEqual(r["status"], "PASS_SYNTHETIC_CAS_AUDIT_ONLY")

    def test_missing_chunk_fails_closed_and_does_not_purge_manifest(self):
        key = compressed_cas._parse_manifest(self.manifest_bytes)["chunks"][0]
        (self.chunks / (key + ".cz")).unlink()  # synthetic disposable fixture only
        r = self.inspect()
        self.assertEqual(r["status"], "HOLD_DAMAGED_OR_MISSING")
        self.assertEqual(r["missing_chunk_count"], 1)
        self.assertEqual(r["verified_generation_count"], 0)
        self.assertEqual(self.manifest.read_bytes(), self.manifest_bytes)

    def test_invalid_chunk_fails_closed(self):
        key = compressed_cas._parse_manifest(self.manifest_bytes)["chunks"][0]
        (self.chunks / (key + ".cz")).write_bytes(b"tampered")
        r = self.inspect()
        self.assertEqual(r["status"], "HOLD_DAMAGED_OR_MISSING")
        self.assertGreater(r["invalid_generation_count"], 0)
        self.assertEqual(r["missing_chunk_count"], 0)

    def test_orphan_candidate_flags_manual_review_without_deleting(self):
        untouched = self.chunks / ("a" * 64 + ".cz")
        untouched.write_bytes(b"synthetic-orphan")
        r = self.inspect()
        self.assertEqual(r["unreferenced_chunk_count"], 1)
        self.assertEqual(r["status"], "HOLD_MANUAL_REVIEW")
        self.assertEqual(untouched.read_bytes(), b"synthetic-orphan")

    def test_unrecognized_staging_files_hold_manual_review(self):
        stray = self.chunks / "pending.staged"
        stray.write_bytes(b"orphaned-synthetic-test")
        r = self.inspect()
        self.assertEqual(r["status"], "HOLD_MANUAL_REVIEW")
        self.assertGreaterEqual(r["unrecognized_file_count"], 1)
        self.assertTrue(stray.exists())

    def test_invalid_duplicate_manifest_key_rejected_without_edit(self):
        self.manifest.write_bytes(b'{"contract":"x","contract":"y"}')
        with self.assertRaisesRegex(cas_audit.CasAuditError, "INVALID_MANIFEST"):
            self.inspect()
        self.assertEqual(self.manifest.read_bytes(), b'{"contract":"x","contract":"y"}')

    def test_symlink_directory_or_file_denied(self):
        alias = self.snap / "alias"
        try:
            alias.symlink_to(self.chunks, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink requires elevated permissions on this runner")
        with self.assertRaisesRegex(cas_audit.CasAuditError, "UNTRUSTED_DIRECTORY"):
            cas_audit.audit(alias, self.manifests, synthetic_only=True)
        foreign = self.chunks / "shortcut.cz"
        foreign.symlink_to(self.manifest)
        with self.assertRaisesRegex(cas_audit.CasAuditError, "UNTRUSTED_ENTRY"):
            self.inspect()

    def test_missing_ack_or_relative_paths_never_scan(self):
        with self.assertRaisesRegex(cas_audit.CasAuditError, "SYNTHETIC_ONLY_REQUIRED"):
            cas_audit.audit(self.chunks, self.manifests)
        with self.assertRaisesRegex(cas_audit.CasAuditError, "INVALID_DIRECTORY"):
            cas_audit.audit("relative", self.manifests, synthetic_only=True)

    def test_cli_invalid_argument_never_leaks_path_or_password(self):
        secret = "C:\\client-secret\\database.sqlite"
        with redirect_stderr(io.StringIO()) as output:
            code = cas_audit.main(["--chunk-dir", secret, "--manifest-dir",
                                   str(self.manifests), "--synthetic-only"])
        self.assertEqual(code, 2)
        self.assertNotIn(secret, output.getvalue())
        with redirect_stderr(io.StringIO()) as output:
            code = cas_audit.main(["--unknown", secret])
        self.assertEqual(code, 2)
        self.assertNotIn(secret, output.getvalue())

    def test_manifest_and_chunk_output_directories_separate(self):
        with self.assertRaisesRegex(cas_audit.CasAuditError, "SEPARATE_DIRECTORIES_REQUIRED"):
            cas_audit.audit(self.chunks, self.chunks, synthetic_only=True)


if __name__ == "__main__":
    unittest.main()
