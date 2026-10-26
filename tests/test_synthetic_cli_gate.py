"""Synthetic gate fail-closed behavior independent of filesystem capabilities."""
from contextlib import redirect_stderr, redirect_stdout
import io
import hashlib
from pathlib import Path
import tempfile
import json
import sys
import unittest
from unittest.mock import patch

from scripts import synthetic_cli_gate as gate


class SyntheticCliGateTests(unittest.TestCase):
    def test_invalid_cli_json_fails_closed(self):
        with patch.object(gate, 'archive_cli_main', return_value=2):
            with self.assertRaises(gate.GateFailure) as error:
                gate._invoke('snapshot')
        self.assertEqual(str(error.exception), 'INVALID_CLI_JSON')

    def test_safe_cli_error_code_preserved(self):
        def failure(_):
            print(json.dumps({'ok': False, 'error': {'code': 'SYNTHETIC_ONLY_REQUIRED'}}), file=sys.stderr)
            return 2
        with patch.object(gate, 'archive_cli_main', side_effect=failure):
            with self.assertRaises(gate.GateFailure) as error:
                gate._invoke('snapshot')
        self.assertEqual(str(error.exception), 'CLI_SYNTHETIC_ONLY_REQUIRED')

    def test_generated_file_hash_is_independently_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            name = 'dbvora-' + 'a' * 32 + '.dbvz'
            data = b'synthetic frame only'
            (base / name).write_bytes(data)
            actual = gate._generated_file(base, name, 'dbvz',
                                          expected_sha=hashlib.sha256(data).hexdigest())
            self.assertEqual(actual.name, name)

    def test_generated_file_does_not_trust_reported_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            name = 'dbvora-' + 'b' * 32 + '.sqlite'
            (base / name).write_bytes(b'altered synthetic bytes')
            with self.assertRaises(gate.GateFailure) as error:
                gate._generated_file(base, name, 'sqlite', expected_sha='0' * 64)
        self.assertEqual(str(error.exception), 'INDEPENDENT_FILE_SHA_MISMATCH')

    def test_parent_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            name = '../dbvora-' + 'b' * 32 + '.sqlite'
            with self.assertRaises(gate.GateFailure) as error:
                gate._generated_file(Path(tmp), name, 'sqlite')
        self.assertEqual(str(error.exception), 'INVALID_GENERATED_FILENAME')

    def test_wrong_extension_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(gate.GateFailure):
                gate._generated_file(Path(tmp), 'dbvora-' + 'c' * 32 + '.zip', 'sqlite')

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            target = base / 'safe-source'
            target.write_bytes(b'synthetic source')
            name = 'dbvora-' + 'd' * 32 + '.sqlite'
            try:
                (base / name).symlink_to(target)
            except (NotImplementedError, OSError):
                # Privilege-free fallback: still exercise the fail-closed branch.
                with patch.object(Path, 'is_symlink', return_value=True):
                    with self.assertRaises(gate.GateFailure):
                        gate._generated_file(base, name, 'sqlite')
                return
            with self.assertRaises(gate.GateFailure) as error:
                gate._generated_file(base, name, 'sqlite')
        self.assertEqual(str(error.exception), 'EXPECTED_ARTIFACT_MISSING')

    def test_failure_report_denies_customer_readiness(self):
        result = io.StringIO()
        with patch.object(gate, 'run_gate', side_effect=gate.GateFailure('HASH_MISMATCH')):
            with redirect_stdout(result):
                code = gate.main()
        self.assertEqual(code, 1)
        data = json.loads(result.getvalue())
        self.assertEqual(data['status'], 'FAIL')
        self.assertEqual(data['error_code'], 'HASH_MISMATCH')
        self.assertIs(data['ready_for_customer_data'], False)


if __name__ == '__main__':
    unittest.main()
