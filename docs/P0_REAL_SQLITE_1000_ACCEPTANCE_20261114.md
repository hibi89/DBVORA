# DBVORA P0 — Real synthetic SQLite 1000/1001-limit API + browser acceptance

2026-11-14 KST · source `a0d710127cbc4e606c188f1b7328c6a3fedb9d0b`, branch `hibi89/DBVORA@feature/p0-db-map`.

## Design / trade-offs
Option A was to rely on previous client-only injected 1000-table JSON UI tests: fastest, cheapest, but proves nothing about physical SQLite schema parsing, FK metadata, server serialization, payload limits or HTTP error handling.
Option B was to generate a **temporary synthetic 1000-table SQLite file**, have the existing read-only FastAPI app inspect that actual file over localhost, render in Chromium, then verify 1001 is refused and 1000 restores. Option B chosen: higher test runtime/CI CPU but no new subscription, dependencies, customer access or production API code changes. Both methods' evidence retained and clearly separated.

## Files
- `tests/fixtures/large_sqlite.py`: test-only, allows targets 1000 or 1001, requires existing fixture sentinel `NOT_FOR_SCHEMA_OUTPUT`, refuses missing/non-fixture and opens SQLite via `mode=rw` to prevent silent new DB creation. Generated identifiers only; each new table has a declared parent FK.
- `tests/test_large_sqlite_catalog.py`: Python unit/HTTP contract tests for 1000 accepted with exact metadata and unchanged file hash/mtime, 1001 returns JSON code `CATALOG_LIMIT` HTTP422 without sensitive data/path, and removing just the synthetic extra restores HTTP200.
- `scripts/browser_http_e2e.py`: after existing 3-table/4-table XSS checks and client-only 1000 test, grow the **same disposable fixture** to 1000 and verify HTTP200 (634619B, 997 declared FKs), then browser 1000 cards+997 paths/name filter/keyboard Enter/pressed state/zero matches/reset. At 1001, API 422 and visible UI error. Remove just the last generated test table to recover 1000 and hide error. Test-owned DB source SHA/mtime unchanged during all reads. Existing origin/host/non-GET guard tests preserved.

## Exact results
- [Full offline gate #43573784544](https://github.com/hibi89/DBVORA/actions/runs/43573784544): Ubuntu24.04 Python3.11 **710PASS/0FAIL/0SKIP**, Win2025 **709PASS/0FAIL/1 named POSIX-only SKIP**; 710 discovered each, 12/12 mandatory stages each, Node UI DOM PASS; whole run 2/2 SUCCESS.
- [Real Chromium localhost #43573784521](https://github.com/hibi89/DBVORA/actions/runs/43573784521): Ubuntu/Windows both **14/14 checks PASS** including four newly added real-catalog steps. In addition to previous client-only 1000, now the server actually read **1000 SQLite tables, 997 FK**, returned JSON634619B; verified 1001 fails closed, recovery succeeds.
- Single-run CI metrics: Linux API 73.738ms, browser-ready 193.518ms; Win API 156ms, browser-ready 250ms. These metrics are neither SLAs nor evidence of real customer hardware.
- Production code and user database/backups not changed; only test-side Python scripts/fixture used.

## Unverified (not launch certified)
Real customer database/consent, owner Windows10 or Windows11 system, sustained 1000-table refresh/stress, physical power-loss/different filesystems, signature and third-party licensing/NOTICE, user final approved weighted 100-point acceptance, commercial release and Kmong registration. Official **UNASSESSED** (historical internal95 only), `[작업중]` and RELEASE HOLD preserved, actual registration0, Vercel/Production not applicable.
