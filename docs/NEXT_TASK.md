# NEXT_TASK — P1-C1 ZSTD baseline and recovery hardening

Recovery trigger [디비보라 깃헙보고 작업해] or ㄱ. Verify newest GitHub feature/p0-db-map SHA and code, read HANDOFF then STATUS, AGENTS, REQUIREMENTS before editing. Do not repeat P0/C0.

## Completed through 2026-10-26 KST
- P0-01: SQLite read-only schema inventory and metric provenance.
- P0-02: localhost FastAPI inventory API and clickable SVG map. HTTP + virtual Node DOM verified; real browser E2E blocked by Chromium managed URLBlocklist '*'.
- P1-C0: offline SQLite Connection.backup -> new standalone snapshot -> integrity/SHA -> ZIP(DEFLATE) with manifest -> independent restore dry-run -> strict validated new-file restore. No source overwrite and no web archive endpoint.
- Tests: 46 Python PASS / 0 FAIL / 0 SKIP (including 18 new archive cases); Node DOM 1 PASS; Python wheel includes archive code and UI. Synthetic WAL committed row, corrupt ZIP and failed publication cleanup covered.
- Not verified: Python 3.11, Windows, customer data, sustained WAL writer stress/locks, filesystem power-cut durability, browser E2E, GitHub Actions and actual market compression.

## First unfinished safe unit P1-C1
1. Compare design A (ZIP baseline + optional ZSTD library) and B (custom compression codec); keep A as adopted for lower risk/cost until real benchmarks indicate otherwise.
2. Using one synthetic SQLite online snapshot per trial, add optional ZSTD codec and independent restored bytes+SQLite integrity check. Do not embed customer records in GitHub or upload data to any service.
3. Run >=3 controlled trials each for raw snapshot, ZIP(deflate) and ZSTD several levels. Report all stored bytes including manifest, compression/restore wall time, any measured memory, full SHA matches. Distinguish incompressible data.
4. Test truncated/corrupt ZSTD, wrong manifest SHA, dependency missing, interrupted publication, repeated restore and file-size caps; protect original and previous stable artifacts.
5. Consider crash-safe fsync / rename strategy, symlink TOCTOU, Windows os.link support and malicious manifest provenance. Do not claim these solved without tests.
6. Re-run prior 46 tests, Node DOM and wheel. Verify actual GitHub branch SHA, commit author and updated HANDOFF/STATUS/NEXT_TASK.

## Deferred gates
Windows and Python 3.11 execution, full browser real UI tests in permitted browser environment, live customer data/continuous writer tests, signed/encrypted archive and durable power-failure restart tests. User approval is required before real customer DB access, deletion/overwrite, public deployment or external paid data services.

See docs/P1_C0_VERIFICATION.md and docs/COMPRESSION_PLAN.md for baseline contract.