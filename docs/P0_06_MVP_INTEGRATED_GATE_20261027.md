# DBVORA P0-06 — executable synthetic integrated MVP gate (2026-10-27 KST)

## Purpose and isolation
Added a real-code end-to-end **P0-only** acceptance command for the locally implemented multi-DB viewer, SQLite catalog inventory, user-declared cross-DB structural links, bounded dbstat allocation and manual measured-delta workflow. It is not a physical backup test, customer audit or Windows release sign-off.

Run from a full source checkout:
```
python -m scripts.mvp_offline_gate
python -W error::ResourceWarning -m unittest -q tests.test_mvp_offline_gate
```
The gate prints stable JSON and exits 0 on `PASS_SYNTHETIC_P0_ONLY` or 1 on `FAIL_CLOSED`. Public output has fixed check IDs, no customer path or SQL exception leakage. It intentionally reports `ready_for_customer_data=false`, `windows_file_browser_verified=false`, `windows_archive_durability_verified=false`, `full_release_gate_verified=false`.

## Actual acceptance checks
13 named checks use only temporary generated SQLite fixtures and the existing product modules (not a fake renderer): multi-DB inventory, scoped declared FK, an explicitly user-declared but **unverified** DB link, source SQLite file SHA unchanged across metadata inspection, no path/row content in output, metadata baseline write/read, two real measured timestamps with positive database size delta after synthetic inserts, bounded dbstat source label or honest unavailable, real integrated HTML SHA, no row content leak, embedded measured history, unique no-overwrite HTML names, and no-network CSP. Data fixtures and output files are deleted by the scoped OS temporary directory after execution.

This gate does NOT exercise the original `dbvora.demo_preview` single-DB HTML branch (it remains covered by its separate tests), native `file://` navigation, Python3.11 on Windows, installed packaging, Linux full release suite or NTFS archive durability.

## Execution actually observed
- Previous branch SHA `65b0293b98fddc9f2a8b271818aa1277fbbc62c6`, private `feature/p0-db-map`; actual local P0 source files (`storage_metrics`, `workspace`, `workspace_html`, `workspace_observations`) had Git SHA blob IDs matching current private feature versions. The developer container has a **partial reconstructed P0 mirror**, not the entire private repository.
- Python3.13.5 Linux, strict `ResourceWarning`: `python -W error::ResourceWarning -m unittest -q tests.test_mvp_offline_gate tests.test_workspace tests.test_workspace_registry tests.test_workspace_links tests.test_workspace_storage` -> **Ran 58 tests in 0.580s, OK**; an independent second run -> **58/58 PASS**. Old P0 components 50, new MVP gate tests 8.
- `python -m scripts.mvp_offline_gate` -> `PASS_SYNTHETIC_P0_ONLY` with `required_check_count=13` and `passed_check_count=13`, all named checks PASS, release/customer/native verification booleans all false. `compileall` for the new files PASS.
- Git blob identity confirmed for exactly tested modules `scripts/mvp_offline_gate.py=9ddbafb27f202131170b5828665a87c61e1f2e4e` and `tests/test_mvp_offline_gate.py=cd3b4657679ae07d640bf4aa57009994c90629f2`.
- We attempted authenticated source verification: GitHub connector accessible, but the isolated shell's direct `git ls-remote https://github.com/hibi89/DBVORA.git` failed DNS, so **full source checkout + release verification did NOT run**. Do not misreport the minimum 312 as 312 test results.

## Product progression and blockers
1. P0 visual demo, metadata inventory, manual declared cross-DB navigation, measured dbstat/two-observation history: feature implemented and real local targeted tests PASS; the 13-check P0 integration contract now executable independently by any authorized runner.
2. The global release gate requires the two new files and increases discovery minimum from 304 to **312**, plus Node TAP/real CLI/compile/FS preflight. **Full gate still not executed** on complete private source.
3. Windows Python3.11 and actual offline browser navigation, physical power-loss durability and archiving safety remain BLOCKED or UNVERIFIED. Do not alter production `safe_zip._sync_directory` or publish customer backups to make the gate green.
4. No real/customer DB, credentials, network submission, paid runner, original archive mutation, branch promotion, file removal, public release or unsafe filesystem flags were used.
