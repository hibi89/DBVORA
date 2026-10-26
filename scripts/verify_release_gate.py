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

EXPECTED_PYTHON_TESTS = 141
EXPECTED_GATE_CHECKS = 7
TEST_COUNT = re.compile(r"Ran\s+(\d+)\s+tests?\s+in\s+", re.IGNORECASE)
ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "pyproject.toml", "dbvora/archive_cli.py", "dbvora/archive/safe_zip.py",
    "dbvora/archive/receipts.py", "tests/test_archive_cli.py",
    "scripts/synthetic_cli_gate.py", "tests/test_ui_dom.cjs",
    "tests/test_verify_release_gate.py",
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
                           "discover", "-s", "tests", "-q"], timeout=240)
    count_match = TEST_COUNT.search(out + "\n" + err)
    count = int(count_match.group(1)) if count_match else 0
    unit_pass = code == 0 and count >= EXPECTED_PYTHON_TESTS
    report["steps"].append({"step": "python_unittest", "status": "PASS" if unit_pass else "FAIL",
                            "discovered_tests": count, "minimum_required": EXPECTED_PYTHON_TESTS})

    code, out, _ = _run([sys.executable, "-m", "scripts.synthetic_cli_gate"], timeout=240)
    try:
        gate = json.loads(out)
    except (ValueError, TypeError):
        gate = {}
    checks = gate.get("check_count", 0)
    zstd_status = gate.get("optional_zstd", "missing")
    available = shutil.which("zstd") is not None
    gate_pass = (code == 0 and gate.get("status") == "PASS_SYNTHETIC_ONLY"
                 and type(checks) is int and checks >= EXPECTED_GATE_CHECKS
                 and gate.get("ready_for_customer_data") is False
                 and (zstd_status == "passed" if available else zstd_status == "skipped_no_local_codec"))
    report["steps"].append({"step": "real_cli_roundtrip", "status": "PASS" if gate_pass else "FAIL",
                            "checks": checks if type(checks) is int else 0,
                            "zstd": zstd_status if zstd_status in ("passed", "skipped_no_local_codec") else "failed"})

    code, _, _ = _run([sys.executable, "-m", "compileall", "-q", "dbvora", "tests", "scripts"])
    report["steps"].append({"step": "compileall", "status": "PASS" if code == 0 else "FAIL"})

    if shutil.which("node"):
        code, _, _ = _run(["node", "--test", "tests/test_ui_dom.cjs"])
        node_pass = code == 0
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
