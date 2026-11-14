# R01-07 — asynchronous database/table state isolation

Date: 2026-11-15 KST  
Repository/branch: hibi89/DBVORA / feature/p0-db-map  
Final source/test SHA: 6913bcbf68ef2133e9cc7f9ad8090efae1bd5fda  
UI implementation SHA: 156d87c5c4d4b07b21cbb9cf7ce5fb551baf92f1  
Scoped status: PASS_SCOPED

## Change

- Added a bounded, in-memory filter map keyed by each configured SQLite database identity. Switching databases restores that database's filter; an unvisited database starts with an empty filter. Refresh preserves the selected database, selected table and its filter. Removed database identities are pruned from the map.
- Kept the existing opt-in SQLite dbstat measurement behavior: changing the database or selected table aborts the previous request. A late success or transport failure from an aborted A→B request is ignored and cannot update B's inspector.
- Added actual localhost Chromium checks comparing selected database identity to API data for the displayed main-file size and selected table. Checks cover delayed successful response, rejected stale failure, same-database table switch, per-database filters, and refresh preservation.
- Filtered graph edges remain hidden when one endpoint table is filtered out.

## Exact-SHA Actions

- Full offline release gate [#43653187661](https://github.com/hibi89/DBVORA/actions/runs/43653187661), final SHA 6913bcbf68ef2133e9cc7f9ad8090efae1bd5fda: PASS. Ubuntu 791/791, 0 skips. Windows 791 discovered; 790 PASS plus one named POSIX-only skip: `test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`.
- Actual Chromium localhost acceptance [#43653187677](https://github.com/hibi89/DBVORA/actions/runs/43653187677), final SHA 6913bcbf68ef2133e9cc7f9ad8090efae1bd5fda: PASS on Ubuntu and Windows, 35/35 checks each. New named checks: `multi_delayed_storage_success_failure_isolated`, `multi_selected_database_size_and_filter_scope`, and existing table/database switch, refresh, mobile checks.
- PostgreSQL 16 TLS/UI [#43653187670](https://github.com/hibi89/DBVORA/actions/runs/43653187670), final SHA 6913bcbf68ef2133e9cc7f9ad8090efae1bd5fda: PASS; verified-TLS/read-only TLS acceptance 5 checks and browser acceptance 9 checks.
- Blueprint evidence gate [#43653187930](https://github.com/hibi89/DBVORA/actions/runs/43653187930), final SHA 6913bcbf68ef2133e9cc7f9ad8090efae1bd5fda: PASS.
- The implementation SHA 156d87c5c4d4b07b21cbb9cf7ce5fb551baf92f1 also passed offline release gate [#43652365880](https://github.com/hibi89/DBVORA/actions/runs/43652365880) and PostgreSQL TLS/UI [#43652365851](https://github.com/hibi89/DBVORA/actions/runs/43652365851).
- Source ZIP workflow [#43652365827](https://github.com/hibi89/DBVORA/actions/runs/43652365827), implementation SHA 156d87c5c4d4b07b21cbb9cf7ce5fb551baf92f1: PASS, 75 files, ZIP SHA-256 `4a7b248131ef48c9dc3de3cc3d80bdd8fcfc83cff2199fac407a2ec40a2b9669`; artifact 14136682194 digest `sha256:d64a46cbbd4c58a9f72cd71f5033751d70989684100dd2e1cecadd60e52f18f0`.
- Windows demo EXE [#43652365854](https://github.com/hibi89/DBVORA/actions/runs/43652365854), implementation SHA 156d87c5c4d4b07b21cbb9cf7ce5fb551baf92f1: PASS, executable SHA-256 `828c3a5723ba1c851c777652da78380e39ebf962731ae072bc146eae7db114a4`; artifact 14136223667 digest `sha256:cedfa94b25f951556bd4de18f07b823b9ab0e48c2d954c7bddaf919f2542a332`.
- Synthetic Chromium screenshots at final SHA: Ubuntu artifact 14136802170 digest `sha256:e358853a24ae1743e4bb6b945488daa05431adea98e999c695167a7bd4d9a134`; Windows artifact 14136896738 digest `sha256:18e3b333fdea8673d8e97bf82cd17040b428df6e00cfbd13bc9b68f4ee6a2e2b`.

## Failure history and correction

- Initial final-browser attempt [#43652365838](https://github.com/hibi89/DBVORA/actions/runs/43652365838) failed the combined `MULTI_RACE_SWITCH_PRECONDITION`. That combined assertion did not report which subcondition differed. In the next test revision, the checks were separated and the expected size uses the app's own formatter while inspector scope is compared to the API catalog. Those scoped checks passed on the final run.
- Browser attempt [#43652979947](https://github.com/hibi89/DBVORA/actions/runs/43652979947) reached the DB-filter restoration check and failed `MULTI_SWITCH_BACK_FAILED`: the test expected one FK edge with the `ORDERS` filter even though the `customers` endpoint was hidden. The expected edge count was corrected to zero because filtered-out endpoints are deliberately not drawn.
- Intermediate full gate [#43652979859](https://github.com/hibi89/DBVORA/actions/runs/43652979859) and PostgreSQL TLS/UI [#43652979855](https://github.com/hibi89/DBVORA/actions/runs/43652979855) passed before the final browser expectation correction. Final SHA results above supersede the intermediate runs.

## Limits and release status

All browser/API fixtures use two synthetic SQLite databases; PostgreSQL checks use the ephemeral synthetic PostgreSQL 16 read-only TLS service. No customer data, user PC, external network, physical power-loss test, publisher signature, owner-device or legal/commercial acceptance was involved. Packaging artifacts are unsigned and correspond to the unchanged application-code SHA 156d87c5c4d4b07b21cbb9cf7ce5fb551baf92f1; the final SHA follow-ups changed only browser regression assertions.

Official overall completion remains UNASSESSED / RELEASE HOLD. OWNER_GATE stays open.

