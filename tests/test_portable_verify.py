"""SHA manifest checks for an extracted unsigned preview, no customer content."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import portable_verify as package


class ExtractedPreviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='dbvora-preview-manifest-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.create_package()

    def create_package(self):
        files = {}
        for name in package._REQUIRED:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b'# generated synthetic source only\n')
            files[name] = {'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
                           'bytes': dest.stat().st_size}
        (self.root / 'MANIFEST.sha256.json').write_text(json.dumps({
            'format': 'dbvora-portable-dev-v1', 'unsigned': True, 'files': files}), encoding='utf-8')

    def test_valid_explicit_unsigned_manifest(self):
        result = package.verify(self.root)
        self.assertEqual(result['status'], 'PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY')
        self.assertFalse(result['signed'])
        self.assertFalse(result['publisher_authenticity_verified'])
        self.assertFalse(result['customer_ready'])

    def test_source_bytes_tamper_detected(self):
        target = self.root / 'dbvora/archive/request_service.py'
        target.write_bytes(b'# changed file\n')
        with self.assertRaisesRegex(package.PortableVerifyError, 'PACKAGE_DIGEST_MISMATCH'):
            package.verify(self.root)

    def test_missing_file_rejected(self):
        (self.root / 'dbvora/archive/request_service.py').unlink()
        with self.assertRaisesRegex(package.PortableVerifyError, 'PACKAGE_ENTRY_UNAVAILABLE'):
            package.verify(self.root)

    def test_unlisted_executable_source_rejected(self):
        (self.root / 'sitecustomize.py').write_text('print("bad")')
        with self.assertRaisesRegex(package.PortableVerifyError, 'UNLISTED_PACKAGE_SOURCE'):
            package.verify(self.root)

    def test_manifest_signed_true_rejected(self):
        p = self.root / 'MANIFEST.sha256.json'
        data = json.loads(p.read_text())
        data['unsigned'] = False
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(package.PortableVerifyError, 'INVALID_PACKAGE_MANIFEST'):
            package.verify(self.root)

    def test_manifest_unlisted_db_path_rejected(self):
        p = self.root / 'MANIFEST.sha256.json'
        data = json.loads(p.read_text())
        data['files']['../customer.sqlite'] = {'sha256':'a'*64,'bytes': 1}
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(package.PortableVerifyError, 'INVALID_PACKAGE_MANIFEST'):
            package.verify(self.root)

    def test_manifest_missing_required_code_rejected(self):
        p = self.root / 'MANIFEST.sha256.json'
        data = json.loads(p.read_text())
        data['files'].pop('dbvora/archive/portable_verify.py')
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(package.PortableVerifyError, 'INVALID_PACKAGE_MANIFEST'):
            package.verify(self.root)

    def test_manifest_unreasonable_byte_size_rejected(self):
        p = self.root / 'MANIFEST.sha256.json'
        data = json.loads(p.read_text())
        data['files']['dbvora/archive/review_html.py']['bytes'] = 90000000
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(package.PortableVerifyError, 'INVALID_PACKAGE_MANIFEST'):
            package.verify(self.root)

    def test_manifest_raw_symlink_rejected(self):
        target = self.root / 'dbvora/archive/request_service.py'
        target.unlink()
        try:
            target.symlink_to(self.root / 'dbvora/archive/request_ledger.py')
        except (OSError, NotImplementedError):
            self.skipTest('symlink unsupported')
        with self.assertRaisesRegex(package.PortableVerifyError, 'UNSAFE_PACKAGE_ENTRY'):
            package.verify(self.root)

    def test_manifested_python_cache_tolerated(self):
        cache = self.root / 'dbvora/archive/__pycache__'
        cache.mkdir()
        (cache / 'request_service.cpython-311.pyc').write_bytes(b'generated')
        self.assertEqual(package.verify(self.root)['status'], 'PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY')

    def test_foreign_cache_bytecode_rejected(self):
        cache = self.root / 'dbvora/archive/__pycache__'
        cache.mkdir()
        for name in ('foreign.cpython-311.pyc', 'request_service.pypy310.pyc',
                     'request_service.cpython-311.opt-99.pyc'):
            with self.subTest(name=name):
                path = cache / name
                path.write_bytes(b'INERT-SYNTHETIC')
                try:
                    with self.assertRaisesRegex(
                            package.PortableVerifyError, 'UNLISTED_PACKAGE_SOURCE'):
                        package.verify(self.root)
                finally:
                    path.unlink()

    def test_unmanifested_non_executable_sidecars_rejected(self):
        for name in ('INJECTED_NO_EXTENSION', 'unexpected.ini', 'subfolder/readme.txt',
                     '.hidden_marker'):
            with self.subTest(name=name):
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'INERT-SYNTHETIC')
                try:
                    with self.assertRaisesRegex(
                            package.PortableVerifyError, 'UNLISTED_PACKAGE_SOURCE'):
                        package.verify(self.root)
                finally:
                    path.unlink()

    def test_cache_not_exempt_outside_pycache(self):
        path = self.root / 'dbvora/archive/request_service.cpython-311.pyc'
        path.write_bytes(b'INERT-SYNTHETIC')
        try:
            with self.assertRaisesRegex(
                    package.PortableVerifyError, 'UNLISTED_PACKAGE_SOURCE'):
                package.verify(self.root)
        finally:
            path.unlink()

    def test_cache_symlink_rejected_before_ignored_bytecode(self):
        cache = self.root / 'dbvora/__pycache__'
        cache.mkdir()
        link = cache / 'evil.cpython-311.pyc'
        try:
            link.symlink_to(self.root / 'dbvora/archive/request_service.py')
        except (OSError, NotImplementedError):
            self.skipTest('symlink unsupported')
        with self.assertRaisesRegex(package.PortableVerifyError, 'UNSAFE_PACKAGE_ENTRY'):
            package.verify(self.root)

    def test_unlisted_executable_sidecars_rejected(self):
        # Detect unmanifested native, startup and bytecode executables.
        # A legitimate generated __pycache__/*.pyc is tested separately.
        for name in ('sitecustomize.pyc', 'hook.pth', 'run.cmd',
                     'run.ps1', 'dbvora/archive/hook.pyd',
                     'dbvora/archive/agent.so', 'dbvora/__pycache__/hook.py'):
            with self.subTest(name=name):
                target = self.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'INERT-SYNTHETIC')
                try:
                    with self.assertRaisesRegex(
                            package.PortableVerifyError, 'UNLISTED_PACKAGE_SOURCE'):
                        package.verify(self.root)
                finally:
                    target.unlink()

    def test_bad_name_rejected(self):
        for bad in ('../private.py', 'dbvora/./temp.py', 'dbvora/../sitecustomize.py',
                    'dbvora\\private.py', '/tmp/private.py', '.env', 'customer.sqlite'):
            self.assertFalse(package._valid_name(bad), bad)

    def test_cli_refuses_any_user_supplied_path(self):
        output = io.StringIO()
        with redirect_stdout(output):
            rc = package.main(['--verify', '/private/customer.sqlite'])
        self.assertEqual(rc, 1)
        self.assertEqual(json.loads(output.getvalue())['error_code'], 'NO_USER_INPUT_ALLOWED')
        self.assertNotIn('/private', output.getvalue())

    def test_non_absolute_root_rejected(self):
        with self.assertRaisesRegex(package.PortableVerifyError, 'INVALID_PACKAGE_ROOT'):
            package.verify(Path('relative'))

    def test_no_source_files_are_modified(self):
        before = (self.root / 'dbvora/archive/request_ledger.py').read_bytes()
        package.verify(self.root)
        self.assertEqual(before, (self.root / 'dbvora/archive/request_ledger.py').read_bytes())


if __name__ == '__main__':
    unittest.main()
