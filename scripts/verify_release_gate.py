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

EXPECTED_PYTHON_TESTS = 668
EXPECTED_GATE_CHECKS = 9
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
    "scripts/mvp_offline_gate.py", "tests/test_mvp_offline_gate.py",
    "dbvora/safe_metadata_file.py", "tests/test_safe_metadata_file.py",
    "dbvora/publication_cleanup.py", "tests/test_publication_cleanup.py",
    "tests/test_workspace_publication.py",
    "dbvora/schema_review.py", "tests/test_schema_review.py",
    "tests/test_schema_review_ui.py",
    "dbvora/sqlite_identifiers.py", "tests/test_sqlite_identifiers.py",
    "tests/test_workspace_html_dom.cjs",
    "tests/test_schema_review_identifier_case.py",
    "dbvora/archive/request_ledger.py", "tests/test_request_ledger.py",
    "scripts/request_archive_gate.py", "tests/test_request_archive_gate.py",
    "dbvora/archive/request_service.py", "tests/test_request_service.py",
    "dbvora/connectors/postgres_reader.py", "tests/test_postgres_reader.py",
    "dbvora/multi_engine_report.py", "tests/test_multi_engine_report.py",
    "dbvora/archive/request_audit.py", "tests/test_request_audit.py",
    "dbvora/archive/review_html.py", "tests/test_review_html.py",
    "dbvora/archive/review_selftest.py", "tests/test_review_selftest.py",
    "dbvora/archive/portable_verify.py", "tests/test_portable_verify.py",
    "scripts/recovery_review_gate.py", "tests/test_recovery_review_gate.py",
    "dbvora/mixed_cli.py", "tests/test_mixed_cli.py",
    "scripts/verify_trusted_extraction.py", "tests/test_trusted_extraction.py",
    "scripts/portable_acceptance_gate.py", "tests/test_portable_acceptance_gate.py",
    "dbvora/connectors/postgres_statistics.py", "tests/test_postgres_statistics.py",
    "dbvora/optimization_review.py", "tests/test_optimization_review.py",
    "scripts/pg_synthetic_acceptance.py", "tests/test_pg_synthetic_acceptance.py",
    "tests/test_pg_html_script.py",
    "dbvora/archive/incremental_cas.py", "tests/test_incremental_cas.py",
    "dbvora/incremental_cli.py", "tests/test_incremental_cli.py",
    "dbvora/archive/compressed_cas.py", "tests/test_compressed_cas.py",
    "tests/test_compressed_cas_failures.py",
    "tests/test_cas_abrupt_process.py", "tests/test_weekly_synthetic.py",
    "dbvora/archive/daily_synthetic.py", "tests/test_daily_synthetic.py",
    "dbvora/process_resources.py", "tests/test_process_resources.py",
    "dbvora/archive/cas_audit.py", "tests/test_cas_audit.py",
    "scripts/incremental_cli_gate.py",
    "scripts/benchmark_synthetic_archives.py", "tests/test_benchmark_synthetic_archives.py",
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
    # On Windows, the POSIX 0600 permission check is inapplicable; allow only
    # that *named* skip with its exact reason. No other OS skip is accepted.
    windows_posix_skip = "test_created_report_is_mode_0600_on_posix"
    allowed_skips = (0 if zstd_available else 1) + (1 if os.name == "nt" else 0)
    skip_lines = [line for line in err.splitlines() if " ... skipped " in line]
    def expected_skip(line):
        return (
            (not zstd_available and line.startswith(OPTIONAL_ZSTD_TEST + " (")
             and OPTIONAL_ZSTD_SKIP_REASON in line)
            or (os.name == "nt" and line.startswith(windows_posix_skip + " (")
                and "posix permission only" in line)
        )
    skip_identity_ok = (skipped == len(skip_lines)
                        and skipped <= allowed_skips
                        and all(expected_skip(line) for line in skip_lines)
                        and len(set(line.split(" (", 1)[0] for line in skip_lines)) == len(skip_lines))
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

    # A separate, fresh synthetic ZIP request replay gate. This does not
    # certify Windows NTFS, crash-atomic publication, or customer readiness.
    code, out, _ = _run([sys.executable, "-m", "scripts.request_archive_gate"], timeout=240)
    try:
        request_gate = json.loads(out)
    except (ValueError, TypeError):
        request_gate = {}
    request_ok = (
        code == 0 and request_gate.get("status") == "PASS_SYNTHETIC_REQUEST_AND_ZIP_ONLY"
        and type(request_gate.get("checks")) is int and request_gate["checks"] >= 9
        and request_gate.get("archive_executed") is True
        and request_gate.get("replay_held") is True
        and request_gate.get("zip_restore_content_verified") is True
        and request_gate.get("ledger_artifact_state") == "RECORDED_UNVERIFIED"
        and request_gate.get("ready_for_customer_data") is False
        and request_gate.get("exactly_once_verified") is False
        and request_gate.get("windows_ntfs_verified") is False
    )
    report["steps"].append({"step": "synthetic_request_zip_replay",
                            "status": "PASS" if request_ok else "FAIL",
                            "checks": request_gate.get("checks", 0)
                                if type(request_gate.get("checks")) is int else 0,
                            "exit_code": code if type(code) is int else -1,
                            "error_code": "NONE" if request_ok else
                                _safe_code(request_gate.get("error_code"), "REQUEST_GATE_FAILED")})

    # Separate synthetic-only full engine snapshot -> archive -> independent
    # recovery catalog -> local static report -> replay and corruption HOLD.
    # Does not prove Windows durability, exactly-once, or customer readiness.
    code, out, _ = _run([sys.executable, "-m", "scripts.recovery_review_gate"], timeout=240)
    try:
        recovery = json.loads(out)
    except (ValueError, TypeError):
        recovery = {}
    recovery_checks = recovery.get("checks", 0)
    recovery_zstd = recovery.get("optional_zstd")
    recovery_ok = (
        code == 0 and recovery.get("status") == "PASS_SYNTHETIC_ARCHIVE_REVIEW_ONLY"
        and type(recovery_checks) is int
        and recovery_checks >= (16 if zstd_available else 8)
        and recovery.get("zip") == "passed"
        and (recovery_zstd == "passed" if zstd_available
             else recovery_zstd == "skipped_no_local_codec")
        and recovery.get("replay_held") is True
        and recovery.get("content_corruption_detected") is True
        and recovery.get("offline_html_written") is True
        and recovery.get("source_unchanged") is True
        and recovery.get("customer_ready") is False
        and recovery.get("exactly_once_verified") is False
        and recovery.get("power_loss_verified") is False
        and recovery.get("windows_ntfs_verified") is False
    )
    report["steps"].append({"step": "synthetic_recovery_review",
                            "status": "PASS" if recovery_ok else "FAIL",
                            "checks": recovery_checks if type(recovery_checks) is int else 0,
                            "exit_code": code if type(code) is int else -1,
                            "zstd": recovery_zstd if recovery_zstd in
                                ("passed", "skipped_no_local_codec") else "failed",
                            "error_code": "NONE" if recovery_ok else
                                _safe_code(recovery.get("error_code"), "RECOVERY_REVIEW_GATE_FAILED")})

    # Mandatory real developer ZIP builder/extraction, separately trusted
    # pre-import audit, isolated synthetic archive self-test and tamper rejection.
    # This is NOT Windows durability, customer data approval or publisher signing.
    code, out, _ = _run([sys.executable, "-m", "scripts.portable_acceptance_gate"], timeout=240)
    try:
        portable = json.loads(out)
    except (ValueError, TypeError):
        portable = {}
    portable_checks = portable.get("checks", 0)
    portable_digest = portable.get("zip_sha256")
    portable_ok = (
        code == 0 and portable.get("status") == "PASS_SYNTHETIC_PORTABLE_ONLY"
        and type(portable_checks) is int and portable_checks >= 4
        and portable.get("ready_for_customer_data") is False
        and portable.get("signed") is False
        and portable.get("windows_ntfs_verified") is False
        and isinstance(portable_digest, str)
        and re.fullmatch(r"[0-9a-f]{64}", portable_digest) is not None
    )
    report["steps"].append({
        "step": "trusted_portable_zip_e2e",
        "status": "PASS" if portable_ok else "FAIL",
        "checks": portable_checks if type(portable_checks) is int else 0,
        "exit_code": code if type(code) is int else -1,
        "zip_sha256": portable_digest if portable_ok else None,
        "error_code": "NONE" if portable_ok else
            _safe_code(portable.get("error_code"), "PORTABLE_GATE_FAILED"),
    })

    # Real local production module integration, but ONLY a synthetic PostgreSQL
    # catalog cursor. Never a network connection or customer-readiness claim.
    code, out, _ = _run([sys.executable, "-m", "scripts.pg_synthetic_acceptance"], timeout=90)
    try:
        pg_end_to_end = json.loads(out)
    except (ValueError, TypeError):
        pg_end_to_end = {}
    pg_count = pg_end_to_end.get("checks")
    pg_ok = (
        code == 0 and pg_end_to_end.get("status") == "PASS_SYNTHETIC_PG_ONLY"
        and type(pg_count) is int and pg_count >= 6
        and pg_end_to_end.get("real_pg_connected") is False
        and pg_end_to_end.get("ready_for_customer_data") is False
        and pg_end_to_end.get("automatic_actions") is False
    )
    report["steps"].append({
        "step": "synthetic_pg_to_offline_html",
        "status": "PASS" if pg_ok else "FAIL",
        "checks": pg_count if type(pg_count) is int else 0,
        "exit_code": code if type(code) is int else -1,
        "error_code": "NONE" if pg_ok else
            _safe_code(pg_end_to_end.get("error_code"), "PG_SYNTHETIC_GATE_FAILED"),
    })

    # Mandatory real subprocess acceptance of the incremental content-addressed
    # implementation. Both operating systems must verify restore, replay
    # reuse, tamper denial, and unchanged synthetic original.
    code, out, _ = _run([sys.executable, "-m", "scripts.incremental_cli_gate"], timeout=160)
    try:
        incremental = json.loads(out)
    except (ValueError, TypeError):
        incremental = {}
    inc_checks = incremental.get("checks", 0)
    inc_ok = (
        code == 0
        and incremental.get("status") == "PASS_SYNTHETIC_INCREMENTAL_CLI_ONLY"
        and type(inc_checks) is int and inc_checks >= 12
        and incremental.get("source_unchanged") is True
        and incremental.get("independent_restore_verified") is True
        and incremental.get("second_generation_reused_chunks") is True
        and incremental.get("tampered_chunk_rejected") is True
        and incremental.get("compressed_independent_restore_verified") is True
        and incremental.get("compressed_second_generation_reused_chunks") is True
        and incremental.get("compressed_tamper_rejected") is True
        and incremental.get("format_mismatch_rejected") is True
        and incremental.get("customer_ready") is False
        and incremental.get("power_loss_verified") is False
        and incremental.get("automatic_deletion") is False
    )
    report["steps"].append({
        "step": "synthetic_incremental_cli_roundtrip",
        "status": "PASS" if inc_ok else "FAIL",
        "checks": inc_checks if type(inc_checks) is int else 0,
        "exit_code": code if type(code) is int else -1,
        "error_code": "NONE" if inc_ok else
            _safe_code(incremental.get("error_code"), "INCREMENTAL_CLI_GATE_FAILED"),
    })

    # Same two exact synthetic SQLite generations: compare actually stored
    # ZIP/CAS bytes and independently restore both formats (no universal claim).
    code, out, _ = _run([sys.executable, "-m", "scripts.benchmark_synthetic_archives"], timeout=180)
    try:
        sizes = json.loads(out)
    except (ValueError, TypeError):
        sizes = {}
    metrics = sizes.get("metrics", {})
    timings = sizes.get("timings_ns", {})
    timings_ok = (
        isinstance(timings, dict)
        and set(timings) == {
            "zip_write_ns", "raw_write_ns", "zlib_write_ns",
            "zip_restore_ns", "raw_restore_ns", "zlib_restore_ns"}
        and all(type(value) is int and 0 < value < 180_000_000_000
                for value in timings.values())
    )
    benchmark_ok = (
        code == 0 and sizes.get("status") == "PASS_SYNTHETIC_STORAGE_COMPARISON_ONLY"
        and type(sizes.get("checks")) is int and sizes["checks"] >= 11
        and sizes.get("same_synthetic_workload") is True
        and sizes.get("both_generations_restored") is True
        and sizes.get("second_generation_reused_blocks") is True
        and sizes.get("source_unchanged_during_archiving") is True
        and sizes.get("compressed_generations_restored") is True
        and sizes.get("compressed_second_reused_blocks") is True
        and sizes.get("no_universal_compression_claim") is True
        and sizes.get("timing_scope") == "one_sample_two_generations_wall_clock_only"
        and timings_ok
        and sizes.get("ready_for_customer_data") is False
        and isinstance(metrics, dict)
        and type(metrics.get("two_zip_archives_bytes")) is int
        and metrics["two_zip_archives_bytes"] > 0
        and type(metrics.get("cas_total_stored_bytes")) is int
        and metrics["cas_total_stored_bytes"] > 0
        and type(metrics.get("cas_minus_zip_bytes")) is int
        and metrics["cas_minus_zip_bytes"] == (
            metrics["cas_total_stored_bytes"] - metrics["two_zip_archives_bytes"])
        and type(metrics.get("compressed_cas_total_stored_bytes")) is int
        and metrics["compressed_cas_total_stored_bytes"] > 0
        and type(metrics.get("compressed_cas_minus_zip_bytes")) is int
        and metrics["compressed_cas_minus_zip_bytes"] == (
            metrics["compressed_cas_total_stored_bytes"] - metrics["two_zip_archives_bytes"])
    )
    report["steps"].append({
        "step": "synthetic_archive_size_comparison",
        "status": "PASS" if benchmark_ok else "FAIL",
        "checks": sizes.get("checks", 0) if type(sizes.get("checks")) is int else 0,
        "exit_code": code if type(code) is int else -1,
        "metrics": metrics if benchmark_ok else None,
        "timings_ns": timings if benchmark_ok else None,
        "timing_scope": "one_sample_two_generations_wall_clock_only" if benchmark_ok else None,
        "error_code": "NONE" if benchmark_ok else
            _safe_code(sizes.get("error_code"), "SYNTHETIC_BENCHMARK_GATE_FAILED"),
    })

    if all(step["status"] == "PASS" for step in report["steps"]):
        report["status"] = "PASS_SYNTHETIC_ENVIRONMENT_ONLY"
    return report


def main():
    report = verify()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS_SYNTHETIC_ENVIRONMENT_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
