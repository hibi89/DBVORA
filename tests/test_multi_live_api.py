"""Synthetic local-only multi-SQLite live viewer contracts, no row data or paths."""
from contextlib import closing
import hashlib
from pathlib import Path
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from dbvora.api import create_app
from dbvora.errors import InventoryError
from tests.fixtures.make_sqlite import create_fixture


class MultiLiveApiTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="dbvora-live-multi-synthetic-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.first = create_fixture(root / "first.sqlite")
        self.second = root / "second.sqlite"
        with closing(sqlite3.connect(self.second)) as db:
            db.executescript("""
                CREATE TABLE warehouses(id INTEGER PRIMARY KEY);
                CREATE TABLE shipments(id INTEGER PRIMARY KEY, wid INTEGER REFERENCES warehouses(id));
                INSERT INTO warehouses VALUES (1);
                INSERT INTO shipments VALUES (2, 1);
            """)
        self.client = TestClient(create_app([self.first, self.second], port=8765),
                                 base_url="http://127.0.0.1:8765")
        self.addCleanup(self.client.close)

    def fingerprints(self):
        return tuple((hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                     for p in (self.first, self.second))

    def test_two_sources_readonly_named_scopes_no_eager_dbstat(self):
        before = self.fingerprints()
        with patch('dbvora.workspace.collect_table_storage') as scan:
            r = self.client.get('/api/inventory')
        scan.assert_not_called()
        self.assertEqual(r.status_code, 200)
        report = r.json()
        self.assertEqual(report['contract_version'], 'p0-03.workspace.v1')
        self.assertEqual(report['database_count'], 2)
        self.assertEqual([len(db['tables']) for db in report['databases']], [3, 2])
        self.assertEqual(report['table_count'], 5)
        self.assertEqual(report['cross_database_edges_verified'], 0)
        self.assertEqual(report['cross_database_relationships'], 'not_inferred')
        self.assertEqual([db['label'] for db in report['databases']], ['Database 1', 'Database 2'])
        self.assertTrue(all(db['table_storage_status'] == 'unavailable'
                            for db in report['databases']))
        self.assertEqual(len(report['relationships']), 2)
        self.assertNotEqual(report['relationships'][0]['database_id'],
                            report['relationships'][1]['database_id'])
        self.assertEqual(before, self.fingerprints())
        for sensitive in (str(self.first), str(self.second), 'example@invalid.test'):
            self.assertNotIn(sensitive, r.text)

    def test_table_size_requires_registered_database_id(self):
        report = self.client.get('/api/inventory').json()
        first_id, second_id = [d['db_id'] for d in report['databases']]
        before = self.fingerprints()
        good = self.client.get('/api/table-storage', params={
            'database': second_id, 'table': 'shipments'})
        self.assertEqual(good.status_code, 200)
        self.assertEqual(good.json()['table'], 'shipments')
        self.assertIn(good.json()['metric']['status'], ('measured', 'unavailable'))
        missing = self.client.get('/api/table-storage', params={
            'database': first_id, 'table': 'shipments'})
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()['error']['code'], 'TABLE_NOT_FOUND')
        for invalid in ('/api/table-storage?table=shipments',
                        '/api/table-storage?database=wrong&table=shipments',
                        '/api/table-storage?database=' + second_id + '&table=',
                        '/api/table-storage?database=' + second_id + '&table=shipments&db=x'):
            self.assertEqual(self.client.get(invalid).status_code, 422, invalid)
        self.assertEqual(self.client.get('/api/table-storage?table=shipments&database=' + second_id,
                                         headers={'Host': 'evil.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/table-storage?table=shipments&database=' + second_id).status_code, 405)
        self.assertEqual(before, self.fingerprints())

    def test_invalid_multi_startup_denies_duplicates_and_excess(self):
        with self.assertRaises(InventoryError) as caught:
            create_app([self.first, self.first])
        self.assertEqual(caught.exception.code, 'DUPLICATE_DATABASE')
        with self.assertRaises(InventoryError) as caught:
            create_app([self.first] * 9)
        self.assertEqual(caught.exception.code, 'INVALID_DATABASE_COUNT')
        with self.assertRaises(InventoryError):
            create_app([self.first, self.second.parent / 'hidden_missing.sqlite'])
        hardlink = self.second.parent / 'alias.sqlite'
        try:
            os.link(self.first, hardlink)
        except OSError:
            self.skipTest('hardlink unavailable')
        with self.assertRaises(InventoryError) as caught:
            create_app([self.first, hardlink])
        self.assertEqual(caught.exception.code, 'DUPLICATE_DATABASE')

    def test_lost_second_database_fails_closed_without_source_path(self):
        name = str(self.second)
        self.second.unlink()
        r = self.client.get('/api/inventory')
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()['error']['code'], 'FILE_UNAVAILABLE')
        self.assertNotIn(name, r.text)


if __name__ == '__main__':
    unittest.main()
