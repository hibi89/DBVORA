"""Synthetic ZSTD CLI archive tests; no user/customer records or cloud calls."""
import hashlib
import json
import os
from pathlib import Path
from contextlib import closing
import shutil
import sqlite3
import struct
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive.safe_zip import ArchiveError, create_snapshot, make_zip_archive
from dbvora.archive.zstd_archive import (
    MAGIC, create_zstd_archive, restore_zstd_archive, _cli,
)
from tests.fixtures.make_sqlite import create_fixture


class ZstdArchiveTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.out = self.root / 'out'
        self.out.mkdir()
        self.rest = self.root / 'rest'
        self.rest.mkdir()
        self.source = create_fixture(self.root / 'synthetic.sqlite')
        self.original = (self.digest(self.source), self.source.stat().st_mtime_ns)
        self.snapshot = create_snapshot(self.source, self.out)

    @staticmethod
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def files(self, where):
        return sorted(p.name for p in where.iterdir())

    def make(self, level=3):
        return create_zstd_archive(self.snapshot['snapshot_path'], self.out, level=level)

    def require_cli(self):
        if not shutil.which('zstd'):
            self.skipTest('optional local zstd CLI unavailable')

    def test_all_levels_roundtrip(self):
        self.require_cli()
        for level in (1, 3, 9):
            with self.subTest(level=level):
                arc = self.make(level)
                back = restore_zstd_archive(arc['archive_path'], self.rest)
                self.assertEqual(arc['level'], level)
                self.assertEqual(arc['verification'], 'independent_restore_ok')
                self.assertEqual(back['restored_sha256'], self.snapshot['snapshot_sha256'])
                self.assertEqual(self.digest(back['restored_path']), self.snapshot['snapshot_sha256'])
                with closing(sqlite3.connect(back['restored_path'])) as con:
                    self.assertEqual(con.execute('PRAGMA integrity_check').fetchone(), ('ok',))
        self.assertEqual((self.digest(self.source), self.source.stat().st_mtime_ns), self.original)

    def test_zip_and_zstd_identical_restored_snapshot(self):
        self.require_cli()
        arc = self.make()
        zipped = make_zip_archive(self.snapshot['snapshot_path'], self.out)
        self.assertEqual(arc['snapshot_sha256'], zipped['snapshot_sha256'])
        self.assertGreater(arc['archive_size_bytes'], 0)

    def test_separate_new_restore_files_without_overwrite(self):
        self.require_cli()
        arc = self.make()
        a = restore_zstd_archive(arc['archive_path'], self.rest)
        b = restore_zstd_archive(arc['archive_path'], self.rest)
        self.assertNotEqual(a['restored_path'], b['restored_path'])
        self.assertEqual(self.digest(a['restored_path']), self.digest(b['restored_path']))

    def test_no_source_path_in_manifest(self):
        self.require_cli()
        arc = self.make()
        raw = Path(arc['archive_path']).read_bytes()
        self.assertEqual(raw[:8], MAGIC)
        length = struct.unpack('>I', raw[8:12])[0]
        manifest = json.loads(raw[12:12 + length])
        self.assertEqual(manifest['format'], 'dbvora-zstd-v1')
        self.assertNotIn(str(self.source), str(manifest))
        self.assertNotIn(str(self.snapshot['snapshot_path']), str(manifest))
        self.assertEqual(manifest['snapshot_sha256'], self.snapshot['snapshot_sha256'])
        self.assertEqual(manifest['frame_size_bytes'], len(raw) - 12 - length)

    def test_invalid_levels_do_not_publish(self):
        prior = self.files(self.out)
        for level in (-1, 0, 2, 23, 3.0, True):
            with self.subTest(level=level), self.assertRaises(ArchiveError) as ctx:
                self.make(level)
            self.assertEqual(ctx.exception.code, 'INVALID_LEVEL')
        self.assertEqual(self.files(self.out), prior)

    def test_missing_codec_exposes_safe_error(self):
        with patch('dbvora.archive.zstd_archive.shutil.which', return_value=None):
            with self.assertRaises(ArchiveError) as ctx:
                self.make()
        self.assertEqual(ctx.exception.code, 'CODEC_UNAVAILABLE')
        self.assertNotIn(str(self.source), ctx.exception.message)
        self.assertFalse([p for p in self.out.iterdir() if p.name.endswith('.part')])

    def test_truncated_and_invalid_envelope(self):
        self.require_cli()
        arc = self.make()
        raw = Path(arc['archive_path']).read_bytes()
        for name, content in [('short', raw[:6]), ('empty-frame', raw[:-15]), ('wrong-magic', b'WRONGMAG' + raw[8:])]:
            altered = self.root / (name + '.dbvz')
            altered.write_bytes(content)
            before = self.files(self.rest)
            with self.subTest(name=name), self.assertRaises(ArchiveError):
                restore_zstd_archive(altered, self.rest)
            self.assertEqual(self.files(self.rest), before)

    def test_mutated_frame_checksum_fails_without_publishing(self):
        self.require_cli()
        arc = self.make()
        tampered = bytearray(Path(arc['archive_path']).read_bytes())
        tampered[-2] ^= 0xFF
        file = self.root / 'changed.dbvz'
        file.write_bytes(tampered)
        with self.assertRaises(ArchiveError) as ctx:
            restore_zstd_archive(file, self.rest)
        self.assertEqual(ctx.exception.code, 'HASH_MISMATCH')
        self.assertEqual(self.files(self.rest), [])

    def test_mutated_manifest_checksum_fails(self):
        self.require_cli()
        arc = self.make()
        raw = Path(arc['archive_path']).read_bytes()
        length = struct.unpack('>I', raw[8:12])[0]
        manifest = json.loads(raw[12:12 + length])
        manifest['snapshot_sha256'] = '0' * 64
        newer = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()
        changed = self.root / 'bad-manifest.dbvz'
        changed.write_bytes(raw[:8] + struct.pack('>I', len(newer)) + newer + raw[12 + length:])
        with self.assertRaises(ArchiveError) as ctx:
            restore_zstd_archive(changed, self.rest)
        self.assertEqual(ctx.exception.code, 'HASH_MISMATCH')
        self.assertEqual(self.files(self.rest), [])

    def test_manifest_length_huge_refused_before_decompression(self):
        file = self.root / 'large-manifest.dbvz'
        file.write_bytes(MAGIC + struct.pack('>I', 9_999_999) + b'{}')
        with self.assertRaises(ArchiveError) as ctx:
            restore_zstd_archive(file, self.rest)
        self.assertEqual(ctx.exception.code, 'BAD_MANIFEST')

    def test_frame_bomb_prototype_limit_blocks_expansion(self):
        self.require_cli()
        arc = self.make()
        with patch('dbvora.archive.zstd_archive.MAX_SNAPSHOT_BYTES', 1024):
            with self.assertRaises(ArchiveError) as ctx:
                restore_zstd_archive(arc['archive_path'], self.rest)
        self.assertIn(ctx.exception.code, ('BAD_MANIFEST', 'TOO_LARGE'))
        self.assertEqual(self.files(self.rest), [])

    def test_publishing_failure_preserves_previous_archive(self):
        self.require_cli()
        first = self.make()
        before = self.files(self.out)
        original_sha = self.digest(first['archive_path'])
        with patch('dbvora.archive.zstd_archive._publish_new', side_effect=ArchiveError('PUBLISH_FAILED', 'Simulated failure')):
            with self.assertRaises(ArchiveError):
                self.make()
        self.assertEqual(self.files(self.out), before)
        self.assertEqual(self.digest(first['archive_path']), original_sha)

    def test_restore_publish_failure_preserves_previous_restoration(self):
        self.require_cli()
        arc = self.make()
        good = restore_zstd_archive(arc['archive_path'], self.rest)
        before = self.files(self.rest)
        with patch('dbvora.archive.zstd_archive._publish_new', side_effect=ArchiveError('PUBLISH_FAILED', 'Simulated failure')):
            with self.assertRaises(ArchiveError):
                restore_zstd_archive(arc['archive_path'], self.rest)
        self.assertEqual(self.files(self.rest), before)
        self.assertEqual(self.digest(good['restored_path']), self.snapshot['snapshot_sha256'])

    def test_relative_and_symlink_paths_rejected(self):
        self.require_cli()
        arc = self.make()
        with self.assertRaises(ArchiveError):
            restore_zstd_archive('relative.dbvz', self.rest)
        link = self.root / 'link.dbvz'
        try:
            link.symlink_to(arc['archive_path'])
        except (OSError, NotImplementedError):
            self.skipTest('symlink unavailable')
        with self.assertRaises(ArchiveError):
            restore_zstd_archive(link, self.rest)

    def test_incompressible_fixture_roundtrip(self):
        self.require_cli()
        other = self.root / 'random.sqlite'
        with closing(sqlite3.connect(other)) as con:
            con.execute('CREATE TABLE records(id INTEGER PRIMARY KEY, payload BLOB)')
            con.executemany('INSERT INTO records(payload) VALUES (?)', [(os.urandom(8192),) for _ in range(16)])
            con.commit()
        snap = create_snapshot(other, self.out)
        arc = create_zstd_archive(snap['snapshot_path'], self.out, level=1)
        back = restore_zstd_archive(arc['archive_path'], self.rest)
        self.assertEqual(back['restored_sha256'], snap['snapshot_sha256'])
        self.assertGreater(arc['archive_size_bytes'], 100000)

    def test_archive_is_local_and_not_exposed_by_api(self):
        import dbvora.api
        self.assertFalse(hasattr(dbvora.api, 'create_zstd_archive'))


if __name__ == '__main__':
    unittest.main()
