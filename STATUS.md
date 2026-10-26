# DBVORA STATUS — P0-01 feature branch

Updated: 2026-10-26 KST. Repository: hibi89/DBVORA, Private. Branch: feature/p0-db-map. Main/develop original HEAD: 890f842e3ba0e13c901e785633bdd06eadc76cce. New feature HEAD must be verified after commit and is not embedded in this self-referential file.

| Item | State | Evidence |
| --- | --- | --- |
| Repository, branches and planning docs | VERIFIED | GitHub remote inspected |
| P0-01 SQLite read-only schema extraction | TESTED_LOCAL | Linux Python 3.13.5 SQLite 3.46.1; 16 PASS / 0 FAIL / 0 SKIP |
| JSON catalog, measured file bytes, declared FK | TESTED_LOCAL | synthetic customers/orders/events |
| Synthetic source preserved | TESTED_LOCAL | SHA256+mtime unchanged; INSERT via readonly connection failed |
| GitHub source | STAGED_LOCAL_TEST_MATCHED | 12 source/test Git blob hashes match staged tree; confirm remote ref after commit |
| P0-02 localhost API and clickable SVG UI | NOT_STARTED | next work |
| Compression, restore, archive scheduler | NOT_STARTED | no archive created |
| Python 3.11, Windows, WAL/locks, customer DB | NOT_TESTED | no live DB/consent |
| GitHub Actions and browser | NOT_TESTED | no workflow or browser run |
| Vercel Production | NOT_APPLICABLE | standalone local app |

Run: python -m unittest discover -s tests -v
Files: dbvora/connectors/sqlite_reader.py, dbvora/inventory.py, dbvora/metrics.py, dbvora/errors.py, dbvora/__main__.py, tests/test_inventory.py, tests/fixtures/make_sqlite.py, docs/P0_01_USAGE.md.
Next: P0-02 secure localhost JSON API plus interactive schema SVG map and HTTP/UI test.
No data, keys, external API costs, permissions, or remote deployments changed.
MVP incomplete; no live customer support claimed.
