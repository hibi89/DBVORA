# DBVORA P1-PG02 — Mixed SQLite + PostgreSQL offline topology and CLI

**Date:** 2026-11-11 KST. **Source:** private `hibi89/DBVORA`, branch `feature/p0-db-map`; parent `121df3edad7c3ba04cf1cc24de625febedaa635f`.
**Security scope:** opt-in, **synthetic-only** local development preview. Never upload customer rows or credentials. Preserve all existing SQLite and archive CLI operations.

## Product design choices
- **A — selected:** normalize verified metadata already returned by the existing SQLite and optional PostgreSQL catalog readers into an offline, local, new-only HTML report, with an explicit single CLI. Uses stdlib and the existing fail-closed publisher; zero third-party browser or cloud dependencies. Existing UI untouched.
- **B — deferred:** modify existing local FastAPI and multi-SQLite workspace to introduce live PostgreSQL sources directly. Would change current customer-facing read boundaries and require real PostgreSQL auth/TLS, cross-engine provenance and Windows package compatibility. No unapproved rollout.

## Completed code and validation
1. `dbvora/multi_engine_report.py`: `assemble_workspace([sqlite_metadata, pg_metadata])`, `render_report`, and `export_report`. Accepts 1–8 explicitly supplied catalog dictionaries, total 2,000-table bound, 5 MiB report cap. Copies only schema names, column types, indexes, size/catalog evidence and declared same-engine FKs; never includes source DB path, DSN, SQL data rows, or unrelated dictionary fields. Cross-DB inferred FK count permanently zero. Escapes HTML/script terminators and renders schema names through DOM `textContent`. New-only OS-temp staged, fsync + hardlink archive publisher; output directory symlinks rejected. No automatic cleanup/delete.
2. `dbvora/mixed_cli.py`: `python -m dbvora.mixed_cli --sqlite /absolute/synthetic.sqlite --output-dir /absolute/report-dir --synthetic-only --accept-unencrypted-metadata`. Extra SQLite paths may be repeated, limited total eight. PostgreSQL is **not automatically contacted**: requires `--postgres-dsn-env DBVORA_TEST_DSN --allow-postgres-network` and the environment variable (no secret passed as CLI argument). The optional PG driver requires authorized test credentials and remains **not live-verified**. Duplicate SQLite inputs and output/source directory mixing fail closed.
3. `tests/test_multi_engine_report.py`: **18 PASS**, exact SHA `98d067d067d4e6af9fce1585896be91c4fcd3157`; `tests/test_mixed_cli.py`: **13 PASS**, SHA `b0eef4f8abb4e28e14b1df63d1f09d20818c576f`.
4. Source blobs exactly SHA-matched local tested copies: `multi_engine_report.py` `4b7c95d41fdc2e2933ffadd068a0e750a61ef189`; `mixed_cli.py` `0a51f06e60ddb74947c0393e409131cfd0482ec9`. Committed GitHub blob hashes independently confirmed.
5. Original-source Linux Python 3.13.5, `-W error::ResourceWarning`, **178/178 PASS**, 0 FAIL, 0 SKIP across 12 Python modules: existing ZIP/ZSTD + archive receipt + read-only SQLite, P3-05 request service, PG mock catalog and new mixed CLI/report. `compileall -q dbvora tests` PASS.
6. Chromium 144 `page.set_content` DOM integration on generated HTML, **9 conditions PASS**: 2 DBs/5 tables/2 within-DB FKs, node click/column/relationships/search, 0 JS errors and 0 outgoing network requests. Direct `file://` navigation was **blocked by environment policy** `ERR_BLOCKED_BY_ADMINISTRATOR`, so direct local file URL opening is **unverified**. First CSP meta warning caused by unsupported `frame-ancestors` directive was fixed (removed) and re-tested; CLI safe-code bug and output-directory symlink resolution were fixed then re-tested.

## Milestone-only completion model (engineering estimate; not a release certificate)
| Weighted category | Achieved | Maximum | Remaining |
|---|---:|---:|---|
| P0 SQLite/multi-engine schema topology & offline exploratory UI | 22 | 25 | Native file URL / full UI suite |
| P1 PostgreSQL metadata-only catalog & read-only boundary | 8 | 15 | Live read-only PostgreSQL role/TLS compatibility |
| P2 SQLite online snapshot / ZIP+ZSTD integrity & restore | 18 | 20 | Native filesystem power-loss guarantees |
| P3 persistent request reservation / replay fail-closed | 13 | 20 | Scheduling, incremental chain and crash restart proof |
| P4 local delivery CLI / packaging / native QA | 9 | 20 | Windows3.11 NTFS, installer, customer approval |
| **Total** | **70** | **100** | **30** |

**DBVORA 70% provisional engineering milestone** is a scoped *weighted technical assessment*, **NOT** full regression, enterprise security certification, Windows acceptance, customer-ready delivery, or 70% backup compression savings. **RELEASE HOLD**. Full repository Python gate floor was raised `429→460` and is **NOT RUN** on a complete checkout, GitHub Actions CI absent/not executed. Real PostgreSQL, Windows3.11 NTFS, browser `file://`, installed package and user data tests remain open.

## Follow-ups
Run `python -m scripts.verify_release_gate` (Python >=460 and Node TAP) against a complete authorized private checkout. Run actual offline HTML through native file URL on Windows+Chromium/Edge and verify no exceptions or network. Obtain explicit approval before accessing a live PostgreSQL DB or customer records, enabling paid CI, signing/publishing/installing or changing credentials/security. Keep existing main/develop/Production unchanged.

## Rollback / source provenance
Old feature HEAD `121df3edad7c3ba04cf1cc24de625febedaa635f` remains rollback point. No customer DB, existing archive, telemetry, external billing, permission or secret modified.
