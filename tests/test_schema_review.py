"""P0-09 actual offline SQLite pragma-backed metadata and safety checks."""
from __future__ import annotations

import sqlite3
import unittest
from dbvora.schema_review import SchemaReviewError, summarize_workspace_schema


def sample_workspace(connection: sqlite3.Connection) -> dict:
    names = [x[0] for x in connection.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name")]
    tables = []
    edges = []
    for name in names:
        columns = [{"name": c[1], "pk_position": c[5]} for c in connection.execute("SELECT * FROM pragma_table_xinfo(?)", (name,))]
        indexes = []
        for i in connection.execute("SELECT name, partial FROM pragma_index_list(?)", (name,)):
            keys = [c[0] for c in connection.execute("SELECT name FROM pragma_index_xinfo(?) WHERE \"key\" = 1 ORDER BY seqno", (i[0],))]
            indexes.append({"key_columns": keys, "partial": bool(i[1])})
        for fk in connection.execute("SELECT \"table\", \"from\" FROM pragma_foreign_key_list(?)", (name,)):
            edges.append({"database_id": "database-1", "from_table": name, "to_table": fk[0],
                          "from_columns": [fk[1]], "target_in_inventory": fk[0] in names})
        tables.append({"name": name, "columns": columns, "indexes": indexes})
    return {"contract_version": "p0-03.workspace.v1", "databases": [
        {"db_id": "database-1", "tables": tables}, {"db_id": "database-2", "tables": []}],
        "database_count": 2, "table_count": len(tables), "relationships": edges}


class SchemaReviewTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)

    def test_review_observes_catalog_without_reading_rows(self):
        self.db.executescript("CREATE TABLE customers(id INTEGER PRIMARY KEY);"
                              "CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id), secret TEXT);"
                              "INSERT INTO orders VALUES(1,1,'SECRET_ROW');"
                              "CREATE TABLE logs(message TEXT);")
        result = summarize_workspace_schema(sample_workspace(self.db))
        self.assertEqual(result["without_declared_pk"], 1)
        self.assertEqual(result["fk_index_review"], 1)
        self.assertFalse(result["unresolved_fk_targets"])
        self.assertTrue(result["no_row_scanning"])
        self.assertNotIn("SECRET_ROW", str(result))

    def test_index_on_fk_resolves_review(self):
        self.db.executescript("CREATE TABLE customers(id INTEGER PRIMARY KEY);"
                              "CREATE TABLE orders(customer_id INTEGER REFERENCES customers(id));"
                              "CREATE INDEX ix_customer ON orders(customer_id);")
        result = summarize_workspace_schema(sample_workspace(self.db))
        self.assertEqual(result["fk_index_review"], 0)

    def test_unresolved_declared_fk_is_advisory_only(self):
        self.db.execute("CREATE TABLE child(parent_id INTEGER REFERENCES unavailable(id))")
        result = summarize_workspace_schema(sample_workspace(self.db))
        self.assertEqual(result["unresolved_fk_targets"], 1)
        self.assertEqual(result["status"], "REVIEW_ONLY")

    def test_composite_index_prefix_and_partial_exclusion(self):
        self.db.executescript("CREATE TABLE parent(id INTEGER PRIMARY KEY);"
                              "CREATE TABLE child(x INTEGER REFERENCES parent(id), y INTEGER);"
                              "CREATE INDEX idx_xy ON child(x,y);")
        report = summarize_workspace_schema(sample_workspace(self.db))
        self.assertEqual(report["fk_index_review"], 0)
        self.db.execute("DROP INDEX idx_xy")
        self.db.execute("CREATE INDEX idx_partial ON child(x) WHERE y IS NOT NULL")
        report = summarize_workspace_schema(sample_workspace(self.db))
        self.assertEqual(report["fk_index_review"], 1)

    def test_invalid_duplicate_database_id_rejected(self):
        self.db.execute("CREATE TABLE t(id INT PRIMARY KEY)")
        data = sample_workspace(self.db)
        data["databases"][1]["db_id"] = "database-1"
        with self.assertRaises(SchemaReviewError):
            summarize_workspace_schema(data)

    def test_invalid_relationship_is_rejected(self):
        data = sample_workspace(self.db)
        data["relationships"] = [{"database_id": "bad", "from_table": "x", "to_table": "x", "from_columns": ["x"],
                                  "target_in_inventory": True}]
        with self.assertRaises(SchemaReviewError):
            summarize_workspace_schema(data)

    def test_malformed_index_or_column_fails_closed(self):
        data = sample_workspace(self.db)
        data["databases"][0]["tables"] = [{"name": "x", "columns": [{"name": "x", "pk_position": "wrong"}], "indexes": []}]
        data["table_count"] = 1
        with self.assertRaises(SchemaReviewError):
            summarize_workspace_schema(data)
        data["databases"][0]["tables"][0]["columns"][0]["pk_position"] = 0
        data["databases"][0]["tables"][0]["indexes"] = [{"key_columns": [], "partial": "no"}]
        with self.assertRaises(SchemaReviewError):
            summarize_workspace_schema(data)

    def test_empty_workspace_is_safe(self):
        result = summarize_workspace_schema(sample_workspace(self.db))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["total_tables"], 0)

    def test_report_bound_truncates_without_claiming_completeness(self):
        data = sample_workspace(self.db)
        data["databases"][0]["tables"] = [
            {"name": f"t{i}", "columns": [{"name": "note", "pk_position": 0}], "indexes": []}
            for i in range(205)]
        data["table_count"] = 205
        report = summarize_workspace_schema(data)
        self.assertTrue(report["truncated"])
        self.assertEqual(report["without_declared_pk"], 205)
        self.assertEqual(len(report["findings"]), 200)


if __name__ == "__main__":
    unittest.main()
