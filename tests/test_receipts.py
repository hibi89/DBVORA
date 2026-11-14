"""P1-C4 synthetic unsigned immutable receipt / lineage regression."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dbvora.archive import receipts
from dbvora.archive.receipts import create_receipt, inspect_receipt
from dbvora.archive.safe_zip import ArchiveError, create_snapshot, make_zip_archive
from dbvora.archive.zstd_archive import create_zstd_archive
from tests.fixtures.make_sqlite import create_fixture


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.out = self.root / 'archive'
        self.out.mkdir()
        self.source = create_fixture(self.root / 'synthetic.sqlite')
        self.source_identity = self.identity(self.source)

    @staticmethod
    def identity(path):
        path = Path(path)
        return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns

    def snapshot(self):
        return create_snapshot(self.source, self.out)

    def receipt_file(self, artifact):
        return self.out / receipts._receipt_name(Path(artifact).name)

    def test_absence_is_not_success_and_changes_nothing(self):
        snap = self.snapshot()
        original = self.identity(snap['snapshot_path'])
        result = inspect_receipt(self.out, Path(snap['snapshot_path']).name)
        self.assertEqual(result['status'], 'RECEIPT_FAILED_REVIEW')
        self.assertEqual(result['error_code'], 'MISSING_RECEIPT')
        self.assertEqual(self.identity(snap['snapshot_path']), original)
        self.assertEqual(len(list(self.out.iterdir())), 1)

    def test_create_and_restart_verify_sqlite_receipt(self):
        snap = self.snapshot()
        original = self.identity(snap['snapshot_path'])
        created = create_receipt(snap['snapshot_path'])
        self.assertEqual(created['status'], 'RECORDED_UNSIGNED')
        self.assertEqual(created['authentication'], 'unsigned_untrusted')
        check = inspect_receipt(self.out, Path(snap['snapshot_path']).name)
        self.assertEqual(check['status'], 'RECEIPT_AND_CONTENT_VERIFIED_UNSIGNED')
        self.assertEqual(check['receipt_sha256'], created['receipt_sha256'])
        self.assertEqual(self.identity(snap['snapshot_path']), original)
        self.assertEqual(self.identity(self.source), self.source_identity)

    def test_zip_receipt_recovers_after_new_interpreter_process(self):
        snap = self.snapshot()
        archive = make_zip_archive(snap['snapshot_path'], self.out)
        created = create_receipt(archive['archive_path'])
        before = self.identity(archive['archive_path'])
        program = ('import json,sys; from dbvora.archive.receipts import inspect_receipt;'
                   'print(json.dumps(inspect_receipt(sys.argv[1],sys.argv[2])))')
        result = subprocess.run([sys.executable, '-c', program, str(self.out),
                                 Path(archive['archive_path']).name],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict['receipt_sha256'], created['receipt_sha256'])
        self.assertEqual(verdict['status'], 'RECEIPT_AND_CONTENT_VERIFIED_UNSIGNED')
        self.assertEqual(self.identity(archive['archive_path']), before)

    def test_zstd_optional_receipt_verification(self):
        if not shutil.which('zstd'):
            self.skipTest('Optional local ZSTD CLI missing')
        snap = self.snapshot()
        archive = create_zstd_archive(snap['snapshot_path'], self.out, level=3)
        create_receipt(archive['archive_path'])
        self.assertEqual(inspect_receipt(self.out, Path(archive['archive_path']).name)['status'],
                         'RECEIPT_AND_CONTENT_VERIFIED_UNSIGNED')

    def test_parent_receipt_lineage_chain(self):
        snap = self.snapshot()
        parent = create_receipt(snap['snapshot_path'])
        archive = make_zip_archive(snap['snapshot_path'], self.out)
        child = create_receipt(archive['archive_path'], parent_receipt_name=parent['receipt_name'])
        self.assertNotEqual(parent['receipt_name'], child['receipt_name'])
        self.assertEqual(parent['snapshot_sha256'], child['snapshot_sha256'])
        self.assertEqual(inspect_receipt(self.out, Path(archive['archive_path']).name)['status'],
                         'RECEIPT_AND_CONTENT_VERIFIED_UNSIGNED')
        with self.receipt_file(archive['archive_path']).open('r') as inp:
            doc = json.load(inp)
        self.assertEqual(doc['parent_receipt_sha256'], parent['receipt_sha256'])
        self.assertNotIn(str(self.source), str(doc))
        self.assertNotIn(str(self.out), str(doc))

    def test_three_generation_receipts(self):
        snap = self.snapshot()
        a = create_receipt(snap['snapshot_path'])
        z = make_zip_archive(snap['snapshot_path'], self.out)
        b = create_receipt(z['archive_path'], parent_receipt_name=a['receipt_name'])
        if not shutil.which('zstd'):
            self.skipTest('Optional local ZSTD CLI missing')
        c = create_zstd_archive(snap['snapshot_path'], self.out)
        create_receipt(c['archive_path'], parent_receipt_name=b['receipt_name'])
        self.assertEqual(inspect_receipt(self.out, Path(c['archive_path']).name)['status'],
                         'RECEIPT_AND_CONTENT_VERIFIED_UNSIGNED')

    def test_changed_parent_record_invalidates_child(self):
        snap = self.snapshot()
        a = create_receipt(snap['snapshot_path'])
        z = make_zip_archive(snap['snapshot_path'], self.out)
        create_receipt(z['archive_path'], parent_receipt_name=a['receipt_name'])
        original = self.receipt_file(snap['snapshot_path'])
        obj = json.loads(original.read_text())
        obj['verified_at_utc'] = '2026-01-02T00:00:00+00:00'
        original.write_text(json.dumps(obj))
        result = inspect_receipt(self.out, Path(z['archive_path']).name)
        self.assertEqual(result['status'], 'RECEIPT_FAILED_REVIEW')
        self.assertEqual(result['error_code'], 'LINEAGE_MISMATCH')

    def test_missing_parent_is_not_success(self):
        snap = self.snapshot()
        parent = create_receipt(snap['snapshot_path'])
        z = make_zip_archive(snap['snapshot_path'], self.out)
        create_receipt(z['archive_path'], parent_receipt_name=parent['receipt_name'])
        self.receipt_file(snap['snapshot_path']).unlink()
        result = inspect_receipt(self.out, Path(z['archive_path']).name)
        self.assertEqual(result['error_code'], 'MISSING_RECEIPT')

    def test_changed_parent_artifact_invalidates_child(self):
        snap = self.snapshot()
        parent = create_receipt(snap['snapshot_path'])
        z = make_zip_archive(snap['snapshot_path'], self.out)
        create_receipt(z['archive_path'], parent_receipt_name=parent['receipt_name'])
        Path(snap['snapshot_path']).write_bytes(b'bad source')
        verdict = inspect_receipt(self.out, Path(z['archive_path']).name)
        self.assertEqual(verdict['status'], 'RECEIPT_FAILED_REVIEW')
        self.assertIn(verdict['error_code'], ('CORRUPT_SQLITE', 'ARTIFACT_MISMATCH'))

    def test_published_artifact_changed_after_receipt(self):
        snap = self.snapshot()
        zip_data = make_zip_archive(snap['snapshot_path'], self.out)
        create_receipt(zip_data['archive_path'])
        Path(zip_data['archive_path']).write_bytes(b'evil')
        result = inspect_receipt(self.out, Path(zip_data['archive_path']).name)
        self.assertEqual(result['status'], 'RECEIPT_FAILED_REVIEW')
        self.assertNotIn(result['error_code'], ('MISSING_RECEIPT',))

    def test_receipt_duplicate_is_never_overwritten(self):
        snap = self.snapshot()
        first = create_receipt(snap['snapshot_path'])
        name = self.receipt_file(snap['snapshot_path'])
        before = self.identity(name)
        with self.assertRaises(ArchiveError) as error:
            create_receipt(snap['snapshot_path'])
        self.assertEqual(error.exception.code, 'RECEIPT_EXISTS')
        self.assertEqual(self.identity(name), before)
        self.assertEqual(first['status'], 'RECORDED_UNSIGNED')

    def test_parallel_receipt_creation_only_one_succeeds(self):
        snap = self.snapshot()
        def attempt(_):
            try:
                create_receipt(snap['snapshot_path'])
                return 'created'
            except ArchiveError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=5) as pool:
            statuses = list(pool.map(attempt, range(5)))
        self.assertEqual(statuses.count('created'), 1)
        self.assertEqual(statuses.count('RECEIPT_EXISTS'), 4)
        self.assertEqual(inspect_receipt(self.out, Path(snap['snapshot_path']).name)['status'],
                         'RECEIPT_AND_CONTENT_VERIFIED_UNSIGNED')

    def test_fail_before_link_preserves_unrecorded_archive(self):
        snap = self.snapshot()
        before = self.identity(snap['snapshot_path'])
        if os.name == 'nt':
            from dbvora.archive import windows_ntfs_publish as native
            failure = patch.object(native, '_native_move_write_through',
                                   side_effect=native.WinPublishError('MOVE_FAILED'))
        else:
            failure = patch('dbvora.archive.receipts.os.link', side_effect=OSError('simulated failed link'))
        with failure:
            with self.assertRaises(ArchiveError):
                create_receipt(snap['snapshot_path'])
        self.assertEqual(inspect_receipt(self.out, Path(snap['snapshot_path']).name)['error_code'],
                         'MISSING_RECEIPT')
        self.assertEqual(before, self.identity(snap['snapshot_path']))
        self.assertEqual([p.name for p in self.out.iterdir()], [Path(snap['snapshot_path']).name])

    def test_directory_fsync_failure_rolls_back_new_receipt(self):
        snap = self.snapshot()
        original = self.identity(snap['snapshot_path'])
        if os.name == 'nt':
            from dbvora.archive import windows_ntfs_publish as native
            failure = patch.object(native, '_native_move_write_through',
                                   side_effect=native.WinPublishError('MOVE_FAILED'))
        else:
            failure = patch('dbvora.archive.receipts._sync_directory',
                            side_effect=ArchiveError('PUBLISH_FAILED', 'injected'))
        with failure:
            with self.assertRaises(ArchiveError):
                create_receipt(snap['snapshot_path'])
        self.assertEqual(inspect_receipt(self.out, Path(snap['snapshot_path']).name)['error_code'],
                         'MISSING_RECEIPT')
        self.assertEqual(self.identity(snap['snapshot_path']), original)

    def test_staging_write_failure_preserves_existing_receipt(self):
        snap = self.snapshot()
        before = self.identity(snap['snapshot_path'])
        with patch('dbvora.archive.receipts._sync_staged_file', side_effect=ArchiveError('PUBLISH_FAILED', 'fail')):
            with self.assertRaises(ArchiveError):
                create_receipt(snap['snapshot_path'])
        self.assertEqual(self.identity(snap['snapshot_path']), before)
        self.assertEqual(inspect_receipt(self.out, Path(snap['snapshot_path']).name)['error_code'],
                         'MISSING_RECEIPT')

    def test_reject_invalid_parent_and_self_reference(self):
        snap = self.snapshot()
        with self.assertRaises(ArchiveError):
            create_receipt(snap['snapshot_path'], parent_receipt_name='../../evil')
        with self.assertRaises(ArchiveError):
            create_receipt(snap['snapshot_path'], parent_receipt_name=receipts._receipt_name(Path(snap['snapshot_path']).name))
        self.assertEqual(len(list(self.out.glob('dbvora-receipt-*'))), 0)

    def test_receipt_symlink_is_not_overwritten_or_followed(self):
        snap = self.snapshot()
        target = self.root / 'untouched.txt'
        target.write_text('secret')
        link = self.receipt_file(snap['snapshot_path'])
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symlink unsupported')
        with self.assertRaises(ArchiveError) as err:
            create_receipt(snap['snapshot_path'])
        self.assertEqual(err.exception.code, 'RECEIPT_EXISTS')
        self.assertEqual(inspect_receipt(self.out, Path(snap['snapshot_path']).name)['status'],
                         'RECEIPT_FAILED_REVIEW')
        self.assertEqual(target.read_text(), 'secret')

    def test_missing_artifact_never_marks_valid_receipt(self):
        snap = self.snapshot()
        create_receipt(snap['snapshot_path'])
        Path(snap['snapshot_path']).unlink()
        outcome = inspect_receipt(self.out, Path(snap['snapshot_path']).name)
        self.assertEqual(outcome['status'], 'RECEIPT_FAILED_REVIEW')
        self.assertEqual(outcome['error_code'], 'ARTIFACT_MISSING')

    def test_invalid_receipt_json_not_authentic(self):
        snap = self.snapshot()
        create_receipt(snap['snapshot_path'])
        self.receipt_file(snap['snapshot_path']).write_text('{malformed')
        self.assertEqual(inspect_receipt(self.out, Path(snap['snapshot_path']).name)['error_code'],
                         'BAD_RECEIPT')

    def test_oversized_receipt_refused_and_remains_untouched(self):
        snap = self.snapshot()
        create_receipt(snap['snapshot_path'])
        path = self.receipt_file(snap['snapshot_path'])
        path.write_bytes(b'a' * 5000)
        before = self.identity(path)
        self.assertEqual(inspect_receipt(self.out, Path(snap['snapshot_path']).name)['error_code'],
                         'BAD_RECEIPT')
        self.assertEqual(self.identity(path), before)

    def test_linked_receipt_not_trusted(self):
        snap = self.snapshot()
        create_receipt(snap['snapshot_path'])
        external = self.root / 'external.json'
        os.link(self.receipt_file(snap['snapshot_path']), external)
        self.assertEqual(inspect_receipt(self.out, Path(snap['snapshot_path']).name)['error_code'],
                         'BAD_RECEIPT')

    def test_unsigned_record_not_claimed_to_be_signature(self):
        snap = self.snapshot()
        created = create_receipt(snap['snapshot_path'])
        self.assertEqual(created['durability'], 'power_failure_not_proven')
        report = inspect_receipt(self.out, Path(snap['snapshot_path']).name)
        self.assertEqual(report['authentication'], 'unsigned_untrusted')
        self.assertEqual(report['durability'], 'unproven_after_power_failure')

    def test_report_has_no_database_rows_or_absolute_path(self):
        snap = self.snapshot()
        create_receipt(snap['snapshot_path'])
        report = inspect_receipt(self.out, Path(snap['snapshot_path']).name)
        self.assertNotIn(str(self.root), json.dumps(report))
        self.assertNotIn(str(self.source), json.dumps(report))

    def test_fake_receipt_unbound_to_artifact_name_fails(self):
        snap = self.snapshot()
        create_receipt(snap['snapshot_path'])
        path = self.receipt_file(snap['snapshot_path'])
        record = json.loads(path.read_text())
        record['artifact_name'] = 'dbvora-' + 'a'*32 + '.zip'
        path.write_text(json.dumps(record))
        self.assertEqual(inspect_receipt(self.out, Path(snap['snapshot_path']).name)['error_code'],
                         'BAD_RECEIPT')

    def test_truncated_parent_chain_fails_closed(self):
        snap = self.snapshot()
        receipt = create_receipt(snap['snapshot_path'])
        zip_path = make_zip_archive(snap['snapshot_path'], self.out)['archive_path']
        create_receipt(zip_path, parent_receipt_name=receipt['receipt_name'])
        parent_path = self.receipt_file(snap['snapshot_path'])
        parent_path.write_bytes(b'')
        state = inspect_receipt(self.out, Path(zip_path).name)
        self.assertEqual(state['status'], 'RECEIPT_FAILED_REVIEW')


class ReceiptAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'archives'
        self.output.mkdir()
        self.src = create_fixture(self.root / 'synthetic.sqlite')

    def test_receipt_catalog_distinguishes_missing_and_complete(self):
        from dbvora.archive.receipts import inspect_receipt_catalog
        s = create_snapshot(self.src, self.output)
        before = inspect_receipt_catalog(self.output)
        self.assertEqual(before['records'][0]['status'], 'CONTENT_VERIFIED_PUBLISH_UNPROVEN')
        self.assertEqual(before['records'][0]['receipt_error_code'], 'MISSING_RECEIPT')
        created = create_receipt(s['snapshot_path'])
        after = inspect_receipt_catalog(self.output)
        self.assertEqual(after['records'][0]['status'], 'RECORDED_AND_CONTENT_VERIFIED_UNSIGNED')
        self.assertEqual(after['records'][0]['receipt_sha256'], created['receipt_sha256'])
        self.assertEqual(len(after['records']), 1)

    def test_receipt_catalog_skips_bad_archive_not_falsely_promoting(self):
        from dbvora.archive.receipts import inspect_receipt_catalog
        s = create_snapshot(self.src, self.output)
        create_receipt(s['snapshot_path'])
        Path(s['snapshot_path']).write_bytes(b'changed')
        check = inspect_receipt_catalog(self.output)['records'][0]
        self.assertEqual(check['status'], 'FAILED_REVIEW')
        self.assertEqual(check['receipt_status'], 'SKIPPED_DUE_TO_ARTIFACT_REVIEW_FAILURE')

    def test_subprocess_crash_before_receipt_leaves_explicit_gap(self):
        snap = create_snapshot(self.src, self.output)
        child_code = ('import os,sys;from dbvora.archive.receipts import _receipt_name;'
                      'from pathlib import Path;'
                      'assert not (Path(sys.argv[1])/_receipt_name(sys.argv[2])).exists();'
                      'os._exit(31)')
        proc = subprocess.run([sys.executable,'-c',child_code,str(self.output),Path(snap['snapshot_path']).name],
                              capture_output=True,text=True,timeout=12)
        self.assertEqual(proc.returncode,31,proc.stderr)
        from dbvora.archive.receipts import inspect_receipt_catalog
        audit = inspect_receipt_catalog(self.output)
        self.assertEqual(audit['records'][0]['receipt_error_code'],'MISSING_RECEIPT')
        # Explicit operator action is required; never automatic upon scan.
        create_receipt(snap['snapshot_path'])
        self.assertEqual(inspect_receipt_catalog(self.output)['records'][0]['status'],
                         'RECORDED_AND_CONTENT_VERIFIED_UNSIGNED')

    def test_subprocess_crash_after_receipt_pub_still_restarts_cleanly(self):
        snap = create_snapshot(self.src, self.output)
        child_code = ('import os,sys;from dbvora.archive.receipts import create_receipt;'
                      'create_receipt(sys.argv[1]);os._exit(34)')
        proc = subprocess.run([sys.executable,'-c',child_code,snap['snapshot_path']],
                              capture_output=True,text=True,timeout=18)
        self.assertEqual(proc.returncode,34,proc.stderr)
        from dbvora.archive.receipts import inspect_receipt_catalog
        entry = inspect_receipt_catalog(self.output)['records'][0]
        self.assertEqual(entry['status'],'RECORDED_AND_CONTENT_VERIFIED_UNSIGNED')
        with self.assertRaises(ArchiveError) as raised:
            create_receipt(snap['snapshot_path'])
        self.assertEqual(raised.exception.code,'RECEIPT_EXISTS')


if __name__ == '__main__':
    unittest.main()
