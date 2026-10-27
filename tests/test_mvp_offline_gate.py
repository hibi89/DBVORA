"""P0 integrated smoke gate exercises actual product modules on synthetic SQLite."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import mvp_offline_gate as gate


class MVPIntegratedGateTests(unittest.TestCase):
    def test_actual_p0_end_to_end(self):
        report = gate.verify()
        self.assertEqual(report["status"], "PASS_SYNTHETIC_P0_ONLY", report)
        self.assertEqual(report["passed_check_count"], len(gate.REQUIRED))
        self.assertTrue(all(x == "PASS" for x in report["checks"].values()))

    def test_gate_has_exact_expected_contract(self):
        report = gate.verify()
        self.assertEqual(report["contract"], "dbvora.mvp-offline-check.v1")
        self.assertEqual(report["scope"], "OS_TEMP_SYNTHETIC_ONLY")
        self.assertFalse(report["ready_for_customer_data"])
        self.assertFalse(report["windows_file_browser_verified"])
        self.assertFalse(report["windows_archive_durability_verified"])
        self.assertFalse(report["full_release_gate_verified"])

    def test_failure_is_safe_and_path_free(self):
        with patch.object(gate, "_run", side_effect=RuntimeError("C:/PRIVATE/persons.sqlite")):
            report = gate.verify()
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertEqual(report["error_code"], "SYNTHETIC_MVP_CHECK_FAILED")
        self.assertNotIn("persons", json.dumps(report))

    def test_partial_checks_fail_closed(self):
        result = {key: True for key in gate.REQUIRED}
        result["growth_two_observations"] = False
        with patch.object(gate, "_run", return_value=result):
            report = gate.verify()
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertEqual(report["passed_check_count"], len(gate.REQUIRED) - 1)
        self.assertEqual(report["checks"]["growth_two_observations"], "FAIL")

    def test_missing_check_is_failure(self):
        with patch.object(gate, "_run", return_value={}):
            report = gate.verify()
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertEqual(report["passed_check_count"], 0)

    def test_truthy_non_boolean_is_not_pass(self):
        result = {key: 1 for key in gate.REQUIRED}
        with patch.object(gate, "_run", return_value=result):
            report = gate.verify()
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertEqual(report["passed_check_count"], 0)

    def test_cli_machine_json_exit(self):
        from contextlib import redirect_stdout
        from io import StringIO
        out = StringIO()
        with redirect_stdout(out):
            exit_code = gate.main()
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(out.getvalue())["required_check_count"], len(gate.REQUIRED))

    def test_cli_failure_exit(self):
        from contextlib import redirect_stdout
        from io import StringIO
        out = StringIO()
        with patch.object(gate, "_run", side_effect=OSError("/private/secret")), redirect_stdout(out):
            exit_code = gate.main()
        self.assertEqual(exit_code, 1)
        self.assertNotIn("secret", out.getvalue())


if __name__ == "__main__":
    unittest.main()
