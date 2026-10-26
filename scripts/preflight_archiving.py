"""Opt-in, synthetic-only archive filesystem preflight; no customer DB access.

Use: python -m scripts.preflight_archiving
Tests only a fresh TemporaryDirectory on current OS, never the source DB.
"""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

from dbvora.archive.safe_zip import ArchiveError, _publish_new


def probe() -> dict:
    report = {
        "contract_version": "p1-c3.preflight.v1",
        "platform": sys.platform,
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "sqlite_version": sqlite3.sqlite_version,
        "zstd_cli_available": shutil.which("zstd") is not None,
        "zstd_cli_is_bundled": False,
        "python_zstandard_wheel_tested": False,
        "writes_outside_os_temporary_folder": False,
        "windows_package_verified": False,
        "archive_publish_test": "not_run",
        "ready_for_customer_data": False,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="dbvora-preflight-") as scratch:
            folder = Path(scratch)
            staged = folder / "sample.part"
            staged.write_bytes(b"synthetic-data-only")
            try:
                result = _publish_new(staged, folder, ".test")
                if result.read_bytes() != b"synthetic-data-only":
                    raise RuntimeError("synthetic file changed")
                report["archive_publish_test"] = "passed_on_temporary_filesystem"
            except (ArchiveError, OSError, RuntimeError) as exc:
                report["archive_publish_test"] = "unsupported_or_failed"
                report["failure_code"] = exc.code if isinstance(exc, ArchiveError) else "FILESYSTEM_CHECK_FAILED"
    except OSError:
        report["archive_publish_test"] = "temporary_folder_unavailable"
    return report


def main():
    print(json.dumps(probe(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
