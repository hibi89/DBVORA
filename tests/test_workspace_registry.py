"""SQLite read-only multi-DB aggregation tests, no network or customer records."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from dbvora.errors import InventoryError
from dbvora.workspace import inspect_workspace

class WorkspaceRegistryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='dbvora-workspace-registry-')
        self.addCleanup(temp.cleanup)
        self.one=Path(temp.name)/'first.sqlite'
        self.two=Path(temp.name)/'second.sqlite'
        with closing(sqlite3.connect(self.one)) as conn:
            conn.executescript('CREATE TABLE a (id INTEGER PRIMARY KEY); CREATE TABLE b (aid INTEGER REFERENCES a(id)); INSERT INTO a VALUES(10);')
        with closing(sqlite3.connect(self.two)) as conn:
            conn.executescript("CREATE TABLE c (body TEXT); INSERT INTO c VALUES('PRIVATE_ROW_SENTINEL');")

    def test_real_multi_database_inventory(self):
        result=inspect_workspace([self.one,self.two])
        self.assertEqual(result['database_count'],2)
        self.assertEqual(result['table_count'],3)
        self.assertEqual(len(result['relationships']),1)
        self.assertEqual(result['relationships'][0]['to_table'],'a')
        self.assertEqual(result['relationships'][0]['database_id'],result['databases'][0]['db_id'])
        self.assertTrue(result['relationships'][0]['target_in_inventory'])
        self.assertEqual(result['total_main_db_size_bytes'],self.one.stat().st_size+self.two.stat().st_size)

    def test_no_paths_rows_or_fake_metrics(self):
        result=inspect_workspace([self.one,self.two])
        output=json.dumps(result)
        self.assertNotIn(str(self.one),output)
        self.assertNotIn(str(self.two),output)
        self.assertNotIn('PRIVATE_ROW_SENTINEL',output)
        self.assertEqual(result['cpu_usage'],'unavailable')
        self.assertEqual(result['ram_usage'],'unavailable')
        self.assertEqual(result['cross_database_edges_verified'],0)

    def test_duplicate_is_rejected(self):
        with self.assertRaises(InventoryError) as cm:
            inspect_workspace([self.one,self.one])
        self.assertEqual(cm.exception.code,'DUPLICATE_DATABASE')

    def test_invalid_counts_are_rejected(self):
        for paths in ([],[self.one],[self.one]*9,'text'):
            with self.assertRaises(InventoryError) as cm:
                inspect_workspace(paths)
            self.assertEqual(cm.exception.code,'INVALID_DATABASE_COUNT')

    def test_missing_database_is_rejected(self):
        with self.assertRaises(InventoryError):
            inspect_workspace([self.one,self.one.parent/'nonexistent.sqlite'])

    def test_source_bytes_unchanged(self):
        before=(self.one.read_bytes(),self.two.read_bytes())
        inspect_workspace([self.one,self.two])
        self.assertEqual(before,(self.one.read_bytes(),self.two.read_bytes()))

    def test_declared_fk_with_missing_target_is_marked_unresolved(self):
        with closing(sqlite3.connect(self.two)) as conn:
            conn.execute('CREATE TABLE d (key INTEGER REFERENCES absent(id))')
        result=inspect_workspace([self.one,self.two])
        unresolved=[r for r in result['relationships'] if r['to_table']=='absent']
        self.assertEqual(len(unresolved),1)
        self.assertFalse(unresolved[0]['target_in_inventory'])

if __name__=='__main__':unittest.main()
