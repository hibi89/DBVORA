"""Synthetic-only acceptance for explicit local observation persistence."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import sqlite3
import tempfile
import unittest
from pathlib import Path

from dbvora.observation_ledger import (
    MAX_RECORDS, ObservationError, _digest, append_observation, read_observations,
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
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute("UPDATE observations SET size_bytes=999 WHERE db_id='synthetic_db'")
            conn.commit()
        with self.assertRaisesRegex(ObservationError, "integrity"):
            read_observations(self.path, db_id="synthetic_db")
        with self.assertRaisesRegex(ObservationError, "integrity"):
            self.append("2026-11-14T01:01:00Z", 2048)

    def test_read_does_not_create_or_modify_ledger(self):
        self.assertEqual(read_observations(self.path, db_id="synthetic_db"), [])
        self.assertFalse(self.path.exists())
        self.append("2026-11-14T01:00:00Z", 1024)
        before = self.path.read_bytes()
        self.assertEqual(len(read_observations(self.path, db_id="synthetic_db")), 1)
        self.assertEqual(self.path.read_bytes(), before)

    def test_enforces_ten_thousand_record_capacity(self):
        self.assertEqual(MAX_RECORDS, 10_000)
        origin = datetime(2026, 1, 1, tzinfo=timezone.utc)
        previous = "0" * 64
        records = []
        for seq in range(MAX_RECORDS):
            observed_at = (origin + timedelta(seconds=seq)).isoformat(
                timespec="microseconds")
            body = {"db_id": "synthetic_db", "observed_at": observed_at,
                    "size_bytes": seq, "scope": SCOPE, "prev_hash": previous}
            record_hash = _digest(body)
            records.append((body["db_id"], observed_at, body["size_bytes"],
                            body["scope"], previous, record_hash))
            previous = record_hash
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute("""CREATE TABLE observations (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                db_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                scope TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                UNIQUE(db_id, observed_at, scope)
            )""")
            conn.executemany(
                "INSERT INTO observations(db_id,observed_at,size_bytes,scope,prev_hash,record_hash) "
                "VALUES (?,?,?,?,?,?)", records)
            conn.commit()
        next_time = (origin + timedelta(seconds=MAX_RECORDS)).isoformat(
            timespec="microseconds")
        with self.assertRaisesRegex(ObservationError, "capacity"):
            self.append(next_time, MAX_RECORDS)
        self.assertEqual(len(read_observations(self.path, db_id="synthetic_db")),
                         MAX_RECORDS)

    def test_rejects_bad_metadata(self):
        for db, at, size in [("postgres://secret", "2026-11-14T01:00:00Z", 1),
                             ("synthetic_db", "2026-11-14T01:00:00", 1),
                             ("synthetic_db", "2026-11-14T01:00:00Z", -1),
                             ("synthetic_db", "2026-11-14T01:00:00Z", True)]:
            with self.assertRaises(ObservationError):
                self.append(at, size, db=db)
        self.assertFalse(self.path.exists())

    def test_refuses_existing_non_ledger_database_without_modifying_it(self):
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute("CREATE TABLE customer_data(value TEXT)")
            conn.execute("INSERT INTO customer_data VALUES ('synthetic-only')")
            conn.commit()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ObservationError, "not a DBVORA observation ledger"):
            self.append("2026-11-14T01:00:00Z", 1024)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
