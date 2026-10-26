# DBVORA P1-C1 — offline ZIP vs ZSTD synthetic benchmark

- Date: 2026-10-26 KST. Repo: hibi89/DBVORA; branch: feature/p0-db-map.
- Implementation: dbvora/archive/zstd_archive.py (official zstd CLI via subprocess, no shell). A self-contained .dbvz envelope: fixed 8-byte magic, 4-byte manifest size, bounded JSON manifest, and compressed ZSTD frame.
- Supported compression levels: 1, 3, 9. Same validated standalone SQLite backup snapshot is used for ZIP and all levels in each dataset. New files only, not a customer DB. Frame and restored snapshot SHA-256 plus PRAGMA integrity_check must pass before publication.
- ZIP baseline: existing stdlib ZIP with self-verification. ZSTD adds bounded streamed decompression and fixed output paths. The stored-size measurements include each archive's manifest/envelope; the raw baseline has no envelope.
- Codec installed locally: official zstd CLI 1.5.7 on Linux. The Python 'zstandard' package is not installed; package registry DNS is blocked. This implementation does NOT bundle zstd CLI for Windows. Dependency unavailable raises CODEC_UNAVAILABLE, not a silent fallback.

## Observed 3-trial median on one transient Linux Python 3.13.5 / SQLite 3.46.1 host

Both synthetic SQLite files measured **565,248 bytes** after online snapshot. Wall-clock create times include the archive's own independent restore dry-run. Restore times measure a separate full restore. Results are environment-specific, not representative pricing/customer storage claims.

| Dataset | Codec | Stored bytes incl. manifest | Create seconds median | Restore seconds median | SHA |
| --- | --- | ---: | ---: | ---: | --- |
| repetitive | raw SQLite snapshot (no manifest) | 565248 | 0 (reference) | 0.000293 | PASS |
| repetitive | ZIP DEFLATE | 3799 | 0.008274 | 0.003123 | PASS |
| repetitive | ZSTD-1 | 1390 | 0.018762 | 0.010830 | PASS |
| repetitive | ZSTD-3 | 1373 | 0.017859 | 0.008970 | PASS |
| repetitive | ZSTD-9 | 1265 | 0.026436 | 0.008830 | PASS |
| incompressible payload within SQLite | raw SQLite snapshot | 565248 | 0 (reference) | 0.000372 | PASS |
| incompressible payload within SQLite | ZIP DEFLATE | 528037 | 0.030907 | 0.006634 | PASS |
| incompressible payload within SQLite | ZSTD-1 | 527869 | 0.023712 | 0.012683 | PASS |
| incompressible payload within SQLite | ZSTD-3 | 526749 | 0.041552 | 0.012901 | PASS |
| incompressible payload within SQLite | ZSTD-9 | 526399 | 0.036103 | 0.013849 | PASS |

Method: scripts/bench_codecs.py, 3 independent trials of each method for each of two datasets, one snapshot reused per dataset, archive sizes include metadata, verified restore SHA for every trial. The apparently incompressible test still includes compressible SQLite page/header overhead; not pure random-byte data. Unseeded random payloads vary between runs; compare methods *within* one run only. RAM peak was NOT measured for the combined subprocess/Python process, so no memory advantage claim. Process CPU was not compared. All trial artifacts were generated in OS temp folders, never committed.

## Test evidence and technical limitations
- python -W error::ResourceWarning -m unittest discover -s tests -q => **62 pass, 0 fail, 0 skipped** (prior 46 plus new 16).
- node --check dbvora/web/app.js => PASS; node --test tests/test_ui_dom.cjs => 1 PASS.
- python -m compileall -q dbvora tests scripts/bench_codecs.py => PASS.
- python -m pip wheel . --no-deps --no-build-isolation => PASS; wheel includes zstd_archive.py, old ZIP module and web HTML/JS/CSS.
- Synthetic scenarios include levels 1/3/9, same-snapshot SHA, byte equality, damaged/truncated container, tampered frame and manifest checksums, huge manifest, size-bound simulated decompression bomb, missing codec, symlink/relative path rejection, repeated restore, existing-file preservation on publish failure and randomized BLOB payloads.
- Existing 46 tests remain passing, original bytes/mtime unmodified for synthetic source.
- ZSTD CLI is not bundled in wheel, no Windows compatibility claim. ZIP remains the available standard-library codec. ZSTD archive is custom .dbvz and should not be mistaken for standalone .zst stream.
- SHA and unsigned manifest detect accidental inconsistency but DO NOT authenticate against malicious changes to both payload and manifest. No encryption, directory fsync, provenance signature, power-failure durability, interrupted-run sweep or long-term storage policy.
- Prototype cap 512 MiB; potential path/symlink TOCTOU and Windows hardlink semantics need additional examination. This is NOT safe for unattended customer backups yet.
- Browser E2E remains blocked in prior environment by managed Chromium URLBlocklist '*'. Windows, Python 3.11, live customer DB, PR/CI and public deployments NOT VERIFIED.

## Decision
Retain ZIP fallback and optional real ZSTD CLI backend for **offline synthetic experimentation**. ZSTD was smaller for both samples, but CLI process startup and extra staging work often increased latency. No universal compression improvement or business benefit is claimed. Next focus: tested crash-recovery/durability and Windows codec distribution before real use.
