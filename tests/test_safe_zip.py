"""Synthetic SQLite C0 and ZIP baseline safety tests (no customer data)."""
from contextlib import closing
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import warnings
import unittest
from unittest.mock import patch
import zipfile

from dbvora.archive import safe_zip as safe_zip_module
from dbvora.archive.safe_zip import (
    ArchiveError, MAX_SNAPSHOT_BYTES, create_snapshot, make_zip_archive, restore_zip_archive,
)
from tests.fixtures.make_sqlite import create_fixture


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = create_fixture(self.root / 'synthetic.sqlite')
        self.out = self.root / 'artifacts'
        self.out.mkdir()
        self.restore = self.root / 'restored'
        self.restore.mkdir()

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def source_identity(self):
        stat = self.source.stat()
        return self.sha(self.source), stat.st_mtime_ns, stat.st_size

    def listed(self, folder):
        return sorted(p.name for p in folder.iterdir())

    def workflow(self):
        snap = create_snapshot(self.source, self.out)
        arc = make_zip_archive(snap['snapshot_path'], self.out)
        restored = restore_zip_archive(arc['archive_path'], self.restore)
        return snap, arc, restored

    def test_full_round_trip_byte_identical_and_rows_equal(self):
        before = self.source_identity()
        snap, arc, restored = self.workflow()
        self.assertEqual(snap['sqlite_integrity'], 'ok')
        self.assertEqual(arc['verification'], 'independent_restore_ok')
        self.assertEqual(restored['sqlite_integrity'], 'ok')
        self.assertEqual(self.sha(Path(snap['snapshot_path'])), self.sha(Path(restored['restored_path'])))
        self.assertEqual(snap['snapshot_sha256'], restored['restored_sha256'])
        self.assertEqual(before, self.source_identity())
        with closing(sqlite3.connect(snap['snapshot_path'])) as first, closing(sqlite3.connect(restored['restored_path'])) as second:
            for statement in ['SELECT * FROM customers', 'SELECT * FROM orders', 'SELECT * FROM events']:
                self.assertEqual(first.execute(statement).fetchall(), second.execute(statement).fetchall())

    def test_source_file_unchanged_snapshot_only(self):
        before = self.source_identity()
        snap = create_snapshot(self.source, self.out)
        self.assertTrue(Path(snap['snapshot_path']).exists())
        self.assertEqual(before, self.source_identity())
        self.assertEqual(snap['snapshot_size_bytes'], Path(snap['snapshot_path']).stat().st_size)
        self.assertFalse([p for p in self.out.iterdir() if '.part' in p.name])

    def test_sqlite_wal_committed_rows_included_without_checkpoint(self):
        with closing(sqlite3.connect(self.source)) as live:
            live.execute('PRAGMA journal_mode=WAL')
            live.execute("INSERT INTO events (id, category, content) VALUES (900, 'wal', 'committed')")
            live.commit()
            self.assertTrue(self.source.with_suffix('.sqlite-wal').exists())
            snap = create_snapshot(self.source, self.out)
            with closing(sqlite3.connect(snap['snapshot_path'])) as separate:
                self.assertEqual(separate.execute('SELECT content FROM events WHERE id=900').fetchone(), ('committed',))
                self.assertEqual(separate.execute('PRAGMA integrity_check').fetchone(), ('ok',))

    def test_two_snapshots_and_multiple_restores_never_overwrite(self):
        a = create_snapshot(self.source, self.out)
        b = create_snapshot(self.source, self.out)
        self.assertNotEqual(a['snapshot_path'], b['snapshot_path'])
        arc = make_zip_archive(a['snapshot_path'], self.out)
        r1 = restore_zip_archive(arc['archive_path'], self.restore)
        r2 = restore_zip_archive(arc['archive_path'], self.restore)
        self.assertNotEqual(r1['restored_path'], r2['restored_path'])
        self.assertEqual(self.sha(Path(r1['restored_path'])), self.sha(Path(r2['restored_path'])))
        self.assertEqual(3, len(self.listed(self.out)))

    def test_zip_payload_manifest_is_fixed_no_source_path(self):
        snap, arc, restored = self.workflow()
        with zipfile.ZipFile(arc['archive_path']) as zf:
            self.assertEqual(zf.namelist(), ['snapshot.sqlite', 'manifest.json'])
            manifest = json.loads(zf.read('manifest.json'))
            self.assertEqual(manifest['format'], 'dbvora-zip-v1')
            self.assertEqual(manifest['snapshot_sha256'], snap['snapshot_sha256'])
            self.assertNotIn(str(self.source), json.dumps(manifest))
        self.assertEqual(arc['archive_sha256'], self.sha(Path(arc['archive_path'])))

    def test_truncated_zip_rejected_without_published_restoration(self):
        snap, arc, _ = self.workflow()
        corrupted = self.root / 'truncated.zip'
        corrupted.write_bytes(Path(arc['archive_path']).read_bytes()[:20])
        before = self.listed(self.restore)
        with self.assertRaises(ArchiveError):
            restore_zip_archive(corrupted, self.restore)
        self.assertEqual(before, self.listed(self.restore))
        self.assertEqual(self.sha(Path(snap['snapshot_path'])), arc['snapshot_sha256'])

    def test_manifest_sha_tamper_rejected_without_publish(self):
        snap, arc, _ = self.workflow()
        tampered = self.root / 'tampered.zip'
        with zipfile.ZipFile(arc['archive_path']) as old, zipfile.ZipFile(tampered, 'w') as new:
            data = old.read('snapshot.sqlite')
            manifest = json.loads(old.read('manifest.json'))
            manifest['snapshot_sha256'] = '0' * 64
            new.writestr('snapshot.sqlite', data, compress_type=zipfile.ZIP_DEFLATED)
            new.writestr('manifest.json', json.dumps(manifest), compress_type=zipfile.ZIP_STORED)
        previous = self.listed(self.restore)
        with self.assertRaises(ArchiveError) as ctx:
            restore_zip_archive(tampered, self.restore)
        self.assertEqual(ctx.exception.code, 'HASH_MISMATCH')
        self.assertEqual(previous, self.listed(self.restore))

    def test_path_traversal_archive_member_rejected(self):
        evil = self.root / 'bad-member.zip'
        with zipfile.ZipFile(evil, 'w') as zf:
            zf.writestr('../outside.sqlite', b'secret')
            zf.writestr('manifest.json', '{}')
        with self.assertRaises(ArchiveError) as ctx:
            restore_zip_archive(evil, self.restore)
        self.assertEqual(ctx.exception.code, 'INVALID_ARCHIVE')
        self.assertFalse((self.root / 'outside.sqlite').exists())

    def test_duplicate_member_rejected(self):
        snap = create_snapshot(self.source, self.out)
        archive = self.root / 'dup.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(archive, 'w') as zf:
                zf.writestr('snapshot.sqlite', b'x' * 100)
                zf.writestr('snapshot.sqlite', b'y' * 100)
                zf.writestr('manifest.json', '{}')
        with self.assertRaises(ArchiveError):
            restore_zip_archive(archive, self.restore)
        self.assertFalse(self.listed(self.restore))

    def test_random_file_is_not_valid_snapshot(self):
        fake = self.root / 'fake.sqlite'
        fake.write_bytes(os.urandom(512))
        with self.assertRaises(ArchiveError) as ctx:
            make_zip_archive(fake, self.out)
        self.assertEqual(ctx.exception.code, 'INVALID_SOURCE')

    def test_destination_must_exist_and_be_absolute(self):
        for bad in ('relative-dir', self.root / 'absent'):
            with self.subTest(bad=bad), self.assertRaises(ArchiveError):
                create_snapshot(self.source, bad)
        self.assertEqual(self.listed(self.out), [])

    def test_symlink_directory_rejected(self):
        link = self.root / 'alias'
        try:
            link.symlink_to(self.out, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ArchiveError) as ctx:
            create_snapshot(self.source, link)
        self.assertEqual(ctx.exception.code, 'BAD_DESTINATION')

    def test_zip_creation_rejects_hardlinked_snapshot_input(self):
        snapshot = Path(create_snapshot(self.source, self.out)["snapshot_path"])
        alias = self.root / "snapshot-hardlink.sqlite"
        try:
            os.link(snapshot, alias)
        except (OSError, NotImplementedError):
            self.skipTest("hardlinks unavailable")
        with self.assertRaises(ArchiveError) as ctx:
            make_zip_archive(alias, self.out)
        self.assertEqual(ctx.exception.code, "INVALID_SOURCE")
        self.assertFalse(list(self.out.glob("*.zip")))

    def test_zip_restore_rejects_hardlinked_archive_input(self):
        snapshot = Path(create_snapshot(self.source, self.out)["snapshot_path"])
        archive = Path(make_zip_archive(snapshot, self.out)["archive_path"])
        alias = self.root / "archive-hardlink.zip"
        try:
            os.link(archive, alias)
        except (OSError, NotImplementedError):
            self.skipTest("hardlinks unavailable")
        with self.assertRaises(ArchiveError) as ctx:
            restore_zip_archive(alias, self.restore)
        self.assertEqual(ctx.exception.code, "INVALID_ARCHIVE")
        self.assertEqual(self.listed(self.restore), [])

    def test_restore_rejects_same_size_mtime_path_replacement_before_open(self):
        snapshot = Path(create_snapshot(self.source, self.out)["snapshot_path"])
        archive = Path(make_zip_archive(snapshot, self.out)["archive_path"])
        before = archive.stat()
        replacement = self.root / "replacement.zip"
        replacement.write_bytes(archive.read_bytes())
        self.assertEqual(replacement.stat().st_size, before.st_size)
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(replacement.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertNotEqual(replacement.stat().st_ino, before.st_ino)

        real_open = safe_zip_module.os.open
        swapped = False

        def replace_before_open(path, flags, *args, **kwargs):
            nonlocal swapped
            if Path(path) == archive and not swapped:
                os.replace(replacement, archive)
                swapped = True
            return real_open(path, flags, *args, **kwargs)

        with patch.object(safe_zip_module.os, "open", side_effect=replace_before_open):
            with self.assertRaises(ArchiveError) as ctx:
                restore_zip_archive(archive, self.restore)
        self.assertTrue(swapped)
        self.assertEqual(ctx.exception.code, "INVALID_ARCHIVE")
        self.assertEqual(self.listed(self.restore), [])

    def test_public_messages_no_source_paths(self):
        missing = self.root / 'private-file.sqlite'
        with self.assertRaises(ArchiveError) as ctx:
            create_snapshot(missing, self.out)
        self.assertEqual(ctx.exception.code, 'INVALID_SOURCE')
        self.assertNotIn(str(missing), ctx.exception.message)

    def test_publish_failure_cleans_staging_and_preserves_prior_snapshot(self):
        original = create_snapshot(self.source, self.out)
        prev_sha = self.sha(Path(original['snapshot_path']))
        with patch('dbvora.archive.safe_zip._publish_new', side_effect=ArchiveError('PUBLISH_FAILED', 'Simulated failure')):
            with self.assertRaises(ArchiveError):
                create_snapshot(self.source, self.out)
        self.assertEqual(self.listed(self.out), [Path(original['snapshot_path']).name])
        self.assertEqual(self.sha(Path(original['snapshot_path'])), prev_sha)

    def test_zip_failure_cleans_staging_and_preserves_snapshot(self):
        snap = create_snapshot(self.source, self.out)
        before = self.listed(self.out)
        with patch('dbvora.archive.safe_zip._unpack_verified', side_effect=ArchiveError('CORRUPT', 'Simulated corrupt')):
            with self.assertRaises(ArchiveError):
                make_zip_archive(snap['snapshot_path'], self.out)
        self.assertEqual(self.listed(self.out), before)
        self.assertEqual(self.sha(Path(snap['snapshot_path'])), snap['snapshot_sha256'])

    def test_zip_missing_and_corrupt_inputs_fail_safely(self):
        missing = self.root / 'missing.zip'
        with self.assertRaises(ArchiveError):
            restore_zip_archive(missing, self.restore)
        fake = self.root / 'bad.zip'
        fake.write_bytes(b'not zip')
        with self.assertRaises(ArchiveError):
            restore_zip_archive(fake, self.restore)
        self.assertFalse(self.listed(self.restore))

    def test_snapshot_cannot_be_larger_than_conservative_cap(self):
        with patch('dbvora.archive.safe_zip.MAX_SNAPSHOT_BYTES', 50):
            with self.assertRaises(ArchiveError) as ctx:
                create_snapshot(self.source, self.out)
            self.assertEqual(ctx.exception.code, 'TOO_LARGE')

    def test_restore_rejects_manifest_wrong_type(self):
        snap = create_snapshot(self.source, self.out)
        invalid = self.root / 'wrong_manifest.zip'
        with zipfile.ZipFile(invalid, 'w') as zf:
            zf.writestr('snapshot.sqlite', Path(snap['snapshot_path']).read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
            zf.writestr('manifest.json', json.dumps({'format': 'dbvora-zip-v1', 'codec': 'zip-deflate', 'snapshot_sha256': 42, 'snapshot_size_bytes': True}), compress_type=zipfile.ZIP_STORED)
        with self.assertRaises(ArchiveError) as ctx:
            restore_zip_archive(invalid, self.restore)
        self.assertEqual(ctx.exception.code, 'BAD_MANIFEST')


if __name__ == '__main__':
    unittest.main()
