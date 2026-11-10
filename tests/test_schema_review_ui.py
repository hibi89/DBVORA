"""P0-09 full-source HTML embedding regression; synthetic SQLite only."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest

from dbvora.workspace_html import export_synthetic_workspace, export_workspace


def embedded_workspace(html: str) -> dict:
    match = re.search(r'const encodedWorkspace="([A-Za-z0-9+/=]+)";', html)
    if match is None:
        raise AssertionError("encoded workspace absent")
    return json.loads(base64.b64decode(match.group(1)))


class SchemaReviewUiTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="dbvora-schema-ui-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_synthetic_demo_exposes_advisory_panel(self):
        result = export_synthetic_workspace(self.root)
        html = (self.root / result["filename"]).read_text(encoding="utf-8")
        self.assertIn('id="schema-review"', html)
        workspace = embedded_workspace(html)
        review = workspace["schema_review"]
        self.assertEqual(review["status"], "REVIEW_ONLY")
        self.assertTrue(review["no_row_scanning"])
        self.assertNotIn("SYNTHETIC_ROW_DO_NOT_EXPORT", html)

    def test_real_sqlite_catalog_only_and_no_row_leak(self):
        files = [self.root / "one.db", self.root / "two.db"]
        for p in files:
            with sqlite3.connect(p) as connection:
                connection.execute("CREATE TABLE logs(message TEXT)")
                connection.execute("INSERT INTO logs VALUES('PRIVATE_ROW_NEVER_EXPORT')")
                connection.commit()
        result = export_workspace(files, self.root)
        html = (self.root / result["filename"]).read_text(encoding="utf-8")
        review = embedded_workspace(html)["schema_review"]
        self.assertEqual(review["without_declared_pk"], 2)
        self.assertNotIn("PRIVATE_ROW_NEVER_EXPORT", html)


if __name__ == "__main__":
    unittest.main()
