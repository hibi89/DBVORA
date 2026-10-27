"""Cross-DB explicit declarations stay unverified and never touch rows or DB files."""
from contextlib import closing
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora.errors import InventoryError
from dbvora.workspace import inspect_workspace
from dbvora.workspace_links import attach_declared_links, MAX_DECLARED_LINKS
from dbvora import workspace_html as html


def link(**changes):
    item={'from_db':1,'from_table':'products','from_column':'id',
          'to_db':2,'to_table':'invoices','to_column':'product_id'}
    item.update(changes)
    return item


class WorkspaceLinksTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='dbvora-cross-links-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.a=self.root/'a.sqlite';self.b=self.root/'b.sqlite'
        with closing(sqlite3.connect(self.a)) as db:
            db.executescript("CREATE TABLE products(id INTEGER PRIMARY KEY, secret TEXT); INSERT INTO products VALUES(1,'ROW_SECRET_A');")
        with closing(sqlite3.connect(self.b)) as db:
            db.executescript("CREATE TABLE invoices(id INTEGER PRIMARY KEY, product_id INTEGER, secret TEXT); INSERT INTO invoices VALUES(3,1,'ROW_SECRET_B');")

    def inspect(self, declarations):
        return inspect_workspace([self.a,self.b],declared_links=declarations)

    def test_no_link_not_inferred_from_similar_names(self):
        report=self.inspect([])
        self.assertEqual(report['declared_cross_database_links'],[])
        self.assertEqual(report['declared_cross_database_count'],0)
        self.assertEqual(report['cross_database_edges_verified'],0)

    def test_explicit_existing_columns_are_scoped_but_not_verified(self):
        a,b=self.a.read_bytes(),self.b.read_bytes()
        report=self.inspect([link()]); links=report['declared_cross_database_links']
        self.assertEqual(len(links),1)
        self.assertEqual(links[0]['evidence'],'user_declared_unverified')
        self.assertIs(links[0]['verified'],False)
        self.assertNotEqual(links[0]['from_db_id'],links[0]['to_db_id'])
        self.assertEqual(report['cross_database_edges_verified'],0)
        self.assertNotIn('ROW_SECRET_A',json.dumps(report))
        self.assertNotIn('ROW_SECRET_B',json.dumps(report))
        self.assertNotIn(str(self.a),json.dumps(report))
        self.assertEqual((self.a.read_bytes(),self.b.read_bytes()),(a,b))

    def test_invalid_fields_fail_closed(self):
        for entry in ({**link(), 'private_path':'C:/secret'}, {k:v for k,v in link().items() if k!='from_column'}, 'text', []):
            with self.subTest(entry=entry),self.assertRaises(InventoryError):
                self.inspect([entry])

    def test_reject_bad_endpoint_indices(self):
        for modifications in ({'from_db':0},{'from_db':True},{'to_db':3},{'to_db':1},{'to_db':None}):
            with self.subTest(modifications=modifications),self.assertRaises(InventoryError):
                self.inspect([link(**modifications)])

    def test_unknown_table_or_column_fails_closed(self):
        for modifications in ({'from_table':'unknown'},{'to_column':'unknown'},{'from_column':'ROW_SECRET_A'},{'to_table':'missing'}):
            with self.subTest(modifications=modifications),self.assertRaises(InventoryError) as failure:
                self.inspect([link(**modifications)])
            self.assertEqual(failure.exception.code,'UNKNOWN_LINK_COLUMN')

    def test_duplicate_rejected(self):
        with self.assertRaises(InventoryError) as failure:self.inspect([link(),link()])
        self.assertEqual(failure.exception.code,'DUPLICATE_LINK')

    def test_link_count_limit(self):
        with self.assertRaises(InventoryError) as failure:self.inspect([link()]*(MAX_DECLARED_LINKS+1))
        self.assertEqual(failure.exception.code,'INVALID_LINK_COUNT')

    def test_non_list_link_declarations_rejected(self):
        for value in ('hello',{},42):
            with self.assertRaises(InventoryError):self.inspect(value)

    def test_export_html_embeds_only_explicit_link_with_no_rows(self):
        result=html.export_workspace([self.a,self.b],self.root,declared_links=[link()]);self.assertEqual(result['declared_cross_database_count'],1)
        contents=(self.root/result['filename']).read_bytes()
        self.assertIn(b'id="cross-links"',contents)
        self.assertNotIn(b'ROW_SECRET_A',contents);self.assertNotIn(b'ROW_SECRET_B',contents)
        self.assertEqual(hashlib.sha256(contents).hexdigest(),result['sha256'])
        self.assertIn(b'user-declared / unverified',contents)

    def test_synthetic_demo_carries_one_declaration(self):
        result=html.export_synthetic_workspace(self.root)
        self.assertEqual(result['declared_cross_database_count'],1)
        self.assertTrue(result['synthetic_only'])
        self.assertFalse(result['ready_for_customer_data'])

    def test_links_manifest_loads_explicit_json_only(self):
        path=self.root/'links.json';path.write_text(json.dumps([link()]),encoding='utf-8')
        self.assertEqual(html._load_links_manifest(path),[link()])
        with patch('sys.stdout',new_callable=io.StringIO) as output:
            ret=html.main(['--db',str(self.a),'--db',str(self.b),'--links-file',str(path),'--out',str(self.root)])
        self.assertEqual(ret,0)
        self.assertEqual(json.loads(output.getvalue())['declared_cross_database_count'],1)

    def test_relative_invalid_manifest_rejected(self):
        with self.assertRaises(html.WorkspaceHtmlError):html._load_links_manifest('relative.json')
        path=self.root/'bad.json';path.write_text('null')
        with self.assertRaises(html.WorkspaceHtmlError):html._load_links_manifest(path)
        path.write_bytes(b'x'*(16*1024+1))
        with self.assertRaises(html.WorkspaceHtmlError):html._load_links_manifest(path)

    def test_fake_cross_db_relation_must_fail_in_cli_without_path_leak(self):
        path=self.root/'bad-link.json';path.write_text(json.dumps([link(to_column='SECRET_TOKEN')]))
        with patch('sys.stdout',new_callable=io.StringIO) as output:
            code=html.main(['--db',str(self.a),'--db',str(self.b),'--links-file',str(path),'--out',str(self.root)])
        self.assertNotEqual(code,0)
        self.assertNotIn('SECRET_TOKEN',output.getvalue())
        self.assertNotIn(str(self.root),output.getvalue())

    def test_synthetic_mode_does_not_accept_external_link_file(self):
        path=self.root/'links.json';path.write_text('[]')
        with patch('sys.stdout',new_callable=io.StringIO) as output:
            code=html.main(['--synthetic-only','--links-file',str(path),'--out',str(self.root)])
        self.assertNotEqual(code,0)
        self.assertIn('INVALID_LINK_MANIFEST',output.getvalue())


if __name__=='__main__':unittest.main()
