# P0-04 explicit cross-database links — synthetic evidence (2026-10-27 KST)

## Purpose / boundaries
DBVORA P0-03 already reads 2–8 explicitly selected SQLite files into one metadata-only clickable offline map. Existing SQLite foreign keys are only valid within their own database. P0-04 implements an **explicit operator-supplied cross-DB structural assertion**, NEVER an inferred join, certified FK, or proof that row values match.

## Source changes
- `dbvora/workspace_links.py`: verify each declaration has exactly `from_db/from_table/from_column/to_db/to_table/to_column` (indices 1-based, max 64); verify referenced tables+columns exist, no duplicates/self links. Emit path-free labeled pair, `evidence=user_declared_unverified`, `verified=false`. Keep `cross_database_edges_verified=0`.
- `dbvora/workspace.py`: optional `declared_links`; no-links behavior preserved; call only existing read-only SQLite inventory.
- `dbvora/workspace_html.py`: separate cross-DB list; link click selects target DB and target table in details. Uses DOM `textContent`, not HTML injection; synthetic two-DB demo now includes declared link `products.id -> invoices.product_id`. Optional local `--links-file` for explicit --db mode; absolute UTF-8 JSON list <= 16 KiB, symlink/relative/malformed refused. No network or implicit source path scans.
- `tests/test_workspace_links.py`: 14 new real SQLite fixture cases on positive/negative declarations, duplicates, bad columns, 64 limit, source file preservation, manifest checks, CLI errors, HTML and synthetic demo.

## Verification — actual
- Linux Python 3.13.5, exact-local-source `PYTHONDONTWRITEBYTECODE=1 python -W error::ResourceWarning -m unittest -q tests.test_workspace tests.test_workspace_registry tests.test_workspace_links` -> **36/36 PASS** (prior 22 + new 14).
- Python compileall on changed modules -> PASS.
- Real Chromium Playwright `page.set_content`: **9/9 checks PASS**, zero JS pageerrors. Included DB count=2, exactly one declaration, visible unverified label, target database selection, table `invoices` selection and `product_id` column details.
- Genuine `file://` page navigation returned `net::ERR_BLOCKED_BY_ADMINISTRATOR`; this environment prevents testing the file URL. Does not establish a product regression or file:// PASS.
- Four new/changed source blobs: `workspace.py=acbc28ba5abba79eb19a97f1d6711bd3661a7231`, `workspace_links.py=4ed95bd0adc82ffc32cddc6029bc74e52b475a38`, `workspace_html.py=40ffd86f7e0e6b3703857646db191e89b4d661b0`, `test_workspace_links.py=d0383a8fb9e282f678a61f6d0a969847c4566c08`. GitHub SHA1 equality checked before update.

## Not verified / safety
Entire 290-case regression, real Windows P0-04 browser, real customer databases, NTFS ZIP/ZSTD production archive publish, sudden power loss, Windows installer NOT VERIFIED. Prior owner Windows isolated NTFS publisher 15/15 remains a separate earlier proof; do not conflate.
No modification to existing archive backend, original data, published service, main/develop, permissions, tokens, financial services or external transfers.

## Synthetic demo / optional metadata manifest
```powershell
py -3.11 -B -m dbvora.workspace_html --synthetic-only --out "E:\DBVORA_GIT"
```
Manifest example (with **authorized**, separately specified databases and existing matching column names only):
```json
[{"from_db":1,"from_table":"products","from_column":"id","to_db":2,"to_table":"invoices","to_column":"product_id"}]
```
CLI: `python -m dbvora.workspace_html --db ABS_DB_ONE --db ABS_DB_TWO --links-file ABS_LINKS_JSON --out ABS_EXISTING_FOLDER`. Manifest contains schema identifiers, so treat as private metadata; no actual customer records or database access permitted at this test stage.
Next prioritize full authorized checkout and measured table size/trends (with measurement provenance) over premature production archive activation.

## Git anchor
Private `hibi89/DBVORA`, `feature/p0-db-map`, reviewed parent `e55ad70d9be33991606d3381c8959a642690cbf2`; final SHA must be verified after commit. Vercel/Production N/A.
