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
                self.assertNotIn('/api/postgres', page.text)
                self.assertEqual(client.post('/api/postgres').status_code, 405)
                inspect.assert_not_called()

    def test_explicit_lookup_is_verified_tls_read_only_and_secret_free(self):
        dsn = 'host=synthetic.invalid password=NEVER_RETURN_THIS'
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
        self.assertNotIn(str(self.db), response.text)
        self.assertNotIn('SYNTHETIC_ROW_MUST_NEVER_BE_EXPORTED', response.text)

    def test_connection_failure_is_sanitized_for_recoverable_ui(self):
        dsn = 'host=synthetic.invalid password=NEVER_RETURN_THIS'
        with patch('dbvora.api.inspect_postgres',
                   side_effect=PostgresInventoryError('PG_CONNECTION_FAILED')):
            with self.client(dsn) as client:
                response = client.get('/api/postgres')
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()['error']['code'], 'PG_CONNECTION_FAILED')
        self.assertNotIn(dsn, response.text)
        self.assertNotIn('NEVER_RETURN_THIS', response.text)


if __name__ == '__main__':
    unittest.main()
