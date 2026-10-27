"""Unsafe/mutable metadata input must fail before workspace schema export."""
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dbvora.safe_metadata_file import read_local_json, MetadataInputError
from dbvora import workspace_html
from dbvora.workspace_observations import ObservationError, read_observation


class SafeMetadataFileTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="dbvora-metadata-security-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.target = self.root / "input.json"

    def load(self, content: str, limit=16384):
        self.target.write_text(content, encoding="utf-8")
        return read_local_json(self.target, max_bytes=limit)

    def test_valid_json_roundtrip(self):
        self.assertEqual(self.load('{"edges":[{"from_db":1}]}'), {"edges": [{"from_db": 1}]})

    def test_duplicate_keys_rejected_recursively(self):
        for document in ['{"a":1,"a":2}', '{"a":{"x":1,"x":2}}']:
            with self.subTest(document=document), self.assertRaises(MetadataInputError):
                self.load(document)

    def test_nan_and_infinity_rejected(self):
        for constant in ['NaN','Infinity','-Infinity']:
            with self.subTest(constant=constant), self.assertRaises(MetadataInputError):
                self.load('{"a":' + constant + '}')

    def test_relative_path_rejected(self):
        with self.assertRaises(MetadataInputError):
            read_local_json('relative.json', max_bytes=16384)

    def test_symlink_rejected(self):
        link = self.root / 'link.json'
        self.target.write_text('{}')
        try:
            link.symlink_to(self.target)
        except (OSError, NotImplementedError):
            self.skipTest('Symlinks unavailable on this filesystem')
        with self.assertRaises(MetadataInputError):
            read_local_json(link, max_bytes=16384)

    def test_size_rejected_before_read(self):
        self.target.write_bytes(b'x' * 65)
        with self.assertRaises(MetadataInputError):
            read_local_json(self.target, max_bytes=64)

    def test_mismatched_opened_inode_denied(self):
        self.target.write_text('{}')
        with patch('dbvora.safe_metadata_file.os.fstat') as mocked:
            original = self.target.stat()
            mocked.return_value = type('Info', (), {'st_mode': original.st_mode,
                'st_size': original.st_size, 'st_dev': original.st_dev,
                'st_ino': original.st_ino + 1})()
            with self.assertRaises(MetadataInputError):
                read_local_json(self.target, max_bytes=16384)

    def test_truncate_during_read_denied(self):
        self.target.write_text('{}')
        with patch('dbvora.safe_metadata_file.os.fstat') as mocked:
            original = self.target.stat()
            mocked.return_value = type('Info', (), {'st_mode': original.st_mode,
                'st_size': original.st_size + 2, 'st_dev': original.st_dev,
                'st_ino': original.st_ino})()
            with self.assertRaises(MetadataInputError):
                read_local_json(self.target, max_bytes=16384)

    def test_manifest_duplicate_link_fields_denied(self):
        self.target.write_text('[{"from_db":1,"from_db":2}]')
        with self.assertRaisesRegex(workspace_html.WorkspaceHtmlError, 'INVALID_LINK_MANIFEST'):
            workspace_html._load_links_manifest(self.target)

    def test_manifest_nonfinite_denied(self):
        self.target.write_text('[{"from_db":NaN}]')
        with self.assertRaisesRegex(workspace_html.WorkspaceHtmlError, 'INVALID_LINK_MANIFEST'):
            workspace_html._load_links_manifest(self.target)

    def test_observation_duplicate_contract_denied(self):
        self.target.write_text('{"contract":"good","contract":"bad","databases":[]}')
        with self.assertRaises(ObservationError):
            read_observation(self.target)

    def test_synthetic_cli_rejects_unused_save_observation(self):
        out = StringIO()
        with redirect_stdout(out):
            code = workspace_html.main(['--synthetic-only','--save-observation','--out',str(self.root)])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())['error_code'], 'INVALID_LINK_MANIFEST')
        self.assertFalse(list(self.root.glob('dbvora-workspace-*.html')))


if __name__ == '__main__':
    unittest.main()
