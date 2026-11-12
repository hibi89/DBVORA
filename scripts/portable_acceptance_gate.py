"""Offline developer ZIP build/extract/verify gate; no customer paths or network.

Full original source checkout required. No signing or Windows durability claim.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from scripts import build_portable

ROOT = Path(__file__).resolve().parents[1]


def _child(args: list[str], cwd: Path, timeout: int = 60) -> tuple[int, dict]:
    env = {**os.environ, "PYTHONPATH": "", "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        p = subprocess.run(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=timeout, check=False)
        report = json.loads(p.stdout.decode("utf-8"))
        if type(report) is not dict:
            return -1, {}
        return p.returncode, report
    except (OSError, subprocess.TimeoutExpired, UnicodeError, ValueError):
        return -1, {}


def verify() -> dict:
    """Build from authenticated local checkout, then validate a fresh extraction."""
    result = {"status": "FAIL_CLOSED", "contract": "dbvora.portable-gate.v1",
              "ready_for_customer_data": False, "signed": False,
              "windows_ntfs_verified": False, "checks": 0}
    try:
        with tempfile.TemporaryDirectory(prefix="dbvora-portable-gate-") as scratch:
            root = Path(scratch)
            out = root / "archive"
            dest = root / "extracted"
            out.mkdir()
            dest.mkdir()
            zip_path = build_portable.build(out)
            package_check = build_portable.verify_zip(zip_path)
            if (package_check.get("status") != "PASS_UNSIGNED_SOURCE_INTEGRITY_ONLY"
                    or package_check.get("signed") is not False
                    or package_check.get("ready_for_customer_data") is not False):
                raise ValueError("ZIP_VERIFICATION_FAILED")
            result["checks"] += 1
            result["zip_sha256"] = hashlib.sha256(zip_path.read_bytes()).hexdigest()
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Only extract source bytes after the builder's member and digest checks.
                zf.extractall(dest)
            audit = ROOT / "scripts" / "verify_trusted_extraction.py"
            if not audit.is_file():
                raise ValueError("TRUSTED_AUDITOR_MISSING")
            command = [sys.executable, "-I", "-S", "-B", str(audit),
                       "--extracted", str(dest)]
            rc, report = _child(command, ROOT)
            if (rc != 0 or report.get("status") != "PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY"
                    or report.get("publisher_authenticity_verified") is not False
                    or report.get("customer_ready") is not False):
                raise ValueError("EXTRACTED_AUDIT_FAILED")
            result["checks"] += 1
            # This executes only the newly built synthetic developer preview,
            # never customer data or an externally sourced archive.
            rc, report = _child([sys.executable, "-S", "-B", "-m",
                                 "dbvora.archive.review_selftest"], dest, timeout=90)
            if (rc != 0 or report.get("status") != "PASS_SYNTHETIC_PREVIEW_ONLY"
                    or report.get("zip") != "passed"
                    or report.get("zstd") not in ("passed", "skipped_no_local_codec")
                    or report.get("customer_ready") is not False
                    or report.get("windows_ntfs_durability_verified") is not False):
                raise ValueError("SYNTHETIC_PREVIEW_FAILED")
            result["checks"] += 1
            source = dest / "dbvora" / "archive" / "request_service.py"
            if not source.is_file():
                raise ValueError("REQUIRED_SOURCE_MISSING")
            with source.open("ab") as handle:
                handle.write(b"\n# INERT-SYNTHETIC-TAMPER\n")
            rc, report = _child(command, ROOT)
            if (rc == 0 or report.get("status") != "FAIL_CLOSED"
                    or report.get("error_code") != "PACKAGE_DIGEST_MISMATCH"):
                raise ValueError("TAMPER_REJECTION_FAILED")
            result["checks"] += 1
            result["status"] = "PASS_SYNTHETIC_PORTABLE_ONLY"
    except Exception as error:
        allowed = {"ZIP_VERIFICATION_FAILED", "TRUSTED_AUDITOR_MISSING",
                   "EXTRACTED_AUDIT_FAILED", "SYNTHETIC_PREVIEW_FAILED",
                   "REQUIRED_SOURCE_MISSING", "TAMPER_REJECTION_FAILED"}
        code = str(error)
        result["error_code"] = code if code in allowed else "PORTABLE_GATE_FAILED"
    return result


def main() -> int:
    result = verify()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS_SYNTHETIC_PORTABLE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
