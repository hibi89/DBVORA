"""Real synthetic OS subprocess exit tests; not a physical power-loss guarantee."""
from __future__ import annotations

from contextlib import closing
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from dbvora.archive import compressed_cas as cas
from dbvora.archive.safe_zip import create_snapshot
from tests.fixtures.make_sqlite import create_fixture


CREATE_CRASH = (
    "import os,sys\n"
    "from dbvora.archive import compressed_cas as cas\n"
    "cas._publish_new=lambda *args,**kwargs:os._exit(71)\n"
    "cas.create_compressed(sys.argv[1],sys.argv[2],sys.argv[3],"
    "synthetic_only=True,accept_plaintext=True)\n"
    "os._exit(0)\n"
)
RESTORE_CRASH = (
    "import os,sys\n"
    "from dbvora.archive import compressed_cas as cas\n"
    "cas._publish_new=lambda *args,**kwargs:os._exit(72)\n"
    "cas.restore_compressed(sys.argv[1],sys.argv[2],sys.argv[3],"
    "synthetic_only=True,accept_plaintext=True)\n"
    "os._exit(0)\n"
)


class CasSubprocessCrashTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dbvora-crash-synthetic-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = create_fixture(self.root / "source.sqlite")
        self.snap, self.chunks, self.manifest, self.restored = (
            self.root / name for name in ("snap", "chunks", "manifests", "restored"))
        for folder in (self.snap, self.chunks, self.manifest, self.restored):
            folder.mkdir()
        self.snapshot = Path(create_snapshot(self.source, self.snap)["snapshot_path"])
        self.old = cas.create_compressed(
            self.snapshot, self.chunks, self.manifest,
            synthetic_only=True, accept_plaintext=True)
        self.old_manifest = self.manifest / self.old["manifest_name"]
        self.old_manifest_sha = hashlib.sha256(self.old_manifest.read_bytes()).hexdigest()

    def child(self, code, *paths):
        child = subprocess.run(
            [sys.executable, "-c", code, *(str(x) for x in paths)],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.DEVNULL, capture_output=True,
            timeout=35, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        # No subprocess stdout/stderr should reveal any source path or row.
        self.assertEqual(child.stdout, b"")
        self.assertEqual(child.stderr, b"")
        return child.returncode

    def assert_previous_archive_unchanged(self):
        self.assertTrue(self.old_manifest.exists())
        self.assertEqual(
            hashlib.sha256(self.old_manifest.read_bytes()).hexdigest(), self.old_manifest_sha)

    def test_real_child_exit_before_second_generation_manifest_publish(self):
        with closing(sqlite3.connect(self.source)) as conn:
            conn.execute("CREATE TABLE changed_after_first(id INTEGER PRIMARY KEY)")
            conn.commit()
        newer = Path(create_snapshot(self.source, self.snap)["snapshot_path"])
        original_manifest_names = sorted(p.name for p in self.manifest.iterdir())
        code = self.child(CREATE_CRASH, newer, self.chunks, self.manifest)
        self.assertEqual(code, 71)
        self.assertEqual(original_manifest_names,
                         sorted(p.name for p in self.manifest.glob("dbvora-*.json")))
        self.assert_previous_archive_unchanged()
        old_restore = cas.restore_compressed(
            self.old_manifest, self.chunks, self.restored,
            synthetic_only=True, accept_plaintext=True)
        self.assertEqual(old_restore["restored_sha256"], self.old["snapshot_sha256"])
        self.assertEqual(len(list(self.restored.glob("dbvora-*.sqlite"))), 1)

    def test_real_child_exit_before_restore_publication_keeps_last_good(self):
        good = cas.restore_compressed(
            self.old_manifest, self.chunks, self.restored,
            synthetic_only=True, accept_plaintext=True)
        previous = self.restored / good["restored_name"]
        previous_hash = hashlib.sha256(previous.read_bytes()).hexdigest()
        code = self.child(RESTORE_CRASH, self.old_manifest, self.chunks, self.restored)
        self.assertEqual(code, 72)
        self.assert_previous_archive_unchanged()
        self.assertEqual(len(list(self.restored.glob("dbvora-*.sqlite"))), 1)
        self.assertEqual(hashlib.sha256(previous.read_bytes()).hexdigest(), previous_hash)
        self.assertEqual(previous_hash, self.old["snapshot_sha256"])


if __name__ == "__main__":
    unittest.main()
