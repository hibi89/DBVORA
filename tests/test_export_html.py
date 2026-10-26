"""No-dependency offline HTML export, safety and source immutability tests."""
from contextlib import closing, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora import export_html as view
from tests.fixtures.make_sqlite import create_fixture


class OfflineHtmlTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='dbvora-html-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.db = create_fixture(self.root / 'synthetic.sqlite')
        self.out = self.root / 'maps'
        self.out.mkdir()

    def identity(self):
        return hashlib.sha256(self.db.read_bytes()).hexdigest(), self.db.stat().st_mtime_ns

    def test_export_one_local_html_with_only_schema(self):
        before = self.identity()
        result = view.export(self.db, self.out)
        html = (self.out / result['filename']).read_text()
        self.assertEqual(result['status'], 'CREATED_OFFLINE_SCHEMA_HTML')
        self.assertFalse(result['ready_for_customer_data'])
        self.assertFalse(result['contains_table_rows'])
        self.assertIn('Content-Security-Policy', html)
        self.assertIn("connect-src 'none'", html)
        self.assertIn('window.fetch = async', html)
        self.assertNotIn('src="/assets/app.js"', html)
        self.assertNotIn('href="/assets/style.css"', html)
        self.assertNotIn(str(self.db), html)
        self.assertNotIn('NOT_FOR_SCHEMA_OUTPUT', html)
        self.assertNotIn('example@invalid.test', html)
        self.assertEqual(self.identity(), before)
        self.assertEqual(result['sha256'], hashlib.sha256(html.encode()).hexdigest())

    def test_unsafe_identifier_base64_not_interpolated_in_html(self):
        attack = '<img src=x onerror=alert(17)></script><script>alert(2)</script>'
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute('CREATE TABLE "' + attack + '" ("<svg onload=alert(9)>" TEXT)')
        data = view.export(self.db, self.out)
        html = (self.out / data['filename']).read_text()
        self.assertNotIn(attack, html)
        self.assertNotIn('<svg onload', html)
        encoded = re.search(r'const localSchemaBase64 = "([a-zA-Z0-9+/=]+)"', html)
        self.assertIsNotNone(encoded)
        import base64
        payload = json.loads(base64.b64decode(encoded.group(1)))
        self.assertIn(attack, [x['name'] for x in payload['tables']])
        self.assertEqual(html.count('<script>'), 2)

    def test_report_names_unique_without_overwrites(self):
        one = view.export(self.db, self.out)
        before = (self.out / one['filename']).read_bytes()
        two = view.export(self.db, self.out)
        self.assertNotEqual(one['filename'], two['filename'])
        self.assertEqual((self.out / one['filename']).read_bytes(), before)

    def test_relative_or_missing_output_rejected(self):
        for p in ('relative', self.root / 'missing'):
            with self.subTest(path=p), self.assertRaisesRegex(view.HtmlExportError, 'INVALID_OUTPUT'):
                view.export(self.db, p)

    def test_symlink_output_refused(self):
        link = self.root / 'alias'
        try:
            link.symlink_to(self.out, target_is_directory=True)
        except (NotImplementedError, OSError):
            return
        with self.assertRaisesRegex(view.HtmlExportError, 'INVALID_OUTPUT'):
            view.export(self.db, link)

    def test_invalid_or_missing_database_no_output(self):
        for p in (self.root / 'missing.sqlite', 'relative.sqlite'):
            with self.subTest(path=p), self.assertRaises(view.HtmlExportError):
                view.export(p, self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_html_template_requires_known_asset_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for asset in ('index.html', 'style.css', 'app.js'):
                (p / asset).write_text('x')
            with self.assertRaisesRegex(view.HtmlExportError, 'UNSAFE_WEB_ASSET'):
                view.render_html({'engine': 'sqlite'}, web=p)

    def test_missing_or_duplicated_security_template_anchors_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            template = (view._WEB / 'index.html').read_text(encoding='utf-8')
            for name in ('style.css', 'app.js'):
                (web / name).write_bytes((view._WEB / name).read_bytes())
            for marker in ('<meta charset="utf-8">', '</body>'):
                for replacement in ('', marker * 2):
                    with self.subTest(marker=marker, replacement_count=len(replacement)):
                        (web / 'index.html').write_text(
                            template.replace(marker, replacement), encoding='utf-8'
                        )
                        with self.assertRaisesRegex(view.HtmlExportError, 'UNSAFE_WEB_ASSET'):
                            view.render_html({'engine': 'sqlite', 'tables': []}, web=web)

    def test_closing_script_in_asset_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'index.html').write_text('<meta charset="utf-8">' + view._STYLE_LINK + view._SCRIPT_LINK + '</body>')
            (p / 'style.css').write_text('x{}')
            (p / 'app.js').write_text('const name = "</script>";')
            with self.assertRaisesRegex(view.HtmlExportError, 'UNSAFE_WEB_ASSET'):
                view.render_html({'engine': 'sqlite'}, web=p)

    def test_invalid_schema_and_oversize_fail(self):
        with self.assertRaisesRegex(view.HtmlExportError, 'INVALID_SCHEMA'):
            view.render_html({'engine': 'postgres'})
        with patch.object(view, '_MAX_HTML_BYTES', 100):
            with self.assertRaisesRegex(view.HtmlExportError, 'REPORT_TOO_LARGE'):
                view.export(self.db, self.out)
        self.assertFalse(list(self.out.iterdir()))

    def test_existing_name_never_overwritten_on_collision(self):
        with patch.object(view.uuid, 'uuid4') as make_uuid:
            make_uuid.return_value.hex = 'a' * 32
            old = self.out / ('dbvora-map-' + 'a' * 32 + '.html')
            old.write_bytes(b'keep')
            with self.assertRaisesRegex(view.HtmlExportError, 'ALREADY_EXISTS'):
                view.export(self.db, self.out)
            self.assertEqual(old.read_bytes(), b'keep')

    def test_cli_outputs_only_safe_filename_not_private_path(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = view.main(['--db', str(self.db), '--out', str(self.out)])
        self.assertEqual(code, 0)
        report = json.loads(output.getvalue())
        self.assertNotIn(str(self.db), output.getvalue())
        self.assertEqual(report['status'], 'CREATED_OFFLINE_SCHEMA_HTML')
        self.assertTrue((self.out / report['filename']).exists())

    def test_source_write_attempt_never_needed(self):
        before = self.identity()
        original = view.inspect_sqlite
        with patch.object(view, 'inspect_sqlite', side_effect=lambda p: original(p)):
            view.export(self.db, self.out)
        self.assertEqual(before, self.identity())


if __name__ == '__main__':
    unittest.main()
