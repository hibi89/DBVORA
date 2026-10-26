# DBVORA P1-C5 real-engine synthetic ZIP/ZSTD smoke — 2026-10-26 KST

**Scope:** real unmodified DBVORA archive engine modules, run locally on an **entirely synthetic** SQLite fixture; no customer DB, no network archiving, no CI charge, no Production. This is focused runtime evidence **not** the complete 156-case repository suite, not a Windows test, and not commercial approval.

## Source provenance and environment
- Private repository `hibi89/DBVORA`, branch `feature/p0-db-map`, input HEAD `9c60b88303132ed589e4e5b652cbcb1f98155adc`.
- Files fetched through authenticated GitHub repository connector; bytes reconstituted only into a temporary local workspace. Local `git hash-object` values were compared with the remote Git object SHA **before executing**:
  - `dbvora/archive/safe_zip.py` `a58d2c3bfd3b95a98ada74f59e208b58e35d2e13`
  - `dbvora/archive/zstd_archive.py` `94f638ce8a252f282229312d79dda95464b2a061`
  - `dbvora/connectors/sqlite_reader.py` `1d663d9d8243b75dbca0e697428870328bd87509`
  - `dbvora/errors.py` `03649675b51aed9e7438072b26dd3411160c6695`
  - `tests/fixtures/make_sqlite.py` `7f407189ba98b70be22f52b7ca45b53c935f63e3`
- Temporary local environment: Linux, Python **3.13.5**, SQLite **3.46.1**, external Zstandard CLI **1.5.7**. Temporary package `__init__.py` stubs were empty; actual production source files above were unchanged.
- Inputs created with `tests.fixtures.make_sqlite.create_fixture`, which contains only dummy rows. Snapshot size **24,576 bytes**.

## Real ZIP engine test result
- Directly invoked `dbvora.archive.safe_zip.create_snapshot`, `make_zip_archive`, and `restore_zip_archive` against separate temporary directories. Snapshot, ZIP independent dry-run, SQLite integrity, restored SHA-256 and original SHA-256/mtime/size unchanged all **PASS**.
- Executed **17 local independent synthetic unittest scenarios, 17 PASS, 0 FAIL, 0 SKIP**, Python ResourceWarning-as-error enabled, in approx. 0.256 sec. These 17 test functions are in an ephemeral verification script, **not** the checked-in `tests/test_safe_zip.py`; do not count them as the existing 18 tests or mark the 156 suite green.
- Scenarios: snapshot integrity, ZIP dry-run, restored byte hash, original SHA/mtime/size, row equality, WAL-committed row included, distinct new-only snapshots, ZIP manifest no original path, truncated ZIP rejected, tampered SHA rejected, member traversal rejected, duplicate members rejected, relative destination rejected, missing destination rejected, simulated publish failure preserves previous artifact, simulated ZIP verification failure cleans staging, errors do not echo source path.
- ZIP published size in sample run: **1,006 bytes**. Corrupted archive refusal yielded `INVALID_ARCHIVE`; tampered manifest SHA yielded `HASH_MISMATCH`.

## Real ZSTD engine smoke
With installed official external `zstd`, invoked `create_zstd_archive` / `restore_zstd_archive` from the actual SHA-matched module for levels **1, 3 and 9**. Independently hashed each restored SQLite file against the source snapshot SHA-256. All passed DB integrity, independent restore, restored SHA, and original source hash+mtime check.

| Codec | Sample published archive bytes | Restoration, SHA and SQLite integrity |
| --- | ---: | --- |
| ZIP/DEFLATE | 1,006 | PASS |
| ZSTD level 1 | 906 | PASS |
| ZSTD level 3 | 877 | PASS |
| ZSTD level 9 | 867 | PASS |

Single tiny synthetic fixture with per-artifact envelope overhead; these numbers **do not** indicate representative compression ratio, rate, scalability, or superiority over PostgreSQL/Supabase.

## Remaining gates and constraints
- Actual `dbvora.archive_cli` integration with signed/unsigned receipt catalog, durable receipt chain, independent restart audit, and the unified `scripts.verify_release_gate` not executed this run: `receipts.py` and `recovery_catalog.py` not yet copied to current local runtime.
- The **156** checked-in Python test methods remain **NOT RUN as one suite**, as do real UI browser, Windows/Python3.11/NTFS, unexpected hardware power loss, multi-DB features, performance at real scale, and customer files.
- ZSTD is external optional CLI, unbundled. Windows directory-fsync behavior remains unvalidated and currently designed to fail closed.
- Next: assemble exact-SHA `recovery_catalog.py` and `receipts.py` plus checked-in `archive_cli.py` and `tests/test_archive_cli.py` in the local source workspace, then run the 9 real CLI cases and actual read-only receipt audit; subsequently complete 156-suite acceptance. Avoid paid private CI or external private code transfer without approval.
