"""Local-only API and packaged UI safety regression coverage."""
import hashlib
from contextlib import closing
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


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = create_fixture(Path(self.tmp.name) / 'sample.sqlite')
        self.app = create_app(self.db, port=8765)
        self.client = TestClient(self.app, base_url='http://127.0.0.1:8765')
        self.addCleanup(self.client.close)

    def fingerprint(self):
        return hashlib.sha256(self.db.read_bytes()).hexdigest(), self.db.stat().st_mtime_ns

    def test_http_metadata_and_source_unchanged(self):
        before = self.fingerprint()
        res = self.client.get('/api/inventory')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual([t['name'] for t in data['tables']], ['customers', 'events', 'orders'])
        self.assertEqual(len(data['relationships']), 1)
        self.assertEqual(data['provenance']['cpu_usage'], 'unavailable')
        self.assertEqual(before, self.fingerprint())
        self.assertNotIn(str(self.db), res.text)
        self.assertNotIn('NOT_FOR_SCHEMA_OUTPUT', res.text)
        self.assertNotIn('example@invalid.test', res.text)

    def test_table_storage_is_explicit_bounded_and_does_not_mutate_source(self):
        before = self.fingerprint()
        # Normal inventory fetch must not start a dbstat scan.
        with patch('dbvora.api.collect_table_storage') as scanner:
            self.assertEqual(self.client.get('/api/inventory').status_code, 200)
            scanner.assert_not_called()
        response = self.client.get('/api/table-storage', params={'table': 'orders'})
        self.assertEqual(response.status_code, 200)
        record = response.json()
        self.assertEqual(record['contract'], 'dbvora.local-table-storage.v1')
        self.assertEqual(record['table'], 'orders')
        self.assertIn('dbstat', record['scope'])
        self.assertIn(record['metric']['status'], ('measured', 'unavailable'))
        if record['metric']['status'] == 'measured':
            self.assertGreaterEqual(record['metric']['allocated_btree_bytes'], 0)
            self.assertEqual(record['metric']['source'], 'sqlite_dbstat_aggregate')
        self.assertEqual(before, self.fingerprint())
        self.assertNotIn(str(self.db), response.text)
        self.assertNotIn('NOT_FOR_SCHEMA_OUTPUT', response.text)

    def test_table_storage_rejects_unknown_invalid_and_remote_requests(self):
        for url in ('/api/table-storage', '/api/table-storage?table=',
                    '/api/table-storage?table=orders&table=customers',
                    '/api/table-storage?table=orders&db=other',
                    '/api/table-storage?table=%00evil'):
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 422)
                self.assertEqual(res.json()['error']['code'], 'INVALID_TABLE')
        missing = self.client.get('/api/table-storage', params={'table': 'private_unknown'})
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()['error']['code'], 'TABLE_NOT_FOUND')
        self.assertEqual(self.client.get('/api/table-storage?table=orders',
                                         headers={'Host': 'attacker.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/table-storage?table=orders').status_code, 405)

    def test_table_storage_detects_same_mtime_file_replacement_after_scan(self):
        before = self.fingerprint()
        other = Path(self.tmp.name) / 'replacement.sqlite'
        other.write_bytes(self.db.read_bytes())
        def replace_and_report(path, main_size, tables):
            previous = self.db.stat()
            os.replace(other, self.db)  # Test-owned temporary SQLite only.
            os.utime(self.db, ns=(previous.st_atime_ns, previous.st_mtime_ns))
            return {'scope': 'logical_btree_pages_dbstat_including_indexes_wal_pages_possible',
                    'tables': {'orders': {'status': 'measured', 'allocated_btree_bytes': 4096}}}
        with patch('dbvora.api.collect_table_storage', side_effect=replace_and_report):
            response = self.client.get('/api/table-storage', params={'table': 'orders'})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error']['code'], 'CHANGED_DURING_READ')
        self.assertEqual(before, self.fingerprint())

    def test_page_js_css_served_with_no_cache_and_csp(self):
        for path in ('/', '/assets/app.js', '/assets/style.css'):
            with self.subTest(path=path):
                res = self.client.get(path)
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.headers.get('cache-control'), 'no-store')
                self.assertEqual(res.headers.get('x-content-type-options'), 'nosniff')
                self.assertIn("default-src 'none'", res.headers.get('content-security-policy'))
                self.assertNotIn('access-control-allow-origin', res.headers)
        self.assertIn('Structure map', self.client.get('/').text)
        self.assertIn('textContent', self.client.get('/assets/app.js').text)
        self.assertNotIn('innerHTML', self.client.get('/assets/app.js').text.replace('No innerHTML', ''))

    def test_hostname_allowlist(self):
        for host in ('attacker.example', '127.0.0.1:8765.evil.com', '127.0.0.2:8765', '[::1]:8765'):
            with self.subTest(host=host):
                res = self.client.get('/api/inventory', headers={'Host': host})
                self.assertEqual(res.status_code, 403)
                self.assertNotIn(str(self.db), res.text)
        self.assertEqual(self.client.get('/api/inventory', headers={'Host': 'localhost:8765'}).status_code, 200)

    def test_cross_origin_refused(self):
        for origin in ('https://other.test', 'null', 'http://localhost:9999', 'http://127.0.0.1:8766'):
            with self.subTest(origin=origin):
                self.assertEqual(self.client.get('/api/inventory', headers={'Origin': origin}).status_code, 403)
        self.assertEqual(self.client.get('/api/inventory', headers={'Origin': 'http://127.0.0.1:8765'}).status_code, 200)
        self.assertEqual(self.client.get('/', headers={'Sec-Fetch-Site': 'cross-site'}).status_code, 403)

    def test_methods_fail_closed(self):
        for method in ('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'):
            with self.subTest(method=method):
                self.assertEqual(self.client.request(method, '/api/inventory').status_code, 405)

    def test_no_sql_or_path_query_interface(self):
        res = self.client.get('/api/inventory', params={'db': '/tmp/other.sqlite', 'sql': 'DELETE FROM orders'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()['tables']), 3)
        self.assertEqual(self.client.get('/openapi.json').status_code, 404)

    def test_invalid_selected_file_startup_fails_without_creation(self):
        target = Path(self.tmp.name) / 'missing-credential.sqlite'
        with self.assertRaises(InventoryError) as ctx:
            create_app(target)
        self.assertEqual(ctx.exception.code, 'FILE_UNAVAILABLE')
        self.assertFalse(target.exists())

    def test_missing_database_after_start_responds_safely(self):
        missing = str(self.db)
        self.db.unlink()
        res = self.client.get('/api/inventory')
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()['error']['code'], 'FILE_UNAVAILABLE')
        self.assertNotIn(missing, res.text)

    def test_zero_user_tables(self):
        empty = Path(self.tmp.name) / 'empty.sqlite'
        con = sqlite3.connect(empty)
        con.execute('PRAGMA user_version=1')
        con.close()
        app = create_app(empty)
        with TestClient(app, base_url='http://127.0.0.1:8765') as client:
            self.assertEqual(client.get('/api/inventory').json()['tables'], [])

    def test_unusual_identifiers_are_json_data_only(self):
        bad = '<img src=x onerror=alert(1)>'
        with closing(sqlite3.connect(self.db)) as con:
            con.execute('CREATE TABLE "' + bad + '" ("<svg onload=alert(1)>" TEXT)')
            con.commit()
        res = self.client.get('/api/inventory')
        self.assertEqual(res.status_code, 200)
        self.assertIn(bad, [t['name'] for t in res.json()['tables']])

    def test_unconfigured_port_is_rejected(self):
        with self.assertRaises(ValueError):
            create_app(self.db, port=0)
        with self.assertRaises(ValueError):
            create_app(self.db, port=65536)

    def test_health_is_local_only(self):
        self.assertEqual(self.client.get('/health').json(), {'ok': True, 'mode': 'local-read-only'})
        self.assertEqual(self.client.get('/health', headers={'Host': 'evil.org'}).status_code, 403)


if __name__ == '__main__':
    unittest.main()
