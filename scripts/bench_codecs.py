"""Reproducible offline ZIP vs ZSTD baseline; no customer databases or network.

Each dataset is snapshotted exactly once with SQLite online backup. Each codec
uses that same standalone snapshot for at least three trial runs. Timing includes
archive self-restore verification, because both producers do it. Compressed sizes
include manifests/envelope overhead. Raw baseline is the standalone file alone.
"""

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import statistics
import tempfile
from time import perf_counter

from dbvora.archive.safe_zip import create_snapshot, make_zip_archive, restore_zip_archive
from dbvora.archive.zstd_archive import create_zstd_archive, restore_zstd_archive


def synthetic_db(path: Path, kind: str, rows: int) -> Path:
    # No need to commit or expose the generated database. Random bytes are
    # intentionally unseeded: the reported hash is used only within each run.
    with closing(sqlite3.connect(path)) as con:
        con.execute("CREATE TABLE synthetic (id INTEGER PRIMARY KEY, payload BLOB)")
        if kind == "repetitive":
            payloads = [(b"repeated-token|2026-10-26|" * 340)[:8192] for _ in range(rows)]
        elif kind == "incompressible":
            payloads = [os.urandom(8192) for _ in range(rows)]
        else:
            raise ValueError("unknown dataset")
        con.executemany("INSERT INTO synthetic(payload) VALUES (?)", ((x,) for x in payloads))
        con.commit()
    return path


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as src:
        for block in iter(lambda: src.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def summarize(records: list[dict]) -> dict:
    return {
        "trials": len(records),
        "stored_bytes_median": int(statistics.median(x['bytes'] for x in records)),
        "compression_seconds_median": round(statistics.median(x['create_s'] for x in records), 6),
        "restore_seconds_median": round(statistics.median(x['restore_s'] for x in records), 6),
        "compression_seconds_range": [round(min(x['create_s'] for x in records), 6), round(max(x['create_s'] for x in records), 6)],
        "all_restored_sha_equal": all(x['sha_ok'] for x in records),
        "peak_ram_bytes": None,
        "peak_ram_reason": "not_measured_for_subprocess_and_python_combined",
    }


def run(repeats=3, rows=64) -> dict:
    if repeats < 3:
        raise ValueError('at least 3 trials required')
    if not (1 <= rows <= 1024):
        raise ValueError('rows must be between 1 and 1024')
    report = {"scope": "synthetic_only", "trials_per_codec": repeats,
              "measurement": "wall_clock_including_dry_run_archive_verification",
              "archive_bytes_include_manifest": True, "datasets": {}}
    with tempfile.TemporaryDirectory(prefix='dbvora-codec-benchmark-') as root:
        directory = Path(root)
        work = directory / 'artifacts'
        work.mkdir()
        restored = directory / 'restored'
        restored.mkdir()
        for kind in ('repetitive', 'incompressible'):
            source = synthetic_db(directory / (kind + '.sqlite'), kind, rows)
            original = (sha(source), source.stat().st_mtime_ns)
            snap = create_snapshot(source, work)
            snapshot = Path(snap['snapshot_path'])
            baseline = sha(snapshot)
            runs = {}
            for method in ('raw', 'zip', 'zstd-1', 'zstd-3', 'zstd-9'):
                observed = []
                for _ in range(repeats):
                    if method == 'raw':
                        created = snapshot
                        start = perf_counter()
                        # The raw baseline has no compression and no archive manifest.
                        create_time = perf_counter() - start
                        start = perf_counter()
                        target = restored / (os.urandom(8).hex() + '.sqlite')
                        shutil.copyfile(created, target)
                        restore_time = perf_counter() - start
                        size = created.stat().st_size
                    elif method == 'zip':
                        start = perf_counter()
                        archive = make_zip_archive(snapshot, work)
                        create_time = perf_counter() - start
                        start = perf_counter()
                        restored_info = restore_zip_archive(archive['archive_path'], restored)
                        restore_time = perf_counter() - start
                        target = Path(restored_info['restored_path'])
                        size = archive['archive_size_bytes']
                    else:
                        level = int(method.split('-')[1])
                        start = perf_counter()
                        archive = create_zstd_archive(snapshot, work, level=level)
                        create_time = perf_counter() - start
                        start = perf_counter()
                        restored_info = restore_zstd_archive(archive['archive_path'], restored)
                        restore_time = perf_counter() - start
                        target = Path(restored_info['restored_path'])
                        size = archive['archive_size_bytes']
                    observed.append({"bytes": size, "create_s": create_time,
                                     "restore_s": restore_time, "sha_ok": sha(target) == baseline})
                    if not observed[-1]['sha_ok']:
                        raise RuntimeError('SHA-256 restored snapshot mismatch')
                runs[method] = summarize(observed)
            if (sha(source), source.stat().st_mtime_ns) != original:
                raise RuntimeError('source file mutated')
            report['datasets'][kind] = {"snapshot_bytes": snap['snapshot_size_bytes'],
                                        "snapshot_integrity": snap['sqlite_integrity'],
                                        "methods": runs}
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', type=int, default=3)
    parser.add_argument('--rows', type=int, default=64)
    args = parser.parse_args()
    print(json.dumps(run(args.trials, args.rows), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
