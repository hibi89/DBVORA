"""P1-C3 post-restart read-only inventory and capability preflight tests."""
from contextlib import closing
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import recovery_catalog as audit
from dbvora.archive.safe_zip import ArchiveError, _staging_file, create_snapshot, make_zip_archive
from dbvora.archive.zstd_archive import create_zstd_archive
from scripts.preflight_archiving import probe
from tests.fixtures.make_sqlite import create_fixture


class RecoveryCatalogTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.output = self.home / 'archives'
        self.output.mkdir()
        self.source = create_fixture(self.home / 'synthetic.sqlite')

    def fingerprint(self, path):
        p = Path(path)
        return hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns

    def names(self):
        return sorted(p.name for p in self.output.iterdir())

    def audit(self):
        return audit.inspect_recovery_catalog(self.output)

    def test_empty_catalog_no_files_created(self):
        report = self.audit()
        self.assertTrue(report['complete'])
        self.assertEqual(report['records'], [])
        self.assertEqual(self.names(), [])

    def test_snapshot_verified_after_independent_reopen(self):
        previous = self.fingerprint(self.source)
        snap = create_snapshot(self.source, self.output)
        source_before = self.fingerprint(snap['snapshot_path'])
        report = self.audit()
        record, = report['records']
        self.assertEqual(record['status'], 'CONTENT_VERIFIED_PUBLISH_UNPROVEN')
        self.assertEqual(record['snapshot_sha256'], snap['snapshot_sha256'])
        self.assertEqual(record['authentication'], 'unsigned_untrusted')
        self.assertIn('unknown', record['publication_durability'])
        self.assertEqual(self.fingerprint(snap['snapshot_path']), source_before)
        self.assertEqual(self.fingerprint(self.source), previous)
        self.assertEqual(self.names(), [Path(snap['snapshot_path']).name])

    def test_zip_verified_by_complete_independent_restore(self):
        snap = create_snapshot(self.source, self.output)
        zipped = make_zip_archive(snap['snapshot_path'], self.output)
        archive_fingerprint = self.fingerprint(zipped['archive_path'])
        records = self.audit()['records']
        zipped_rec, = [r for r in records if r['kind'] == 'zip']
        self.assertEqual(zipped_rec['status'], 'CONTENT_VERIFIED_PUBLISH_UNPROVEN')
        self.assertEqual(zipped_rec['snapshot_sha256'], snap['snapshot_sha256'])
        self.assertEqual(self.fingerprint(zipped['archive_path']), archive_fingerprint)

    def test_zstd_checked_if_optional_local_cli_present(self):
        if not shutil.which('zstd'):
            self.skipTest('zstd executable unavailable')
        snap = create_snapshot(self.source, self.output)
        arc = create_zstd_archive(snap['snapshot_path'], self.output)
        output = [r for r in self.audit()['records'] if r['kind'] == 'dbvz']
        self.assertEqual(output[0]['status'], 'CONTENT_VERIFIED_PUBLISH_UNPROVEN')
        self.assertEqual(output[0]['snapshot_sha256'], arc['snapshot_sha256'])

    def test_corrupted_snapshot_has_failed_review_without_deletion(self):
        snap = create_snapshot(self.source, self.output)
        original = Path(snap['snapshot_path'])
        original.write_bytes(b'corrupt')
        fp = self.fingerprint(original)
        record, = self.audit()['records']
        self.assertEqual(record['status'], 'FAILED_REVIEW')
        self.assertEqual(record['error_code'], 'CORRUPT_SQLITE')
        self.assertEqual(self.fingerprint(original), fp)

    def test_corrupted_zip_has_failed_review_and_is_preserved(self):
        snap = create_snapshot(self.source, self.output)
        zipped = make_zip_archive(snap['snapshot_path'], self.output)
        path = Path(zipped['archive_path'])
        path.write_bytes(b'not zip')
        fp = self.fingerprint(path)
        entry, = [x for x in self.audit()['records'] if x['kind'] == 'zip']
        self.assertEqual(entry['status'], 'FAILED_REVIEW')
        self.assertEqual(self.fingerprint(path), fp)

    def test_changed_zstd_frame_is_failed_review(self):
        if not shutil.which('zstd'):
            self.skipTest('zstd executable unavailable')
        snap = create_snapshot(self.source, self.output)
        arc = create_zstd_archive(snap['snapshot_path'], self.output)
        p = Path(arc['archive_path'])
        data = bytearray(p.read_bytes())
        data[-1] ^= 0x01
        p.write_bytes(data)
        fp = self.fingerprint(p)
        entry, = [x for x in self.audit()['records'] if x['kind'] == 'dbvz']
        self.assertEqual(entry['status'], 'FAILED_REVIEW')
        self.assertEqual(self.fingerprint(p), fp)

    def test_incomplete_temp_never_deleted(self):
        temp = _staging_file(self.output)
        temp.write_bytes(b'incomplete')
        record, = self.audit()['records']
        self.assertEqual(record['kind'], 'temporary')
        self.assertEqual(record['status'], 'UNPUBLISHED_OR_ACTIVE')
        self.assertTrue(temp.exists())

    def test_unrelated_files_ignored_not_read_or_deleted(self):
        unrelated = self.output / 'customer_notes.txt'
        unrelated.write_text('never return this content')
        (self.output / 'subfolder').mkdir()
        before = self.names()
        report = self.audit()
        self.assertEqual(report['ignored_entry_count'], 2)
        self.assertEqual(self.names(), before)
        self.assertNotIn('never return this content', str(report))

    def test_symlink_named_as_archive_fail_closed_without_following(self):
        target = self.home / 'other.sqlite'
        target.write_text('secret')
        link = self.output / ('dbvora-' + 'a' * 32 + '.sqlite')
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        rec, = self.audit()['records']
        self.assertEqual(rec['status'], 'FAILED_REVIEW')
        self.assertEqual(rec['error_code'], 'UNSAFE_ENTRY')
        self.assertEqual(target.read_text(), 'secret')

    def test_hardlinked_published_name_fail_closed(self):
        snap = create_snapshot(self.source, self.output)
        linked = self.home / 'secondary.sqlite'
        os.link(snap['snapshot_path'], linked)
        rec, = self.audit()['records']
        self.assertEqual(rec['status'], 'FAILED_REVIEW')
        self.assertEqual(rec['error_code'], 'UNSAFE_ENTRY')

    def test_fixed_entry_limit_fails_closed(self):
        for idx in range(3):
            (self.output / ('dbvora-' + str(idx) * 32 + '.zip')).write_bytes(b'empty')
        with self.assertRaises(ArchiveError) as ctx:
            audit.inspect_recovery_catalog(self.output, max_entries=2)
        self.assertEqual(ctx.exception.code, 'CATALOG_LIMIT')

    def test_oversize_file_refused_without_reading_payload(self):
        large = self.output / ('dbvora-' + 'f' * 32 + '.zip')
        with large.open('wb') as stream:
            stream.truncate(audit.MAX_ARCHIVE_BYTES + 1)
        rec, = self.audit()['records']
        self.assertEqual(rec['status'], 'FAILED_REVIEW')
        self.assertEqual(rec['error_code'], 'TOO_LARGE')

    def test_simulated_mutation_detected_and_reported(self):
        snap = create_snapshot(self.source, self.output)
        with patch.object(audit, '_stable_copy', side_effect=ArchiveError('RACE_DETECTED', 'changed')):
            rec, = self.audit()['records']
        self.assertEqual(rec['status'], 'FAILED_REVIEW')
        self.assertEqual(rec['error_code'], 'RACE_DETECTED')
        self.assertTrue(Path(snap['snapshot_path']).exists())

    def test_simulated_denied_permissions_is_non_destructive(self):
        snap = create_snapshot(self.source, self.output)
        with patch.object(audit, '_stable_copy', side_effect=ArchiveError('INSPECTION_FAILED', 'denied')):
            rec, = self.audit()['records']
        self.assertEqual(rec['error_code'], 'INSPECTION_FAILED')
        self.assertTrue(Path(snap['snapshot_path']).exists())

    def test_zstd_unavailable_does_not_mark_verified(self):
        if not shutil.which('zstd'):
            self.skipTest('zstd executable unavailable')
        snap = create_snapshot(self.source, self.output)
        create_zstd_archive(snap['snapshot_path'], self.output)
        with patch('dbvora.archive.zstd_archive.shutil.which', return_value=None):
            entries = self.audit()['records']
        entry, = [x for x in entries if x['kind'] == 'dbvz']
        self.assertEqual(entry['status'], 'FAILED_REVIEW')
        self.assertEqual(entry['error_code'], 'CODEC_UNAVAILABLE')

    def test_preflight_only_writes_synthetic_temp_and_never_marks_customer_ready(self):
        report = probe()
        self.assertFalse(report['ready_for_customer_data'])
        self.assertFalse(report['writes_outside_os_temporary_folder'])
        self.assertIn(report['archive_publish_test'], ('passed_on_temporary_filesystem', 'unsupported_or_failed'))
        self.assertFalse(report['windows_package_verified'])


    def test_separate_new_process_rechecks_existing_zip_on_restart(self):
        snap = create_snapshot(self.source, self.output)
        arc = make_zip_archive(snap['snapshot_path'], self.output)
        before = self.names()
        snippet = ('import json,sys; from dbvora.archive.recovery_catalog import '
                   'inspect_recovery_catalog; print(json.dumps(inspect_recovery_catalog(sys.argv[1])))')
        child = subprocess.run([sys.executable, '-c', snippet, str(self.output)],
                               capture_output=True, text=True, timeout=20)
        self.assertEqual(child.returncode, 0, child.stderr)
        report = json.loads(child.stdout)
        zip_record, = [x for x in report['records'] if x['kind'] == 'zip']
        self.assertEqual(zip_record['status'], 'CONTENT_VERIFIED_PUBLISH_UNPROVEN')
        self.assertEqual(zip_record['snapshot_sha256'], arc['snapshot_sha256'])
        self.assertEqual(self.names(), before)

    def test_fake_symlink_temporary_not_mistaken_for_active_staged_file(self):
        target = self.home / 'untouched.txt'
        target.write_text('secret')
        link = self.output / '.dbvora-incomplete-aaaaaaaa.part'
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symlink unavailable')
        record, = self.audit()['records']
        self.assertEqual(record['status'], 'UNSAFE_TEMP_ENTRY')
        self.assertEqual(target.read_text(), 'secret')

    def test_bad_directory_path_rejected(self):
        with self.assertRaises(ArchiveError):
            audit.inspect_recovery_catalog('not/absolute')


if __name__ == '__main__':
    unittest.main()
