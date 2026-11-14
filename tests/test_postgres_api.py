"""GET-only PostgreSQL UI API safety contract."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from dbvora.api import create_app
from dbvora.connectors.postgres_reader import PostgresInventoryError
from tests.fixtures.make_sqlite import create_fixture


class PostgreSQLApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = create_fixture(Path(self.tmp.name) / 'local.sqlite')

    def client(self, dsn=None):
        return TestClient(create_app(self.db, port=8765, postgres_dsn=dsn),
                          base_url='http://127.0.0.1:8765')

    def test_disabled_by_default_and_no_automatic_connection(self):
        with patch('dbvora.api.inspect_postgres') as inspect:
            with self.client() as client:
                page = client.get('/')
                self.assertEqual(page.status_code, 200)
                response = client.get('/api/postgres')
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()['error']['code'], 'POSTGRES_DISABLED')
                self.assertEqual(client.get('/api/postgres/statistics').status_code, 404)
                self.assertNotIn('/api/postgres', page.text)
                self.assertEqual(client.post('/api/postgres').status_code, 405)
                inspect.assert_not_called()

    def test_explicit_lookup_is_verified_tls_read_only_and_secret_free(self):
        dsn = 'host=synthetic.invalid password=NEVER_RETURN_THIS sslrootcert=/private/runner/certs/NEVER_RETURN_CA.pem'
        catalog = {'contract_version': 'dbvora.pg_catalog.v1', 'engine': 'postgresql',
                   'tables': [{'schema': 'public', 'name': 'synthetic_table',
                               'relation_kind': 'r', 'columns': [], 'indexes': [],
                               'primary_key_columns': [], 'foreign_keys': []}]}
        with patch('dbvora.api.inspect_postgres', return_value=catalog) as inspect:
            with self.client(dsn) as client:
                self.assertEqual(client.get('/api/postgres?table=ignored').status_code, 422)
                self.assertEqual(client.request('GET', '/api/postgres', json={'dsn': dsn}).status_code, 422)
                inspect.assert_not_called()
                response = client.get('/api/postgres')
        self.assertEqual(response.status_code, 200)
        inspect.assert_called_once_with(dsn, require_tls=True, include_statistics=False)
        self.assertNotIn(dsn, response.text)
        self.assertNotIn('NEVER_RETURN_THIS', response.text)
        self.assertNotIn('NEVER_RETURN_CA.pem', response.text)
        self.assertNotIn('/private/runner/certs', response.text)
        self.assertNotIn(str(self.db), response.text)
        self.assertNotIn('SYNTHETIC_ROW_MUST_NEVER_BE_EXPORTED', response.text)

    def test_statistics_are_a_separate_explicit_allowlisted_metadata_response(self):
        dsn = 'host=synthetic.invalid password=NEVER_RETURN_THIS'
        catalog = {
            'contract_version': 'dbvora.pg_catalog.v1', 'engine': 'postgresql',
            'observed_at': '2026-11-15T00:00:00Z',
            'tables': [
                {'schema': 'public', 'name': 'synthetic_table', 'relation_kind': 'r',
                 'columns': [{'name': 'private_column_name'}], 'indexes': [],
                 'primary_key_columns': [], 'foreign_keys': [],
                 'statistics': {'status': 'observed', 'estimated_live_rows': 1,
                    'estimated_dead_rows': 0, 'heap_bytes': 8192, 'index_bytes': 4096,
                    'row_count_provenance': 'pg_stat_user_tables_estimate_not_exact',
                    'storage_provenance': 'pg_relation_size_and_pg_indexes_size'}},
                {'schema': 'public', 'name': 'synthetic_view', 'relation_kind': 'v',
                 'columns': [], 'indexes': [], 'primary_key_columns': [], 'foreign_keys': [],
                 'statistics': {'status': 'unavailable', 'reason': 'relation_not_in_statistics_view'}},
            ],
        }
        with patch('dbvora.api.inspect_postgres', return_value=catalog) as inspect:
            with self.client(dsn) as client:
                page = client.get('/')
                self.assertEqual(page.status_code, 200)
                self.assertNotIn('/api/postgres/statistics', page.text)
                self.assertEqual(client.get('/api/postgres/statistics?table=synthetic_table').status_code, 422)
                self.assertEqual(client.request('GET', '/api/postgres/statistics',
                                                json={'dsn': dsn}).status_code, 422)
                inspect.assert_not_called()
                response = client.get('/api/postgres/statistics')
        self.assertEqual(response.status_code, 200)
        inspect.assert_called_once_with(dsn, require_tls=True, include_statistics=True)
        result = response.json()
        self.assertEqual(result['contract'], 'dbvora.pg_statistics.v1')
        self.assertTrue(result['statistics_may_lag'])
        self.assertIn('not statistics refresh time', result['freshness_note'])
        self.assertEqual(result['tables'][0]['statistics']['estimated_live_rows'], 1)
        self.assertEqual(result['tables'][1]['statistics'],
                         {'status': 'unavailable', 'reason': 'relation_not_in_statistics_view'})
        self.assertNotIn('columns', response.text)
        self.assertNotIn('private_column_name', response.text)
        self.assertNotIn(dsn, response.text)
        self.assertNotIn('NEVER_RETURN_THIS', response.text)
        self.assertNotIn('SYNTHETIC_ROW_MUST_NEVER_BE_EXPORTED', response.text)

    def test_connection_failure_is_sanitized_for_recoverable_ui(self):
        dsn = 'host=synthetic.invalid password=NEVER_RETURN_THIS sslrootcert=/private/runner/certs/NEVER_RETURN_CA.pem'
        with patch('dbvora.api.inspect_postgres',
                   side_effect=PostgresInventoryError('PG_CONNECTION_FAILED')):
            with self.client(dsn) as client:
                response = client.get('/api/postgres')
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()['error']['code'], 'PG_CONNECTION_FAILED')
        self.assertNotIn(dsn, response.text)
        self.assertNotIn('NEVER_RETURN_THIS', response.text)
        self.assertNotIn('NEVER_RETURN_CA.pem', response.text)
        self.assertNotIn('/private/runner/certs', response.text)


if __name__ == '__main__':
    unittest.main()
