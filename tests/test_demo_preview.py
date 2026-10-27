"""Synthetic offline demo safety checks; no customer DB/network."""
from pathlib import Path
from contextlib import closing
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora import demo_preview


class DemoPreviewTests(unittest.TestCase):
    def test_fixture_has_schema_fk_and_private_row_canary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.sqlite"
            demo_preview.create_synthetic_database(path)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual([r[0] for r in db.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name")],
                                 ["departments", "employees"])
                self.assertEqual(db.execute("PRAGMA foreign_key_list(employees)").fetchone()[2], "departments")
                self.assertEqual(db.execute("SELECT display_name FROM employees").fetchone()[0], demo_preview._SENTINEL)

    def test_real_export_generates_offline_map_and_removes_synthetic_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = demo_preview.create_demo(Path(tmp))
            self.assertEqual(report["status"], "CREATED_SYNTHETIC_DEMO", report)
            self.assertFalse(report["contains_table_rows"])
            self.assertFalse(report["database_file_retained"])
            self.assertFalse(report["ready_for_customer_data"])
            output = Path(tmp) / report["filename"]
            html = output.read_bytes()
            self.assertIn(b"localSchemaBase64", html)
            self.assertNotIn(demo_preview._SENTINEL.encode(), html)
            self.assertEqual(list(Path(tmp).glob("*.sqlite")), [])
            self.assertEqual(len(list(Path(tmp).glob("*.html"))), 1)

    def test_two_runs_never_replace_the_first_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = demo_preview.create_demo(tmp)
            before = (Path(tmp) / first["filename"]).read_bytes()
            second = demo_preview.create_demo(tmp)
            self.assertEqual(second["status"], "CREATED_SYNTHETIC_DEMO")
            self.assertNotEqual(first["filename"], second["filename"])
            self.assertEqual(before, (Path(tmp) / first["filename"]).read_bytes())

    def test_relative_output_rejected(self):
        self.assertEqual(demo_preview.create_demo("relative-output")["status"], "FAIL_CLOSED")

    def test_export_failure_does_not_echo_sensitive_paths(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(demo_preview, "export", side_effect=ValueError("/private/raw.sqlite")):
            report = demo_preview.create_demo(tmp)
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertNotIn("private", json.dumps(report))

    def test_corrupt_export_metadata_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(demo_preview, "export", return_value={"status": "CREATED_OFFLINE_SCHEMA_HTML", "filename": "../escape.html", "contains_table_rows": False}):
            self.assertEqual(demo_preview.create_demo(tmp)["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
