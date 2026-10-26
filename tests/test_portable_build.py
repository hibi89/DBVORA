"""Offline package provenance, tamper rejection and new-name publication tests."""
import hashlib
import os
import subprocess
import sys
from tests.fixtures.make_sqlite import create_fixture
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import build_portable as pack


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dbvora-portable-tests-')
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def test_build_and_verify_unsigned(self):
        file = pack.build(self.folder)
        check = pack.verify_zip(file)
        self.assertEqual(check['status'], 'PASS_UNSIGNED_SOURCE_INTEGRITY_ONLY')
        self.assertFalse(check['ready_for_customer_data'])
        self.assertFalse(check['signed'])

    def test_bundle_has_explicit_allowlist_and_no_customer_db(self):
        file = pack.build(self.folder)
        with zipfile.ZipFile(file) as z:
            names = z.namelist()
            self.assertTrue(pack._REQUIRED.issubset(names))
            self.assertTrue(all(not n.endswith(('.sqlite', '.db', '.env', '.pyc')) for n in names))
            self.assertNotIn('tests/test_receipts.py', names)
            self.assertIn('C:\\absolute', z.read('README_PORTABLE.txt').decode('utf-8'))

    def test_determinism_rebuild_in_new_folder(self):
        a = pack.build(self.folder)
        bdir = self.folder / 'second'
        bdir.mkdir()
        b = pack.build(bdir)
        self.assertEqual(hashlib.sha256(a.read_bytes()).digest(), hashlib.sha256(b.read_bytes()).digest())

    def test_existing_archive_refused_without_overwrite(self):
        file = pack.build(self.folder)
        digest = hashlib.sha256(file.read_bytes()).digest()
        with self.assertRaisesRegex(pack.PortableError, 'ALREADY_EXISTS'):
            pack.build(self.folder)
        self.assertEqual(hashlib.sha256(file.read_bytes()).digest(), digest)

    def test_relative_output_refused(self):
        with self.assertRaisesRegex(pack.PortableError, 'INVALID_OUTPUT'):
            pack.build(Path('relative'))

    def test_symlinked_output_refused(self):
        link = self.folder / 'link'
        link.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaisesRegex(pack.PortableError, 'INVALID_OUTPUT'):
            pack.build(link)

    def _mutate(self, change):
        original = pack.build(self.folder)
        invalid = self.folder / 'changed.zip'
        with zipfile.ZipFile(original) as src, zipfile.ZipFile(invalid, 'w') as dst:
            for item in src.infolist():
                data = src.read(item)
                dst.writestr(item.filename, change(item.filename, data))
        return invalid

    def test_mutated_payload_rejected(self):
        changed = self._mutate(lambda n,d: (b'X' + d[1:]) if n=='dbvora/__init__.py' else d)
        with self.assertRaisesRegex(pack.PortableError, 'CHECKSUM_MISMATCH'):
            pack.verify_zip(changed)

    def test_extra_member_rejected(self):
        changed = self._mutate(lambda n,d: d)
        with zipfile.ZipFile(changed,'a') as z:
            z.writestr('password.txt', 'not allowed')
        with self.assertRaisesRegex(pack.PortableError, 'INVALID_MANIFEST'):
            pack.verify_zip(changed)

    def test_path_traversal_rejected(self):
        changed = self._mutate(lambda n,d: d)
        with zipfile.ZipFile(changed,'a') as z:
            z.writestr('../escape.txt', 'unsafe')
        with self.assertRaisesRegex(pack.PortableError, 'INVALID_MEMBERS'):
            pack.verify_zip(changed)

    def test_truncated_zip_rejected(self):
        file = pack.build(self.folder)
        file.write_bytes(file.read_bytes()[:40])
        with self.assertRaisesRegex(pack.PortableError, 'INVALID_ARCHIVE'):
            pack.verify_zip(file)

    def test_missing_required_source_refused(self):
        with patch.object(pack, '_contents', return_value={'pyproject.toml': b'dummy'}):
            data = pack._zip_bytes(pack.ROOT)
        path = self.folder / 'missing.zip'
        path.write_bytes(data)
        with self.assertRaisesRegex(pack.PortableError, 'INVALID_MANIFEST'):
            pack.verify_zip(path)

    def test_extracted_source_cli_executes_on_synthetic_db(self):
        file = pack.build(self.folder)
        self.assertEqual(pack.verify_zip(file)['status'], 'PASS_UNSIGNED_SOURCE_INTEGRITY_ONLY')
        extracted = self.folder / 'unpacked'
        extracted.mkdir()
        with zipfile.ZipFile(file) as archive:
            archive.extractall(extracted)
        fixture = create_fixture(self.folder / 'test-only.sqlite')
        before = hashlib.sha256(fixture.read_bytes()).hexdigest()
        env = dict(os.environ, PYTHONPATH='')
        done = subprocess.run([sys.executable, '-m', 'dbvora', 'inspect', str(fixture)],
                              cwd=extracted, env=env, capture_output=True, text=True,
                              timeout=10, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(json.loads(done.stdout)['tables']), 3)
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(), before)

    def test_version_matches_module(self):
        import dbvora
        self.assertEqual(pack._version(pack.ROOT), dbvora.__version__)


if __name__ == '__main__':
    unittest.main()
