"""Repeated synthetic-only ZIP/ZSTD/CAS benchmark on the same two snapshots.

No customer data, network, provider price comparison, or general compression
claim. Every stored-size result is measured from emitted files and every
generation is restored independently and checked against its snapshot SHA.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import statistics
import subprocess
import tempfile
from time import perf_counter_ns

from dbvora.archive.incremental_cas import create_incremental, restore_incremental
from dbvora.archive.compressed_cas import create_compressed, restore_compressed
from dbvora.archive.safe_zip import (
    create_snapshot, make_zip_archive, restore_zip_archive,
)
from dbvora.archive.zstd_archive import create_zstd_archive, restore_zstd_archive
from tests.fixtures.make_sqlite import create_fixture

STATUS = "PASS_SYNTHETIC_STORAGE_COMPARISON_ONLY"
DEFAULT_TRIALS = 3
MAX_TRIALS = 7
METHODS = ("zip", "zstd", "raw_cas", "compressed_cas")
OPTIONS = {
    "zip": "stdlib ZIP_DEFLATED default options",
    "zstd": "zstd CLI level 3",
    "raw_cas": "synthetic incremental CAS v1, 64 KiB chunks",
    "compressed_cas": "synthetic compressed CAS v2, zlib level 6, 64 KiB chunks",
}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _summary(values: list[int]) -> dict:
    if not values or any(type(value) is not int or value < 0 for value in values):
        raise ValueError("INVALID_MEASUREMENT_SERIES")
    return {
        "sample_count": len(values),
        "median": int(statistics.median(values)),
        "min": min(values),
        "max": max(values),
        "samples": values,
    }


def _zstd_version(binary: str) -> str:
    try:
        result = subprocess.run([binary, "--version"], capture_output=True,
                                text=True, timeout=5, check=False)
        match = re.search(r"\bv(\d+\.\d+\.\d+)\b",
                          ((result.stdout or "") + " " + (result.stderr or ""))[:512])
        return match.group(1) if result.returncode == 0 and match else "version_unavailable"
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return "version_unavailable"


def _storage_bytes(method: str, root: Path) -> int:
    if method == "zip":
        files = list((root / "archives").glob("*.zip"))
    elif method == "zstd":
        files = list((root / "archives").glob("*.dbvz"))
    elif method == "raw_cas":
        files = list((root / "chunks").glob("*.chunk"))
        files += list((root / "manifests").glob("*.json"))
    else:
        files = list((root / "compressed_chunks").glob("*.cz"))
        files += list((root / "compressed_manifests").glob("*.json"))
    return sum(file.stat().st_size for file in files)


def _create_trial(method: str, root: Path, first: Path, second: Path) -> tuple[list[dict], int]:
    archives, restores = root / "archives", root / "restores"
    archives.mkdir()
    restores.mkdir()
    artifacts = []
    start = perf_counter_ns()
    if method == "zip":
        artifacts = [make_zip_archive(snapshot, archives) for snapshot in (first, second)]
    elif method == "zstd":
        artifacts = [create_zstd_archive(snapshot, archives, level=3)
                     for snapshot in (first, second)]
    elif method == "raw_cas":
        chunks, manifests = root / "chunks", root / "manifests"
        chunks.mkdir()
        manifests.mkdir()
        artifacts = [create_incremental(
            snapshot, chunks, manifests, synthetic_only=True, accept_plaintext=True)
            for snapshot in (first, second)]
    else:
        chunks, manifests = root / "compressed_chunks", root / "compressed_manifests"
        chunks.mkdir()
        manifests.mkdir()
        artifacts = [create_compressed(
            snapshot, chunks, manifests, synthetic_only=True, accept_plaintext=True)
            for snapshot in (first, second)]
    elapsed = perf_counter_ns() - start
    return artifacts, elapsed


def _restore_trial(method: str, root: Path, artifacts: list[dict],
                   expected_shas: tuple[str, str]) -> tuple[bool, int]:
    restores = root / "restores"
    start = perf_counter_ns()
    okay = True
    for artifact, expected_sha in zip(artifacts, expected_shas):
        if method == "zip":
            result = restore_zip_archive(artifact["archive_path"], restores)
            target = Path(result["restored_path"])
        elif method == "zstd":
            result = restore_zstd_archive(artifact["archive_path"], restores)
            target = Path(result["restored_path"])
        elif method == "raw_cas":
            result = restore_incremental(
                root / "manifests" / artifact["manifest_name"],
                root / "chunks", restores, synthetic_only=True, accept_plaintext=True)
            target = restores / result["restored_name"]
        else:
            result = restore_compressed(
                root / "compressed_manifests" / artifact["manifest_name"],
                root / "compressed_chunks", restores,
                synthetic_only=True, accept_plaintext=True)
            target = restores / result["restored_name"]
        okay = okay and _sha(target) == expected_sha
    elapsed = perf_counter_ns() - start
    return okay, elapsed


def _fixture_snapshot(base: Path) -> tuple[Path, Path, Path, tuple[str, str], tuple[str, int]]:
    db = create_fixture(base / "synthetic.sqlite")
    with closing(sqlite3.connect(db)) as connection:
        connection.executemany(
            "INSERT INTO events(id,category,content) VALUES (?, ?, ?)",
            ((index, "synthetic", hashlib.sha256(str(index).encode()).digest() * 128)
             for index in range(3, 203)),
        )
        connection.commit()
    snapshots = base / "snapshots"
    snapshots.mkdir()
    first = Path(create_snapshot(db, snapshots)["snapshot_path"])
    first_sha = _sha(first)
    with closing(sqlite3.connect(db)) as connection:
        connection.execute(
            "UPDATE events SET content=? WHERE id=100",
            (b"SECOND_GENERATION_CHANGED_SYNTHETIC_BYTE" * 100,))
        connection.commit()
    second = Path(create_snapshot(db, snapshots)["snapshot_path"])
    second_sha = _sha(second)
    if first_sha == second_sha:
        raise ValueError("NO_SNAPSHOT_DELTA")
    source_state = (_sha(db), db.stat().st_mtime_ns)
    return db, first, second, (first_sha, second_sha), source_state


def _environment(zstd_binary: str | None) -> dict:
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine() or "unavailable",
        "processor": platform.processor() or "unavailable",
        "logical_cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "zstd_cli": "available" if zstd_binary else "unavailable",
        "zstd_cli_version": _zstd_version(zstd_binary) if zstd_binary else None,
    }


def verify(repeats: int = DEFAULT_TRIALS) -> dict:
    if type(repeats) is not int or not 3 <= repeats <= MAX_TRIALS:
        return {"contract": "dbvora.synthetic-repeat-benchmark.v1",
                "status": "FAIL_CLOSED", "error_code": "INVALID_TRIAL_COUNT",
                "ready_for_customer_data": False}
    report = {
        "contract": "dbvora.synthetic-repeat-benchmark.v1",
        "status": "FAIL_CLOSED", "checks": 0,
        "same_synthetic_workload": False, "generation_count": 2,
        "benchmark_trials_per_method": repeats, "benchmarks": {},
        "both_generations_restored": False, "second_generation_reused_blocks": False,
        "compressed_generations_restored": False,
        "compressed_second_reused_blocks": False, "zstd_generations_restored": False,
        "zstd": "unavailable", "source_unchanged_during_archiving": False,
        "no_universal_compression_claim": True, "customer_data": False,
        "ready_for_customer_data": False,
        "cache_policy": "OS caches are not cleared; method order rotates across trials.",
        "creation_timing_scope": "API call wall time; API self-verification may be included.",
        "restore_timing_scope": "Independent restore API plus restored-file SHA-256 check.",
    }
    try:
        zstd_binary = shutil.which("zstd")
        report["environment"] = _environment(zstd_binary)
        methods = [method for method in METHODS if method != "zstd" or zstd_binary]
        with tempfile.TemporaryDirectory(prefix="dbvora-two-gen-benchmark-") as temp:
            base = Path(temp)
            db, first, second, expected_shas, source_state = _fixture_snapshot(base)
            report["snapshot_bytes"] = [first.stat().st_size, second.stat().st_size]
            report["checks"] += 2
            observed = {method: [] for method in methods}
            trial_orders = []
            for trial in range(repeats):
                order = methods[trial % len(methods):] + methods[:trial % len(methods)]
                trial_orders.append(order)
                for method in order:
                    trial_root = base / "trials" / (method + "-" + str(trial + 1))
                    trial_root.mkdir(parents=True)
                    artifacts, create_ns = _create_trial(method, trial_root, first, second)
                    if any(artifact.get("snapshot_sha256") != expected_shas[index]
                           for index, artifact in enumerate(artifacts)):
                        raise ValueError("SNAPSHOT_SHA_MISMATCH")
                    restored, restore_ns = _restore_trial(
                        method, trial_root, artifacts, expected_shas)
                    if not restored:
                        raise ValueError("RESTORED_SHA_MISMATCH")
                    reused = None
                    if method in ("raw_cas", "compressed_cas"):
                        reused = artifacts[1].get("reused_chunks", 0)
                        if artifacts[0].get("new_chunks", 0) < 1 or reused < 1:
                            raise ValueError("SECOND_GENERATION_REUSE_MISSING")
                    stored_bytes = _storage_bytes(method, trial_root)
                    if stored_bytes <= 0 or create_ns <= 0 or restore_ns <= 0:
                        raise ValueError("INVALID_OBSERVED_MEASUREMENT")
                    observed[method].append({
                        "artifact_bytes": stored_bytes, "create_wall_ns": create_ns,
                        "restore_wall_ns": restore_ns, "restore_sha256_verified": True,
                        "second_generation_reused_chunks": reused,
                        "generation_count": 2,
                    })
                    report["checks"] += 2

            if (_sha(db), db.stat().st_mtime_ns) != source_state:
                raise ValueError("SOURCE_CHANGED_DURING_ARCHIVE")
            report["source_unchanged_during_archiving"] = True
            report["checks"] += 1
            summaries = {}
            for method in methods:
                trials = observed[method]
                if len(trials) != repeats or not all(
                        trial["restore_sha256_verified"] and trial["generation_count"] == 2
                        for trial in trials):
                    raise ValueError("INCOMPLETE_TRIALS")
                summary = {
                    "trial_count": len(trials), "generation_count": 2,
                    "options": OPTIONS[method], "trials": trials,
                    "artifact_bytes": _summary([trial["artifact_bytes"] for trial in trials]),
                    "create_wall_ns": _summary([trial["create_wall_ns"] for trial in trials]),
                    "restore_wall_ns": _summary([trial["restore_wall_ns"] for trial in trials]),
                    "restore_sha256_verified": True,
                }
                if method == "raw_cas":
                    summary["second_generation_reused_chunks"] = True
                elif method == "compressed_cas":
                    summary["second_generation_reused_chunks"] = True
                summaries[method] = summary
            report["benchmarks"] = summaries
            report["trial_orders"] = trial_orders
            report["same_synthetic_workload"] = True
            report["both_generations_restored"] = all(
                summaries[method]["restore_sha256_verified"]
                for method in ("zip", "raw_cas"))
            report["second_generation_reused_blocks"] = (
                summaries["raw_cas"].get("second_generation_reused_chunks") is True)
            report["compressed_generations_restored"] = (
                summaries["compressed_cas"]["restore_sha256_verified"])
            report["compressed_second_reused_blocks"] = (
                summaries["compressed_cas"].get("second_generation_reused_chunks") is True)
            if zstd_binary:
                report["zstd"] = "passed"
                report["zstd_generations_restored"] = summaries["zstd"]["restore_sha256_verified"]
            else:
                report["zstd"] = "skipped_no_local_codec"
                report["zstd_generations_restored"] = False
            if (report["generation_count"] != 2
                    or report["benchmark_trials_per_method"] != repeats
                    or not report["same_synthetic_workload"]
                    or not report["both_generations_restored"]
                    or not report["second_generation_reused_blocks"]
                    or not report["compressed_generations_restored"]
                    or not report["compressed_second_reused_blocks"]
                    or (zstd_binary and not report["zstd_generations_restored"])):
                raise ValueError("REPEATED_BENCHMARK_ACCEPTANCE_FAILED")

            metrics = {
                "first_snapshot_bytes": report["snapshot_bytes"][0],
                "second_snapshot_bytes": report["snapshot_bytes"][1],
                "benchmark_trials_per_method": repeats,
                "two_zip_archives_bytes": summaries["zip"]["artifact_bytes"]["median"],
                "zstd_archives_bytes": summaries["zstd"]["artifact_bytes"]["median"]
                    if zstd_binary else None,
                "cas_total_stored_bytes": summaries["raw_cas"]["artifact_bytes"]["median"],
                "compressed_cas_total_stored_bytes": summaries["compressed_cas"]["artifact_bytes"]["median"],
            }
            metrics["cas_minus_zip_bytes"] = (
                metrics["cas_total_stored_bytes"] - metrics["two_zip_archives_bytes"])
            metrics["compressed_cas_minus_zip_bytes"] = (
                metrics["compressed_cas_total_stored_bytes"] - metrics["two_zip_archives_bytes"])
            metrics["zstd_minus_zip_bytes"] = (
                metrics["zstd_archives_bytes"] - metrics["two_zip_archives_bytes"]
                if metrics["zstd_archives_bytes"] is not None else None)
            timings = {
                "zip_write_ns": summaries["zip"]["create_wall_ns"]["median"],
                "raw_write_ns": summaries["raw_cas"]["create_wall_ns"]["median"],
                "zlib_write_ns": summaries["compressed_cas"]["create_wall_ns"]["median"],
                "zip_restore_ns": summaries["zip"]["restore_wall_ns"]["median"],
                "raw_restore_ns": summaries["raw_cas"]["restore_wall_ns"]["median"],
                "zlib_restore_ns": summaries["compressed_cas"]["restore_wall_ns"]["median"],
            }
            zstd_timings = ({
                "zstd_write_ns": summaries["zstd"]["create_wall_ns"]["median"],
                "zstd_restore_ns": summaries["zstd"]["restore_wall_ns"]["median"],
            } if zstd_binary else {})
            if (any(type(value) is not int or not 0 < value < 180_000_000_000
                    for value in timings.values())
                    or any(type(value) is not int or not 0 < value < 180_000_000_000
                           for value in zstd_timings.values())):
                raise ValueError("INVALID_TIMING_MEASUREMENT")
            report["metrics"] = metrics
            report["timings_ns"] = timings
            report["zstd_timings_ns"] = zstd_timings
            report["timing_scope"] = (
                str(repeats) + "_trial_medians_two_generations_wall_clock_only")
            report["checks"] += 2
            report["status"] = STATUS
    except Exception:
        # Do not leak input paths, private SQL, payloads or raw process messages.
        report["error_code"] = "SYNTHETIC_SIZE_COMPARISON_FAILED"
    return report


def main():
    result = verify()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
