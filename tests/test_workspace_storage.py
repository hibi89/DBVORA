"""Real synthetic SQLite dbstat page accounting and two-snapshot growth tests."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora import workspace_html
from dbvora.errors import InventoryError
from dbvora.storage_metrics import MAX_DBSTAT_MAIN_BYTES, collect_table_storage
from dbvora.workspace import inspect_workspace
from dbvora.workspace_observations import (ObservationError, compare_growth,
                                           from_workspace, read_observation,
                                           write_observation)


class WorkspaceStorageTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="dbvora-storage-synthetic-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.a = self.root / "first.sqlite"
        self.b = self.root / "second.sqlite"
        with closing(sqlite3.connect(self.a)) as db:
            db.executescript("CREATE TABLE owners (id INTEGER PRIMARY KEY, name TEXT);"
                             "CREATE TABLE inventory (id INTEGER PRIMARY KEY, owner_id INTEGER REFERENCES owners(id), note TEXT);"
                             "CREATE INDEX idx_inventory_owner ON inventory(owner_id);"
                             "INSERT INTO owners VALUES(1,'ROW_SECRET_DO_NOT_EMBED');"
                             "INSERT INTO inventory VALUES(2,1,'private');")
        with closing(sqlite3.connect(self.b)) as db:
            db.executescript("CREATE TABLE orders (id INTEGER PRIMARY KEY, amount INTEGER);"
                             "INSERT INTO orders VALUES(1,100);")

    def inspect(self):
        return inspect_workspace([self.a, self.b])

    def test_real_sqlite_dbstat_reports_allocated_pages_for_indexes(self):
        report = self.inspect()
        by_name = {t["name"]: t for t in report["databases"][0]["tables"]}
        owner, inv = by_name["owners"], by_name["inventory"]
        # SQLite btree pages, not logical row-data bytes or filesystem disk used.
        self.assertEqual(owner["storage"]["status"], "measured")
        self.assertEqual(inv["storage"]["btree_count"], 2)
        self.assertGreaterEqual(inv["storage"]["allocated_btree_bytes"], 8192)
        self.assertEqual(report["databases"][0]["table_storage_status"], "measured")
        self.assertIn("wal_pages_possible", report["databases"][0]["table_storage_scope"])
        self.assertEqual(report["cpu_usage"], "unavailable")
        self.assertEqual(report["ram_usage"], "unavailable")
        self.assertNotIn("ROW_SECRET_DO_NOT_EMBED", json.dumps(report))
        self.assertNotIn(str(self.a), json.dumps(report))

    def test_main_file_scan_budget_marks_unavailable_without_open(self):
        with patch("dbvora.storage_metrics.read_only_connection") as connection:
            data = collect_table_storage(self.a, MAX_DBSTAT_MAIN_BYTES + 1, [{"name": "inventory"}])
        connection.assert_not_called()
        self.assertEqual(data["status"], "unavailable")
        self.assertEqual(data["reason"], "main_file_exceeds_scan_limit")

    def test_missing_dbstat_marks_unavailable_without_rows(self):
        with patch("dbvora.storage_metrics.read_only_connection", side_effect=sqlite3.OperationalError("unsupported")):
            result = collect_table_storage(self.a, 2048, [{"name": "inventory"}])
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["tables"], {})

    def test_snapshot_schema_excludes_paths_and_rows(self):
        snapshot = from_workspace(self.inspect())
        serialized = json.dumps(snapshot)
        self.assertNotIn(str(self.a), serialized)
        self.assertNotIn("ROW_SECRET_DO_NOT_EMBED", serialized)
        self.assertEqual(snapshot["contract"], "dbvora.workspace-size-observation.v1")
        self.assertEqual(len(snapshot["databases"]), 2)

    def test_growth_after_insert_is_two_measurements_not_forecast(self):
        before = from_workspace(self.inspect())
        old = datetime.now(timezone.utc) - timedelta(minutes=5)
        for db in before["databases"]:
            db["observed_at"] = old.isoformat()
        with closing(sqlite3.connect(self.a)) as con:
            con.executemany("INSERT INTO inventory(owner_id,note) VALUES (?,?)", [(1, "x" * 200)] * 500)
            con.commit()
        current = from_workspace(self.inspect())
        growth = compare_growth(before, current)
        first = growth[current["databases"][0]["db_id"]]
        self.assertEqual(first["status"], "measured")
        self.assertGreater(first["delta_main_file_bytes"], 0)
        self.assertGreater(first["table_deltas"]["inventory"]["delta_allocated_btree_bytes"], 0)
        self.assertEqual(first["trend"], "two_observations_only_no_forecast")
        second = growth[current["databases"][1]["db_id"]]
        self.assertEqual(second["delta_main_file_bytes"], 0)

    def test_earlier_or_equal_time_is_unavailable(self):
        snapshot = from_workspace(self.inspect())
        growth = compare_growth(snapshot, snapshot)
        self.assertEqual(next(iter(growth.values()))["reason"], "non_increasing_observation_time")

    def test_missing_db_fingerprint_has_no_fabricated_growth(self):
        old = from_workspace(self.inspect())
        old["databases"][0]["db_id"] = "a" * 24
        current = from_workspace(self.inspect())
        growth = compare_growth(old, current)
        self.assertEqual(growth[current["databases"][0]["db_id"]]["reason"], "no_matching_baseline")

    def test_invalid_baseline_must_fail_closed(self):
        original = from_workspace(self.inspect())
        for bad in ([], {}, {**original, "secret_path": "C:/PRIVATE"}):
            with self.assertRaises(ObservationError):
                compare_growth(bad, original)
        original["databases"][0]["size_bytes"] = True
        with self.assertRaises(ObservationError):
            compare_growth(original, from_workspace(self.inspect()))

    def test_baseline_json_unique_no_overwrite_and_roundtrip(self):
        observation = from_workspace(self.inspect())
        first = write_observation(self.root, observation)
        content = (self.root / first).read_bytes()
        second = write_observation(self.root, observation)
        self.assertNotEqual(first, second)
        self.assertEqual((self.root / first).read_bytes(), content)
        self.assertEqual(read_observation(self.root / first), observation)

    def test_baseline_loader_rejects_relative_and_oversize(self):
        with self.assertRaises(ObservationError):
            read_observation("relative-baseline.json")
        bad = self.root / "too-large.json"
        bad.write_bytes(b"0" * (512 * 1024 + 1))
        with self.assertRaises(ObservationError):
            read_observation(bad)

    def test_baseline_loader_rejects_symlink(self):
        src = self.root / "source.json"
        src.write_text(json.dumps(from_workspace(self.inspect())))
        link = self.root / "link.json"
        try:
            link.symlink_to(src)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unsupported")
        with self.assertRaises(ObservationError):
            read_observation(link)

    def test_real_html_embeds_allocated_pages_and_no_rows(self):
        result = workspace_html.export_workspace([self.a, self.b], self.root)
        data = (self.root / result["filename"]).read_bytes()
        self.assertIn(b"Allocated btree pages", data)
        self.assertIn(b"delta_main_file_bytes", data)  # Runtime code path, no baseline value
        self.assertNotIn(b"ROW_SECRET_DO_NOT_EMBED", data)
        self.assertNotIn(str(self.a).encode(), data)
        self.assertEqual(result["growth_comparison"], "unavailable_no_baseline")

    def test_cli_creates_baseline_then_compares(self):
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            rc = workspace_html.main(["--db", str(self.a), "--db", str(self.b),
                                      "--out", str(self.root), "--save-observation"])
        self.assertEqual(rc, 0, output.getvalue())
        first = json.loads(output.getvalue())
        self.assertTrue(first["observation_filename"].endswith(".json"))
        with patch("sys.stdout", new_callable=io.StringIO) as output2:
            rc = workspace_html.main(["--db", str(self.a), "--db", str(self.b),
                                      "--out", str(self.root),
                                      "--baseline-file", str(self.root / first["observation_filename"])])
        self.assertEqual(rc, 0, output2.getvalue())
        second = json.loads(output2.getvalue())
        self.assertEqual(second["growth_comparison"], "two_observations")
        self.assertNotIn(str(self.a), output2.getvalue())

    def test_synthetic_only_does_not_accept_external_baseline(self):
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            rc = workspace_html.main(["--synthetic-only", "--out", str(self.root),
                                     "--baseline-file", str(self.root / "ignored.json")])
        self.assertNotEqual(rc, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
