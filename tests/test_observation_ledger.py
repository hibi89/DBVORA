"""Synthetic-only acceptance for explicit local observation persistence."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from dbvora.observation_ledger import (
    ObservationError, append_observation, read_observations,
)

SCOPE = "sqlite_main_file_excluding_wal_shm"


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "observations.sqlite"

    def append(self, at, size, db="synthetic_db", consent=True):
        return append_observation(self.path, db_id=db, observed_at=at,
                                  size_bytes=size, scope=SCOPE, consent=consent)

    def test_opt_in_idempotent_restart_and_isolation(self):
        with self.assertRaisesRegex(ObservationError, "consent"):
            self.append("2026-11-14T01:00:00Z", 1024, consent=False)
        self.assertFalse(self.path.exists())
        first = self.append("2026-11-14T01:00:00Z", 1024)
        self.assertEqual(first["status"], "appended")
        self.assertEqual(self.append("2026-11-14T01:00:00+00:00", 1024)["status"], "duplicate")
        self.append("2026-11-14T01:01:00Z", 2048)
        self.append("2026-11-14T01:00:00Z", 99, db="other_db")
        rows = read_observations(self.path, db_id="synthetic_db")
        self.assertEqual([x["size_bytes"] for x in rows], [1024, 2048])
        self.assertEqual(len(read_observations(self.path, db_id="other_db")), 1)
        self.assertEqual(rows[0]["record_hash"], first["record_hash"])

    def test_rollback_conflicting_duplicate_and_scope(self):
        self.append("2026-11-14T01:00:00Z", 1024)
        for at, size in [("2026-11-14T00:59:00Z", 512),
                         ("2026-11-14T01:00:00Z", 512)]:
            with self.assertRaises(ObservationError):
                self.append(at, size)
        with self.assertRaises(ObservationError):
            append_observation(self.path, db_id="synthetic_db",
                               observed_at="2026-11-14T01:02:00Z",
                               size_bytes=3, scope="customer_rows", consent=True)
        self.assertEqual(len(read_observations(self.path, db_id="synthetic_db")), 1)

    def test_detects_tampering_before_next_write(self):
        self.append("2026-11-14T01:00:00Z", 1024)
        with sqlite3.connect(self.path) as conn:
            conn.execute("UPDATE observations SET size_bytes=999 WHERE db_id='synthetic_db'")
        with self.assertRaisesRegex(ObservationError, "integrity"):
            read_observations(self.path, db_id="synthetic_db")
        with self.assertRaisesRegex(ObservationError, "integrity"):
            self.append("2026-11-14T01:01:00Z", 2048)

    def test_rejects_bad_metadata(self):
        for db, at, size in [("postgres://secret", "2026-11-14T01:00:00Z", 1),
                             ("synthetic_db", "2026-11-14T01:00:00", 1),
                             ("synthetic_db", "2026-11-14T01:00:00Z", -1),
                             ("synthetic_db", "2026-11-14T01:00:00Z", True)]:
            with self.assertRaises(ObservationError):
                self.append(at, size, db=db)
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
