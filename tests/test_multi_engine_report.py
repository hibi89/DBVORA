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


if __name__ == '__main__':
    unittest.main()
