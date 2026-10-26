# DBVORA next unfinished unit — P0-02

Recovery trigger: [디비보라 깃헙보고 작업해]. Command ㄱ advances the next safe unit. Always compare GitHub HEAD, code and tests before repeating work.

## Finished P0-01
- Python read-only SQLite metadata inventory: tables, columns, key positions, declared nullability, FK, indexes and declared relationships.
- Stable JSON contract, path-derived DB ID, main database file size, UTC observation time, metric provenance and explicitly unavailable resource metrics.
- Three-table synthetic fixture and 16 unittest cases including path rejection, read-only mutation failure, original file hash+mtime preservation, unusual identifiers, CLI error hygiene.
- Linux Python 3.13.5 / SQLite 3.46.1: 16/16 PASS. Python 3.11, Windows, live WAL and browser untested.
- Source/tests on feature/p0-db-map. Verify remote branch head SHA before further changes.
- Run test: python -m unittest discover -s tests -v
- CLI: python -m dbvora inspect ABSOLUTE_SYNTHETIC_SQLITE_PATH

## P0-02 next target
1. Add minimal FastAPI server bound to 127.0.0.1 with explicit synthetic DB selection and no home scanning.
2. Localhost-only inventory JSON endpoint; validate Host/Origin; disallow permissive CORS, arbitrary SQL and remote telemetry.
3. Static HTML/JS/SVG clickable map: DB → tables → columns; visualized declared FK edges; measured file bytes and unavailable resources.
4. UI tests: XSS-escaping special SQLite identifier names, safe endpoint failures, empty DB; HTTP smoke test. Browser check if available, else mark NOT_TESTED.
5. Update STATUS/HANDOFF/NEXT_TASK, check GitHub SHA; PR to develop after passing tests if appropriate.
6. Do not start customer DB access or compression/restore without the required gates.

## Acceptance
HTTP/UI returns only schema metadata, no rows/secrets/absolute paths. Clicking a table reveals columns/indexes/FKs. No invented edges or false resource measurements. Synthetic DB hash/mtime unchanged. Tests executed and GitHub remote SHA verified.

Later: validated consistent snapshot → ZIP/ZSTD benchmark → isolated restore → retention/incremental with safety and Windows tests.
