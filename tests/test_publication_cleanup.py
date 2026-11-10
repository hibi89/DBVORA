"""Standalone P0-08 generated-file cleanup safety tests."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from dbvora.publication_cleanup import remove_new_report

NAME = "dbvora-workspace-" + "a" * 32 + ".html"


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.target = self.directory / NAME

    def write_created(self):
        with self.target.open("xb") as output:
            output.write(b"created")
            return os.fstat(output.fileno())

    def test_removes_exact_generated_inode(self):
        original = self.write_created()
        self.assertTrue(remove_new_report(self.directory, NAME, original))
        self.assertFalse(self.target.exists())

    def test_replaced_file_preserved(self):
        original = self.write_created()
        different = self.directory / "replacement"
        different.write_bytes(b"customer")
        os.replace(different, self.target)
        self.assertFalse(remove_new_report(self.directory, NAME, original))
        self.assertEqual(self.target.read_bytes(), b"customer")

    def test_symlink_replacement_preserved(self):
        original = self.write_created()
        source = self.directory / "target"
        source.write_bytes(b"user owned")
        self.target.unlink()
        try:
            self.target.symlink_to(source)
        except OSError:
            self.skipTest("symlink creation unavailable")
        self.assertFalse(remove_new_report(self.directory, NAME, original))
        self.assertEqual(source.read_bytes(), b"user owned")
        self.assertTrue(self.target.is_symlink())

    def test_invalid_target_name_rejected(self):
        original = self.write_created()
        for bad in ["../" + NAME, "/tmp/" + NAME, "other.html", NAME.upper(), ""]:
            self.assertFalse(remove_new_report(self.directory, bad, original))
        self.assertEqual(self.target.read_bytes(), b"created")

    def test_missing_and_unverified_inode_preserved(self):
        original = self.write_created()
        self.assertFalse(remove_new_report(self.directory, NAME, None))
        self.target.unlink()
        self.assertFalse(remove_new_report(self.directory, NAME, original))


class ObservationCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.name = "dbvora-observation-" + "b" * 32 + ".json"
        self.target = self.directory / self.name

    def test_partial_observation_cleanup(self):
        from dbvora.publication_cleanup import remove_new_observation
        with self.target.open("xb") as out:
            out.write(b"partial")
            identity = os.fstat(out.fileno())
        self.assertTrue(remove_new_observation(self.directory, self.name, identity))
        self.assertFalse(self.target.exists())

    def test_replaced_observation_preserved(self):
        from dbvora.publication_cleanup import remove_new_observation
        with self.target.open("xb") as out:
            out.write(b"partial")
            identity = os.fstat(out.fileno())
        other = self.directory / "other"
        other.write_bytes(b"existing")
        os.replace(other, self.target)
        self.assertFalse(remove_new_observation(self.directory, self.name, identity))
        self.assertEqual(self.target.read_bytes(), b"existing")


if __name__ == "__main__":
    unittest.main()
