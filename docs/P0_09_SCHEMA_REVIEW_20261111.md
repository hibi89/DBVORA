# P0-09 — DBVORA offline SQLite schema review (2026-11-11 KST)

## Scope and alternatives
The end-user requirement is safe inspection of an explicitly selected SQLite workspace. Two choices were weighed:
- **A (selected):** run a bounded catalog-only, advisory validator on the already-inspected workspace in memory. Zero network, no DB row SQL, no new dependency, predictable CPU cost and reusable metadata contract.
- **B (rejected for this phase):** actively profile customer table rows or open a live PostgreSQL connection. Greater potential insight but additional permissions, privacy exposure, runtime cost and inconsistent availability.

## Code and user-visible behavior
- `dbvora/schema_review.py` is a pure metadata review; input contract `p0-03.workspace.v1`, max 8 DB / 2,000 tables / 8,000 FK relationship descriptions / 200 listed findings. It reports counts beyond 200 as truncated rather than silently reporting completeness.
- Advisory codes: `NO_DECLARED_PRIMARY_KEY` (not necessarily an error); `FK_TARGET_OUTSIDE_INVENTORY` (declared target absent in inspected scope); `FK_INDEX_REVIEW` (declared FK columns do not appear as a leading key of a non-partial index or declared PK). These are **not** guaranteed query-performance or correctness diagnoses.
- `dbvora/workspace_html.py` adds a read-only Schema review panel to the existing offline HTML. Dynamic labels are inserted via DOM `textContent`, never HTML interpolation. The panel explicitly says review only. An audit parser limit/invalid result maps to `UNAVAILABLE` without blocking the previously supported workspace export.
- No row values, paths, secrets, SQL execution based on identifiers, external telemetry, input DB mutation, automatic index creation, archive code or customer permission changes. Normal multi-DB preview remains in its existing source branch.
- `scripts/verify_release_gate.py` requires both new source/tests and the HTML integration tests; expected minimum discovered Python tests **336 -> 347**.

## Evidence
- Tested **exact Git blob** Python module `25d671c6f02aa4500b26032542d75a89f204c65b` with new test module `7a76c2af2b43ed543d55ffa314f76a780422d67f`, both local hash matches the created GitHub blobs.
- Linux container Python3: nine new SQLite PRAGMA-backed, in-memory test cases **9/9 PASS**, 0 FAIL/0 SKIP. Previous generated-file cleanup tests **7/7 PASS** using exact Git blob sources. Local `python -m compileall` PASS on these isolated files, JS schema-review rendering snippet `node --check` PASS. Those results do **not** prove the full existing HTML module or any full checkout regression.
- Two new full-source SQLite HTML embedding tests are committed but **NOT RUN** (private full checkout cannot be obtained in this container); full >=347 unittest/Node TAP release gate, Windows Python3.11, actual browser file navigation, customer DB and power-cut safety remain **UNVERIFIED**.
- No Actions billed or triggered. `main`, `develop`, public repository, customer data and production are unchanged.

## Execution gates and acceptance
1. On an authorized complete private `feature/p0-db-map` checkout run `python -B -m unittest -v tests.test_schema_review tests.test_schema_review_ui tests.test_publication_cleanup tests.test_workspace_publication`; collect pass/fail/skip and source SHA.
2. Run `python -m scripts.verify_release_gate` and inspect expected >=347 Python tests, Node TAP, real ZIP/restore/receipt and local temporary filesystem; resolve exact failing assertions without disabling data-loss safeguards.
3. Run owner Windows3.11 source-backed demo and offline HTML browser only after native environment available. Never claim per-row profiling, power-loss durability, or performance improvement from a catalog warning.
4. Commercial product completion remains **55% provisional**, unchanged until the complete feature and integration evidence is available; target 70% not yet met. Release HOLD.

Rollback: revert this bounded P0-09 feature commit normally; previous P0-08 cleanup and archive paths remain independent.
