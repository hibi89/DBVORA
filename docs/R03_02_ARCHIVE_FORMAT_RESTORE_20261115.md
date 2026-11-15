# R03-02 — Independent restore across ZIP, ZSTD, raw CAS, and compressed CAS

**Status:** PASS_SCOPED  
**Source/test SHA:** `49ab1080dc8a7a28f0e1435233f51d1caff0f87a`  
**Branch:** `feature/p0-db-map`  
**Date:** 2026-11-15 KST

## Exact-SHA behavior and checks

The existing archive implementation was rechecked without rewriting it. ZIP and ZSTD independently restore the standalone SQLite snapshots; raw CAS v1 and compressed CAS v2 reconstruct snapshots from immutable content-addressed chunks. All four restore paths validate the whole-file SHA-256 and run SQLite `PRAGMA integrity_check` before publishing a new output filename. The CAS readers also verify each chunk and the declared size/hash; failure leaves no restored SQLite artifact. Restore destinations must be separate valid local directories and generated output names are not overwritten.

The synthetic repeat benchmark uses the **same two generated SQLite backup snapshots** for each available format. The exact-SHA release gate ran three trials per format, independently restored both generations, compared each restored file SHA-256 to its source snapshot, and confirmed generation-two chunk reuse for both CAS formats. ZSTD was available on both runners.

Relevant implementation and regression coverage:

- ZIP: [`safe_zip.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/dbvora/archive/safe_zip.py), [`test_safe_zip.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/tests/test_safe_zip.py) — byte-identical restore, integrity, unique restores, truncated/duplicate/tampered ZIP rejection and traversal rejection.
- ZSTD: [`zstd_archive.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/dbvora/archive/zstd_archive.py), [`test_zstd_archive.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/tests/test_zstd_archive.py) — SHA/integrity across supported levels, distinct outputs, frame/manifest tamper rejection and no publication on failure.
- Raw CAS v1: [`incremental_cas.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/dbvora/archive/incremental_cas.py), [`test_incremental_cas.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/tests/test_incremental_cas.py) — chunk and whole-snapshot digest verification, integrity validation, old/new generation restore, and corrupt/missing chunk or duplicate-key manifest refusal.
- Compressed CAS v2: [`compressed_cas.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/dbvora/archive/compressed_cas.py), [`test_compressed_cas.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/tests/test_compressed_cas.py) — per-chunk and whole-snapshot digest, integrity validation, independent generation restores, compressed corruption/bomb refusal, and format separation from raw CAS v1.
- Cross-format repeat verification: [`benchmark_synthetic_archives.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/scripts/benchmark_synthetic_archives.py), [`test_benchmark_synthetic_archives.py`](https://github.com/hibi89/DBVORA/blob/49ab1080dc8a7a28f0e1435233f51d1caff0f87a/tests/test_benchmark_synthetic_archives.py).

## Exact-SHA GitHub Actions

- [Offline full release gate #43679171661](https://github.com/hibi89/DBVORA/actions/runs/43679171661) — PASS_SYNTHETIC_ENVIRONMENT_ONLY. Ubuntu 798/798, 0 skips; Windows 797 PASS + one named POSIX-only skip (`test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`). All 12 required gate steps passed on both runners.
- Within that gate, `synthetic_archive_size_comparison` passed 29 checks on each OS. ZIP, ZSTD, raw CAS and compressed CAS each report 3 trials × 2 generations and `restore_sha256_verified: true`; ZSTD availability was confirmed; second-generation chunk reuse passed for raw and compressed CAS.
- [Unsigned source ZIP #43679171633](https://github.com/hibi89/DBVORA/actions/runs/43679171633) — PASS, 75 files, offline self-check 9/9.
- [Unsigned Windows demo EXE #43679171613](https://github.com/hibi89/DBVORA/actions/runs/43679171613) — PASS.
- [Final blueprint evidence gate #43679171766](https://github.com/hibi89/DBVORA/actions/runs/43679171766) — PASS.

All databases and artifacts in this acceptance are synthetic. These GitHub runner checks do not establish physical power-loss survival, owner-device recovery, or customer workload readiness. ZIP/EXE previews are unsigned and not for sale. Overall completion remains **UNASSESSED / RELEASE HOLD**; OWNER_GATE remains open.

**Next:** R03-03 — recheck CAS generation-chain linkage, manifest integrity, and failure-safe behavior at a fixed exact SHA.
