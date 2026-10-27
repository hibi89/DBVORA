# P0-05: bounded SQLite dbstat and timestamped growth evidence — 2026-10-27 KST

## Scope and original requirement
- Original owner request: per-DB/table sizes and resource usage/growth, without fabricated CPU/RAM, keeping MVP-first. This milestone adds **logical allocated SQLite btree pages**, including index btrees, and explicitly opt-in **two-time-point deltas**. Neither is SQL row payload size nor exact customer disk usage. DB main-file size remains a separate measured filesystem stat, explicitly excluding WAL/SHM.
- Read-only SQLite source: `dbvora/storage_metrics.py` calls a fixed `sqlite_schema` query and `dbstat` aggregation; never builds SQL from identifiers, runs table-row queries, creates a virtual table, installs an extension, attaches another DB, or writes source DBs. Only catalogs-owned table and index btree names are summed per table.
- Cap scans at **64 MiB main DB file** and **0.75 second watchdog**. Unavailable extension/scan timeout/large file yields `status=unavailable`; it must never be represented as 0 bytes or estimated.
- Virtual-table shadow storage may not be wholly attributed. Index pages are included in table measurement. Logical dbstat scan may account for pages in live WAL while main-size stat excludes WAL/SHM. This is disclosed in HTML.
- Scoped Python modules `dbvora/workspace_observations.py` compare repeated metadata-only snapshots by stable path-derived DB ID (ID is a 24-hex digest, **not source pathname**), table name, UTC observation time, main-file scope. No forecast inferred from only two snapshots, and missing or out-of-order baseline is explicitly unavailable.
- Optional `--save-observation` writes new **metadata-only** unique JSON using exclusive create in existing absolute output directory; local JSON contains identifiers/table schema *names* but not original paths or rows. Maximum 512KiB. `--baseline-file` reads only explicit absolute regular non-symlink JSON, validates shape, duplicate IDs, integer size and timestamps. Customer authorization still required for real source, feature not certified.
- No scheduled scanning, OS process/CPU/RAM readings, cloud, network, DB data transfer or automatic pruning. Windows archive publish logic untouched and still fail-closed.

## Demo CLI for synthetic/test files only
First observation:
```sh
python -m dbvora.workspace_html --db /absolute/synthetic-A.sqlite --db /absolute/synthetic-B.sqlite --out /absolute/existing-output --save-observation
```
The returned `observation_filename` is the local filename to preserve. Later, if actual synthetic fixture bytes change, run:
```sh
python -m dbvora.workspace_html --db /absolute/synthetic-A.sqlite --db /absolute/synthetic-B.sqlite --out /absolute/existing-output --baseline-file /absolute/existing-output/dbvora-observation-EXACT_ID.json --save-observation
```
No baseline implies `Δ unavailable`; two valid observations imply signed measured differences. A zero delta is not proof of no row changes (e.g. SQLite may reuse allocated pages). Negative difference is allowed (e.g. VACUUM). WAL absent from main-file size; never claim SQL row size or exact file allocation.

## Verification completed in this development container
- Source mirrors of exact current GitHub `dbvora/workspace.py`, `workspace_html.py` independently validated via `git hash-object` before modifications. Existing local read-only inventory is a functional mirror of GitHub, not a complete private repository clone.
- Real Linux Python3.13.5 synthetic SQLite: `python -W error::ResourceWarning -m unittest -q tests.test_workspace tests.test_workspace_registry tests.test_workspace_links tests.test_workspace_storage` — **50/50 PASS**; previous 36 + **14 new tests**. Includes real dbstat+index bytes, actual SQLite inserts increasing file/allocated page delta, save/load baseline, nonincreasing/missing baseline, malicious/oversized/symlink JSON, unmeasurable dbstat, no customer path or row sentinel leak, existing cross-DB regressions.
- Real Chromium (Linux) `page.set_content`: DB Δ/table Δ visible, click declared cross DB link and details, no JS page errors — **PASS**. Independent generated self-contained synthetic HTML with `--baseline`/save in temp directory. **file:// navigation remains blocked by managed Chromium policy**, NOT TESTED. No Windows Python3.11 run of this P0-05 feature.
- Local sources Git blobs: `storage_metrics.py=f2f1b18f926610495459b879480ec0f8f3182552`; `workspace_observations.py=a4cb7eebea2f67dd1ef76b18966db92ae570aeab`; `workspace.py=d941e954d59b70375cbcbe8dc8f06c434ae3e557`; `workspace_html.py=0aabb3125be54dd412a3848448a8d0bf6e0911f3`; `tests/test_workspace_storage.py=6b4dcee7ee50a5b9673f1d81e3683687d5907212`. All new/modified blobs were uploaded exactly and SHA-checked.
- Full product **>=304** Python release gate and Node/CLI/full archive tests **NOT RUN** in this turn. This threshold increases the required discovery count from 290 by 14; it is not a pass claim. Customer release, native Windows backup durability, source/renderer authentication, browser `file://`, and Windows installer remain BLOCKED or NOT_TESTED.

## Risk/dependency and next unit
- Complete native Python3.11 and Windows/offline-browser verification and full release gate are still needed; do not make real customer DB or release claims.
- Next original-design gap: bounded repeat observations for sizes without automatic scheduling/deletion and explicit UI of missing dbstat; or move into archiving recovery safety only after MVP full checkout validation.
- No original `safe_zip.py`/ZSTD/receipts/CLI patch, no credentials/remote upload, no paid GitHub Actions, no branch promotion or data destructive action.
