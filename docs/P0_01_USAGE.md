# P0-01: SQLite read-only schema inventory

Status: implemented in feature/p0-db-map; not the clickable UI MVP.
No customer databases were used; fixtures are generated in temporary folders.

## Local prerequisites and commands
- Python >=3.11 with SQLite table-valued PRAGMA support. Verified runtime: Python 3.13.5 / SQLite 3.46.1 / Linux.
- Test: python -m unittest discover -s tests -v
- Synthetic fixture: python -c "from pathlib import Path; from tests.fixtures.make_sqlite import create_fixture; create_fixture(Path('/tmp/dbvora-demo.sqlite'))"
- CLI: python -m dbvora inspect /tmp/dbvora-demo.sqlite
Use an equivalent absolute temporary path on Windows. Never commit the generated SQLite binary.

## Contract
inspect_sqlite(absolute_file_path) returns contract_version, db_id (24 hex path-derived characters), engine, size_bytes, size_scope, observed_at, provenance, tables[], relationships[].
Each table contains name, columns[], foreign_keys[], indexes[]. Column nullable_declared reflects catalog notnull declaration, not unconditional runtime nullability for rowid PK modes. Relationship evidence is exclusively declared_foreign_key; no speculative edges.
size_bytes measures main SQLite database file only (excludes WAL/SHM). CPU/RAM and trends are unavailable, not estimated.
Error output is safe JSON with stable code/message, CLI exit code 2.

## Security scope and limitations
- Explicit local absolute path; no scanning or automatic DB discovery.
- SQLite mode=ro plus PRAGMA query_only=ON; no row extraction or arbitrary user SQL interface.
- Reject symlinks, missing/invalid files; bounded number of metadata records.
- Concurrent/live WAL, sidecar writes, locked files, Windows and Python 3.11 not yet fully tested. Real/customer databases require prior owner approval.
- No API, network upload, scheduler, archive writing or compression.
- db_id is derived from local path; never treat it as an authorization secret.

## Evidence — 2026-10-26 KST
- python -m compileall -q dbvora tests: completed.
- python -m unittest discover -s tests -v: 16 PASS, 0 FAIL, 0 SKIP after fixing uninitialized zero-byte SQLite fixture.
- SHA-256 and mtime of synthetic file unchanged after inspection.
- All 12 code/test source Git blob hashes compared exactly between working copy and staged GitHub tree.
- NOT_TESTED: Windows, Python 3.11, live WAL/locked DB, customer DB, browser and GitHub CI.
