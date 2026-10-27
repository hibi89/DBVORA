"""Strict audit CLI fail-closed synthetic tests; no customer files."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest


class StrictAuditCliTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dbvora-audit-strict-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for directory in ("snapshot", "archive"):
            (self.root / directory).mkdir()
        self.source = self.root / "synthetic.sqlite"
        with closing(sqlite3.connect(self.source)) as conn:
            conn.execute("CREATE TABLE synthetic_items(id INTEGER PRIMARY KEY, value TEXT)")
            conn.executemany("INSERT INTO synthetic_items(value) VALUES (?)",
                             [(f"s{i}",) for i in range(30)])
            conn.commit()

    def command(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "dbvora.archive_cli", *args],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=40,
            stdin=subprocess.DEVNULL, check=False,
        )

    def prepare_archive(self):
        flags = ("--synthetic-only", "--accept-plaintext")
        snap = self.command("snapshot", "--source", str(self.source),
                            "--output-dir", str(self.root / "snapshot"), *flags)
        self.assertEqual(snap.returncode, 0, snap.stderr)
        snapshot = self.root / "snapshot" / json.loads(snap.stdout)["result"]["snapshot_path"]
        packed = self.command("archive", "--snapshot", str(snapshot),
                               "--output-dir", str(self.root / "archive"),
                               "--codec", "zip", *flags)
        self.assertEqual(packed.returncode, 0, packed.stderr)
        return self.root / "archive" / json.loads(packed.stdout)["result"]["archive_path"]

    def strict(self):
        return self.command("audit", "--output-dir", str(self.root / "archive"),
                            "--require-all-verified")

    def test_empty_catalog_rejected(self):
        p = self.strict()
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stderr)["error"]["code"], "AUDIT_VERIFICATION_FAILED")
        self.assertNotIn(str(self.root), p.stderr)

    def test_unrecorded_artifact_rejected_while_legacy_audit_retained(self):
        self.prepare_archive()
        p = self.strict()
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stderr)["error"]["code"], "AUDIT_VERIFICATION_FAILED")
        legacy = self.command("audit", "--output-dir", str(self.root / "archive"))
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        self.assertEqual(json.loads(legacy.stdout)["result"]["records"][0]["receipt_error_code"],
                         "MISSING_RECEIPT")

    def test_orphan_receipt_rejected_but_unrelated_file_ignored(self):
        artifact = self.prepare_archive()
        signed = self.command("receipt", "--artifact", str(artifact),
                              "--accept-unsigned", "--synthetic-only")
        self.assertEqual(signed.returncode, 0, signed.stderr)
        output = self.root / "archive"
        (output / "my-unrelated-note.txt").write_text("not a DBVORA receipt")
        self.assertEqual(self.strict().returncode, 0)
        orphan = output / ("dbvora-receipt-" + "e" * 32 + ".json")
        orphan.write_text("unpaired synthetic receipt")
        rejected = self.strict()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(json.loads(rejected.stderr)["error"]["code"],
                         "AUDIT_VERIFICATION_FAILED")
        self.assertNotIn(str(self.root), rejected.stderr)
        legacy = self.command("audit", "--output-dir", str(output))
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        self.assertEqual(json.loads(legacy.stdout)["result"]["records"][0]["status"],
                         "RECORDED_AND_CONTENT_VERIFIED_UNSIGNED")

    def test_verified_receipt_passes_then_artifact_tamper_fails(self):
        artifact = self.prepare_archive()
        receipt = self.command("receipt", "--artifact", str(artifact),
                               "--accept-unsigned", "--synthetic-only")
        self.assertEqual(receipt.returncode, 0, receipt.stderr)
        passed = self.strict()
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertEqual(json.loads(passed.stdout)["result"]["records"][0]["status"],
                         "RECORDED_AND_CONTENT_VERIFIED_UNSIGNED")
        with artifact.open("ab") as handle:
            handle.write(b"synthetic-receipt-mismatch")
        rejected = self.strict()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(json.loads(rejected.stderr)["error"]["code"],
                         "AUDIT_VERIFICATION_FAILED")
        self.assertNotIn(str(self.root), rejected.stderr)
        legacy = self.command("audit", "--output-dir", str(self.root / "archive"))
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        self.assertEqual(json.loads(legacy.stdout)["result"]["records"][0]["receipt_error_code"],
                         "ARTIFACT_MISMATCH")


if __name__ == "__main__":
    unittest.main()
