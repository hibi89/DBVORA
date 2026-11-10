"""SQLite catalog FK target casing: real in-memory engine checks."""
from __future__ import annotations

import sqlite3
from contextlib import closing
import unittest
from dbvora.sqlite_identifiers import sqlite_identifier_key


class SqliteIdentifierTests(unittest.TestCase):
    def test_ascii_table_case_matches_sqlite_catalog_semantics(self):
        with closing(sqlite3.connect(":memory:")) as c:
            c.executescript('CREATE TABLE "Parent" (id INTEGER PRIMARY KEY);'
                            'CREATE TABLE child (parent_id INTEGER REFERENCES "PARENT"(id));')
            actual = {sqlite_identifier_key(r[0]) for r in c.execute(
                "SELECT name FROM sqlite_schema WHERE type='table'")}
            target = c.execute('SELECT "table" FROM pragma_foreign_key_list(?)',
                               ('child',)).fetchone()[0]
            self.assertEqual(target, "PARENT")
            self.assertIn(sqlite_identifier_key(target), actual)
            self.assertNotIn(target, {"Parent", "child"})

    def test_quoted_unquoted_ascii_cases_match(self):
        self.assertEqual(sqlite_identifier_key("Mixed_Name"), sqlite_identifier_key("mixed_name"))
        self.assertEqual(sqlite_identifier_key('Parent'), sqlite_identifier_key('PARENT'))

    def test_unicode_case_is_not_falsely_folded(self):
        self.assertNotEqual(sqlite_identifier_key("ÄParent"), sqlite_identifier_key("äParent"))
        with closing(sqlite3.connect(":memory:")) as c:
            c.executescript('CREATE TABLE "ÄParent" (id INT);'
                            'CREATE TABLE child (parent_id INT REFERENCES "äParent"(id));')
            names = {sqlite_identifier_key(r[0]) for r in c.execute(
                "SELECT name FROM sqlite_schema WHERE type='table'")}
            target = c.execute('SELECT "table" FROM pragma_foreign_key_list(?)',
                               ('child',)).fetchone()[0]
            self.assertNotIn(sqlite_identifier_key(target), names)

    def test_special_symbols_preserved(self):
        self.assertEqual(sqlite_identifier_key("Ab[1]ß_!"), "ab[1]ß_!")

    def test_nonstring_rejected(self):
        for invalid in (None, 1, True, b"table", [], {}):
            with self.subTest(invalid=type(invalid).__name__), self.assertRaises(TypeError):
                sqlite_identifier_key(invalid)

    def test_empty_identifier_does_not_mutate(self):
        self.assertEqual(sqlite_identifier_key(""), "")


if __name__ == "__main__":
    unittest.main()
