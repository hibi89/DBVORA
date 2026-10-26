"""Synthetic-only C2 byte reuse estimation, not archive restore certification."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import dedup_plan as mod


class DedupPlannerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='dbvora-c2-plan-tests-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def write(self, name, data):
        target = self.root / name
        target.write_bytes(data)
        return target

    def test_identical_chunks_reused_only_after_byte_match(self):
        a = self.write('a', b'A' * 4096 + b'B' * 4096)
        b = self.write('b', b'A' * 4096 + b'C' * 4096)
        report = mod.plan([a, b], chunk_bytes=4096)
        self.assertEqual(report['candidate_reusable_bytes'], 4096)
        self.assertEqual(report['estimated_unique_bytes'], 12288)
        self.assertEqual(report['unique_chunks'], 3)
        self.assertEqual(report['reused_chunks'], 1)
        self.assertFalse(report['independent_restore_verified'])
        self.assertFalse(report['ready_for_customer_data'])

    def test_repeated_chunk_in_one_source_counted(self):
        p = self.write('one', b'Z' * (4096 * 3))
        r = mod.plan([p], chunk_bytes=4096)
        self.assertEqual(r['candidate_reusable_bytes'], 8192)
        self.assertEqual(r['unique_chunks'], 1)

    def test_empty_source_has_zero_estimated_bytes(self):
        p = self.write('empty', b'')
        r = mod.plan([p], chunk_bytes=4096)
        self.assertEqual((r['unique_chunks'], r['reused_chunks']), (0, 0))

    def test_identical_digest_with_distinct_bytes_is_not_reuse(self):
        a = self.write('a', b'A' * 4096)
        b = self.write('b', b'B' * 4096)
        with patch.object(mod.hashlib, 'sha256', return_value=hashlib.sha256(b'unrelated')):
            r = mod.plan([a, b], chunk_bytes=4096)
        self.assertEqual(r['candidate_reusable_bytes'], 0)
        self.assertEqual(r['unique_chunks'], 2)

    def test_reject_duplicate_same_inode_and_symlink(self):
        p = self.write('same', b'A' * 4096)
        with self.assertRaisesRegex(mod.DedupPlanError, 'DUPLICATE_SOURCE'):
            mod.plan([p, p])
        link = self.root / 'link'
        link.symlink_to(p)
        with self.assertRaisesRegex(mod.DedupPlanError, 'UNSAFE_SOURCE'):
            mod.plan([link])

    def test_reject_invalid_chunk_size_and_relative_path(self):
        p = self.write('one', b'')
        for size in (0, 12345, 1024, 2**21, True):
            with self.subTest(size=size), self.assertRaisesRegex(mod.DedupPlanError, 'INVALID_CHUNK_SIZE'):
                mod.plan([p], chunk_bytes=size)
        with self.assertRaisesRegex(mod.DedupPlanError, 'INVALID_SOURCE'):
            mod.plan([Path('relative')])

    def test_large_sources_fail_before_reading(self):
        p = self.write('small', b'A' * 4096)
        with patch.object(mod, 'MAX_FILE_BYTES', 20):
            with self.assertRaisesRegex(mod.DedupPlanError, 'SOURCE_TOO_LARGE'):
                mod.plan([p], chunk_bytes=4096)

    def test_original_bytes_and_mtime_unchanged_no_path_leak(self):
        p = self.write('private_filename_secret', b'A' * 4096)
        before = (hashlib.sha256(p.read_bytes()).digest(), p.stat().st_mtime_ns)
        r = mod.plan([p], chunk_bytes=4096)
        self.assertEqual(before, (hashlib.sha256(p.read_bytes()).digest(), p.stat().st_mtime_ns))
        self.assertNotIn(str(p), str(r))
        self.assertNotIn('private_filename_secret', str(r))

    def test_synthetic_selfcheck(self):
        r = mod.synthetic_selfcheck()
        self.assertEqual(r['candidate_reusable_bytes'], 12288)
        self.assertEqual(r['source_total_bytes'], 24576)
        self.assertFalse(r['content_store_created'])


if __name__ == '__main__':
    unittest.main()
