"""Fail-closed Windows 3.11 / NTFS *synthetic-only* validation entrypoint.

Run on an authorized Windows development PC from a private checkout:
    py -3.11 -B -m scripts.windows_ntfs_gate

Never touches or asks for a customer's DB path. Reports no full path, raw
exception, secret or customer record. An unsupported durability operation is
BLOCKED; never infer safety from a successful POSIX run or a file's presence.
"""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import platform
import sys
import tempfile

_REQUIRED_STEPS = (
    "checkout", "python_unittest", "real_cli_roundtrip",
    "compileall", "node_dom", "filesystem_preflight",
)


def _temp_volume_filesystem() -> str:
    """Query the *operating system temporary drive*, not any customer path."""
    if os.name != "nt":
        return "NOT_WINDOWS"
    try:
        drive = Path(tempfile.gettempdir()).anchor
        if not drive:
            return "UNAVAILABLE"
        fs_name = ctypes.create_unicode_buffer(40)
        get_volume = ctypes.WinDLL("kernel32", use_last_error=True).GetVolumeInformationW
        get_volume.argtypes = [
            wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD,
        ]
        get_volume.restype = wintypes.BOOL
        ok = get_volume(drive, None, 0, None, None, None, fs_name, len(fs_name))
        return fs_name.value.upper() if ok else "UNAVAILABLE"
    except (OSError, ValueError, AttributeError, TypeError):
        return "UNAVAILABLE"


def _step(name: str, ok: bool) -> dict:
    return {"step": name, "status": "PASS" if ok else "FAIL"}


def verify_windows_ntfs(*, platform_name=None, python_version=None, filesystem=None,
                        preflight_fn=None, release_fn=None) -> dict:
    """No file activity until Windows + Python 3.11 + temp-volume NTFS validate.

    Injected callables are exclusively for platform-independent unit tests.
    """
    report = {
        "contract": "dbvora.windows-ntfs-synthetic-gate.v1",
        "ready_for_customer_data": False,
        "scope": "OS_TEMP_SYNTHETIC_ONLY",
        "windows_host_verified": False,
        "hardware_power_loss_verified": False,
        "status": "BLOCKED_UNVERIFIED",
        "steps": [],
    }
    current_platform = platform_name if platform_name is not None else platform.system()
    win = current_platform == "Windows" and (platform_name is not None or os.name == "nt")
    report["steps"].append(_step("windows_platform", win))
    if not win:
        report["reason"] = "WINDOWS_HOST_REQUIRED"
        return report

    version = python_version if python_version is not None else sys.version_info[:2]
    valid_python = tuple(version) == (3, 11)
    report["steps"].append(_step("python_3_11", valid_python))
    if not valid_python:
        report["reason"] = "PYTHON_3_11_REQUIRED"
        return report

    fs = filesystem if filesystem is not None else _temp_volume_filesystem()
    fs_ok = fs == "NTFS"
    report["steps"].append(_step("os_temp_ntfs", fs_ok))
    if not fs_ok:
        report["reason"] = "NTFS_TEMP_VOLUME_REQUIRED"
        return report

    if preflight_fn is None:
        from scripts.preflight_archiving import probe
        preflight_fn = probe
    try:
        preflight = preflight_fn()
    except Exception:
        preflight = {}
    publish_ok = (type(preflight) is dict
                  and preflight.get("archive_publish_test") == "passed_on_temporary_filesystem"
                  and preflight.get("ready_for_customer_data") is False
                  and preflight.get("writes_outside_os_temporary_folder") is False)
    report["steps"].append(_step("temporary_durable_publish", publish_ok))
    if not publish_ok:
        report["reason"] = "DURABILITY_NOT_PROVEN_FAIL_CLOSED"
        return report

    if release_fn is None:
        from scripts.verify_release_gate import verify
        release_fn = verify
    try:
        release = release_fn()
    except Exception:
        release = {}
    all_gate_steps = (type(release) is dict and type(release.get("steps")) is list
                      and len(release["steps"]) == len(_REQUIRED_STEPS)
                      and [s.get("step") for s in release["steps"] if type(s) is dict]
                      == list(_REQUIRED_STEPS)
                      and all(s.get("status") == "PASS" for s in release["steps"]))
    release_ok = (type(release) is dict
                  and release.get("status") == "PASS_SYNTHETIC_ENVIRONMENT_ONLY"
                  and release.get("ready_for_customer_data") is False
                  and all_gate_steps)
    report["steps"].append(_step("complete_synthetic_release_gate", release_ok))
    if not release_ok:
        report["reason"] = "REGRESSION_OR_SYNTHETIC_GATE_FAILED"
        return report

    report["status"] = "PASS_WINDOWS_NTFS_SYNTHETIC_ONLY"
    report["windows_host_verified"] = True
    return report


def main() -> int:
    result = verify_windows_ntfs()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS_WINDOWS_NTFS_SYNTHETIC_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
