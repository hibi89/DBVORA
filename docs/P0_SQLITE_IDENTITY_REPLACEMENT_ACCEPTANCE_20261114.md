# P0 SQLite same-size / same-mtime replacement safety — 2026-11-14 KST

## Decision and scope
- Goal: R01 local read-only SQLite schema result must not silently certify a file swapped during inventory with the original byte length and mtime.
- A: duplicate source SQLite into a scratch snapshot before scanning (requires storage, increases copies of sensitive data, adds I/O and source snapshot lifecycle).
- B: compare local main-file device, file ID, ctime and existing size/mtime around the schema scan; reject a changed or non-regular final path with the existing safe `CHANGED_DURING_READ` error. B selected for zero extra backup files, no API contract change and small maintenance cost.
- Source changed: `dbvora/inventory.py`, `dbvora/metrics.py`; new disposable fixture tests in `tests/test_inventory.py`. No changes to customer DB writer, archive, API endpoints, browser UI, GitHub settings or third-party services.
- Detects path replacement and symlink-at-end in common POSIX/NTFS stat conditions; this is NOT an atomic snapshot of SQLite/WAL or a proof against every filesystem race. The operator may retry once the DB is stable.

## Exact verified functional commit
- `hibi89/DBVORA@feature/p0-db-map`: [`f687d93def8465c355e192486f0d2af7ff64bc0a`](https://github.com/hibi89/DBVORA/commit/f687d93def8465c355e192486f0d2af7ff64bc0a).
- [Whole release Windows2025 + Ubuntu24.04 #43591183883](https://github.com/hibi89/DBVORA/actions/runs/43591183883): **2/2 SUCCESS**, 716 Python discovered, Linux 716 PASS/0 FAIL/0 SKIP; Windows 715 PASS/0 FAIL/1 named POSIX-only SKIP; mandatory 12/12 steps each OS, Node DOM PASS.
- [Real Chromium synthetic localhost #43591183881](https://github.com/hibi89/DBVORA/actions/runs/43591183881): **2/2 SUCCESS**; 22/22 real browser checks on Windows/Ubuntu, temporary SQLite 1,000 tables/997 FK, 24 refresh cycles with 4 injected browser disconnects, source hash/mtime invariant. This browser job exercises existing UI/API and is a regression, not real customer-system acceptance.
- [Unsigned owner ZIP #43591183876](https://github.com/hibi89/DBVORA/actions/runs/43591183876) SUCCESS; [unsigned Windows synthetic demo #43591183841](https://github.com/hibi89/DBVORA/actions/runs/43591183841) SUCCESS; [blueprint evidence #43591184100](https://github.com/hibi89/DBVORA/actions/runs/43591184100) SUCCESS. None implies signed commercial release.

## New regression behavior
1. Replace test-owned SQLite with byte-identical different physical file, restoring original size/mtime; standalone observation rejects with `CHANGED_DURING_READ`.
2. Inject same-size/mtime physical replacement after real read-only schema inspection, before the last validation; full inventory raises the same safe path-free error and does not return stale observations.
3. The two tests are part of the all-OS Python total 714 → 716; no real customer data was used. The synthetic replacement is owned by the test, not caused by product runtime.

## Accepted / not accepted
- Accepted: synthetic same-size/mtime file replacement detection, Linux+Windows test and full regression, browser unaffected, no original-write path or disk copy.
- Not verified: real buyer Win10/11 environment, customer's DB or WAL concurrency semantics, physical power interruption, unusual filesystems without stable file IDs/ctime, commercial LICENSE/NOTICE, final weighted R01–R07 owner signoff. Do not claim complete protection against every TOCTOU race.
- Official completion `UNASSESSED`; historical technical95 only; `[작업중]`, `RELEASE HOLD`, Kmong registered0; local installed product, Vercel/Production N/A.
