# DBVORA P0-03 multi-DB workspace inventory — 2026-10-27 KST

## Priority and design
The user requested accelerated **working MVP first → compare original plan → final compatibility/security/reliability checks**, without sacrificing original-file non-destructiveness. Compared A (simple read-only workspace aggregation over current SQLite inventory) versus B (immediate PostgreSQL/hosted DB aggregation and persistent credentials). **Selected A**: zero external API cost, fewer moving parts, reuses existing proven SQLite inspector and provenance fields, lower complexity and no customer-data access. B remains after baseline MVP.

## Changes committed to GitHub
- `dbvora/workspace.py` exposes `inspect_workspace(db_paths)` for **2 to 8 explicitly supplied SQLite paths**. It calls the existing read-only `inspect_sqlite`, returns stable DB IDs, labels Database 1...N rather than exposing file basenames, per-DB tables/columns/indexes, main-file-size metrics, FK evidence scoped to that DB, and a total of main DB file sizes. It does **not** infer or draw cross-database relationships and explicitly reports CPU/RAM unavailable.
- `tests/test_workspace_registry.py` adds **7** real synthetic SQLite fixture tests: FK grouping, size accounting, no sensitive row/path leakage, count limit, duplicate rejection, absent DB error, file-byte immutability, unresolved destination.
- The fail-closed combined release gate now requires source presence and `>=261` Python test cases. This number is a **discovery minimum**, not a pass claim. Gate decision fixtures updated.

## Actual executed evidence
- On Linux Python3.13.5 with temporary, source-reviewed clones of existing `inventory.py`, `sqlite_reader.py`, `metrics.py` and `errors.py`: **22/22 PASS** over new registry 7 tests + independently developed UI integration 15 tests, all with ResourceWarnings treated as errors. The original source of the 4 support files was read from GitHub, reconstructed locally, and basic SQLite output checked.
- A separate standalone `workspace_html.py` clickable offline HTML prototype was implemented **outside GitHub** during this work. Synthetic 2-DB demo generated real HTML with FK SVG and DB/table drilldown. Chromium `page.set_content` real browser **12 scoped checks PASS**, zero pageerrors, JS `node --check` PASS. A screenshot was inspected. **Actual `file://` navigation, Windows Python3.11 and the current whole private checkout remain unverified**.
- Separate developer source ZIP `DBVORA_P0_multidb_source_20261027.zip` (9,128 B) in the conversation working artifacts contains `dbvora/workspace.py`, `dbvora/workspace_html.py`, and `tests/test_workspace.py`. **HTML prototype and its 15-test file are not committed to GitHub in this commit**. Do not claim production UI is updated or that ZIP is a customer release; its local absolute path is transient.

## Exact repository scope and safety
- Repository private `hibi89/DBVORA`, only `feature/p0-db-map` changed; parent before work `7dec734172b7ef0c9f6dc7888f8a75ba34d6c741`. Main/develop baseline untouched.
- No real/user/customer DB queried; generated files live in OS-managed temp folders. No credentials, paid CI, cloud API, remote deployment, or archive pipeline changes. Existing Windows backup fail-closed code unchanged; native NTFS previous owner 15/15 remains independent.
- The original MVP screenshot browser was `set_content` rather than real file navigation; no customer or hardware proof.

## Next action
1. Integrate the tested `workspace_html.py` prototype and its 15 tests from the *existing source ZIP / working container*, matching exact local Git hashes `c9dce06791661b87a0fc5c35fab5ffcbc52c1a56` and `b96144c887220a274ce5d2178b550e6ae97ef913`. Ensure module imports the committed workspace logic and perform re-run. Do not re-implement from scratch or repeat failing ZIP transport strategies.
2. Run full checkout release gate, real offline file navigation where platform allows, and Windows Python3.11 native checks later. Keep back-end reliability/security validation mandatory before customer use.
3. Once a usable P0 offline multi-DB map has genuine integrated acceptance, compare further original requirements: DB process resource observation with correct provenance, stored observations/trends, secure connectors, compression and recovery. No unsupported metrics claims.

## P0-03 HTML integration completed on feature branch (2026-10-27 KST)
- Added **exact tested** `dbvora/workspace_html.py` (Git blob `0df3fd2a91781875ebff93a0df78e5660caa354e`) and `tests/test_workspace.py` (Git blob `b96144c887220a274ce5d2178b550e6ae97ef913`). The exporter is offline-only Python stdlib with Base64 metadata embedded into a CSP-constrained HTML page, DOM textContent-based labels, per-database selection, table-column/index detail and declared FK SVG links. No inferred cross-DB connections or row content.
- CLI: `python -m dbvora.workspace_html --synthetic-only --out /absolute/existing/folder`; generates 2 temporary fixture DBs and only retains uniquely named `dbvora-workspace-UUID.html`. Alternate explicitly chosen `--db /abs/a.sqlite --db /abs/b.sqlite --out ...` available for **synthetic/authorized fixtures only**, never automatically searches actual customer files.
- Local Linux Python3.13.5 targeted **22/22 PASS**, combining previously committed 7 registry tests and new exact-source 15 HTML integration tests (strict ResourceWarning). Real Chromium `page.set_content` **12/12 scoped DOM/interaction assertions PASS**, zero JS page errors, Node JS `--check` PASS. This is real browser DOM but not file:// navigation. Source hash matches commit blobs for both files.
- Fail-closed checked: duplicate DBs, invalid count, missing files, impossible FK target, hostile SQL table identifier `</script>...` not injected into HTML/JS, path/row content withheld, output uniqueness and SHA, relative/symlink output rejection on Linux.
- Whole private repository **>=276 Python case** acceptance and Python3.11/Windows actual file:// UX NOT RUN. Original Windows durable archive/ZIP/ZSTD backend remains separate and blocked for customer use. Do not equate synthetic read-only P0 MVP with complete DBVORA product.
