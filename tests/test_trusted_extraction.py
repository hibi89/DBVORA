"""Synthetic tests for the separately trusted, non-importing ZIP auditor."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dbvora.archive.portable_verify import _REQUIRED
from scripts import verify_trusted_extraction as audited

TRUSTED_ROOT = Path(__file__).resolve().parents[1]
TRUSTED_SCRIPT = TRUSTED_ROOT / "scripts" / "verify_trusted_extraction.py"


class TrustedExtractedTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dbvora-trusted-audit-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root / "extracted"
        self.package.mkdir()
        self.manifest = {}
        for name in _REQUIRED:
            path = self.package / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = b"# inert synthetic source only\\n"
            path.write_bytes(data)
            self.manifest[name] = {
                "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)
            }
        self.write_manifest()

    def write_manifest(self):
        (self.package / "MANIFEST.sha256.json").write_text(
            json.dumps({"format": "dbvora-portable-dev-v1",
                        "unsigned": True, "files": self.manifest}), encoding="utf-8"
        )

    def invoke(self, *, destination=None, env=None):
        return subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(TRUSTED_SCRIPT),
             "--extracted", str(destination or self.package)],
            cwd=self.root, env=env or os.environ.copy(), capture_output=True,
            text=True, timeout=15, check=False,
        )

    def test_checked_package_passes_without_publisher_claim(self):
        completed = self.invoke()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY")
        self.assertFalse(report["publisher_authenticity_verified"])
        self.assertFalse(report["customer_ready"])

    def test_mutated_file_fail_closed_and_no_path_output(self):
        path = self.package / "dbvora/archive/request_service.py"
        path.write_bytes(b"mutated")
        completed = self.invoke()
        self.assertNotEqual(completed.returncode, 0)
        report = json.loads(completed.stdout)
        self.assertEqual(report["error_code"], "PACKAGE_DIGEST_MISMATCH")
        self.assertNotIn(str(self.root), completed.stdout)

    def test_matching_source_cache_is_rejected_without_importing_it(self):
        cache = self.package / "dbvora/archive/__pycache__"
        cache.mkdir()
        (cache / "portable_verify.cpython-313.pyc").write_bytes(b"INERT")
        completed = self.invoke()
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(json.loads(completed.stdout)["error_code"], "PACKAGE_BYTECODE_PRESENT")

    def test_untrusted_pythonpath_cannot_redirect_auditor(self):
        fake = self.root / "fake" / "dbvora" / "archive"
        fake.mkdir(parents=True)
        (fake / "portable_verify.py").write_text("raise RuntimeError('untrusted loaded')")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.root / "fake")
        completed = self.invoke(env=env)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("untrusted loaded", completed.stdout + completed.stderr)

    def test_refuses_same_checkout_as_trusted_source(self):
        with self.assertRaisesRegex(ValueError, "SEPARATE_TRUSTED_CHECKOUT_REQUIRED"):
            audited.check(TRUSTED_ROOT, trusted_root=TRUSTED_ROOT)

    def test_rejects_missing_or_relative_extraction(self):
        with self.assertRaisesRegex(ValueError, "ABSOLUTE_PACKAGE_PATH_REQUIRED"):
            audited.check(Path("relative"), trusted_root=TRUSTED_ROOT)
        with self.assertRaisesRegex(ValueError, "PACKAGE_UNAVAILABLE"):
            audited.check(self.root / "missing", trusted_root=TRUSTED_ROOT)

    def test_never_creates_or_modifies_source(self):
        path = self.package / "dbvora/archive/request_service.py"
        before = path.read_bytes()
        self.assertEqual(audited.check(self.package)["status"],
                         "PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY")
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
