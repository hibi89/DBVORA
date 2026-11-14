"""Isolated synthetic regression tests; do not certify real Windows durability."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch

from dbvora.archive import windows_ntfs_publish as publish
from dbvora.archive import safe_zip
from scripts import windows_ntfs_publish_probe as probe


def simulated_create_only(source, target):
    # No replacement; link+remove simulates the resulting namespace only.
    os.link(source, target)
    source.unlink()


class WindowsSyntheticPublicationTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory(prefix='dbvora-win32-synthetic-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        staged = root / ('.dbvora-stage-' + uuid.uuid4().hex + '.part')
        target = root / ('dbvora-' + uuid.uuid4().hex + '.bin')
        staged.write_bytes(b'A' * 4096)
        return root, staged, target

    def test_non_windows_is_always_fail_closed(self):
        result = probe.run_probe(platform_name='Linux', python_version=(3,11),
                                 filesystem='NTFS', move=simulated_create_only)
        self.assertEqual(result['status'], 'BLOCKED_UNVERIFIED')
        self.assertFalse(result['native_windows_tested'])

    def test_simulation_is_not_native_certification(self):
        report = probe.run_probe(platform_name='Windows', python_version=(3,11),
                                 filesystem='NTFS', move=simulated_create_only)
        self.assertEqual(report['status'], 'PASS_SIMULATED_ONLY')
        self.assertEqual([s['status'] for s in report['steps']], ['PASS'] * 6)
        self.assertFalse(report['power_loss_durable_verified'])
        self.assertFalse(report['ready_for_customer_data'])

    def test_real_source_is_unchanged_on_publish(self):
        root, stage, target = self.fixture()
        expected = hashlib.sha256(stage.read_bytes()).hexdigest()
        actual = publish._commit_synthetic_staged(root, stage, target, move=simulated_create_only)
        self.assertEqual(actual, expected)
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), expected)
        self.assertFalse(stage.exists())

    def test_staging_fsync_uses_writable_handle_on_windows(self):
        root, stage, target = self.fixture()
        observed_modes = []
        original_open = Path.open
        def open_spy(path, *args, **kwargs):
            if path == stage:
                observed_modes.append(args[0] if args else kwargs.get('mode', 'r'))
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', open_spy):
            publish._commit_synthetic_staged(root, stage, target, move=simulated_create_only)
        self.assertIn('r+b', observed_modes)

    def test_collision_never_overwrites_existing(self):
        root, stage, target = self.fixture()
        target.write_bytes(b'customer-keep-synthetic')
        with self.assertRaisesRegex(publish.WinPublishError, 'DESTINATION_EXISTS'):
            publish._commit_synthetic_staged(root, stage, target, move=simulated_create_only)
        self.assertEqual(target.read_bytes(), b'customer-keep-synthetic')
        self.assertEqual(stage.read_bytes(), b'A' * 4096)

    def test_failing_move_does_not_remove_stage(self):
        root, stage, target = self.fixture()
        def fail(_a,_b):
            raise publish.WinPublishError('INJECTED_FAILURE')
        with self.assertRaisesRegex(publish.WinPublishError, 'INJECTED_FAILURE'):
            publish._commit_synthetic_staged(root, stage, target, move=fail)
        self.assertTrue(stage.exists())
        self.assertFalse(target.exists())

    def test_detects_tamper_after_publication(self):
        root, stage, target = self.fixture()
        def bad(a,b):
            os.link(a,b); a.unlink(); b.write_bytes(b'altered')
        with self.assertRaisesRegex(publish.WinPublishError, 'PUBLISHED_BYTES_DIFFER'):
            publish._commit_synthetic_staged(root, stage, target, move=bad)

    def test_rejects_output_outside_temporary_root(self):
        root, stage, _ = self.fixture()
        target = root.parent / ('dbvora-' + uuid.uuid4().hex + '.bin')
        with self.assertRaisesRegex(publish.WinPublishError, 'UNSAFE_SYNTHETIC_PATH'):
            publish._commit_synthetic_staged(root, stage, target, move=simulated_create_only)

    def test_rejects_stage_symlink(self):
        root, stage, target = self.fixture()
        actual = root / 'actual.bin'
        actual.write_bytes(b'never-modify')
        stage.unlink()
        try:
            stage.symlink_to(actual)
        except (OSError, NotImplementedError):
            # Windows unprivileged accounts may forbid creating symlinks.
            # Retain a no-skip negative check using a simulated link identity.
            stage.write_bytes(b'fake-link')
            real_is_symlink = Path.is_symlink
            with patch.object(Path, 'is_symlink', lambda p: p == stage or real_is_symlink(p)):
                with self.assertRaises(publish.WinPublishError):
                    publish._commit_synthetic_staged(root, stage, target, move=simulated_create_only)
        else:
            with self.assertRaises(publish.WinPublishError):
                publish._commit_synthetic_staged(root, stage, target, move=simulated_create_only)
        self.assertEqual(actual.read_bytes(), b'never-modify')

    def test_rejects_non_ntfs_before_any_write(self):
        report = probe.run_probe(platform_name='Windows', python_version=(3,11),
                                 filesystem='FAT32', move=simulated_create_only)
        self.assertEqual(report['status'], 'BLOCKED_UNVERIFIED')
        self.assertEqual(report['reason'], 'NTFS_TEMP_REQUIRED')

    def test_rejects_python_not_311(self):
        report = probe.run_probe(platform_name='Windows', python_version=(3,12),
                                 filesystem='NTFS', move=simulated_create_only)
        self.assertEqual(report['reason'], 'PYTHON311_REQUIRED')

    def test_win32_flag_does_not_enable_replacement(self):
        self.assertEqual(publish.MOVEFILE_WRITE_THROUGH, 0x8)
        self.assertEqual(publish.MOVEFILE_WRITE_THROUGH & 0x1, 0)


    def test_native_move_denial_is_sanitized(self):
        if os.name != 'nt':
            with self.assertRaisesRegex(publish.WinPublishError, 'WINDOWS_REQUIRED'):
                publish._native_move_write_through(Path('stage'), Path('target'))
            return

        class DeniedMove:
            argtypes = None
            restype = None
            def __call__(self, *_args):
                # Model a Win32 access-denied return without changing any ACL.
                return 0

        class FakeKernel32:
            MoveFileExW = DeniedMove()

        with patch.object(publish.ctypes, 'WinDLL', return_value=FakeKernel32()):
            with self.assertRaisesRegex(publish.WinPublishError, 'MOVE_FAILED') as error:
                publish._native_move_write_through(Path('stage'), Path('target'))
        self.assertNotIn('stage', str(error.exception))
        self.assertNotIn('target', str(error.exception))

    def test_archive_publisher_maps_native_denial_and_preserves_stage(self):
        root, stage, target = self.fixture()
        original = stage.read_bytes()
        with patch.object(publish, '_windows_volume_type', return_value='NTFS'), \\
                patch.object(publish, '_native_move_write_through',
                             side_effect=publish.WinPublishError('MOVE_FAILED')):
            with self.assertRaises(safe_zip.ArchiveError) as error:
                safe_zip._publish_new_ntfs(stage, root, target)
        self.assertEqual(error.exception.code, 'PUBLISH_FAILED')
        self.assertNotIn(str(root), str(error.exception))
        self.assertEqual(stage.read_bytes(), original)
        self.assertFalse(target.exists())

    def test_archive_publisher_rejects_unsupported_volume_before_move(self):
        root, stage, target = self.fixture()
        original = stage.read_bytes()
        with patch.object(publish, '_windows_volume_type', return_value='ReFS'), \\
                patch.object(publish, '_native_move_write_through') as move:
            with self.assertRaises(safe_zip.ArchiveError) as error:
                safe_zip._publish_new_ntfs(stage, root, target)
        self.assertEqual(error.exception.code, 'PUBLISH_FAILED')
        move.assert_not_called()
        self.assertEqual(stage.read_bytes(), original)
        self.assertFalse(target.exists())

    def test_windows_parent_alias_publishes_same_temp_target(self):
        root, stage, target = self.fixture()
        if os.name != 'nt':
            self.assertEqual(publish._windows_volume_type(root), 'NOT_WINDOWS')
            return

        import ctypes
        from ctypes import wintypes
        get_short = ctypes.WinDLL('kernel32', use_last_error=True).GetShortPathNameW
        get_short.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD)
        get_short.restype = wintypes.DWORD
        alias_parent = None
        try:
            needed = get_short(str(root.parent), None, 0)
            if needed:
                buffer = ctypes.create_unicode_buffer(needed + 1)
                if get_short(str(root.parent), buffer, len(buffer)):
                    alias_parent = Path(buffer.value)
        except (OSError, AttributeError, TypeError, ValueError):
            alias_parent = None
        # Use a valid case alias if this volume has 8.3 names disabled.
        if alias_parent is None:
            alias_parent = Path(str(root.parent).upper())

        alias_root = alias_parent / root.name
        alias_stage = alias_root / stage.name
        alias_target = alias_root / target.name
        expected = hashlib.sha256(stage.read_bytes()).hexdigest()
        actual = publish._commit_synthetic_staged(alias_root, alias_stage, alias_target)
        self.assertEqual(actual, expected)
        self.assertFalse(alias_stage.exists())
        self.assertEqual(hashlib.sha256(alias_target.read_bytes()).hexdigest(), expected)

    def test_competing_create_only_publications_one_winner(self):
        root, first, target = self.fixture()
        second = root / ('.dbvora-stage-' + uuid.uuid4().hex + '.part')
        second.write_bytes(b'B' * 4096)
        mover = None if os.name == 'nt' else simulated_create_only
        outcomes = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(publish._commit_synthetic_staged, root, staged, target, move=mover)
                       for staged in (first, second)]
            for future in futures:
                try:
                    outcomes.append(('PASS', future.result(timeout=15)))
                except publish.WinPublishError as error:
                    outcomes.append(('BLOCKED', str(error)))
        self.assertEqual(sum(status == 'PASS' for status, _ in outcomes), 1)
        self.assertEqual(sum(status == 'BLOCKED' for status, _ in outcomes), 1)
        self.assertIn(target.read_bytes(), (b'A' * 4096, b'B' * 4096))
        self.assertEqual(sum(stage.exists() for stage in (first, second)), 1)
        survivor = first if first.exists() else second
        self.assertNotEqual(survivor.read_bytes(), target.read_bytes())

    def test_child_exit_before_publication_preserves_stage(self):
        root, stage, target = self.fixture()
        expected = hashlib.sha256(stage.read_bytes()).hexdigest()
        script = (
            'import os,sys;from pathlib import Path;'
            'from dbvora.archive.windows_ntfs_publish import _commit_synthetic_staged;'
            '_commit_synthetic_staged(Path(sys.argv[1]),Path(sys.argv[2]),'
            'Path(sys.argv[3]),move=lambda *_: os._exit(17))'
        )
        done = subprocess.run([sys.executable, '-B', '-c', script,
                               str(root), str(stage), str(target)],
                              capture_output=True, timeout=15, check=False)
        self.assertEqual(done.returncode, 17)
        self.assertFalse(target.exists())
        self.assertEqual(hashlib.sha256(stage.read_bytes()).hexdigest(), expected)

    def test_child_exit_after_native_publication_keeps_exact_bytes(self):
        root, stage, target = self.fixture()
        expected = hashlib.sha256(stage.read_bytes()).hexdigest()
        # A controlled child exit is NOT a physical power-loss durability check.
        script = (
            'import os,sys;from pathlib import Path;'
            'from dbvora.archive.windows_ntfs_publish import _commit_synthetic_staged,'
            '_native_move_write_through;'
            'root,stage,target=map(Path,sys.argv[1:4]);'
            'defmove=(_native_move_write_through if os.name=="nt" else '
            '(lambda s,t:(os.link(s,t),os.unlink(s))));'
            '_commit_synthetic_staged(root,stage,target,move='
            '(lambda s,t:(defmove(s,t),os._exit(19))))'
        )
        done = subprocess.run([sys.executable, '-B', '-c', script,
                               str(root), str(stage), str(target)],
                              capture_output=True, timeout=15, check=False)
        self.assertEqual(done.returncode, 19)
        self.assertFalse(stage.exists())
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), expected)

if __name__ == '__main__':
    unittest.main()
