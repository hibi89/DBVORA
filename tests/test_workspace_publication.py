"""P0-08 offline SQLite report/observation consistency checks."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from dbvora.workspace_html import WorkspaceHtmlError, export_workspace
from dbvora.workspace_observations import ObservationError


class WorkspacePublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dbvora-p008-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = [self.root / "one.sqlite", self.root / "two.sqlite"]
        for p in self.paths:
            with closing(sqlite3.connect(p)) as conn:
                conn.execute("CREATE TABLE example(id INTEGER PRIMARY KEY, name TEXT)")
                conn.execute("INSERT INTO example(name) VALUES('ROW_CANARY_DO_NOT_EXPORT')")
                conn.commit()

    def test_success_publishes_both_new_non_overwriting_files(self):
        result = export_workspace(self.paths, self.root, save_observation=True)
        self.assertTrue((self.root / result["filename"]).is_file())
        self.assertTrue((self.root / result["observation_filename"]).is_file())
        self.assertNotIn("ROW_CANARY_DO_NOT_EXPORT", (self.root / result["filename"]).read_text())
        self.assertEqual(len(list(self.root.glob("dbvora-workspace-*.html"))), 1)

    def test_observation_failure_cleans_only_new_report(self):
        existing = self.root / ("dbvora-workspace-" + "f" * 32 + ".html")
        existing.write_text("customer-owned")
        with patch("dbvora.workspace_html.write_observation",
                   side_effect=ObservationError("OBSERVATION_WRITE_FAILED")):
            with self.assertRaises(ObservationError):
                export_workspace(self.paths, self.root, save_observation=True)
        self.assertEqual(existing.read_text(), "customer-owned")
        self.assertEqual([p.name for p in self.root.glob("dbvora-workspace-*.html")], [existing.name])

    def test_replaced_generated_report_never_deleted(self):
        observed = []
        def replace_then_fail(*_):
            report, = self.root.glob("dbvora-workspace-*.html")
            foreign = self.root / "foreign-owned.txt"
            foreign.write_text("do-not-delete")
            os.replace(foreign, report)
            observed.append(report)
            raise ObservationError("OBSERVATION_WRITE_FAILED")
        with patch("dbvora.workspace_html.write_observation", side_effect=replace_then_fail):
            with self.assertRaises(ObservationError):
                export_workspace(self.paths, self.root, save_observation=True)
        self.assertEqual(observed[0].read_text(), "do-not-delete")

    def test_html_write_failure_removes_partial_new_report(self):
        with patch("dbvora.workspace_html.os.fsync", side_effect=OSError("synthetic write failure")):
            with self.assertRaises(WorkspaceHtmlError) as e:
                export_workspace(self.paths, self.root)
        self.assertEqual(str(e.exception), "OUTPUT_WRITE_FAILED")
        self.assertEqual(list(self.root.glob("dbvora-workspace-*.html")), [])

    def test_observation_fsync_failure_removes_both_generated_outputs(self):
        real_fsync = os.fsync
        calls = [0]
        def fail_on_second(fd):
            calls[0] += 1
            if calls[0] == 2:
                raise OSError("synthetic second write failure")
            return real_fsync(fd)
        with patch("dbvora.workspace_html.os.fsync", side_effect=fail_on_second):
            with self.assertRaises(ObservationError):
                export_workspace(self.paths, self.root, save_observation=True)
        self.assertEqual(calls[0], 2)
        self.assertEqual(list(self.root.glob("dbvora-workspace-*.html")), [])
        self.assertEqual(list(self.root.glob("dbvora-observation-*.json")), [])



if __name__ == "__main__":
    unittest.main()
