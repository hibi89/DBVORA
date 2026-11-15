# R02-04 — Local resource provenance and unavailable metrics

**Status:** PASS_SCOPED  
**Source/test SHA:** `d8a61d583e930755513c05d40b82f21da9270240`  
**Branch:** `feature/p0-db-map`  
**Date:** 2026-11-15 KST

## Accepted behavior

- CPU is cumulative `time.process_time_ns()` for the current DBVORA Python process. The contract labels it as process CPU time, not a CPU percentage.
- RAM is resident memory for that same Python process: Linux `/proc/self/statm` or Windows PSAPI working set. If the OS source is unsupported or fails, the value stays `null` and the source/status say `unavailable`.
- Disk reports total/free bytes for the filesystem volume containing the explicitly supplied local directory. It is not database-file size, process disk I/O, or database-server storage.
- PostgreSQL/SQLite server CPU and RAM are explicitly `null`; the implementation does not infer them from DBVORA process metrics.
- Two-sample comparison requires valid contract and process identity, strictly increasing monotonic time, and nondecreasing CPU counters. CPU and RSS are raw deltas, with no CPU percentage, projection, or forecast. RAM delta stays unavailable when either sample lacks RAM or its provenance changes.
- The local CLI requires an explicit local directory; its optional sampling interval is bounded to 100–5000 ms. Invalid/symlink paths and unsafe intervals fail without echoing private paths. Automatic actions and customer-data readiness remain disabled.

## Regression coverage added

At this exact SHA, tests pin the successful metric scope/source labels and ensure unavailable RAM/disk do not contain fabricated numeric values. The existing process-resource suite covers real local counters, two-sample raw deltas, process/session mismatch, invalid clocks/counters, legacy or untrusted fields, missing RAM, path/symlink rejection, sanitized CLI failures, bounded sampling, and the actual CLI contract.

Source: [`dbvora/process_resources.py`](https://github.com/hibi89/DBVORA/blob/d8a61d583e930755513c05d40b82f21da9270240/dbvora/process_resources.py)  
Tests: [`tests/test_process_resources.py`](https://github.com/hibi89/DBVORA/blob/d8a61d583e930755513c05d40b82f21da9270240/tests/test_process_resources.py)

## Exact-SHA GitHub Actions

- [Full offline release gate #43658719628](https://github.com/hibi89/DBVORA/actions/runs/43658719628) — PASS on Ubuntu 24.04 and Windows 2025, Python 3.11. Ubuntu: 797/797 passed, 0 skips. Windows: 797 discovered, 796 passed and one named POSIX-only test skipped. Required release-gate steps passed on both runners. Synthetic-only.
- [Unsigned source ZIP #43658719559](https://github.com/hibi89/DBVORA/actions/runs/43658719559) — PASS; 75 files, self-check 9/9; source ZIP SHA-256 `e6e4d4042baddf871726a888937db5aa550c85019c28e9f6598b3922802a20dc`; artifact ID `14139073992`; artifact archive digest `sha256:b40de66574c6e22e042dfd44652981a74cf70bf37c3ccda7ca3c01016871e51c`.
- [Unsigned Windows demo EXE #43658719555](https://github.com/hibi89/DBVORA/actions/runs/43658719555) — PASS; EXE SHA-256 `b1488c44072cac8f1d521736de601209ef705b9cfab4451f9091e3019ec95fd6`; artifact ID `14138084360`; artifact archive digest `sha256:b60505264434851491c8df6c70dfa024de66b8287339407178fc8a5c20bfcd04`.
- [Final blueprint evidence gate #43658719927](https://github.com/hibi89/DBVORA/actions/runs/43658719927) — PASS.

## Limits

This acceptance establishes local process and host-volume provenance on GitHub runners. It does not measure per-process disk I/O or PostgreSQL/SQLite server CPU/RAM, and it does not prove production workload performance or customer-data readiness. ZIP and EXE are unsigned synthetic previews. Owner, physical-device, power-loss, legal and commercial gates remain open. Overall completion remains **UNASSESSED / RELEASE HOLD**.
