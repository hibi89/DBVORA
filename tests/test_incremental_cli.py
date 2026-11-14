"""Local synthetic-only subprocess and malformed-input CLI safety contracts."""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from dbvora import incremental_cli as module
from scripts.incremental_cli_gate import run


class IncrementalCliTests(unittest.TestCase):
    def test_real_synthetic_subprocess_roundtrip_and_tamper(self):
        report = run()
        self.assertEqual(report["status"], "PASS_SYNTHETIC_INCREMENTAL_CLI_ONLY")
        self.assertEqual(report["checks"], 12)
        self.assertTrue(report["independent_restore_verified"])
        self.assertTrue(report["second_generation_reused_chunks"])
        self.assertTrue(report["tampered_chunk_rejected"])
        self.assertTrue(report["compressed_independent_restore_verified"])
        self.assertTrue(report["compressed_second_generation_reused_chunks"])
        self.assertTrue(report["compressed_tamper_rejected"])
        self.assertTrue(report["format_mismatch_rejected"])
        self.assertFalse(report["customer_ready"])

    def test_missing_required_and_unknown_option_never_echo_paths(self):
        for args in ([], ["create", "--snapshot", "/secret/customer.sqlite"],
                     ["create", "--unknown", "/very-secret/customer.sqlite"],
                     ["restore", "--manifest", "/very-secret/customer.json"],
                     ["create", "--format", "unknown", "--snapshot", "/secret/db"]):
            with self.subTest(args=args), io.StringIO() as capture, redirect_stderr(capture):
                self.assertEqual(module.main(args), 2)
                result = capture.getvalue()
                self.assertIn('"ok": false', result)
                self.assertNotIn("/very-secret", result)
                self.assertNotIn("/secret", result)

    def test_readonly_acks_and_no_api_call_on_invalid_invocation(self):
        with patch.object(module, "create_incremental") as create:
            with io.StringIO() as err, redirect_stderr(err):
                code = module.main(["create", "--snapshot", "/secret/path",
                                    "--chunk-dir", "/tmp/some-chunks",
                                    "--manifest-dir", "/tmp/some-manifests"])
            self.assertEqual(code, 2)
            create.assert_called_once_with("/secret/path", "/tmp/some-chunks",
                                           "/tmp/some-manifests", synthetic_only=False,
                                           accept_plaintext=False)


if __name__ == "__main__":
    unittest.main()
