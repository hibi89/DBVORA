"""Actual synthetic 1,000/1,001-table SQLite read-only API contract."""
from __future__ import annotations

from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from fastapi.testclient import TestClient

from dbvora.api import create_app
from dbvora.errors import InventoryError
from dbvora.inventory import inspect_sqlite
from tests.fixtures.make_sqlite import create_fixture
from tests.fixtures.large_sqlite import extend_synthetic_catalog


class LargeSQLiteCatalogTests(unittest.TestCase):
    def test_real_1000_tables_are_read_only_and_1001_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="dbvora-real-1000-synthetic-") as root:
            database = create_fixture(Path(root) / "catalog.sqlite")
            last = extend_synthetic_catalog(database, target_tables=1000)
            original = hashlib.sha256(database.read_bytes()).hexdigest()
            mtime = database.stat().st_mtime_ns
            with TestClient(create_app(database, port=8765),
                            base_url="http://127.0.0.1:8765") as client:
                result = client.get("/api/inventory")
                self.assertEqual(result.status_code, 200)
                inventory = result.json()
                self.assertEqual(len(inventory["tables"]), 1000)
                self.assertEqual(len(inventory["relationships"]), 998)
                # 3 original tables: 1 FK + 997 synthesized FK.
                self.assertIn(last, {table["name"] for table in inventory["tables"]})
                self.assertNotIn("NOT_FOR_SCHEMA_OUTPUT", result.text)
                self.assertNotIn("example@invalid.test", result.text)
                self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(),
                                 original)
                self.assertEqual(database.stat().st_mtime_ns, mtime)

                excessive = extend_synthetic_catalog(database, target_tables=1001)
                exceeded_original = hashlib.sha256(database.read_bytes()).hexdigest()
                exceeded_mtime = database.stat().st_mtime_ns
                too_many = client.get("/api/inventory")
                self.assertEqual(too_many.status_code, 422)
                self.assertEqual(too_many.json()["error"]["code"], "CATALOG_LIMIT")
                self.assertNotIn(str(database), too_many.text)
                self.assertNotIn("NOT_FOR_SCHEMA_OUTPUT", too_many.text)
                self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(),
                                 exceeded_original)
                self.assertEqual(database.stat().st_mtime_ns, exceeded_mtime)
                with self.assertRaises(InventoryError) as context:
                    inspect_sqlite(database)
                self.assertEqual(context.exception.code, "CATALOG_LIMIT")

                with closing(sqlite3.connect(database)) as conn:
                    conn.execute('DROP TABLE "' + excessive + '"')
                    conn.commit()
                self.assertEqual(client.get("/api/inventory").status_code, 200)


if __name__ == "__main__":
    unittest.main()
