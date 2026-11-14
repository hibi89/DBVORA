"""P1-C5: offline command smoke using ONLY generated SQLite fixtures."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from dbvora.archive_cli import main
from tests.fixtures.make_sqlite import create_fixture


class ArchiveCliTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dbvora-cli-synthetic-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = create_fixture(self.root / "fixture.sqlite")
        self.snapshots = self.root / "snapshots"
        self.artifacts = self.root / "archives"
        self.restores = self.root / "restored"
        for directory in (self.snapshots, self.artifacts, self.restores):
            directory.mkdir()
        self.file_hash_before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.mtime_before = self.source.stat().st_mtime_ns

    def run_cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(list(args))
        raw = stdout.getvalue() if code == 0 else stderr.getvalue()
        return code, json.loads(raw), raw

    def test_roundtrip_and_signed_warning_audit_without_source_mutation(self):
        code, snap, raw = self.run_cli("snapshot", "--source", str(self.source),
                         "--output-dir", str(self.snapshots), "--synthetic-only", "--accept-plaintext")
        self.assertEqual(code, 0)
        self.assertNotIn(str(self.source), raw)
        snapshot = self.snapshots / snap["result"]["snapshot_path"]
        self.assertTrue(snapshot.is_file())

        code, arc, _ = self.run_cli("archive", "--snapshot", str(snapshot),
                         "--output-dir", str(self.artifacts), "--codec", "zip",
                         "--synthetic-only", "--accept-plaintext")
        self.assertEqual(code, 0)
        artifact = self.artifacts / arc["result"]["archive_path"]
        self.assertTrue(artifact.is_file())

        code, receipt, _ = self.run_cli("receipt", "--artifact", str(artifact),
                         "--synthetic-only", "--accept-unsigned")
        self.assertEqual(code, 0)
        self.assertEqual(receipt["result"]["authentication"], "unsigned_untrusted")

        code, restored, _ = self.run_cli("restore", "--archive", str(artifact),
                               "--output-dir", str(self.restores),
                               "--synthetic-only", "--accept-plaintext")
        self.assertEqual(code, 0)
        self.assertEqual(hashlib.sha256((self.restores / restored["result"]["restored_path"]).read_bytes()).hexdigest(),
                         snap["result"]["snapshot_sha256"])

        code, audit, _ = self.run_cli("audit", "--output-dir", str(self.artifacts))
        self.assertEqual(code, 0)
        statuses = {record["name"]: record["status"] for record in audit["result"]["records"]}
        self.assertEqual(statuses[artifact.name], "RECORDED_AND_CONTENT_VERIFIED_UNSIGNED")
        self.assertEqual(self.file_hash_before, hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(self.mtime_before, self.source.stat().st_mtime_ns)


    def _create_zip(self):
        code, snapshot, _ = self.run_cli(
            "snapshot", "--source", str(self.source), "--output-dir", str(self.snapshots),
            "--synthetic-only", "--accept-plaintext",
        )
        self.assertEqual(code, 0)
        snapshot_path = self.snapshots / snapshot["result"]["snapshot_path"]
        code, archive, _ = self.run_cli(
            "archive", "--snapshot", str(snapshot_path), "--output-dir", str(self.artifacts),
            "--codec", "zip", "--synthetic-only", "--accept-plaintext",
        )
        self.assertEqual(code, 0)
        return snapshot["result"], self.artifacts / archive["result"]["archive_path"]

    def test_preview_binds_restore_to_hashes_and_new_output(self):
        snapshot, artifact = self._create_zip()
        artifact_before = hashlib.sha256(artifact.read_bytes()).hexdigest()
        code, preview, raw = self.run_cli(
            "preview", "--archive-dir", str(self.artifacts),
            "--synthetic-only", "--accept-plaintext",
        )
        self.assertEqual(code, 0)
        self.assertNotIn(str(self.artifacts), raw)
        records = preview["result"]["records"]
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["status"], "CONTENT_VERIFIED_PUBLISH_UNPROVEN")
        self.assertEqual(record["snapshot_sha256"], snapshot["snapshot_sha256"])
        self.assertEqual(record["artifact_sha256"], artifact_before)

        code, restored, raw = self.run_cli(
            "restore-selected", "--archive", str(artifact),
            "--artifact-sha256", record["artifact_sha256"],
            "--snapshot-sha256", record["snapshot_sha256"],
            "--output-dir", str(self.restores),
            "--synthetic-only", "--accept-plaintext",
        )
        self.assertEqual(code, 0, raw)
        result = restored["result"]
        self.assertTrue(result["selection_verified"])
        restored_path = self.restores / result["restored_path"]
        self.assertTrue(restored_path.is_file())
        self.assertEqual(result["restored_sha256"], snapshot["snapshot_sha256"])
        self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), artifact_before)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.file_hash_before)
        self.assertEqual(self.mtime_before, self.source.stat().st_mtime_ns)

    def test_restore_selected_rejects_stale_preview_and_same_directory(self):
        _, artifact = self._create_zip()
        code, preview, _ = self.run_cli(
            "preview", "--archive-dir", str(self.artifacts),
            "--synthetic-only", "--accept-plaintext",
        )
        self.assertEqual(code, 0)
        record = preview["result"]["records"][0]
        code, error, _ = self.run_cli(
            "restore-selected", "--archive", str(artifact),
            "--artifact-sha256", "0" * 64,
            "--snapshot-sha256", record["snapshot_sha256"],
            "--output-dir", str(self.restores),
            "--synthetic-only", "--accept-plaintext",
        )
        self.assertEqual(code, 2)
        self.assertEqual(error["error"]["code"], "SELECTION_CHANGED")
        self.assertEqual(list(self.restores.iterdir()), [])

        artifact.write_bytes(artifact.read_bytes() + b"post-preview-change")
        code, error, _ = self.run_cli(
            "restore-selected", "--archive", str(artifact),
            "--artifact-sha256", record["artifact_sha256"],
            "--snapshot-sha256", record["snapshot_sha256"],
            "--output-dir", str(self.restores),
            "--synthetic-only", "--accept-plaintext",
        )
        self.assertEqual(code, 2)
        self.assertEqual(error["error"]["code"], "SELECTION_CHANGED")
        self.assertEqual(list(self.restores.iterdir()), [])

        code, error, _ = self.run_cli(
            "restore-selected", "--archive", str(artifact),
            "--artifact-sha256", record["artifact_sha256"],
            "--snapshot-sha256", record["snapshot_sha256"],
            "--output-dir", str(self.artifacts),
            "--synthetic-only", "--accept-plaintext",
        )
        self.assertEqual(code, 2)
        self.assertEqual(error["error"]["code"], "SEPARATE_OUTPUT_REQUIRED")
        self.assertEqual(list(self.artifacts.glob("dbvora-*.sqlite")), [])

    def test_restore_zip_expected_preview_hash_stops_before_publish(self):
        from dbvora.archive.safe_zip import ArchiveError, restore_zip_archive

        _, artifact = self._create_zip()
        with self.assertRaises(ArchiveError) as raised:
            restore_zip_archive(artifact, self.restores, expected_snapshot_sha256="0" * 64)
        self.assertEqual(raised.exception.code, "HASH_MISMATCH")
        self.assertEqual(list(self.restores.iterdir()), [])

    def test_no_confirmation_produces_no_artifacts(self):
        code, err, _ = self.run_cli("snapshot", "--source", str(self.source),
                                    "--output-dir", str(self.snapshots), "--accept-plaintext")
        self.assertEqual(code, 2)
        self.assertEqual(err["error"]["code"], "SYNTHETIC_ONLY_REQUIRED")
        self.assertEqual(list(self.snapshots.iterdir()), [])

    def test_plaintext_confirmation_mandatory(self):
        code, err, _ = self.run_cli("snapshot", "--source", str(self.source),
                                    "--output-dir", str(self.snapshots), "--synthetic-only")
        self.assertEqual(code, 2)
        self.assertEqual(err["error"]["code"], "PLAINTEXT_ACK_REQUIRED")
        self.assertEqual(list(self.snapshots.iterdir()), [])

    def test_separate_source_and_output_required(self):
        code, err, _ = self.run_cli("snapshot", "--source", str(self.source),
                                    "--output-dir", str(self.root), "--synthetic-only", "--accept-plaintext")
        self.assertEqual(code, 2)
        self.assertEqual(err["error"]["code"], "SEPARATE_OUTPUT_REQUIRED")

    def test_archive_rejects_untracked_sqlite_source(self):
        code, err, _ = self.run_cli("archive", "--snapshot", str(self.source),
                                    "--output-dir", str(self.artifacts), "--codec", "zip",
                                    "--synthetic-only", "--accept-plaintext")
        self.assertEqual(code, 2)
        self.assertEqual(err["error"]["code"], "GENERATED_ARTIFACT_REQUIRED")

    def test_zip_rejects_level_override_without_writing(self):
        code, snapshot, _ = self.run_cli("snapshot", "--source", str(self.source),
                                        "--output-dir", str(self.snapshots),
                                        "--synthetic-only", "--accept-plaintext")
        self.assertEqual(code, 0)
        code, err, _ = self.run_cli("archive", "--snapshot", str(self.snapshots / snapshot["result"]["snapshot_path"]),
                                    "--output-dir", str(self.artifacts), "--codec", "zip", "--level", "9",
                                    "--synthetic-only", "--accept-plaintext")
        self.assertEqual(code, 2)
        self.assertEqual(err["error"]["code"], "UNSUPPORTED_LEVEL")
        self.assertFalse(list(self.artifacts.iterdir()))

    def test_source_path_not_echoed_on_invalid_argument(self):
        private = str(self.source) + "-private-test"
        code, error, raw = self.run_cli("snapshot", "--source", private,
                                        "--output-dir", str(self.snapshots), "--synthetic-only",
                                        "--accept-plaintext", "--unexpected-option")
        self.assertEqual(code, 2)
        self.assertEqual(error["error"]["code"], "INVALID_ARGUMENT")
        self.assertNotIn(private, raw)

    def test_repeat_creates_distinct_new_artifacts_no_overwrite(self):
        code, first, _ = self.run_cli("snapshot", "--source", str(self.source),
                                      "--output-dir", str(self.snapshots),
                                      "--synthetic-only", "--accept-plaintext")
        code2, second, _ = self.run_cli("snapshot", "--source", str(self.source),
                                        "--output-dir", str(self.snapshots),
                                        "--synthetic-only", "--accept-plaintext")
        self.assertEqual((code, code2), (0, 0))
        self.assertNotEqual(first["result"]["snapshot_path"], second["result"]["snapshot_path"])
        self.assertEqual(first["result"]["snapshot_sha256"], second["result"]["snapshot_sha256"])
        self.assertEqual(len(list(self.snapshots.glob("dbvora-*.sqlite"))), 2)

    @unittest.skipUnless(shutil.which("zstd"), "optional external zstd executable unavailable")
    def test_zstd_roundtrip_when_optional_codec_exists(self):
        code, snap, _ = self.run_cli("snapshot", "--source", str(self.source),
                                     "--output-dir", str(self.snapshots), "--synthetic-only", "--accept-plaintext")
        self.assertEqual(code, 0)
        code, arc, _ = self.run_cli("archive", "--snapshot", str(self.snapshots / snap["result"]["snapshot_path"]),
                                    "--output-dir", str(self.artifacts), "--codec", "zstd", "--level", "3",
                                    "--synthetic-only", "--accept-plaintext")
        self.assertEqual(code, 0)
        artifact = self.artifacts / arc["result"]["archive_path"]
        code, preview, _ = self.run_cli("preview", "--archive-dir", str(self.artifacts),
                                        "--synthetic-only", "--accept-plaintext")
        self.assertEqual(code, 0)
        record = preview["result"]["records"][0]
        code, restored, _ = self.run_cli(
            "restore-selected", "--archive", str(artifact),
            "--artifact-sha256", record["artifact_sha256"],
            "--snapshot-sha256", record["snapshot_sha256"],
            "--output-dir", str(self.restores),
            "--synthetic-only", "--accept-plaintext",
        )
        self.assertEqual(code, 0)
        self.assertEqual(snap["result"]["snapshot_sha256"], restored["result"]["restored_sha256"])


if __name__ == "__main__":
    unittest.main()
