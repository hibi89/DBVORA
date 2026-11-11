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

    def test_bundle_includes_synthetic_archive_selfcheck_and_launchers(self):
        archive = pack.build(self.folder)
        self.assertEqual(pack.verify_zip(archive)['status'], 'PASS_UNSIGNED_SOURCE_INTEGRITY_ONLY')
        with zipfile.ZipFile(archive) as zipped:
            members = set(zipped.namelist())
            self.assertIn('dbvora/archive/review_selftest.py', members)
            self.assertIn('check_dbvora_archive_windows.cmd', members)
            self.assertIn('check_dbvora_archive_unix.sh', members)
            self.assertIn(b'dbvora.archive.review_selftest', zipped.read('check_dbvora_archive_windows.cmd'))
            self.assertIn(b'dbvora.archive.review_selftest', zipped.read('check_dbvora_archive_unix.sh'))
            self.assertIn('no customer path', zipped.read('README_PORTABLE.txt').decode('utf-8'))
            self.assertFalse(any(name.startswith('tests/') for name in members))

    def test_unpacked_portable_selfcheck_from_separate_process(self):
        # The actual shipped portable ZIP executes only generated temp SQLite.
        # On native Windows a separate NTFS durability gate is required.
        archive = pack.build(self.folder)
        destination = self.folder / 'separate_unpacked'
        destination.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(destination)
        env = dict(os.environ, PYTHONPATH='')
        executed = subprocess.run(
            [sys.executable, '-m', 'dbvora.archive.review_selftest'],
            cwd=destination, env=env, capture_output=True, text=True,
            timeout=45, check=False)
        result = json.loads(executed.stdout)
        self.assertFalse(result['customer_ready'])
        self.assertFalse(result['windows_ntfs_durability_verified'])
        self.assertFalse(result.get('hardware_power_loss_verified', False))
        if os.name != 'nt':
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(result['status'], 'PASS_SYNTHETIC_PREVIEW_ONLY')
            self.assertEqual(result['zip'], 'passed')
            self.assertIn(result['zstd'], ('passed', 'skipped_no_local_codec'))
        else:
            # Never mistake Linux POSIX success for Windows durability.
            self.assertIn(result['status'], ('PASS_SYNTHETIC_PREVIEW_ONLY', 'FAIL_CLOSED'))

    def test_packaged_selfcheck_refuses_supplied_customer_file(self):
        archive = pack.build(self.folder)
        destination = self.folder / 'no_input_unpacked'
        destination.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(destination)
        completed = subprocess.run(
            [sys.executable, '-m', 'dbvora.archive.review_selftest',
             '--db', 'C:\\customer\\private.sqlite'],
            cwd=destination, env=dict(os.environ, PYTHONPATH=''),
            capture_output=True, text=True, timeout=12, check=False)
        self.assertNotEqual(completed.returncode, 0)
        report = json.loads(completed.stdout)
        self.assertEqual(report['error_code'], 'NO_USER_INPUT_ALLOWED')
        self.assertNotIn('private.sqlite', completed.stdout)

    def test_extracted_source_verifier_passes_unsigned_manifest(self):
        archive = pack.build(self.folder)
        self.assertEqual(pack.verify_zip(archive)['status'], 'PASS_UNSIGNED_SOURCE_INTEGRITY_ONLY')
        dest = self.folder / 'verified_extraction'
        dest.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(dest)
            self.assertIn('dbvora/archive/portable_verify.py', zipped.namelist())
            self.assertIn('verify_dbvora_portable_windows.cmd', zipped.namelist())
            self.assertIn('verify_dbvora_portable_unix.sh', zipped.namelist())
        env = dict(os.environ, PYTHONPATH='')
        result = subprocess.run([sys.executable, '-B', '-m',
                                 'dbvora.archive.portable_verify'],
                                cwd=dest, env=env, capture_output=True,
                                text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        verification = json.loads(result.stdout)
        self.assertEqual(verification['status'], 'PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY')
        self.assertFalse(verification['publisher_authenticity_verified'])
        self.assertFalse(verification['customer_ready'])

    def test_extracted_source_verifier_rejects_modified_script(self):
        archive = pack.build(self.folder)
        dest = self.folder / 'tamper_extraction'
        dest.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(dest)
        with (dest / 'dbvora/archive/request_service.py').open('ab') as stream:
            stream.write(b'\\n# appended\n')
        result = subprocess.run([sys.executable, '-B', '-m',
                                 'dbvora.archive.portable_verify'],
                                cwd=dest, env=dict(os.environ, PYTHONPATH=''),
                                capture_output=True, text=True,
                                timeout=15, check=False)
        self.assertNotEqual(result.returncode, 0)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence['status'], 'FAIL_CLOSED')
        self.assertEqual(evidence['error_code'], 'PACKAGE_DIGEST_MISMATCH')

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

    def test_packaged_offline_export_zero_ui_dependencies(self):
        archive = pack.build(self.folder)
        destination = self.folder / 'unpacked_offline'
        destination.mkdir()
        with zipfile.ZipFile(archive) as z:
            z.extractall(destination)
            self.assertIn('dbvora/export_html.py', z.namelist())
            self.assertIn('export_dbvora_map_windows.cmd', z.namelist())
            self.assertIn('export_dbvora_map_unix.sh', z.namelist())
        out = self.folder / 'offline_reports'
        out.mkdir()
        src = create_fixture(self.folder / 'synthetic_export.sqlite')
        before = hashlib.sha256(src.read_bytes()).hexdigest()
        env = dict(os.environ, PYTHONPATH='')
        process = subprocess.run(
            [sys.executable, '-m', 'dbvora.export_html', '--db', str(src), '--out', str(out)],
            cwd=destination, env=env, text=True, capture_output=True, timeout=12, check=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        response = json.loads(process.stdout)
        self.assertEqual(response['status'], 'CREATED_OFFLINE_SCHEMA_HTML')
        self.assertIn('Content-Security-Policy', (out / response['filename']).read_text())
        self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(), before)

    def test_extracted_portable_offline_selfcheck_needs_no_pip_or_customer_db(self):
        archive = pack.build(self.folder)
        destination = self.folder / 'unpacked_selfcheck'
        destination.mkdir()
        with zipfile.ZipFile(archive) as z:
            z.extractall(destination)
            self.assertIn('dbvora/offline_selftest.py', z.namelist())
            self.assertIn('check_dbvora_windows.cmd', z.namelist())
            self.assertIn('check_dbvora_unix.sh', z.namelist())
        env = dict(os.environ, PYTHONPATH='')
        process = subprocess.run(
            [sys.executable, '-m', 'dbvora.offline_selftest'],
            cwd=destination, env=env, text=True, capture_output=True,
            timeout=15, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        response = json.loads(process.stdout)
        self.assertEqual(response['status'], 'PASS_SYNTHETIC_OFFLINE_HTML_ONLY')
        self.assertEqual(response['checks_passed'], 9)
        self.assertEqual(response['expected_checks'], 9)
        self.assertFalse(response['ready_for_customer_data'])
        self.assertFalse(response['windows_ntfs_durability_verified'])
        self.assertFalse(response['native_file_browser_verified'])

    def test_synthetic_launchers_never_install_or_take_customer_arguments(self):
        archive = pack.build(self.folder)
        with zipfile.ZipFile(archive) as z:
            for file, expected in (
                ('check_dbvora_windows.cmd', 'py -3.11 -m dbvora.offline_selftest'),
                ('check_dbvora_unix.sh', 'python3 -m dbvora.offline_selftest'),
            ):
                launcher = z.read(file).decode('utf-8').lower()
                self.assertIn(expected, launcher)
                self.assertIn('no arguments', launcher)
                for forbidden in ('pip install', 'curl', 'wget', 'invoke-webrequest',
                                  'dbvora.export_html --db', 'del ', 'rm -'):
                    self.assertNotIn(forbidden, launcher)

    def test_launcher_has_no_network_downloads(self):
        archive = pack.build(self.folder)
        with zipfile.ZipFile(archive) as z:
            for path in ('export_dbvora_map_windows.cmd', 'export_dbvora_map_unix.sh'):
                content = z.read(path).decode('utf-8').lower()
                self.assertIn('dbvora.export_html', content)
                self.assertNotIn('pip install', content)
                self.assertNotIn('curl', content)
                self.assertNotIn('wget', content)

    def test_version_matches_module(self):
        import dbvora
        self.assertEqual(pack._version(pack.ROOT), dbvora.__version__)


if __name__ == '__main__':
    unittest.main()
