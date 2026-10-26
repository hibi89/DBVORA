"""Run DBVORA's offline synthetic acceptance checks without network or customers.

Must run from a complete repository checkout; fails closed when files, tools,
or expected test coverage are absent. JSON output contains no captured source paths.
"""

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

EXPECTED_PYTHON_TESTS = 194
EXPECTED_GATE_CHECKS = 7
TEST_COUNT = re.compile(r"Ran\s+(\d+)\s+tests?\s+in\s+", re.IGNORECASE)
SKIPPED_COUNT = re.compile(r"OK\s*\(skipped=(\d+)\)", re.IGNORECASE)
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
    "tests/test_verify_release_gate.py", "tests/test_synthetic_cli_gate.py",
    "tests/test_windows_ntfs_gate.py", "scripts/windows_ntfs_gate.py",
)


def _run(command, timeout=180):
    try:
        child = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                               timeout=timeout, check=False, stdin=subprocess.DEVNULL)
        return child.returncode, child.stdout, child.stderr
    except (OSError, subprocess.TimeoutExpired):
        return -1, "", ""


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
    skipped_match = SKIPPED_COUNT.search(out + "\n" + err)
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
                            "skip_identity_verified": skip_identity_ok})

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
                            "zstd": zstd_status if zstd_status in ("passed", "skipped_no_local_codec") else "failed"})

    code, _, _ = _run([sys.executable, "-m", "compileall", "-q", "dbvora", "tests", "scripts"])
    report["steps"].append({"step": "compileall", "status": "PASS" if code == 0 else "FAIL"})

    if shutil.which("node"):
        code, node_out, node_err = _run(["node", "--test", "tests/test_ui_dom.cjs"])
        tap = node_out + "\n" + node_err
        tests = NODE_TEST_COUNT.search(tap)
        passed = NODE_PASS_COUNT.search(tap)
        failed = NODE_FAIL_COUNT.search(tap)
        node_pass = (code == 0 and tests is not None and passed is not None and failed is not None
                     and int(tests.group(1)) == 1 and int(passed.group(1)) == 1
                     and int(failed.group(1)) == 0)
    else:
        node_pass = False
    report["steps"].append({"step": "node_dom", "status": "PASS" if node_pass else "FAIL"})

    code, out, _ = _run([sys.executable, "-m", "scripts.preflight_archiving"])
    try:
        preflight = json.loads(out)
    except (ValueError, TypeError):
        preflight = {}
    preflight_pass = (code == 0 and preflight.get("archive_publish_test") == "passed_on_temporary_filesystem"
                      and preflight.get("ready_for_customer_data") is False)
    report["steps"].append({"step": "filesystem_preflight", "status": "PASS" if preflight_pass else "FAIL"})
    if all(step["status"] == "PASS" for step in report["steps"]):
        report["status"] = "PASS_SYNTHETIC_ENVIRONMENT_ONLY"
    return report


def main():
    report = verify()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS_SYNTHETIC_ENVIRONMENT_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
