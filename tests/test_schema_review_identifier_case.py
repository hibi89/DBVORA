"""SQLite ASCII-only FK index catalog audit regression, synthetic catalog only."""
from contextlib import closing
import sqlite3
import unittest
from dbvora.schema_review import SchemaReviewError, summarize_workspace_schema


def sample():
    return {
        "contract_version": "p0-03.workspace.v1",
        "databases": [
            {"db_id": "one", "tables": [
                {"name": "parent", "columns": [{"name": "id", "pk_position": 1}], "indexes": []},
                {"name": "child", "columns": [{"name": "RefID", "pk_position": 0}],
                 "indexes": [{"key_columns": ["refid"], "partial": False}]},
            ]},
            {"db_id": "two", "tables": []},
        ],
        "database_count": 2, "table_count": 2,
        "relationships": [{"database_id": "one", "from_table": "child",
                           "to_table": "parent", "from_columns": ["REFID"],
                           "target_in_inventory": True}],
    }


class SchemaReviewIdentifierCaseTests(unittest.TestCase):
    def test_ascii_case_index_prefix(self):
        self.assertEqual(summarize_workspace_schema(sample())["fk_index_review"], 0)

    def test_ascii_case_primary_key(self):
        workspace = sample()
        child = workspace["databases"][0]["tables"][1]
        child["indexes"] = []
        child["columns"][0]["pk_position"] = 1
        self.assertEqual(summarize_workspace_schema(workspace)["fk_index_review"], 0)

    def test_unicode_case_remains_distinct(self):
        workspace = sample()
        workspace["relationships"][0]["from_columns"] = ["ä"]
        workspace["databases"][0]["tables"][1]["indexes"][0]["key_columns"] = ["Ä"]
        self.assertEqual(summarize_workspace_schema(workspace)["fk_index_review"], 1)

    def test_expression_index_is_not_a_covering_index(self):
        workspace = sample()
        workspace["databases"][0]["tables"][1]["indexes"][0]["key_columns"] = [None]
        self.assertEqual(summarize_workspace_schema(workspace)["fk_index_review"], 1)

    def test_invalid_index_entry_fails_closed(self):
        workspace = sample()
        workspace["databases"][0]["tables"][1]["indexes"][0]["key_columns"] = [1]
        with self.assertRaisesRegex(SchemaReviewError, "INVALID_WORKSPACE"):
            summarize_workspace_schema(workspace)

    def test_sqlite_catalog_casing_reference(self):
        with closing(sqlite3.connect(":memory:")) as connection:
            connection.executescript(
                'CREATE TABLE parent(id INTEGER PRIMARY KEY);'
                'CREATE TABLE child("RefID" INTEGER REFERENCES parent(id));'
                'CREATE INDEX idx ON child(refid);'
            )
            self.assertEqual(connection.execute("PRAGMA index_info(idx)").fetchone()[2], "RefID")
            self.assertEqual(connection.execute("PRAGMA foreign_key_list(child)").fetchone()[3], "RefID")


if __name__ == "__main__":
    unittest.main()
