"""Gate decision tests. Real temporary ZIP; subprocess reports are mocked.

Full source builder and native Windows are not represented by these unit tests.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import portable_acceptance_gate as gate


class PortableAcceptanceDecisions(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dbvora-portable-gate-decisions-")
        self.addCleanup(temp.cleanup)
        self.trusted = Path(temp.name) / "trusted"
        (self.trusted / "scripts").mkdir(parents=True)
        (self.trusted / "scripts" / "verify_trusted_extraction.py").write_text(
            "# inert synthetic placeholder\\n", encoding="utf-8")
        self.restore = patch.object(gate, "ROOT", self.trusted)
        self.restore.start()
        self.addCleanup(self.restore.stop)

    @staticmethod
    def _create_zip(output):
        archive = output / "test.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("dbvora/archive/request_service.py", b"# inert synthetic\\n")
        return archive

    @staticmethod
    def _reports():
        return [
            (0, {"status": "PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY",
                 "publisher_authenticity_verified": False, "customer_ready": False}),
            (0, {"status": "PASS_SYNTHETIC_PREVIEW_ONLY", "zip": "passed",
                 "zstd": "skipped_no_local_codec", "customer_ready": False,
                 "windows_ntfs_durability_verified": False}),
            (1, {"status": "FAIL_CLOSED", "error_code": "PACKAGE_DIGEST_MISMATCH"}),
        ]

    def _execute(self, reports, *, package_status="PASS_UNSIGNED_SOURCE_INTEGRITY_ONLY"):
        with patch.object(gate.build_portable, "build", side_effect=self._create_zip):
            with patch.object(gate.build_portable, "verify_zip", return_value={
                "status": package_status, "signed": False, "ready_for_customer_data": False
            }):
                with patch.object(gate, "_child", side_effect=reports):
                    return gate.verify()

    def test_all_four_evidence_steps_required(self):
        report = self._execute(self._reports())
        self.assertEqual(report["status"], "PASS_SYNTHETIC_PORTABLE_ONLY")
        self.assertEqual(report["checks"], 4)
        self.assertFalse(report["ready_for_customer_data"])
        self.assertFalse(report["signed"])
        self.assertRegex(report["zip_sha256"], r"^[0-9a-f]{64}$")

    def test_unsigned_builder_failure_blocks(self):
        report = self._execute(self._reports(), package_status="INVALID")
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertEqual(report["error_code"], "ZIP_VERIFICATION_FAILED")

    def test_auditor_failure_blocks_before_preview(self):
        cases = self._reports()
        cases[0] = (0, {"status": "PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY",
                        "publisher_authenticity_verified": False,
                        "customer_ready": True})
        report = self._execute(cases)
        self.assertEqual(report["error_code"], "EXTRACTED_AUDIT_FAILED")
        self.assertEqual(report["checks"], 1)

    def test_preview_false_success_blocks(self):
        cases = self._reports()
        cases[1][1]["customer_ready"] = True
        self.assertEqual(self._execute(cases)["error_code"], "SYNTHETIC_PREVIEW_FAILED")

    def test_mutation_must_fail_digest(self):
        cases = self._reports()
        cases[2] = (0, {"status": "PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY"})
        report = self._execute(cases)
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertEqual(report["error_code"], "TAMPER_REJECTION_FAILED")

    def test_untrusted_auditor_missing_fails_closed(self):
        (self.trusted / "scripts" / "verify_trusted_extraction.py").unlink()
        report = self._execute(self._reports())
        self.assertEqual(report["error_code"], "TRUSTED_AUDITOR_MISSING")

    def test_child_strict_json(self):
        code, data = gate._child(
            [sys.executable, "-c", "print('{\"a\":true}')"], self.trusted)
        self.assertEqual(code, 0)
        self.assertEqual(data, {"a": True})
        code, data = gate._child(
            [sys.executable, "-c", "print('not json')"], self.trusted)
        self.assertEqual((code, data), (-1, {}))


if __name__ == "__main__":
    unittest.main()
