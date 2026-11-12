"""Synthetic PostgreSQL statistics, metadata-only dashboard and consent contract."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from dbvora.connectors import postgres_statistics as stats
from dbvora.connectors.postgres_reader import inspect_catalog, inspect_postgres
from dbvora.multi_engine_report import assemble_workspace, render_report, ReportError
from tests.test_postgres_reader import Connection


class Cursor:
    def __init__(self, conn): self.conn = conn
    def execute(self, sql, params):
        assert 'FROM pg_catalog.pg_stat_user_tables' in sql
        self.conn.calls.append((sql, params))
    def fetchall(self):
        if isinstance(self.conn.rows, Exception): raise self.conn.rows
        return self.conn.rows
    def close(self): pass


class Fake:
    read_only = True
    def __init__(self, rows): self.rows, self.calls = rows, []
    def cursor(self): return Cursor(self)


def populated():
    conn = Connection()
    base = conn.data
    def data(sql, params):
        if 'FROM pg_catalog.pg_stat_user_tables' in sql:
            return [(1, 320, 4, 8192, 4096), (2, 3, 0, 4096, 4096)]
        return base(sql, params)
    conn.data = data
    return conn


class PostgresStatsTests(unittest.TestCase):
    def test_estimates_distinct_from_measured_bytes(self):
        conn = Fake([(11, 100, 5, 8192, 4096)])
        data = stats.collect_relation_statistics(conn, [11, 12])
        self.assertEqual(data[11]['estimated_live_rows'], 100)
        self.assertEqual(data[11]['heap_bytes'], 8192)
        self.assertIn('not_exact', data[11]['row_count_provenance'])
        self.assertEqual(data[12]['status'], 'unavailable')
        self.assertEqual(conn.calls[0][1], ([11, 12], 301))

    def test_empty_scope_and_readwrite_refusal_do_not_query(self):
        conn = Fake([])
        self.assertEqual(stats.collect_relation_statistics(conn, []), {})
        conn.read_only = False
        with self.assertRaisesRegex(stats.StatisticsError, 'READ_ONLY_CONNECTION_REQUIRED'):
            stats.collect_relation_statistics(conn, [11])
        self.assertEqual(conn.calls, [])

    def test_bad_identifiers_rejected_before_query(self):
        conn = Fake([])
        for ids in ([True], [0], [1, 1], ['1'], [2**32], list(range(1, 302))):
            with self.subTest(ids=repr(ids)[:20]):
                with self.assertRaisesRegex(stats.StatisticsError, 'INVALID_RELATION_IDS'):
                    stats.collect_relation_statistics(conn, ids)
        self.assertFalse(conn.calls)

    def test_permission_failure_does_not_claim_zero(self):
        data = stats.collect_relation_statistics(Fake(RuntimeError('password=SECRET')), [11])
        self.assertEqual(data[11], {'status':'unavailable',
                                    'reason':'pg_statistics_unavailable'})
        self.assertNotIn('SECRET', repr(data))

    def test_bogus_or_duplicate_pg_catalog_rows_rejected(self):
        for rows in ([(11,1,2,3,4),(11,1,2,3,4)], [(11,True,2,3,4)],
                     [(99,1,2,3,4)], [(11,-1,2,3,4)]):
            with self.subTest(rows=rows):
                with self.assertRaisesRegex(stats.StatisticsError, 'INVALID_STATISTICS'):
                    stats.collect_relation_statistics(Fake(rows), [11])

    def test_catalog_opt_in_only(self):
        conn = populated()
        self.assertNotIn('statistics', inspect_catalog(conn)['tables'][0])
        report = inspect_catalog(conn, include_statistics=True)
        self.assertEqual(report['tables'][0]['statistics']['estimated_live_rows'], 320)
        self.assertFalse(report['ready_for_customer_data'])
        self.assertTrue(all(sql.lstrip().startswith('SELECT ') for sql, _ in conn.calls))

    def test_stats_query_failure_reported_unavailable(self):
        conn = Connection()
        base = conn.data
        def data(sql, params):
            if 'FROM pg_catalog.pg_stat_user_tables' in sql: raise RuntimeError('secret')
            return base(sql, params)
        conn.data = data
        result = inspect_catalog(conn, include_statistics=True)
        self.assertEqual(result['tables'][0]['statistics']['status'], 'unavailable')
        self.assertNotIn('secret', repr(result))

    def test_driver_optin_preserves_tls_and_transaction_readonly(self):
        class Session(Connection):
            read_only = False
            def __enter__(self): return self
            def __exit__(self, *_): pass
        conn = Session()
        base = conn.data
        conn.data = lambda sql,args: ([(1,10,0,4096,4096)]
              if 'FROM pg_catalog.pg_stat_user_tables' in sql else base(sql,args))
        calls = []
        def connect(dsn, **kw):
            calls.append((dsn,kw))
            return conn
        with patch.dict('sys.modules', {'psycopg': SimpleNamespace(connect=connect)}):
            output = inspect_postgres('host=example.invalid password=SECRET',
                                      include_statistics=True)
        self.assertEqual(output['tables'][0]['statistics']['estimated_live_rows'],10)
        self.assertEqual(calls[0][1]['sslmode'],'verify-full')
        self.assertTrue(conn.read_only)
        self.assertNotIn('SECRET',repr(output))

    def test_dashboard_separates_estimates_and_storage_metrics(self):
        w = assemble_workspace([inspect_catalog(populated(), include_statistics=True)])
        page = render_report(w)
        self.assertIn('Estimated live rows',page)
        self.assertIn('measured heap',page)
        self.assertIn('"estimated_live_rows":320',page)
        self.assertEqual(w['databases'][0]['tables'][0]['statistics']['heap_bytes'],8192)

    def test_dashboard_rejects_sneaked_credentials(self):
        report = inspect_catalog(populated(),include_statistics=True)
        report['tables'][0]['statistics']['password']='SECRET'
        with self.assertRaisesRegex(ReportError,'INVALID_PG_STATISTICS'):
            assemble_workspace([report])


if __name__=='__main__':
    unittest.main()
