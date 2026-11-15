# R02-01 — SQLite dbstat boundary evidence

**Result:** PASS_SCOPED for the synthetic GitHub CI scope.  
**Implementation code SHA:** `1eb5284cf0ddc0ba6411324902efc4f4d8c917e9` (unchanged by the acceptance-test commit).  
**Source/test SHA:** `7597a9ab0d7ea6e8e84f4184e8d55bbbbf5f358`  
**Branch:** `feature/p0-db-map`

## What was checked

- Audited `dbvora/storage_metrics.py`: table allocation is an optional read-only `dbstat` query, grouped by b-tree name for each table and its indexes. The API inventory path does not eagerly run `dbstat`; the browser harness checks that the explicit table-storage request does.
- Added `test_exact_main_file_limit_and_in_budget_scan_are_measured`. It passes the exact `MAX_DBSTAT_MAIN_BYTES` value (64 MiB) into the measurement boundary and confirms an in-budget synthetic scan returns measured table/index allocation. It does not create a physical 64 MiB database.
- Existing over-limit coverage confirms the scan returns unavailable before opening a read-only SQLite connection. Existing unsupported-`dbstat` coverage confirms the result stays unavailable with an empty table map.
- Added `test_dbstat_watchdog_aborts_after_point_seventy_five_seconds`. A fake connection invokes the installed progress callback after mocked monotonic time passes 0.75 seconds; the simulated SQLite interruption returns `unavailable`, reason `dbstat_unavailable_or_limited`, and no table values. The progress handler is configured for every 1,000 SQLite VM instructions.
- Existing API tests exercise source-file replacement detection, and the 2OS browser/PG16 acceptance for the unchanged implementation SHA remains available below.

This metric describes logical b-tree page allocation reported by SQLite `dbstat`; it is not total filesystem usage, logical row size, or a separate measurement of main/WAL/SHM files. The code explicitly qualifies that physical usage depends on those files and filesystem accounting.

## Exact-SHA GitHub Actions

At source/test SHA `7597a9ab0d7ea6e8e84f4184e8d55bbbbf5f358`:

- Full fail-closed release gate [#43656462650](https://github.com/hibi89/DBVORA/actions/runs/43656462650): PASS, synthetic only. Ubuntu: 796/796 tests, 0 skips; Windows: 796 discovered, 795 pass plus the named POSIX-only skip `test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`. All 12 required gate steps passed on both OSes.
- Unsigned source preview [#43656462699](https://github.com/hibi89/DBVORA/actions/runs/43656462699): PASS, 75 files, packaged self-check 9/9. Source ZIP SHA-256: `d3836d9e6894e79d219a4cbbbf555e8c83b0e8ae3a92e2c779e3aee9500885e5`. GitHub artifact ID 14138870244, artifact ZIP digest `sha256:b9c9a1c630441862f025d171f507f2dc12def41d2e024246969f7e75abdef947`.
- Unsigned Windows demo [#43656462693](https://github.com/hibi89/DBVORA/actions/runs/43656462693): PASS. EXE SHA-256: `5c2a7baf32c3512042d61ec94c25aab03eb27d91ebbe7665c10b99b8df898fbe`. GitHub artifact ID 14137264522, artifact ZIP digest `sha256:9d469726d847f5a41c1432bee6c7ddf45d84871e73b005852c62a0a1735963aa`.
- Final blueprint evidence [#43656462917](https://github.com/hibi89/DBVORA/actions/runs/43656462917): PASS.

The acceptance-test commit changed only `tests/test_workspace_storage.py`. Chromium (36 checks per OS) and PostgreSQL 16 verified-TLS/UI (5 TLS + 10 browser checks) had passed for the unchanged implementation SHA `1eb5284cf0ddc0ba6411324902efc4f4d8c917e9`: [Chromium [#43655575969](https://github.com/hibi89/DBVORA/actions/runs/43655575969)](https://github.com/hibi89/DBVORA/actions/runs/43655575969), [PG16 TLS/UI [#43655576024](https://github.com/hibi89/DBVORA/actions/runs/43655576024)](https://github.com/hibi89/DBVORA/actions/runs/43655576024). No PG credentials or non-synthetic databases were used.

## Limits retained

The watchdog case is a deterministic callback/injected-interruption test, not a measured 0.75-second production query; the exact-cap case checks the input boundary, not an actual 64 MiB file. No WAL/SHM physical-byte total, customer workload performance, owner device, or physical durability claim is made. Overall product completion remains **UNASSESSED / RELEASE HOLD**; OWNER_GATE items remain open.
