"""Synthetic portable launch/stop/restart and safe folder-removal acceptance."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener
import zipfile

from scripts import build_portable as pack
from tests.fixtures.make_sqlite import create_fixture


class PortableLauncherLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='dbvora-launcher-lifecycle-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.opener = build_opener(ProxyHandler({}))

    def _start(self, package: Path, database: Path, port: int, label: str):
        log = self.root / f'{label}.log'
        env = os.environ.copy()
        env.pop('DBVORA_POSTGRES_DSN', None)
        env.pop('DBVORA_OBSERVATION_LEDGER', None)
        env.pop('PYTHONHOME', None)
        env['PYTHONPATH'] = ''
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        launcher = package / ('run_dbvora_windows.cmd' if os.name == 'nt'
                             else 'run_dbvora_unix.sh')
        if os.name == 'nt':
            command = subprocess.list2cmdline([str(launcher), str(database), str(port)])
            options = {'shell': True,
                       'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
        else:
            command = ['sh', str(launcher), str(database), str(port)]
            options = {'start_new_session': True}
        with log.open('w', encoding='utf-8') as stream:
            process = subprocess.Popen(command, cwd=package, env=env,
                                       stdout=stream, stderr=subprocess.STDOUT,
                                       **options)
        return process, log

    def _read_inventory(self, process: subprocess.Popen, log: Path, port: int):
        deadline = time.monotonic() + 20
        url = f'http://127.0.0.1:{port}/api/inventory'
        last_error = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            try:
                with self.opener.open(url, timeout=1) as response:
                    self.assertEqual(response.status, 200)
                    return json.loads(response.read())
            except (OSError, URLError) as error:
                last_error = type(error).__name__
                time.sleep(0.2)
        detail = log.read_text('utf-8', errors='replace')[-2000:]
        self.fail(f'LOCAL_SERVER_DID_NOT_START ({last_error}): {detail}')

    def _stop(self, process: subprocess.Popen):
        if process.poll() is not None:
            return
        try:
            if os.name == 'nt':
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(process.pid, signal.SIGINT)
            process.wait(timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            if os.name == 'nt':
                subprocess.run(['taskkill.exe', '/F', '/T', '/PID', str(process.pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=10, check=False)
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=10)

    def _assert_port_free(self, port: int):
        deadline = time.monotonic() + 10
        last_error = None
        while time.monotonic() < deadline:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                    probe.bind(('127.0.0.1', port))
                return
            except OSError as error:
                last_error = error
                time.sleep(0.2)
        self.fail(f'LOCAL_PORT_REMAINS_BOUND: {last_error}')

    def _postgres_disabled(self, port: int):
        try:
            with self.opener.open(f'http://127.0.0.1:{port}/api/postgres', timeout=3) as response:
                self.fail(f'PostgreSQL was unexpectedly reachable: {response.status}')
        except HTTPError as error:
            self.assertEqual(error.code, 404)
            self.assertEqual(json.loads(error.read())['error']['code'], 'POSTGRES_DISABLED')

    def test_manual_launch_conflict_stop_restart_and_remove_preserves_existing_data(self):
        data_folder = self.root / 'existing-owner-data'
        data_folder.mkdir()
        marker = data_folder / 'keep-existing.txt'
        marker.write_text('synthetic-owner-file', encoding='utf-8')
        database = create_fixture(data_folder / 'synthetic.sqlite')
        original_sha = hashlib.sha256(database.read_bytes()).hexdigest()

        package_parent = self.root / 'applications'
        package_parent.mkdir()
        application = package_parent / 'DBVORA'
        build_output = self.root / 'build-output'
        build_output.mkdir()
        archive = pack.build(build_output, source_commit='c' * 40)
        self.assertEqual(pack.verify_zip(archive)['source_commit'], 'c' * 40)
        application.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(application)
        self.assertTrue((application / 'run_dbvora_windows.cmd').is_file())

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]

        first, first_log = self._start(application, database, port, 'first-start')
        second = None
        restarted = None
        try:
            inventory = self._read_inventory(first, first_log, port)
            self.assertEqual(len(inventory['tables']), 3)
            self._postgres_disabled(port)

            second, second_log = self._start(application, database, port, 'port-conflict')
            try:
                result = second.wait(timeout=12)
            except subprocess.TimeoutExpired:
                self._stop(second)
                self.fail('PORT_CONFLICT_DID_NOT_EXIT')
            conflict_report = second_log.read_text('utf-8', errors='replace')
            self.assertNotEqual(result, 0)
            self.assertIn('PORT_IN_USE', conflict_report)
            self.assertEqual(len(self._read_inventory(first, first_log, port)['tables']), 3)

            self._stop(first)
            self._assert_port_free(port)
            restarted, restarted_log = self._start(application, database, port, 'restart')
            self.assertEqual(len(self._read_inventory(restarted, restarted_log, port)['tables']), 3)
            self._stop(restarted)
            self._assert_port_free(port)
        finally:
            if second is not None and second.poll() is None:
                self._stop(second)
            if first.poll() is None:
                self._stop(first)
            if restarted is not None and restarted.poll() is None:
                self._stop(restarted)

        self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(), original_sha)
        self.assertTrue(marker.is_file())
        self.assertTrue(database.is_file())
        shutil.rmtree(application)
        self.assertFalse(application.exists())
        self.assertTrue(package_parent.is_dir())
        self.assertTrue(data_folder.is_dir())
        self.assertTrue(marker.is_file())
        self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(), original_sha)


if __name__ == '__main__':
    unittest.main()
