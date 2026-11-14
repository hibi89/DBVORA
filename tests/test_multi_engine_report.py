"""No-user-row-data, no-network mixed PostgreSQL/SQLite HTML QA."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora.inventory import inspect_sqlite
from dbvora.multi_engine_report import ReportError, assemble_workspace, render_report, export_report
from tests.fixtures.make_sqlite import create_fixture


class MultiEngineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='dbvora-mixed-test-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.out = self.root / 'output'
        self.out.mkdir()
        self.file = create_fixture(self.root / 'fixture.sqlite')
        self.sqlite = inspect_sqlite(self.file)
        self.pg = {
            'engine': 'postgresql', 'contract_version': 'dbvora.pg_catalog.v1',
            'tables': [{
                'schema': 'public', 'name': 'accounts', 'relation_kind': 'r',
                'size_bytes': 8192, 'primary_key_columns': ['id'],
                'columns': [{'name': 'id', 'type': 'bigint', 'nullable_declared': False},
                            {'name': 'email', 'type': 'text', 'nullable_declared': True}],
                'indexes': [{'name': 'accounts_pkey', 'unique': True,
                             'partial': False, 'key_columns': ['id']}],
                'foreign_keys': []
            }, {
                'schema': 'public', 'name': 'invoices', 'relation_kind': 'r',
                'size_bytes': 16384, 'primary_key_columns': ['id'],
                'columns': [{'name': 'id', 'type': 'bigint', 'nullable_declared': False},
                            {'name': 'account_id', 'type': 'bigint', 'nullable_declared': False}],
                'indexes': [],
                'foreign_keys': [{'constraint': 'fk_invoice_accounts',
                                  'from_columns': ['account_id'],
                                  'to_schema': 'public', 'to_table': 'accounts',
                                  'to_columns': ['id'],
                                  'target_in_inventory': True}]
            }]
        }

    def mix(self):
        return assemble_workspace([self.sqlite, self.pg])

    def source_fingerprint(self):
        return hashlib.sha256(self.file.read_bytes()).hexdigest(), self.file.stat().st_mtime_ns

    def test_synth_mixed_topology_count_and_only_real_edges(self):
        w = self.mix()
        self.assertEqual(w['database_count'], 2)
        self.assertEqual(w['table_count'], 5)
        self.assertEqual(w['cross_database_edges_verified'], 0)
        self.assertEqual(len(w['databases'][0]['relationships']), 1)
        self.assertEqual(len(w['databases'][1]['relationships']), 1)
        self.assertEqual(w['databases'][1]['relationships'][0]['to'], 'public.accounts')

    def test_pg_primary_key_is_visible(self):
        output = self.mix()
        self.assertTrue(output['databases'][1]['tables'][0]['columns'][0]['primary_key'])
        page = render_report(output)
        self.assertIn('"primary_key":true', page)

    def test_actual_pg_catalog_adapter_normalizes(self):
        from dbvora.connectors.postgres_reader import inspect_catalog
        from tests.test_postgres_reader import Connection
        pg_catalog = inspect_catalog(Connection())
        report = assemble_workspace([self.sqlite, pg_catalog])
        self.assertEqual(report['table_count'], 5)
        self.assertEqual(report['databases'][1]['relationships'][0]['to'], 'public.users')
        self.assertEqual(report['databases'][1]['tables'][0]['columns'][0]['primary_key'], True)

    def test_no_customer_records_paths_or_external_credentials(self):
        content = render_report(self.mix())
        self.assertNotIn(str(self.file), content)
        self.assertNotIn('NOT_FOR_SCHEMA_OUTPUT', content)
        self.assertNotIn('example@invalid.test', content)
        self.assertNotIn('postgresql://', content)
        self.assertNotIn('DSN=', content)
        self.assertNotIn('http://', content)

    def test_markup_and_script_breakout_are_escaped(self):
        schema = '</script><img src=x onerror=alert(1)>'
        self.pg['tables'][0]['name'] = schema
        page = render_report(self.mix())
        self.assertNotIn(schema, page)
        self.assertNotIn('<img src=x', page)
        self.assertIn('\\u003c/script\\u003e', page)

    def test_export_is_new_only_and_preserves_original(self):
        old = self.source_fingerprint()
        a = export_report([self.sqlite, self.pg], self.out)
        b = export_report([self.sqlite, self.pg], self.out)
        self.assertNotEqual(a['filename'], b['filename'])
        self.assertEqual(len(list(self.out.glob('dbvora-*.html'))), 2)
        self.assertEqual(old, self.source_fingerprint())
        self.assertFalse(a['ready_for_customer_data'])

    def test_report_rejects_unsupported_engine(self):
        with self.assertRaisesRegex(ReportError, 'UNSUPPORTED_ENGINE'):
            assemble_workspace([{'engine': 'mysql', 'tables': []}])

    def test_report_rejects_duplicate_table(self):
        self.pg['tables'].append(dict(self.pg['tables'][0]))
        with self.assertRaisesRegex(ReportError, 'DUPLICATE_TABLE'):
            self.mix()

    def test_report_rejects_malformed_column(self):
        self.pg['tables'][0]['columns'].append({'name': '', 'type': 'text'})
        with self.assertRaisesRegex(ReportError, 'INVALID_METADATA'):
            self.mix()

    def test_report_rejects_bogus_size(self):
        self.pg['tables'][0]['size_bytes'] = -1
        with self.assertRaisesRegex(ReportError, 'INVALID_SIZE'):
            self.mix()

    def test_report_drops_unobserved_pg_target(self):
        self.pg['tables'][1]['foreign_keys'][0]['target_in_inventory'] = False
        self.assertEqual(self.mix()['databases'][1]['relationships'], [])

    def test_foreign_key_is_not_promoted_to_cross_engine(self):
        self.pg['tables'][1]['foreign_keys'][0]['to_table'] = 'customers'
        self.assertEqual(self.mix()['databases'][1]['relationships'], [])
        self.assertEqual(self.mix()['cross_database_edges_verified'], 0)

    def test_report_rejects_more_than_eight_databases(self):
        with self.assertRaisesRegex(ReportError, 'INVALID_DATABASE_COUNT'):
            assemble_workspace([self.sqlite] * 9)

    def test_render_rejects_unsupported_contract_version(self):
        fake = self.mix()
        fake['contract_version'] = 'dbvora.multi_engine_offline.v999'
        with self.assertRaisesRegex(ReportError, 'INVALID_WORKSPACE'):
            render_report(fake)

    def test_render_rejects_fake_production_readiness(self):
        fake = self.mix()
        fake['ready_for_customer_data'] = True
        with self.assertRaisesRegex(ReportError, 'INVALID_WORKSPACE'):
            render_report(fake)

    def test_export_rejects_nonexistent_destination_without_creating(self):
        missing = self.root / 'missing'
        with self.assertRaises(ReportError):
            export_report([self.sqlite, self.pg], missing)
        self.assertFalse(missing.exists())

    def test_symlink_destination_rejected(self):
        link = self.root / 'alias'
        try:
            link.symlink_to(self.out, target_is_directory=True)
        except OSError:
            return
        with self.assertRaisesRegex(ReportError, 'BAD_DESTINATION'):
            export_report([self.pg], link)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_staging_failure_preserves_existing_report(self):
        first = export_report([self.pg], self.out)
        prior = (self.out / first['filename']).read_bytes()
        with patch('dbvora.multi_engine_report._publish_new', side_effect=OSError('disk-full')):
            with self.assertRaisesRegex(ReportError, 'REPORT_WRITE_FAILED'):
                export_report([self.pg], self.out)
        self.assertEqual((self.out / first['filename']).read_bytes(), prior)
        self.assertFalse(any(p.suffix == '.part' for p in self.out.iterdir()))

    def test_runtime_bytes_are_bounded(self):
        with patch('dbvora.multi_engine_report.MAX_REPORT_BYTES', 200):
            with self.assertRaisesRegex(ReportError, 'REPORT_TOO_LARGE'):
                render_report(self.mix())


    def test_same_name_collision_uses_explicit_database_and_column_identity(self):
        with closing(sqlite3.connect(self.file)) as db:
            db.execute('CREATE TABLE accounts (id INTEGER PRIMARY KEY)')
            db.commit()
        sqlite_catalog = inspect_sqlite(self.file)
        link = {
            'from_db': 1, 'from_schema': None, 'from_table': 'accounts', 'from_column': 'id',
            'to_db': 2, 'to_schema': 'public', 'to_table': 'accounts', 'to_column': 'id',
        }
        without_declaration = assemble_workspace([sqlite_catalog, self.pg])
        self.assertEqual(without_declaration['declared_cross_database_links'], [])
        self.assertEqual(without_declaration['cross_database_edges_verified'], 0)
        report = assemble_workspace([sqlite_catalog, self.pg], declared_links=[link])
        declared = report['declared_cross_database_links']
        self.assertEqual(len(declared), 1)
        edge = declared[0]
        self.assertEqual((edge['from_db_id'], edge['from_schema'], edge['from_table']),
                         (1, None, 'accounts'))
        self.assertEqual((edge['to_db_id'], edge['to_schema'], edge['to_table']),
                         (2, 'public', 'accounts'))
        self.assertNotEqual(edge['from_table_identity'], edge['to_table_identity'])
        self.assertEqual(edge['evidence'], 'user_declared_unverified')
        self.assertIs(edge['verified'], False)
        self.assertEqual(report['cross_database_edges_verified'], 0)
        page = render_report(report)
        exported = export_report([sqlite_catalog, self.pg], self.out, declared_links=[link])
        self.assertEqual(exported['declared_cross_database_count'], 1)
        self.assertIn('id="cross-database-links"', page)
        self.assertIn('Relationships are never inferred.', page)
        payload = page.split('<script type="application/json" id="catalog">', 1)[1].split('</script>', 1)[0]
        model = json.loads(payload)
        self.assertEqual(model['declared_cross_database_links'][0]['to_table_identity'],
                         edge['to_table_identity'])

    def test_mixed_declared_link_rejects_ambiguous_or_unscoped_endpoints(self):
        sqlite_catalog = self.sqlite
        valid = {
            'from_db': 1, 'from_schema': None, 'from_table': 'customers', 'from_column': 'id',
            'to_db': 2, 'to_schema': 'public', 'to_table': 'accounts', 'to_column': 'id',
        }
        for patch in ({'from_db': 2}, {'to_db': 1}, {'from_db': True},
                      {'from_schema': 'public'}, {'to_column': 'missing'},
                      {'to_table': 'missing'}, {'to_schema': None}):
            with self.subTest(patch=patch), self.assertRaises(ReportError):
                assemble_workspace([sqlite_catalog, self.pg], declared_links=[{**valid, **patch}])

    def test_mixed_declared_links_reject_duplicates_and_limit(self):
        valid = {
            'from_db': 1, 'from_schema': None, 'from_table': 'customers', 'from_column': 'id',
            'to_db': 2, 'to_schema': 'public', 'to_table': 'accounts', 'to_column': 'id',
        }
        with self.assertRaisesRegex(ReportError, 'DUPLICATE_LINK'):
            assemble_workspace([self.sqlite, self.pg], declared_links=[valid, valid])
        with self.assertRaisesRegex(ReportError, 'INVALID_LINK_COUNT'):
            assemble_workspace([self.sqlite, self.pg], declared_links=[valid] * 65)

    def test_postgres_same_table_name_in_multiple_schemas_is_unambiguous(self):
        one = {
            'schema': 'a.b', 'name': 'c', 'size_bytes': None, 'primary_key_columns': [],
            'columns': [{'name': 'id', 'type': 'integer'}], 'indexes': [], 'foreign_keys': [],
        }
        two = {
            'schema': 'a', 'name': 'b.c', 'size_bytes': None, 'primary_key_columns': [],
            'columns': [{'name': 'id', 'type': 'integer'}], 'indexes': [], 'foreign_keys': [],
        }
        pg = {'engine': 'postgresql', 'tables': [one, two]}
        report = assemble_workspace([pg])
        tables = report['databases'][0]['tables']
        self.assertEqual(len({table['identity'] for table in tables}), 2)
        self.assertNotEqual(tables[0]['key'], tables[1]['key'])



    def test_render_cannot_promote_declared_link_to_verified_relationship(self):
        link = {
            'from_db': 1, 'from_schema': None, 'from_table': 'customers', 'from_column': 'id',
            'to_db': 2, 'to_schema': 'public', 'to_table': 'accounts', 'to_column': 'id',
        }
        workspace = assemble_workspace([self.sqlite, self.pg], declared_links=[link])
        workspace['declared_cross_database_links'][0]['verified'] = True
        workspace['declared_cross_database_links'][0]['evidence'] = 'declared_foreign_key'
        page = render_report(workspace)
        payload = page.split('<script type="application/json" id="catalog">', 1)[1].split('</script>', 1)[0]
        embedded = json.loads(payload)
        restored = embedded['declared_cross_database_links'][0]
        self.assertEqual(restored['evidence'], 'user_declared_unverified')
        self.assertIs(restored['verified'], False)
        self.assertEqual(embedded['cross_database_edges_verified'], 0)



if __name__ == '__main__':
    unittest.main()
