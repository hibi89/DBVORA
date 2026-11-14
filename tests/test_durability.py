"""C2: synthetic failure injection, safe orphan inventory, concurrent publication."""
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from dbvora.archive import safe_zip
from dbvora.archive.safe_zip import (
    ArchiveError, create_snapshot, make_zip_archive, restore_zip_archive,
    _staging_file, _staging_files, _publish_new,
    inspect_stale_temps, cleanup_stale_temps,
)
from dbvora.archive.zstd_archive import create_zstd_archive, restore_zstd_archive
from tests.fixtures.make_sqlite import create_fixture


def _process_snapshot(path: str, output_dir: str) -> tuple[str, str]:
    out = create_snapshot(path, output_dir)
    return out['snapshot_path'], out['snapshot_sha256']


class DurabilityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.out = self.root / 'out'
        self.out.mkdir()
        self.restore = self.root / 'restore'
        self.restore.mkdir()
        self.db = create_fixture(self.root / 'fixture.sqlite')
        self.source_before = self.fingerprint(self.db)

    @staticmethod
    def fingerprint(path):
        file = Path(path)
        return hashlib.sha256(file.read_bytes()).hexdigest(), file.stat().st_mtime_ns

    def files(self):
        return sorted(x.name for x in self.out.iterdir())

    def older(self, path, hours=48):
        older = time.time() - hours * 3600
        try:
            os.utime(path, (older, older), follow_symlinks=False)
        except NotImplementedError:
            # Python 3.11 Windows does not expose follow_symlinks=False.
            # This test fixture is a regular locally-created file only.
            if path.is_symlink() or not path.is_file():
                raise
            os.utime(path, (older, older))

    def test_publish_syncs_file_then_parent_after_link(self):
        order = []
        real_file = safe_zip._sync_staged_file
        real_parent = safe_zip._sync_directory
        with patch.object(safe_zip, '_sync_staged_file', side_effect=lambda path: (order.append('file'), real_file(path))), \
             patch.object(safe_zip, '_sync_directory', side_effect=lambda path: (order.append('directory'), real_parent(path))):
            result = create_snapshot(self.db, self.out)
        self.assertEqual(order, ['file', 'directory'] if os.name != 'nt' else ['file'])
        self.assertTrue(Path(result['snapshot_path']).exists())
        self.assertEqual(self.source_before, self.fingerprint(self.db))

    def test_directory_sync_failure_after_link_rolls_back_only_new_name(self):
        old = create_snapshot(self.db, self.out)
        old_hash = self.fingerprint(old['snapshot_path'])
        before = self.files()
        if os.name == 'nt':
            # Simulate a native no-replace move failure without touching old.
            from dbvora.archive import windows_ntfs_publish as native
            failure = patch.object(native, '_native_move_write_through', side_effect=native.WinPublishError('MOVE_FAILED'))
        else:
            failure = patch.object(safe_zip, '_sync_directory', side_effect=ArchiveError('DURABILITY_UNAVAILABLE', 'test'))
        with failure:
            with self.assertRaises(ArchiveError) as ctx:
                create_snapshot(self.db, self.out)
        self.assertEqual(ctx.exception.code, 'PUBLISH_FAILED')
        self.assertEqual(before, self.files())
        self.assertEqual(old_hash, self.fingerprint(old['snapshot_path']))
        self.assertEqual(self.source_before, self.fingerprint(self.db))

    def test_file_sync_failure_prevents_link_and_cleans_stage(self):
        with patch.object(safe_zip, '_sync_staged_file', side_effect=ArchiveError('PUBLISH_FAILED', 'test')):
            with self.assertRaises(ArchiveError):
                create_snapshot(self.db, self.out)
        self.assertEqual(self.files(), [])

    def test_hardlink_collision_does_not_replace_existing_backup(self):
        first = create_snapshot(self.db, self.out)
        before = self.files()
        saved = self.fingerprint(first['snapshot_path'])
        if os.name == 'nt':
            from dbvora.archive import windows_ntfs_publish as native
            failure = patch.object(native, '_native_move_write_through', side_effect=native.WinPublishError('MOVE_FAILED'))
        else:
            failure = patch.object(safe_zip.os, 'link', side_effect=FileExistsError('simulated'))
        with failure:
            with self.assertRaises(ArchiveError):
                create_snapshot(self.db, self.out)
        self.assertEqual(before, self.files())
        self.assertEqual(self.fingerprint(first['snapshot_path']), saved)

    def test_grouped_staging_file_creation_failure_is_clean(self):
        orig = safe_zip._staging_file
        counter = 0
        def fail_at_second(d):
            nonlocal counter
            counter += 1
            if counter == 2:
                raise ArchiveError('STORAGE_FAILED', 'simulated')
            return orig(d)
        with patch.object(safe_zip, '_staging_file', side_effect=fail_at_second):
            with self.assertRaises(ArchiveError):
                _staging_files(self.out, 4)
        self.assertEqual(self.files(), [])

    def test_symlink_stage_not_published(self):
        stage = _staging_file(self.out)
        stage.unlink()
        stage.symlink_to(self.db)
        with self.assertRaises(ArchiveError):
            _publish_new(stage, self.out, '.sqlite')
        self.assertEqual(self.files(), [stage.name])
        self.assertEqual(self.source_before, self.fingerprint(self.db))

    def test_recovery_inventory_does_not_delete_anything(self):
        stale = _staging_file(self.out)
        self.older(stale)
        recent = _staging_file(self.out)
        other = self.out / 'personal-important.part'
        other.write_text('keep')
        symlink = self.out / '.dbvora-incomplete-aaaaaaaa.part'
        symlink.symlink_to(self.db)
        candidates = inspect_stale_temps(self.out)
        self.assertEqual(candidates, [stale.name])
        self.assertTrue(stale.exists())
        self.assertTrue(recent.exists())
        self.assertTrue(other.exists())
        self.assertTrue(symlink.is_symlink())

    def test_explicit_confirmation_only_cleanup_and_idempotency(self):
        stale = _staging_file(self.out)
        stale.write_text('incomplete')
        self.older(stale)
        recent = _staging_file(self.out)
        other = self.out / 'dbvora-existing.zip'
        other.write_text('safe existing archive')
        with self.assertRaises(ArchiveError) as ctx:
            cleanup_stale_temps(self.out)
        self.assertEqual(ctx.exception.code, 'CONFIRM_REQUIRED')
        self.assertTrue(stale.exists())
        if os.name != 'posix':
            with self.assertRaises(ArchiveError) as ctx:
                cleanup_stale_temps(self.out, confirm=True)
            self.assertEqual(ctx.exception.code, 'RECOVERY_UNSUPPORTED')
        else:
            self.assertEqual(cleanup_stale_temps(self.out, confirm=True), [stale.name])
            self.assertEqual(cleanup_stale_temps(self.out, confirm=True), [])
        self.assertTrue(recent.exists())
        self.assertEqual(other.read_text(), 'safe existing archive')

    def test_hardlinked_staging_file_is_never_cleanup_candidate(self):
        staged = _staging_file(self.out)
        existing = self.out / 'dbvora-keep.zip'
        os.link(staged, existing)
        self.older(staged)
        self.assertEqual(inspect_stale_temps(self.out), [])
        if os.name == 'posix':
            self.assertEqual(cleanup_stale_temps(self.out, confirm=True), [])
        self.assertTrue(existing.exists())
        self.assertTrue(staged.exists())

    def test_invalid_min_age_rejected(self):
        for age in (0, -1, 59, 3599, 1.0, True):
            with self.subTest(age=age), self.assertRaises(ArchiveError):
                inspect_stale_temps(self.out, older_than_seconds=age)

    def test_killed_process_leaves_only_temp_then_manual_recovery(self):
        # Simulate abrupt process death BEFORE publication; no production crash claim.
        snippet = ('import os,sys;from pathlib import Path;'
                   'from dbvora.archive.safe_zip import _staging_file;'
                   'p=_staging_file(Path(sys.argv[1]));'
                   'f=p.open("wb");f.write(b"incomplete");f.flush();'
                   'os._exit(17)')
        done = subprocess.run([sys.executable, '-c', snippet, str(self.out)],
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(done.returncode, 17, done.stderr)
        items = list(self.out.iterdir())
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].name.startswith('.dbvora-incomplete-'))
        self.older(items[0])
        self.assertEqual(inspect_stale_temps(self.out), [items[0].name])
        if os.name == 'posix':
            self.assertEqual(cleanup_stale_temps(self.out, confirm=True), [items[0].name])
            self.assertEqual(self.files(), [])
        self.assertEqual(self.source_before, self.fingerprint(self.db))

    def test_multiprocess_unique_snapshots_and_source_unmodified(self):
        with ProcessPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(_process_snapshot, [str(self.db)] * 8, [str(self.out)] * 8))
        self.assertEqual(len({p for p, h in results}), 8)
        self.assertEqual(len({h for p, h in results}), 1)
        for file, sha in results:
            self.assertEqual(hashlib.sha256(Path(file).read_bytes()).hexdigest(), sha)
        self.assertEqual(self.source_before, self.fingerprint(self.db))
        self.assertEqual(len(self.files()), 8)

    def test_zip_restore_and_zstd_after_durability_changes(self):
        snapshot = create_snapshot(self.db, self.out)
        zip_arc = make_zip_archive(snapshot['snapshot_path'], self.out)
        zip_restore = restore_zip_archive(zip_arc['archive_path'], self.restore)
        self.assertEqual(snapshot['snapshot_sha256'], zip_restore['restored_sha256'])
        if __import__('shutil').which('zstd'):
            z_arc = create_zstd_archive(snapshot['snapshot_path'], self.out)
            restored = restore_zstd_archive(z_arc['archive_path'], self.restore)
            self.assertEqual(snapshot['snapshot_sha256'], restored['restored_sha256'])
        self.assertEqual(self.source_before, self.fingerprint(self.db))

    def test_publish_on_unsupported_directory_sync_fails_closed(self):
        with patch.object(safe_zip.os, 'fsync', side_effect=OSError('unsupported')):
            with self.assertRaises(ArchiveError):
                create_snapshot(self.db, self.out)
        self.assertEqual(self.files(), [])


if __name__ == '__main__':
    unittest.main()
