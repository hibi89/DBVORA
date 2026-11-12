"""Real source-only PostgreSQL catalog -> offline HTML acceptance; no network."""
from contextlib import redirect_stdout
from io import StringIO
import json
import socket
import unittest
from unittest.mock import patch

from scripts import pg_synthetic_acceptance as gate


class PgSyntheticAcceptanceTests(unittest.TestCase):
    def test_actual_metadata_through_html_and_disk(self):
        report = gate.verify()
        self.assertEqual(report["status"], "PASS_SYNTHETIC_PG_ONLY")
        self.assertEqual(report["checks"], 6)
        self.assertFalse(report["real_pg_connected"])
        self.assertFalse(report["ready_for_customer_data"])
        self.assertFalse(report["automatic_actions"])

    def test_no_socket_is_opened(self):
        with patch.object(socket, "create_connection",
                          side_effect=AssertionError("network prohibited")) as connect:
            report = gate.verify()
        self.assertEqual(report["status"], "PASS_SYNTHETIC_PG_ONLY")
        connect.assert_not_called()

    def test_denied_pg_catalog_never_false_passes(self):
        with patch.object(gate, "inspect_catalog",
                          side_effect=RuntimeError("password=private")):
            report = gate.verify()
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertEqual(report["error_code"], "SYNTHETIC_PG_GATE_FAILED")
        self.assertNotIn("private", str(report))

    def test_forged_workspace_fails_before_export(self):
        with patch.object(gate, "assemble_workspace",
                          side_effect=ValueError("source=/private")):
            report = gate.verify()
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertNotIn("/private", str(report))

    def test_broken_export_is_not_acceptance(self):
        with patch.object(gate, "export_report",
                          side_effect=OSError("customer-path")):
            report = gate.verify()
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertNotIn("customer-path", str(report))

    def test_cli_reports_stable_machine_json(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            code = gate.main()
        result = json.loads(buffer.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["checks"], 6)
        self.assertNotIn("postgresql://", buffer.getvalue())
        self.assertNotIn("password=", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
