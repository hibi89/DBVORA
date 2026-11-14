"""Synthetic-only tests for explicit local observation recording."""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from dbvora.observation_cli import main
from dbvora.observation_ledger import read_observations
from tests.fixtures.make_sqlite import create_fixture


class ObservationCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = create_fixture(Path(self.tmp.name) / "source.sqlite")
        self.ledger = Path(self.tmp.name) / "observations.sqlite"

    def invoke(self, *, consent=False, ledger=None):
        output, error = io.StringIO(), io.StringIO()
        args = ["--database", str(self.source), "--ledger",
                str(ledger or self.ledger)]
        if consent:
            args.append("--consent")
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(args)
        return code, output.getvalue(), error.getvalue()

    def test_missing_explicit_consent_creates_nothing(self):
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        code, output, error = self.invoke(consent=False)
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("CONSENT_REQUIRED", error)
        self.assertFalse(self.ledger.exists())
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before)

    def test_explicit_record_is_local_metadata_only(self):
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        code, output, error = self.invoke(consent=True)
        self.assertEqual(code, 0, error)
        result = json.loads(output)
        self.assertEqual(result["contract"], "dbvora.local-observation-write.v1")
        self.assertEqual(result["status"], "appended")
        self.assertEqual(result["scope"], "sqlite_main_file_excluding_wal_shm")
        self.assertNotIn(str(self.source), output)
        self.assertNotIn(str(self.ledger), output)
        rows = read_observations(self.ledger, db_id=result["db_id"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["record_hash"], result["record_hash"])
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before)

    def test_source_database_cannot_be_selected_as_ledger(self):
        before = self.source.read_bytes()
        code, output, error = self.invoke(consent=True, ledger=self.source)
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("OBSERVATION_REJECTED", error)
        self.assertEqual(self.source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
