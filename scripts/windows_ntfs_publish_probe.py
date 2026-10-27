"""Opt-in independent NTFS publication experiment using ONLY OS-temp bytes.

python -m scripts.windows_ntfs_publish_probe --synthetic-only
Does not read DB files, or change DBVORA's production archive backend.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path
import sys
import tempfile
import uuid

from dbvora.archive.windows_ntfs_publish import (
    WinPublishError, _commit_synthetic_staged, _windows_temp_filesystem,
)


def run_probe(*, platform_name=None, python_version=None, filesystem=None, move=None) -> dict:
    """Optional injection simulates behavior in unit tests, never certifies Windows."""
    host = platform.system() if platform_name is None else platform_name
    version = tuple(sys.version_info[:2]) if python_version is None else tuple(python_version)
    volume = _windows_temp_filesystem() if filesystem is None else filesystem
    actual_native = os.name == "nt" and platform_name is None and python_version is None and filesystem is None and move is None
    report = {"contract": "dbvora.ntfs-create-only-probe.v1", "scope": "OS_TEMP_SYNTHETIC_ONLY",
              "ready_for_customer_data": False, "power_loss_durable_verified": False,
              "directory_metadata_durable_verified": False, "native_windows_tested": False,
              "status": "BLOCKED_UNVERIFIED", "steps": []}
    for name, success in (("windows", host == "Windows"),
                          ("python_3_11", version == (3, 11)),
                          ("temp_ntfs", volume == "NTFS")):
        report["steps"].append({"step": name, "status": "PASS" if success else "FAIL"})
        if not success:
            report["reason"] = {"windows":"WINDOWS_REQUIRED", "python_3_11":"PYTHON311_REQUIRED",
                                "temp_ntfs":"NTFS_TEMP_REQUIRED"}[name]
            return report
    try:
        with tempfile.TemporaryDirectory(prefix="dbvora-win32-synthetic-") as tmp:
            root = Path(tmp)
            def new_stage(content: bytes) -> Path:
                staged = root / (".dbvora-stage-" + uuid.uuid4().hex + ".part")
                with staged.open("xb") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                return staged
            target = root / ("dbvora-" + uuid.uuid4().hex + ".bin")
            source = new_stage((b"DBVORA-NATIVE-SYNTHETIC-" + bytes(range(256))) * 128)
            original = source.read_bytes()
            _commit_synthetic_staged(root, source, target, move=move)
            ok = target.read_bytes() == original and not source.exists()
            report["steps"].append({"step":"create_only_and_sha256", "status":"PASS" if ok else "FAIL"})
            if not ok:
                raise WinPublishError("BYTE_ROUNDTRIP_FAILED")
            collision_stage = new_stage(b"not-published")
            old_target = target.read_bytes()
            try:
                _commit_synthetic_staged(root, collision_stage, target, move=move)
                raise WinPublishError("OVERWRITE_GUARD_BROKEN")
            except WinPublishError as e:
                if str(e) != "DESTINATION_EXISTS":
                    raise
            ok = target.read_bytes() == old_target and collision_stage.read_bytes() == b"not-published"
            report["steps"].append({"step":"collision_preserves_both", "status":"PASS" if ok else "FAIL"})
            if not ok:
                raise WinPublishError("OVERWRITE_GUARD_BROKEN")
            failed_stage = new_stage(b"failed-move-preserves-stage")
            fails_target = root / ("dbvora-" + uuid.uuid4().hex + ".bin")
            def failure(_stage, _target):
                raise WinPublishError("INJECTED_FAILURE")
            try:
                _commit_synthetic_staged(root, failed_stage, fails_target, move=failure)
                raise WinPublishError("FAILURE_INJECTION_NOT_DETECTED")
            except WinPublishError as e:
                if str(e) != "INJECTED_FAILURE":
                    raise
            ok = failed_stage.read_bytes() == b"failed-move-preserves-stage" and not os.path.lexists(fails_target)
            report["steps"].append({"step":"failure_preserves_source", "status":"PASS" if ok else "FAIL"})
            if not ok:
                raise WinPublishError("FAILURE_CLEANUP_UNSAFE")
    except WinPublishError as e:
        report["reason"] = str(e)
        return report
    except OSError:
        report["reason"] = "FILESYSTEM_UNAVAILABLE"
        return report
    report["native_windows_tested"] = actual_native
    report["status"] = "PASS_WINDOWS_NTFS_SYNTHETIC_ONLY" if actual_native else "PASS_SIMULATED_ONLY"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Synthetic-only experimental NTFS create-only test")
    parser.add_argument("--synthetic-only", required=True, action="store_true")
    parser.parse_args(argv)
    report = run_probe()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS_WINDOWS_NTFS_SYNTHETIC_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
