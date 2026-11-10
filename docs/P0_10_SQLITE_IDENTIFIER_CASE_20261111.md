# DBVORA P0-10 — SQLite FK target casing correction (2026-11-11 KST)

## Reproduced defect
SQLite compares ASCII identifiers case-insensitively. In a real local SQLite fixture, a table named Parent and a foreign key referencing PARENT are the same target. The old workspace code used case-sensitive Python set membership and incorrectly reported target_in_inventory=false. Unicode identifier matching is not generally case-insensitive, so indiscriminate Python casefold would create false relationship claims.

## Compared approaches and choice
A: transform ASCII A-Z to a-z strictly for metadata comparison, preserving original names. Zero dependencies, O(tables + FK edges), aligns with SQLite. **Selected**.
B: Unicode lower/casefold across all names. Similar cost but misleading for distinct non-ASCII SQLite identifiers; rejected.

## Actual changes
- dbvora/sqlite_identifiers.py: ASCII-only catalog key, rejects non-string input; no SQL rewriting or data access.
- dbvora/workspace.py: use catalog key for FK target presence instead of raw exact string equality.
- tests/test_sqlite_identifiers.py: 6 real SQLite/edge unit cases including Unicode distinction.
- tests/test_workspace_registry.py: 2 real multi-database topology integration cases in the repository.
- scripts/verify_release_gate.py: required file membership and Python discovery minimum **347 -> 355** (6+2 new tests); mocked gate test fixtures updated.

## Executed evidence
- Local Linux Python3.13.5, SQLite3.46.1; exact new code blob **f43796a6d3a346aba409d7e937efb178c45af742** and test blob **53149f54068095d7e9db524e69294ac5c772f04d** matched local hash-object.
- Actual in-memory SQLite 6 new tests + 9 prior schema review + 7 prior publication cleanup = **22/22 PASS, 0 FAIL, 0 SKIP**, strict ResourceWarning policy. Initial fixture resource warning fixed with contextlib.closing before last successful run.
- Added full-source registry 2 tests **NOT RUN** in this runtime, because private full checkout blocked by DNS. Entire >=355 Python/Node/ZIP/ZSTD/receipt gate, native Windows Python3.11, real browser/file URL and power-loss/customer data **NOT RUN**. No paid GitHub Actions used.
- Implementation Git commit **a8169a969db919f336a2fc68343a63f291513960**. Private feature only. main/develop/archives/credentials/Production unchanged. No new permission, external data transfer or purchase.

## Completion boundary and next gate
The P0-10 fix is not a customer release or full product integration proof. DBVORA final completeness **55% unchanged**, target **70%**, RELEASE HOLD.

Next, in an authorized full checkout, run:
- python -B -m unittest -v tests.test_sqlite_identifiers tests.test_workspace_registry tests.test_schema_review tests.test_schema_review_ui tests.test_publication_cleanup tests.test_workspace_publication
- python -m scripts.verify_release_gate

Then perform Windows native and actual HTML UX validation. Rollback by normal revert of implementation commit; no forced Git history.
