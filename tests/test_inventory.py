"""Run with: python -m unittest discover -s tests -v"""

import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from dbvora.errors import InventoryError
from dbvora.connectors.sqlite_reader import read_only_connection
from dbvora.inventory import inspect_sqlite
from tests.fixtures.make_sqlite import create_fixture


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = create_fixture(Path(self.temp.name) / "sample.sqlite")

    def fingerprint(self):
        return (hashlib.sha256(self.path.read_bytes()).hexdigest(), self.path.stat().st_mtime_ns)

    def test_fixture_three_tables_and_no_data_content(self):
        raw = json.dumps(inspect_sqlite(self.path))
        data = json.loads(raw)
        self.assertEqual([t["name"] for t in data["tables"]], ["customers", "events", "orders"])
        self.assertNotIn("NOT_FOR_SCHEMA_OUTPUT", raw)
        self.assertNotIn("example@invalid.test", raw)
        self.assertNotIn(str(self.path), raw)

    def test_indexes_and_explicit_foreign_key(self):
        report = inspect_sqlite(self.path)
        order = next(t for t in report["tables"] if t["name"] == "orders")
        self.assertIn("idx_orders_customer", [i["name"] for i in order["indexes"]])
        self.assertEqual(order["foreign_keys"][0]["to_table"], "customers")
        self.assertEqual(report["relationships"], [{
            "from_table": "orders", "from_columns": ["customer_id"],
            "to_table": "customers", "to_columns": ["id"],
            "evidence": "declared_foreign_key",
        }])

    def test_nullability_and_primary_key_are_catalog_based(self):
        orders = next(t for t in inspect_sqlite(self.path)["tables"] if t["name"] == "orders")
        fields = {c["name"]: c for c in orders["columns"]}
        self.assertFalse(fields["amount_cents"]["nullable_declared"])
        self.assertTrue(fields["memo"]["nullable_declared"])
        self.assertEqual(fields["id"]["pk_position"], 1)

    def test_empty_database(self):
        empty = Path(self.temp.name) / "empty.db"
        con = sqlite3.connect(empty)
        con.execute("PRAGMA user_version=1")  # initialize valid empty schema file
        con.close()
        self.assertEqual(inspect_sqlite(empty)["tables"], [])

    def test_observation_deterministic_except_timestamp(self):
        one, two = inspect_sqlite(self.path), inspect_sqlite(self.path)
        one.pop("observed_at")
        two.pop("observed_at")
        self.assertEqual(one, two)

    def test_main_database_size_provenance(self):
        report = inspect_sqlite(self.path)
        self.assertEqual(report["size_bytes"], self.path.stat().st_size)
        self.assertEqual(report["provenance"]["cpu_usage"], "unavailable")
        self.assertIn("excludes_wal", report["size_scope"])

    def test_source_bytes_and_mtime_unchanged(self):
        before = self.fingerprint()
        inspect_sqlite(self.path)
        self.assertEqual(before, self.fingerprint())

    def test_rejects_relative_path_without_echoing_path(self):
        with self.assertRaises(InventoryError) as ctx:
            inspect_sqlite("secret/relative.sqlite")
        self.assertEqual(ctx.exception.code, "INVALID_PATH")
        self.assertNotIn("secret", ctx.exception.message)

    def test_missing_path_and_corrupt_file(self):
        for file in (Path(self.temp.name) / "missing.sqlite", Path(self.temp.name) / "corrupt.sqlite"):
            if file.name.startswith("corrupt"):
                file.write_bytes(b"this is not sqlite")
            with self.subTest(file=file.name), self.assertRaises(InventoryError):
                inspect_sqlite(file)

    def test_rejects_symlink(self):
        link = Path(self.temp.name) / "link.sqlite"
        try:
            link.symlink_to(self.path)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(InventoryError) as ctx:
            inspect_sqlite(link)
        self.assertEqual(ctx.exception.code, "SYMLINK_FORBIDDEN")

    def test_sql_identifier_with_quotes_is_not_executable_sql(self):
        con = sqlite3.connect(self.path)
        con.execute('CREATE TABLE "test\"\"quoted" ("a\"\"b" TEXT)')
        con.commit()
        con.close()
        report = inspect_sqlite(self.path)
        table = next(t for t in report["tables"] if t["name"] == 'test"quoted')
        self.assertEqual(table["columns"][0]["name"], 'a"b')

    def test_read_only_cannot_write_and_cli_exit(self):
        before = self.fingerprint()
        result = subprocess.run(
            [sys.executable, "-m", "dbvora", "inspect", str(self.path)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["engine"], "sqlite")
        self.assertEqual(before, self.fingerprint())

    def test_readonly_connector_rejects_mutation(self):
        before = self.fingerprint()
        with read_only_connection(self.path) as con:
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("INSERT INTO events (id, category) VALUES (99, 'nope')")
        self.assertEqual(before, self.fingerprint())

    def test_metadata_only_even_with_expression_indexes(self):
        with sqlite3.connect(self.path) as con:
            con.execute("CREATE INDEX idx_event_lower ON events(lower(category))")
        report = inspect_sqlite(self.path)
        event = next(t for t in report["tables"] if t["name"] == "events")
        expression_index = next(i for i in event["indexes"] if i["name"] == "idx_event_lower")
        self.assertEqual(expression_index["key_columns"], [None])

    def test_invalid_sqlite_header_same_length_fails_safely(self):
        fake = Path(self.temp.name) / "fake.db"
        fake.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
        with self.assertRaises(InventoryError) as ctx:
            inspect_sqlite(fake)
        self.assertEqual(ctx.exception.code, "DB_READ_FAILED")

    def test_cli_errors_no_traceback_or_path(self):
        missing = str(Path(self.temp.name) / "private_missing.sqlite")
        result = subprocess.run(
            [sys.executable, "-m", "dbvora", "inspect", missing],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(missing, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(json.loads(result.stderr)["error"]["code"], "FILE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
