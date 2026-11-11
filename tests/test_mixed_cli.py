"""Subprocess and mocked-Postgres mixed CLI acceptance, synthetic fixtures only."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dbvora import mixed_cli
from tests.fixtures.make_sqlite import create_fixture


class MixedCliTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='dbvora-mixed-cli-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = create_fixture(self.root / 'fixture.sqlite')
        self.output = self.root / 'out'
        self.output.mkdir()
        self.flags = ['--sqlite', str(self.source), '--output-dir', str(self.output),
                      '--synthetic-only', '--accept-unencrypted-metadata']

    def invoke(self, args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = mixed_cli.main(args)
        return code, json.loads(out.getvalue() if code == 0 else err.getvalue())

    def test_cli_creates_plaintext_report_and_preserves_fixture(self):
        sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        ts = self.source.stat().st_mtime_ns
        code, result = self.invoke(self.flags)
        self.assertEqual(code, 0)
        page = (self.output / result['result']['filename']).read_text()
        self.assertIn('Structure map', page)
        self.assertIn('customers', page)
        self.assertTrue(result['result']['status'].startswith('OFFLINE_'))
        self.assertEqual((sha, ts), (hashlib.sha256(self.source.read_bytes()).hexdigest(),
                                     self.source.stat().st_mtime_ns))

    def test_unacknowledged_command_writes_nothing(self):
        code, result = self.invoke(self.flags[:-1])
        self.assertEqual(code, 2)
        self.assertEqual(result['error']['code'], 'PLAINTEXT_ACK_REQUIRED')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_no_synthetic_confirmation_writes_nothing(self):
        code, result = self.invoke([x for x in self.flags if x != '--synthetic-only'])
        self.assertEqual(code, 2)
        self.assertEqual(result['error']['code'], 'SYNTHETIC_ONLY_REQUIRED')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_repeated_source_is_rejected(self):
        code, result = self.invoke(self.flags + ['--sqlite', str(self.source)])
        self.assertEqual(code, 2)
        self.assertEqual(result['error']['code'], 'DUPLICATE_SOURCE')

    def test_output_source_dir_protection(self):
        bad = self.flags.copy()
        bad[bad.index('--output-dir') + 1] = str(self.source.parent)
        code, result = self.invoke(bad)
        self.assertEqual(code, 2)
        self.assertEqual(result['error']['code'], 'SEPARATE_OUTPUT_REQUIRED')

    def test_output_symlink_is_rejected_before_publication(self):
        alias = self.root / 'link'
        try:
            alias.symlink_to(self.output, target_is_directory=True)
        except OSError:
            return
        args = self.flags.copy()
        args[args.index('--output-dir') + 1] = str(alias)
        code, result = self.invoke(args)
        self.assertEqual(code, 2)
        self.assertEqual(result['error']['code'], 'BAD_DESTINATION')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_pg_requires_explicit_network_flag(self):
        code, result = self.invoke(['--postgres-dsn-env', 'DBVORA_TEST_DSN',
                                    '--output-dir', str(self.output),
                                    '--synthetic-only', '--accept-unencrypted-metadata'])
        self.assertEqual(code, 2)
        self.assertEqual(result['error']['code'], 'NETWORK_ACK_REQUIRED')

    def test_pg_missing_environment_is_safe(self):
        args = ['--postgres-dsn-env', 'DBVORA_TEST_DSN', '--allow-postgres-network',
                '--output-dir', str(self.output), '--synthetic-only', '--accept-unencrypted-metadata']
        with patch.dict(os.environ, {}, clear=True):
            code, result = self.invoke(args)
        self.assertEqual(result['error']['code'], 'PG_DSN_UNAVAILABLE')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_pg_metadata_only_integration_with_fake_connection(self):
        from dbvora.connectors.postgres_reader import inspect_catalog
        from tests.test_postgres_reader import Connection
        pg = inspect_catalog(Connection())
        args = self.flags + ['--postgres-dsn-env', 'DBVORA_TEST_DSN', '--allow-postgres-network']
        with patch.dict(os.environ, {'DBVORA_TEST_DSN': 'host=secret password=hidden'}), \
                patch.object(mixed_cli, 'inspect_postgres', return_value=pg) as connect:
            code, result = self.invoke(args)
        self.assertEqual(code, 0)
        self.assertEqual(connect.call_count, 1)
        self.assertIn('public.orders', (self.output / result['result']['filename']).read_text())
        self.assertNotIn('password', json.dumps(result))
        self.assertNotIn('secret', json.dumps(result))

    def test_env_name_rejects_injected_argument(self):
        code, result = self.invoke(self.flags + ['--postgres-dsn-env', 'BAD/ENV',
                                                 '--allow-postgres-network'])
        self.assertEqual(code, 2)
        self.assertEqual(result['error']['code'], 'INVALID_ENV_NAME')

    def test_sqlite_subprocess_exact_command(self):
        child = subprocess.run([sys.executable, '-m', 'dbvora.mixed_cli', *self.flags],
                               capture_output=True, text=True, timeout=15)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(json.loads(child.stdout)['ok'], True)
        self.assertNotIn(str(self.source), child.stdout)

    def test_unrecognized_option_never_echoes_private_path(self):
        secret = '/home/private/secrets.sqlite'
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = mixed_cli.main(self.flags + [secret])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(err.getvalue())['error']['code'], 'INVALID_ARGUMENT')
        self.assertNotIn(secret, err.getvalue())

    def test_pg_driver_absence_never_exposes_dsn(self):
        args = self.flags + ['--postgres-dsn-env', 'DBVORA_TEST_DSN', '--allow-postgres-network']
        with patch.dict(os.environ, {'DBVORA_TEST_DSN': 'password=super-secret host=localhost'}), \
                patch.dict(sys.modules, {'psycopg': None}):
            code, result = self.invoke(args)
        self.assertEqual(code, 2)
        self.assertEqual(result['error']['code'], 'DRIVER_UNAVAILABLE')
        self.assertNotIn('super-secret', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
