"""P3-02 request/ZIP bridge behavior with disposable synthetic inputs only."""
from contextlib import redirect_stdout
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import request_archive_gate as gate


class RequestArchiveGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="dbvora-p3-gate-test-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_bounded_digest_matches_independent_file_hash(self):
        p = self.root / "artifact.zip"
        p.write_bytes(b"synthetic fixture only")
        self.assertEqual(gate._digest(p), hashlib.sha256(p.read_bytes()).hexdigest())

    def test_missing_artifact_fails_closed(self):
        with self.assertRaisesRegex(gate.GateFailure, "SYNTHETIC_ARTIFACT_UNREADABLE"):
            gate._digest(self.root / "missing.zip")

    def test_directory_is_not_accepted_as_artifact(self):
        with self.assertRaisesRegex(gate.GateFailure, "UNSAFE_SYNTHETIC_ARTIFACT"):
            gate._digest(self.root)

    def test_zero_byte_artifact_is_rejected(self):
        p = self.root / "zero.zip"
        p.touch()
        with self.assertRaisesRegex(gate.GateFailure, "UNSAFE_SYNTHETIC_ARTIFACT"):
            gate._digest(p)

    def test_size_bound_is_enforced(self):
        p = self.root / "oversized.zip"
        p.write_bytes(b"a" * 8)
        with self.assertRaisesRegex(gate.GateFailure, "UNSAFE_SYNTHETIC_ARTIFACT"):
            gate._digest(p, max_bytes=4)

    def test_first_reservation_success_never_claims_executed(self):
        gate._reserve_first(self.root)
        from dbvora.archive.request_ledger import reserve
        self.assertEqual(reserve(self.root, gate.REQUEST_ID, gate.PLAN_SHA)["status"],
                         "REPLAY_REQUIRES_MANUAL_REVIEW")

    def test_duplicate_first_reservation_aborts(self):
        gate._reserve_first(self.root)
        with self.assertRaisesRegex(gate.GateFailure, "REQUEST_RESERVATION_NOT_NEW"):
            gate._reserve_first(self.root)

    def test_injected_interruption_holds_request_without_archive(self):
        report = gate.run_gate(interrupt_after_reserve=True)
        self.assertEqual(report["status"], "PASS_PENDING_REPLAY_HELD_SYNTHETIC_ONLY")
        self.assertFalse(report["archive_executed"])
        self.assertFalse(report["exactly_once_verified"])

    def test_symlinked_archive_is_rejected_without_following_target(self):
        original = self.root / "original.zip"
        original.write_bytes(b"safe fixture")
        linked = self.root / "alias.zip"
        try:
            linked.symlink_to(original)
        except (OSError, NotImplementedError):
            with self.assertRaisesRegex(gate.GateFailure, "SYNTHETIC_ARTIFACT_UNREADABLE"):
                gate._digest(linked)
            return
        with self.assertRaisesRegex(gate.GateFailure, "UNSAFE_SYNTHETIC_ARTIFACT"):
            gate._digest(linked)
        self.assertEqual(original.read_bytes(), b"safe fixture")

    def test_hardlinked_archive_is_rejected(self):
        import os
        original = self.root / "original.zip"
        original.write_bytes(b"same source")
        linked = self.root / "alias.zip"
        try:
            os.link(original, linked)
        except OSError:
            with self.assertRaisesRegex(gate.GateFailure, "SYNTHETIC_ARTIFACT_UNREADABLE"):
                gate._digest(linked)
            return
        with self.assertRaisesRegex(gate.GateFailure, "UNSAFE_SYNTHETIC_ARTIFACT"):
            gate._digest(linked)
        self.assertEqual(original.read_bytes(), b"same source")

    def test_conflicting_request_plan_never_restarts_archive(self):
        from dbvora.archive.request_ledger import reserve, LedgerError
        gate._reserve_first(self.root)
        different = hashlib.sha256(b"different").hexdigest()
        with self.assertRaisesRegex(LedgerError, "REQUEST_PLAN_CONFLICT"):
            reserve(self.root, gate.REQUEST_ID, different)

    def test_injected_interruption_does_not_change_external_source(self):
        before = list(self.root.iterdir())
        result = gate.run_gate(interrupt_after_reserve=True)
        self.assertFalse(result["archive_executed"])
        self.assertEqual(list(self.root.iterdir()), before)

    def test_digest_refuses_size_over_limit_before_file_read(self):
        p = self.root / "big.zip"
        p.write_bytes(b"ABCDEFGH")
        with self.assertRaisesRegex(gate.GateFailure, "UNSAFE_SYNTHETIC_ARTIFACT"):
            gate._digest(p, max_bytes=7)
        self.assertEqual(p.read_bytes(), b"ABCDEFGH")

    def test_replay_is_held_after_archive_and_source_unchanged(self):
        report = gate.run_gate()
        self.assertEqual(report["status"], "PASS_SYNTHETIC_REQUEST_AND_ZIP_ONLY")
        self.assertTrue(report["replay_held"])
        self.assertTrue(report["zip_restore_content_verified"])
        self.assertFalse(report["exactly_once_verified"])
        self.assertFalse(report["windows_ntfs_verified"])

    def test_zip_tamper_before_hash_comparison_fails_closed(self):
        original_invoke = gate._invoke
        def corrupt_after_archive(command, *args):
            result = original_invoke(command, *args)
            if command == "archive":
                opts = dict(zip(args[::2], args[1::2]))
                path = Path(opts["--output-dir"]) / result["archive_path"]
                with path.open("ab") as out:
                    out.write(b"tamper")
            return result
        with patch.object(gate, "_invoke", side_effect=corrupt_after_archive):
            with self.assertRaisesRegex(gate.GateFailure, "ARCHIVE_SHA_MISMATCH"):
                gate.run_gate()

    def test_restored_bytes_tamper_is_rejected(self):
        original_invoke = gate._invoke
        def corrupt_after_restore(command, *args):
            result = original_invoke(command, *args)
            if command == "restore":
                opts = dict(zip(args[::2], args[1::2]))
                path = Path(opts["--output-dir"]) / result["restored_path"]
                with path.open("ab") as out:
                    out.write(b"tamper")
            return result
        with patch.object(gate, "_invoke", side_effect=corrupt_after_restore):
            with self.assertRaisesRegex(gate.GateFailure, "RESTORE_SHA_MISMATCH"):
                gate.run_gate()

    def test_main_emits_sanitized_error_without_path(self):
        out = io.StringIO()
        with patch.object(gate, "run_gate", side_effect=OSError("C:\\client\\secrets.sqlite")):
            with redirect_stdout(out):
                self.assertEqual(gate.main(), 1)
        self.assertIn('"error_code": "GATE_FAILED"', out.getvalue())
        self.assertNotIn("secrets.sqlite", out.getvalue())


if __name__ == "__main__":
    unittest.main()
