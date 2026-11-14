"""Local GET-only observation API acceptance with synthetic SQLite files."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from dbvora.api import create_app
from dbvora.inventory import inspect_sqlite
from dbvora.errors import InventoryError
from dbvora.observation_ledger import append_observation
from tests.fixtures.make_sqlite import create_fixture

SCOPE = "sqlite_main_file_excluding_wal_shm"


class ObservationApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = create_fixture(Path(self.tmp.name) / "source.sqlite")
        self.ledger = Path(self.tmp.name) / "ledger.sqlite"
        self.db_id = inspect_sqlite(self.source)["db_id"]

    def client(self, enabled=True):
        return TestClient(create_app(self.source, port=8765,
                                    observation_ledger_path=self.ledger if enabled else None),
                          base_url="http://127.0.0.1:8765")

    def test_disabled_by_default_and_no_implicit_write(self):
        with self.client(enabled=False) as client:
            response = client.get("/api/observations", params={"database": self.db_id})
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error"]["code"], "OBSERVATIONS_DISABLED")
        self.assertFalse(self.ledger.exists())

    def test_explicit_ledger_read_and_source_unchanged(self):
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        append_observation(self.ledger, db_id=self.db_id,
                           observed_at="2026-11-14T01:00:00Z", size_bytes=2048,
                           scope=SCOPE, consent=True)
        with self.client() as client:
            response = client.get("/api/observations", params={"database": self.db_id})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["contract"], "dbvora.local-observation.v1")
            self.assertEqual(len(data["records"]), 1)
            self.assertEqual(data["records"][0]["size_bytes"], 2048)
            self.assertNotIn(str(self.source), response.text)
            self.assertNotIn(str(self.ledger), response.text)
            self.assertEqual(client.post("/api/observations", json={}).status_code, 405)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before)

    def test_configured_empty_ledger_is_read_only_and_not_created(self):
        with self.client() as client:
            response = client.get("/api/observations", params={"database": self.db_id})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["records"], [])
        self.assertFalse(self.ledger.exists())

    def test_rejects_source_database_as_ledger_configuration(self):
        with self.assertRaises(InventoryError) as raised:
            create_app(self.source, port=8765, observation_ledger_path=self.source)
        self.assertEqual(raised.exception.code, "INVALID_OBSERVATION_LEDGER")

    def test_rejects_unconfigured_database_and_extra_query(self):
        with self.client() as client:
            for query in ("", "?database=not-configured",
                          "?database=" + self.db_id + "&database=" + self.db_id,
                          "?database=" + self.db_id + "&path=/tmp/secret"):
                self.assertEqual(client.get("/api/observations" + query).status_code, 422)
            self.assertEqual(client.get("/api/observations?database=" + self.db_id,
                                        headers={"Host": "evil.invalid"}).status_code, 403)
        self.assertFalse(self.ledger.exists())


if __name__ == "__main__":
    unittest.main()
