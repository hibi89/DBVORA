# DBVORA STATUS — 2026-10-26 KST

Repository: hibi89/DBVORA (private). Work branch: feature/p0-db-map. Previous verified feature HEAD dc87d475334e83ca3f32ee76e67eebb1828f3b27; new HEAD must be read from GitHub after commit. main/develop remain at 890f842e3ba0e13c901e785633bdd06eadc76cce.

| Scope | State | Evidence |
|---|---|---|
| P0-01 SQLite readonly inventory | TESTED_SYNTHETIC | Existing tests |
| P0-02 localhost API + clickable map | TESTED_HTTP_DOM_SIMULATED | HTTP and Node DOM pass; full browser E2E blocked by managed policy |
| P1-C0 snapshot via SQLite backup API | TESTED_SYNTHETIC | No raw live DB copy; integrity check and SHA |
| P1-C0 ZIP + independent restore | TESTED_SYNTHETIC | Verified manifest, SHA-256, restored SQLite integrity |
| WAL committed-row fixture | TESTED_SYNTHETIC | PASS |
| Invalid/corrupted ZIP and interrupted publication simulations | TESTED_SYNTHETIC | Rejects artifacts, preserves previous files |
| Total Python suite | PASS | 46 PASS / 0 FAIL / 0 SKIP, Linux Python 3.13.5 SQLite 3.46.1 |
| JS simulator, wheel package | PASS | Node DOM 1 PASS, archive+web files included |
| ZIP/ZSTD comparative benchmark | NOT_STARTED | No superiority claim |
| Browser real UI / Windows / Python 3.11 / customer DB | NOT_TESTED | No approved live DB |
| Vercel and external deployment | NOT_APPLICABLE | Local software |

Smoke synthetic snapshot 24576 B, ZIP 1006 B, roundtrip SHA equal. Toy fixture ratio is NOT representative customer compression efficiency. ZIP is unencrypted; SHA manifest is not authenticated. 512 MiB prototype cap and same-filesystem hardlink publication require Windows and power-failure verification. No files or credentials uploaded. No GitHub Actions run.

Tests: python -W error::ResourceWarning -m unittest discover -s tests -q
Next: docs/NEXT_TASK.md, P1-C1 optional ZSTD and fair benchmarking.