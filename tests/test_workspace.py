"""Actual SQLite fixture integrations with existing read-only inventory machinery."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora.errors import InventoryError
from dbvora.workspace import inspect_workspace
from dbvora import workspace_html as html


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dbvora-ws-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = self.root / "main.sqlite"
        self.b = self.root / "other.sqlite"
        with closing(sqlite3.connect(self.a)) as conn:
            conn.executescript("""
                CREATE TABLE parents(id INTEGER PRIMARY KEY);
                CREATE TABLE children(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id));
                INSERT INTO parents VALUES(11);
                INSERT INTO children VALUES(22,11);
            """)
        with closing(sqlite3.connect(self.b)) as conn:
            conn.executescript("""
                CREATE TABLE events(id INTEGER PRIMARY KEY, payload TEXT);
                INSERT INTO events VALUES(33,'SHOULD_NOT_APPEAR_IN_METADATA');
            """)

    def test_real_multi_inventory_scoped_edges_and_sum(self):
        report=inspect_workspace([self.a,self.b]);self.assertEqual(report['database_count'],2)
        self.assertEqual(report['table_count'],3);self.assertEqual(report['cross_database_edges_verified'],0)
        self.assertEqual(len(report['relationships']),1)
        edge=report['relationships'][0];self.assertTrue(edge['target_in_inventory'])
        self.assertEqual(edge['database_id'],report['databases'][0]['db_id'])
        self.assertEqual(edge['from_table'],'children');self.assertEqual(edge['to_table'],'parents')
        self.assertEqual(report['total_main_db_size_bytes'],self.a.stat().st_size+self.b.stat().st_size)
        self.assertEqual(report['cpu_usage'],'unavailable')
        self.assertEqual(report['databases'][0]['size_scope'],'main_database_file_only_excludes_wal_and_shm')
        self.assertNotIn(str(self.a),json.dumps(report));self.assertNotIn(str(self.b),json.dumps(report))
        self.assertNotIn('SHOULD_NOT_APPEAR_IN_METADATA',json.dumps(report))

    def test_reject_duplicate_source_without_alias_path_echo(self):
        with self.assertRaises(InventoryError) as cm:inspect_workspace([self.a,self.a])
        self.assertEqual(cm.exception.code,'DUPLICATE_DATABASE')
        self.assertNotIn(str(self.a),str(cm.exception))

    def test_count_limits(self):
        for paths in [[],[self.a],[self.a]*9,'string']:
            with self.assertRaises(InventoryError) as cm:inspect_workspace(paths)
            self.assertEqual(cm.exception.code,'INVALID_DATABASE_COUNT')

    def test_bad_second_source_fails_without_committed_html(self):
        with self.assertRaises(InventoryError):html.export_workspace([self.a,self.root/'missing.sqlite'],self.root)
        self.assertEqual(list(self.root.glob('dbvora-workspace-*.html')),[])

    def test_html_is_self_contained_and_contains_no_row_data(self):
        result=html.export_workspace([self.a,self.b],self.root)
        self.assertEqual(result['status'],'CREATED_WORKSPACE_HTML')
        out=self.root/result['filename'];content=out.read_bytes()
        self.assertEqual(hashlib.sha256(content).hexdigest(),result['sha256'])
        self.assertEqual(len(content),result['size_bytes'])
        self.assertIn(b'encodedWorkspace',content);self.assertIn(b'connect-src \'none\'',content)
        self.assertNotIn(b'fetch(',content);self.assertNotIn(b'https://',content)
        self.assertEqual(content.count(b'http://'), 1) # W3C SVG namespace, not an outbound request
        self.assertNotIn(b'SHOULD_NOT_APPEAR_IN_METADATA',content)
        self.assertNotIn(str(self.a).encode(),content)
        self.assertFalse(result['ready_for_customer_data'])

    def test_repeated_exports_keep_both_reports(self):
        first=html.export_workspace([self.a,self.b],self.root)
        before=(self.root/first['filename']).read_bytes()
        second=html.export_workspace([self.a,self.b],self.root)
        self.assertNotEqual(first['filename'],second['filename'])
        self.assertEqual(before,(self.root/first['filename']).read_bytes())

    def test_relative_output_refused(self):
        with self.assertRaisesRegex(html.WorkspaceHtmlError,'INVALID_OUTPUT'):
            html.export_workspace([self.a,self.b],'relative-path')

    def test_nested_symlink_output_refused(self):
        link=self.root/'link'
        try:link.symlink_to(self.root,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest('Symlink unavailable')
        with self.assertRaisesRegex(html.WorkspaceHtmlError,'INVALID_OUTPUT'):
            html.export_workspace([self.a,self.b],link)

    def test_untrusted_identifier_not_script_injected(self):
        ugly=self.root/'weird.sqlite'
        with closing(sqlite3.connect(ugly)) as con:
            con.execute('CREATE TABLE "</script><img src=x onerror=alert(1)>" ("<x>" TEXT)')
        out=html.export_workspace([self.a,ugly],self.root)
        body=(self.root/out['filename']).read_text()
        self.assertEqual(body.count('</script>'),1)
        self.assertNotIn('<img src=x onerror=alert(1)>',body)
        self.assertIn('textContent',body)

    def test_workspace_html_invalid_contract(self):
        with self.assertRaisesRegex(html.WorkspaceHtmlError,'INVALID_WORKSPACE'):
            html.render_workspace_html({'contract_version':'unknown','databases':[]})

    def test_synthetic_demo_real_integration(self):
        output=html.export_synthetic_workspace(self.root)
        self.assertTrue(output['synthetic_only'])
        self.assertEqual(output['database_count'],2)
        self.assertEqual(output['table_count'],4)
        self.assertFalse(output['database_file_retained'])
        self.assertNotIn('SYNTHETIC_ROW_DO_NOT_EXPORT',(self.root/output['filename']).read_text())
        self.assertFalse(output['ready_for_customer_data'])

    def test_main_cli_synthetic_only(self):
        from unittest.mock import patch
        import io
        with patch('sys.stdout',new_callable=io.StringIO) as buffer:
            rc=html.main(['--synthetic-only','--out',str(self.root)])
        self.assertEqual(rc,0)
        report=json.loads(buffer.getvalue());self.assertEqual(report['status'],'CREATED_WORKSPACE_HTML')

    def test_two_explicit_dbs_cli(self):
        from unittest.mock import patch
        import io
        with patch('sys.stdout',new_callable=io.StringIO) as buffer:
            rc=html.main(['--db',str(self.a),'--db',str(self.b),'--out',str(self.root)])
        self.assertEqual(rc,0);self.assertNotIn(str(self.a),buffer.getvalue())

    def test_error_cli_does_not_echo_path(self):
        from unittest.mock import patch
        import io
        with patch('sys.stdout',new_callable=io.StringIO) as buffer:
            rc=html.main(['--db',str(self.a),'--db',str(self.root/'PRIVATE-NOT-FOUND.sqlite'),'--out',str(self.root)])
        self.assertNotEqual(rc,0);self.assertNotIn('PRIVATE-NOT-FOUND',buffer.getvalue())

    def test_detect_missing_target_fk_without_fabricating_edge(self):
        missing=self.root/'missing-target.sqlite'
        with closing(sqlite3.connect(missing)) as con:
            con.execute('CREATE TABLE child (id INTEGER, pid INTEGER REFERENCES absent_parent(id))')
        result=inspect_workspace([missing,self.a]);self.assertEqual(result['relationships'][0]['to_table'],'absent_parent')
        self.assertFalse(result['relationships'][0]['target_in_inventory'])


if __name__=='__main__':unittest.main()
