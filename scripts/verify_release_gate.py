"""Run DBVORA's offline synthetic acceptance checks without network or customers.

Must run from a complete repository checkout; fails closed when files, tools,
or expected test coverage are absent. JSON output contains no captured source paths.
"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

EXPECTED_PYTHON_TESTS = 304
EXPECTED_GATE_CHECKS = 7
TEST_COUNT = re.compile(r"Ran\s+(\d+)\s+tests?\s+in\s+", re.IGNORECASE)
SKIPPED_COUNT = re.compile(r"\bskipped=(\d+)\b", re.IGNORECASE)
FAILED_TEST = re.compile(r"(?m)^(?:FAIL|ERROR): (test_[A-Za-z0-9_]+) \(([A-Za-z0-9_.]+)\)")
SKIPPED_TEST = re.compile(r"(?m)^(test_[A-Za-z0-9_]+) \(([A-Za-z0-9_.]+)\) \.\.\. skipped ")
SAFE_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
# Verbose unittest output identifies the one permitted optional ZSTD skip.
OPTIONAL_ZSTD_TEST = "test_zstd_roundtrip_when_optional_codec_exists"
OPTIONAL_ZSTD_SKIP_REASON = "optional external zstd executable unavailable"

NODE_TEST_COUNT = re.compile(r"(?m)^#\s+tests\s+(\d+)\s*$")
NODE_PASS_COUNT = re.compile(r"(?m)^#\s+pass\s+(\d+)\s*$")
NODE_FAIL_COUNT = re.compile(r"(?m)^#\s+fail\s+(\d+)\s*$")
ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "pyproject.toml", "dbvora/archive_cli.py", "dbvora/archive/safe_zip.py",
    "dbvora/archive/receipts.py", "tests/test_archive_cli.py",
    "scripts/synthetic_cli_gate.py", "tests/test_ui_dom.cjs",
    "scripts/build_portable.py", "tests/test_portable_build.py",
    "dbvora/export_html.py", "tests/test_export_html.py",
    "dbvora/offline_selftest.py", "tests/test_offline_selftest.py",
    "tests/test_verify_release_gate.py", "tests/test_synthetic_cli_gate.py",
    "tests/test_audit_strict.py",
    "tests/test_windows_ntfs_gate.py", "scripts/windows_ntfs_gate.py",
    "dbvora/archive/windows_ntfs_publish.py",
    "scripts/windows_ntfs_publish_probe.py", "tests/test_windows_ntfs_publish.py",
    "scripts/windows_ntfs_archive_shadow.py", "tests/test_windows_ntfs_archive_shadow.py",
    "dbvora/demo_preview.py", "tests/test_demo_preview.py",
    "dbvora/workspace.py", "tests/test_workspace_registry.py",
    "dbvora/workspace_html.py", "dbvora/workspace_links.py", "tests/test_workspace_links.py", "tests/test_workspace.py",
    "dbvora/storage_metrics.py", "dbvora/workspace_observations.py", "tests/test_workspace_storage.py",
)


def _run(command, timeout=180):
    """Decode child output as strict UTF-8 on every OS; malformed output fails closed."""
    try:
        # Node emits UTF-8 TAP, even when Windows Python's default is CP949.
        # Read bytes first so a subprocess reader thread cannot silently fail.
        child = subprocess.run(command, cwd=ROOT, capture_output=True,
                               timeout=timeout, check=False, stdin=subprocess.DEVNULL,
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        stdout, stderr = child.stdout, child.stderr
        if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
            return -1, "", ""
        return child.returncode, stdout.decode("utf-8"), stderr.decode("utf-8")
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return -1, "", ""


def _safe_code(value, fallback="NOT_REPORTED"):
    """Emit only fixed-format error identifiers, never source paths or traceback."""
    return value if isinstance(value, str) and SAFE_CODE.fullmatch(value) else fallback


def _failing_test_ids(unittest_output):
    """Extract bounded Python test identifiers, never exception bodies."""
    return sorted({module if module.endswith("." + method) else f"{module}.{method}"
                   for method, module in FAILED_TEST.findall(unittest_output)})[:20]


def _skipped_test_ids(unittest_output):
    """Only report bounded test identities, never filesystem paths or reasons."""
    return sorted({module if module.endswith("." + method) else f"{module}.{method}"
                   for method, module in SKIPPED_TEST.findall(unittest_output)})[:20]


def verify():
    report = {"contract": "dbvora.offline-release-gate.v1", "mode": "synthetic_only",
              "ready_for_customer_data": False, "status": "FAIL_CLOSED", "steps": []}
    missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
    if missing:
        report["steps"].append({"step": "checkout", "status": "FAIL", "error": "INCOMPLETE_SOURCE_CHECKOUT",
                                "missing_count": len(missing)})
        return report
    report["steps"].append({"step": "checkout", "status": "PASS"})

    code, out, err = _run([sys.executable, "-W", "error::ResourceWarning", "-m", "unittest",
                           "discover", "-s", "tests", "-v"], timeout=240)
    count_match = TEST_COUNT.search(out + "\n" + err)
    count = int(count_match.group(1)) if count_match else 0
    combined_tests = out + "\n" + err
    skipped_match = SKIPPED_COUNT.search(combined_tests)
    skipped = int(skipped_match.group(1)) if skipped_match else 0
    zstd_available = shutil.which("zstd") is not None
    allowed_skips = 0 if zstd_available else 1
    skip_lines = [line for line in err.splitlines() if " ... skipped " in line]
    # Never allow an unrelated test to be skipped under the optional ZSTD exception.
    expected_optional_skip = (
        len(skip_lines) == 1
        and skip_lines[0].startswith(OPTIONAL_ZSTD_TEST + " (")
        and OPTIONAL_ZSTD_SKIP_REASON in skip_lines[0]
    )
    skip_identity_ok = (
        skipped == 0 and not skip_lines
        or not zstd_available and skipped == 1 and expected_optional_skip
    )
    unit_pass = (code == 0 and count >= EXPECTED_PYTHON_TESTS
                 and skipped <= allowed_skips and skip_identity_ok)
    report["steps"].append({"step": "python_unittest", "status": "PASS" if unit_pass else "FAIL",
                            "discovered_tests": count, "minimum_required": EXPECTED_PYTHON_TESTS,
                            "skipped_tests": skipped, "maximum_allowed_skips": allowed_skips,
                            "skip_identity_verified": skip_identity_ok,
                            "exit_code": code if type(code) is int else -1,
                            "failed_test_ids": _failing_test_ids(combined_tests),
                            "skipped_test_ids": _skipped_test_ids(combined_tests)})

    code, out, _ = _run([sys.executable, "-m", "scripts.synthetic_cli_gate"], timeout=240)
    try:
        gate = json.loads(out)
    except (ValueError, TypeError):
        gate = {}
    checks = gate.get("check_count", 0)
    zstd_status = gate.get("optional_zstd", "missing")
    gate_pass = (code == 0 and gate.get("status") == "PASS_SYNTHETIC_ONLY"
                 and type(checks) is int and checks >= EXPECTED_GATE_CHECKS
                 and gate.get("ready_for_customer_data") is False
                 and (zstd_status == "passed" if zstd_available else zstd_status == "skipped_no_local_codec"))
    report["steps"].append({"step": "real_cli_roundtrip", "status": "PASS" if gate_pass else "FAIL",
                            "checks": checks if type(checks) is int else 0,
                            "zstd": zstd_status if zstd_status in ("passed", "skipped_no_local_codec") else "failed",
                            "exit_code": code if type(code) is int else -1,
                            "error_code": _safe_code(gate.get("error_code")) if not gate_pass else None})

    code, _, _ = _run([sys.executable, "-m", "compileall", "-q", "dbvora", "tests", "scripts"])
    report["steps"].append({"step": "compileall", "status": "PASS" if code == 0 else "FAIL"})

    if shutil.which("node"):
        code, node_out, node_err = _run(["node", "--test-reporter=tap", "--test", "tests/test_ui_dom.cjs"])
        tap = node_out + "\n" + node_err
        tests = NODE_TEST_COUNT.search(tap)
        passed = NODE_PASS_COUNT.search(tap)
        failed = NODE_FAIL_COUNT.search(tap)
        node_pass = (code == 0 and tests is not None and passed is not None and failed is not None
                     and int(tests.group(1)) == 1 and int(passed.group(1)) == 1
                     and int(failed.group(1)) == 0)
    else:
        code, tests, passed, failed = -1, None, None, None
        node_pass = False
    node_counts = {
        "tests": int(tests.group(1)) if tests else None,
        "passed": int(passed.group(1)) if passed else None,
        "failed": int(failed.group(1)) if failed else None,
    }
    node_issue = ("NONE" if node_pass else
                  "NODE_NOT_INSTALLED" if code == -1 and not shutil.which("node") else
                  "SUBPROCESS_OR_UTF8_ERROR" if code == -1 else
                  "TAP_SUMMARY_MISSING" if any(x is None for x in node_counts.values()) else
                  "NODE_TEST_FAILED")
    report["steps"].append({"step": "node_dom", "status": "PASS" if node_pass else "FAIL",
                            "exit_code": code, "tap": node_counts, "error_code": node_issue})

    code, out, _ = _run([sys.executable, "-m", "scripts.preflight_archiving"])
    try:
        preflight = json.loads(out)
    except (ValueError, TypeError):
        preflight = {}
    preflight_pass = (code == 0 and preflight.get("archive_publish_test") == "passed_on_temporary_filesystem"
                      and preflight.get("ready_for_customer_data") is False)
    report["steps"].append({"step": "filesystem_preflight", "status": "PASS" if preflight_pass else "FAIL",
                            "exit_code": code if type(code) is int else -1,
                            "publish_test": (preflight.get("archive_publish_test")
                                if preflight.get("archive_publish_test") in
                                ("passed_on_temporary_filesystem", "unsupported_or_failed",
                                 "temporary_folder_unavailable", "not_run") else "NOT_REPORTED"),
                            "error_code": _safe_code(preflight.get("failure_code"))
                            if not preflight_pass else None})
    if all(step["status"] == "PASS" for step in report["steps"]):
        report["status"] = "PASS_SYNTHETIC_ENVIRONMENT_ONLY"
    return report


def main():
    report = verify()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS_SYNTHETIC_ENVIRONMENT_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
