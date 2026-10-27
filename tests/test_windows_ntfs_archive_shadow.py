"""Synthetic shadow archive research only; no customer or real NTFS certification."""
import json
import warnings
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from scripts import windows_ntfs_archive_shadow as shadow


def simulated_create_only(source, target):
    os.link(source, target)
    source.unlink()


class ShadowArchiveTests(unittest.TestCase):
    def test_linux_denied_before_creating_fixture(self):
        with patch.object(shadow, '_exercise_shadow', side_effect=AssertionError('must not run')):
            output = shadow.run_probe(platform_name='Linux', python_version=(3, 11), filesystem='NTFS')
        self.assertEqual(output['reason'], 'WINDOWS_REQUIRED')
        self.assertFalse(output['native_windows_tested'])

    def test_unsupported_python_denied(self):
        output = shadow.run_probe(platform_name='Windows', python_version=(3, 12), filesystem='NTFS')
        self.assertEqual(output['reason'], 'PYTHON311_REQUIRED')

    def test_non_ntfs_denied(self):
        output = shadow.run_probe(platform_name='Windows', python_version=(3, 11), filesystem='FAT32')
        self.assertEqual(output['reason'], 'NTFS_TEMP_REQUIRED')

    def test_simulated_roundtrip_is_not_native_durability(self):
        output = shadow.run_probe(platform_name='Windows', python_version=(3, 11),
                                  filesystem='NTFS', move=simulated_create_only)
        self.assertEqual(output['status'], 'PASS_SIMULATED_ONLY')
        self.assertEqual(output['steps_passed'], 7)
        self.assertTrue(output['independent_zip_restore_verified'])
        self.assertTrue(output['source_unchanged'])
        self.assertFalse(output['native_windows_tested'])
        self.assertFalse(output['ready_for_customer_data'])
        self.assertFalse(output['power_loss_durable_verified'])
        self.assertFalse(output['production_archive_integrated'])

    def test_injected_publish_failure_fails_closed(self):
        def failing(*_args):
            raise shadow.WinPublishError('INJECTED_FAILURE')
        output = shadow.run_probe(platform_name='Windows', python_version=(3, 11),
                                  filesystem='NTFS', move=failing)
        self.assertEqual(output['status'], 'BLOCKED_UNVERIFIED')
        self.assertEqual(output['reason'], 'INJECTED_FAILURE')
        self.assertNotIn(tempfile.gettempdir(), json.dumps(output))

    def test_corrupted_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as obj:
                obj.writestr('manifest.json', '{}')
                obj.writestr('snapshot.sqlite', b'bad-data')
            with self.assertRaisesRegex(shadow.ShadowError, 'ZIP_MANIFEST_INVALID'):
                shadow._verify_zip(archive, 'a' * 64, Path(temp))

    def test_duplicate_zip_members_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / 'duplicate.zip'
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(archive, 'w') as obj:
                    obj.writestr('manifest.json', '{}')
                    obj.writestr('snapshot.sqlite', b'bad-data')
                    obj.writestr('snapshot.sqlite', b'other-data')
            with self.assertRaisesRegex(shadow.ShadowError, 'ZIP_ENTRIES_INVALID'):
                shadow._verify_zip(archive, 'a' * 64, Path(temp))

    def test_changing_published_archive_detected(self):
        counter = [0]
        def mover(source, target):
            simulated_create_only(source, target)
            counter[0] += 1
            if counter[0] == 2:
                target.write_bytes(b'mutated')
        output = shadow.run_probe(platform_name='Windows', python_version=(3, 11),
                                  filesystem='NTFS', move=mover)
        self.assertEqual(counter[0], 2)
        self.assertEqual(output['status'], 'BLOCKED_UNVERIFIED')
        self.assertEqual(output['reason'], 'PUBLISHED_BYTES_DIFFER')


if __name__ == '__main__':
    unittest.main()
