# R03-01 — WAL-consistent SQLite snapshot under an active writer

**Status:** PASS_SCOPED  
**Source/test SHA:** `49ab1080dc8a7a28f0e1435233f51d1caff0f87a`  
**Branch:** `feature/p0-db-map`  
**Date:** 2026-11-15 KST

## Implementation already present

`dbvora/archive/safe_zip.py` creates a SQLite snapshot with the SQLite online backup API (`src.backup(dest, pages=64, sleep=0.01)`) after opening the source through the read-only connector. It validates the staged standalone database with `PRAGMA integrity_check`, hashes it, then publishes a new artifact. Existing output must be an approved absolute directory, separate from the source; an existing artifact is never overwritten. This acceptance added regression coverage only; the implementation was not rewritten.

Source: [`safe_zip.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/dbvora/archive/safe_zip.py)  
Tests: [`test_safe_zip.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/tests/test_safe_zip.py)

## Added concurrent-WAL regression

The new test opens a synthetic SQLite fixture in WAL mode, commits a known row, then starts a separate writer holding an uncommitted `BEGIN IMMEDIATE` transaction while the online backup runs. It asserts that the snapshot contains the committed row, excludes the writer’s uncommitted row, passes SQLite integrity validation, and the original main database retains its SHA-256, size, and `mtime_ns`. The writer is released with rollback in a bounded `finally` path.

The existing suite also verifies committed WAL rows are included without checkpointing, standalone snapshots/restores match by SHA-256, source identity is preserved, repeated snapshots use distinct outputs, and failures do not publish partial artifacts or replace a prior snapshot. Inputs are disposable synthetic databases only.

## Exact-SHA GitHub Actions

- [Offline full release gate #43679171661](https://github.com/hibi89/DBVORA/actions/runs/43679171661) — PASS_SYNTHETIC_ENVIRONMENT_ONLY at the exact SHA. Ubuntu: 798/798 PASS, 0 skips. Windows: 798 discovered, 797 PASS and one named POSIX-only skip (`test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`). All 12 release-gate steps passed on both OS runners, including Python tests, CLI roundtrip, compile, DOM, publication preflight, recovery and archive checks.
- [Unsigned source ZIP #43679171633](https://github.com/hibi89/DBVORA/actions/runs/43679171633) — PASS; 75 files, offline self-check 9/9; source ZIP SHA-256 `3b9856c8eb89ff169eb83c2f7f05a539bc022a201e84bc8221457bacf25f407e`; artifact ID `14147457205`; artifact archive digest `sha256:77d3e17e96155e08d85e3cb786db75aa76be61074a81ae15a8672ec6362dcf4a`.
- [Unsigned Windows demo EXE #43679171613](https://github.com/hibi89/DBVORA/actions/runs/43679171613) — PASS; EXE SHA-256 `da9a111a2e6aadf7329f77b2f5369bf3f2b4ed4d6df752b00f827d12cdf8cdc7`; artifact ID `14147940515`; artifact archive digest `sha256:0c191581a4b5bda002ef344bf4a1cab5911fd67be2d346f9df571a47035a1813`.
- [Final blueprint evidence gate #43679171766](https://github.com/hibi89/DBVORA/actions/runs/43679171766) — PASS.

## Limits and next work

This is synthetic GitHub-runner evidence for SQLite online-backup snapshot consistency and source-file preservation. It does not establish physical power-loss durability, customer workload behavior, owner-device recovery, or production readiness. The ZIP/EXE are unsigned preview artifacts and are not for sale. Overall completion remains **UNASSESSED / RELEASE HOLD**; owner gates stay open.

**Next:** R03-02 — independently restore ZIP, ZSTD, raw CAS, and compressed CAS artifacts and compare hashes plus SQLite integrity at exact SHA.
