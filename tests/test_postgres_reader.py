"""Pure-offline PostgreSQL catalog contract tests; no real network/credentials."""
from __future__ import annotations

import unittest
from unittest.mock import patch
from types import SimpleNamespace
from dbvora.connectors import postgres_reader as pg


class Cursor:
    def __init__(self, connection):
        self.conn = connection
    def execute(self, sql, args):
        self.conn.calls.append((sql,args))
        if not sql.lstrip().startswith('SELECT '):
            raise AssertionError('non-readonly SQL')
        if 'FROM pg_catalog.' not in sql:
            raise AssertionError('not pg_catalog')
        if len(args) > 2:
            raise AssertionError('unbound or excessive SQL')
        self.current = self.conn.data(sql, args)
        return self
    def fetchall(self):
        return self.current
    def close(self):
        pass


class Connection:
    read_only = True
    def __init__(self, tables=None, cols=None, idx=None, fks=None, pks=None):
        self.calls=[]
        self.tables=tables if tables is not None else [
            ('public','users',1,'r',8192),('public','orders',2,'r',16384)]
        self.cols=cols or {1:[('id','integer',True,1),('email','text',False,2)],
                           2:[('id','bigint',True,1),('user_id','integer',True,2)]}
        self.idx=idx or {1:[('users_pkey',True,True,False,[1],1)],
                         2:[('ix_orders_user',False,False,False,[2],1)]}
        self.fks=fks or {2:[('orders_user_fk',1,[2],[1])]}
        self.pks=pks or {1:[([1],)],2:[([1],)]}
    def cursor(self): return Cursor(self)
    def data(self, sql, params):
        if 'FROM pg_catalog.pg_class AS c' in sql: return self.tables
        if 'FROM pg_catalog.pg_attribute' in sql: return self.cols.get(params[0],[])
        if 'FROM pg_catalog.pg_index AS ix' in sql: return self.idx.get(params[0],[])
        if 'FROM pg_catalog.pg_constraint' in sql and "contype = 'p'" in sql:
            return self.pks.get(params[0],[])
        if 'FROM pg_catalog.pg_constraint' in sql and "contype = 'f'" in sql:
            return self.fks.get(params[0],[])
        raise AssertionError('unrecognized catalog query')


class PostgresCatalogTests(unittest.TestCase):
    def test_metadata_and_relationship(self):
        conn=Connection()
        result=pg.inspect_catalog(conn)
        self.assertEqual(result['engine'],'postgresql')
        self.assertEqual(result['table_count'],2)
        self.assertEqual(result['tables'][0]['primary_key_columns'],['id'])
        fk=result['relationships'][0]
        self.assertEqual(fk['from_columns'],['user_id'])
        self.assertEqual(fk['to_table'],'users')
        self.assertEqual(fk['to_columns'],['id'])
        self.assertFalse(result['ready_for_customer_data'])
        self.assertEqual(result['cpu_usage'],'unavailable')

    def test_queries_never_interpolate_table_names(self):
        conn=Connection(tables=[('public', 'x";DELETE FROM secrets;--',1,'r',1)])
        result=pg.inspect_catalog(conn)
        self.assertIn('DELETE',result['tables'][0]['name'])
        self.assertTrue(all('DELETE FROM secrets' not in sql for sql,_ in conn.calls))
        self.assertTrue(all('pg_catalog' in sql for sql,_ in conn.calls))

    def test_read_write_connection_refused_before_query(self):
        conn=Connection();conn.read_only=False
        with self.assertRaisesRegex(pg.PostgresInventoryError,'READ_ONLY_CONNECTION_REQUIRED'):
            pg.inspect_catalog(conn)
        self.assertFalse(conn.calls)

    def test_empty_catalog(self):
        c=Connection(tables=[])
        result=pg.inspect_catalog(c)
        self.assertEqual(result['tables'],[])
        self.assertEqual(result['relationships'],[])

    def test_table_limit_rejected_without_followup(self):
        c=Connection(tables=[('s',f't{i}',i+1,'r',1) for i in range(pg.MAX_TABLES+1)])
        with self.assertRaisesRegex(pg.PostgresInventoryError,'CATALOG_LIMIT'):
            pg.inspect_catalog(c)
        self.assertEqual(len(c.calls),1)

    def test_expression_index_none_and_partial(self):
        c=Connection(idx={1:[('expression',False,False,True,[0],1)]})
        table=pg.inspect_catalog(c)['tables'][0]
        self.assertEqual(table['indexes'][0]['key_columns'],[None])
        self.assertTrue(table['indexes'][0]['partial'])

    def test_unlisted_target_fk_does_not_claim_internal_link(self):
        c=Connection(fks={2:[('other',999,[2],[1])]})
        fk=pg.inspect_catalog(c)['tables'][1]['foreign_keys'][0]
        self.assertFalse(fk['target_in_inventory'])
        self.assertIsNone(fk['to_table'])

    def test_invalid_attribute_types_rejected_safely(self):
        c=Connection(cols={1:[('id',42,True,1)]})
        with self.assertRaisesRegex(pg.PostgresInventoryError,'INVALID_CATALOG'):
            pg.inspect_catalog(c)

    def test_catalog_db_exception_does_not_leak(self):
        c=Connection()
        c.data=lambda *_: (_ for _ in ()).throw(RuntimeError('password=secret'))
        with self.assertRaises(pg.PostgresInventoryError) as exc:
            pg.inspect_catalog(c)
        self.assertEqual(exc.exception.code,'PG_CATALOG_QUERY_FAILED')
        self.assertNotIn('secret',str(exc.exception))

    def test_driver_unavailable_safe(self):
        with patch.dict('sys.modules',{'psycopg':None}):
            with self.assertRaisesRegex(pg.PostgresInventoryError,'DRIVER_UNAVAILABLE'):
                pg.inspect_postgres('host=localhost dbname=foo')

    def test_bad_dsn_refused(self):
        for value in (None,'','secret'*1000):
            with self.assertRaisesRegex(pg.PostgresInventoryError,'INVALID_DSN'):
                pg.inspect_postgres(value)

    def test_optional_psycopg_connection_sets_readonly_and_tls(self):
        class FakeConnection(Connection):
            read_only = False
            def __enter__(self): return self
            def __exit__(self, *args): pass
        fake=FakeConnection()
        observed=[]
        def connect(dsn, **kwargs):
            observed.append((dsn,kwargs))
            return fake
        with patch.dict('sys.modules',{'psycopg':SimpleNamespace(connect=connect)}):
            report=pg.inspect_postgres('host=example.invalid dbname=fake')
        self.assertEqual(report['table_count'],2)
        self.assertTrue(fake.read_only)
        self.assertEqual(observed[0][1]['sslmode'],'verify-full')
        self.assertEqual(observed[0][1]['connect_timeout'],5)
        self.assertFalse(observed[0][1]['autocommit'])

    def test_bad_index_key_count_is_rejected(self):
        c=Connection(idx={1:[('bad',False,False,False,[1],2)]})
        with self.assertRaisesRegex(pg.PostgresInventoryError,'INVALID_CATALOG'):
            pg.inspect_catalog(c)

    def test_invisible_referenced_column_rejected(self):
        c=Connection(fks={2:[('bad',1,[2],[999])]})
        with self.assertRaisesRegex(pg.PostgresInventoryError,'INVALID_CATALOG'):
            pg.inspect_catalog(c)

    def test_tls_disable_rejected(self):
        with self.assertRaisesRegex(pg.PostgresInventoryError,'TLS_REQUIRED'):
            pg.inspect_postgres('host=localhost',require_tls=False)


if __name__=='__main__':unittest.main()
