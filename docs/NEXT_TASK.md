# NEXT_TASK — P1-C5 local archive CLI + Windows capability gate

User signal ㄱ or [디비보라 깃헙보고 작업해]. Verify private GitHub hibi89/DBVORA feature/p0-db-map actual head, STATUS/HANDOFF/AGENTS and relevant source/tests. Do not redo P0/C0/C1/C2/C3/C4.

## Verified by 2026-10-26 KST
- P0-01 read-only SQLite inventory, P0-02 localhost FastAPI/JS/SVG clickable map (HTTP/Node DOM pass; real Chromium navigation blocked by managed URLBlocklist '*').
- P1-C0 SQLite online snapshot + lossless ZIP independent SHA/SQLite restore; C1 optional local ZSTD executable level 1/3/9 with repeated synthetic comparison; C2 fsync + exclusive new-file publication, simulated process exit and explicit-only incomplete-temp inventory; C3 read-only post-restart independent archive verification.
- P1-C4 dbvora/archive/receipts.py: opt-in new-only local JSON completion evidence per archive, full independent restore and checksum validation, optional parent receipt name+SHA chain depth up to 12, restart read-only inspect_receipt + inspect_receipt_catalog. Missing receipts/unreadable originals never promoted to success. All metadata unsigned/untrusted, not trusted publication history or power-loss proof.
- Python full 125 PASS/0 FAIL/0 SKIP (96 prior + 29 C4) Linux Python3.13.5, Node DOM 1 PASS, compileall/wheel PASS, ZIP/ZSTD synthetic benchmark smoke SHA PASS, temp-only Linux preflight PASS. New test and source blobs matched local Git hashes; docs/P1_C4_RECEIPTS.md has scope.

## First unfinished safe work: P1-C5
1. Prototype **explicit opt-in local CLI** against synthetic SQLite only: commands for online snapshot, ZIP or ZSTD archive (never raw live copy), independent new-path restore, create receipt with optional already-valid parent, inspect recovery/receipt catalog. Validation for absolute existing output folder and help text that archive contains unencrypted database records; do not enable browsing/selecting live/customer DB automatically or write to original. Prefer no silent deletion/GC.
2. Add CLI argument parsing/fail-closed errors that do not log raw customer rows or source file path, no default automatic schedules, no secret transmission, idempotency and output collision tests. Keep web viewer read-only and separate.
3. Prepare Windows/Python3.11 **synthetic** self-test instructions and run on actual Windows only if environment exists; currently none. Explore optional pinned Python zstandard wheel vs zstd CLI distribution in future, no binary installs/downloads without permission. Keep ZIP fallback.
4. Run previous 125+ Python tests plus CLI E2E, wheel/Node DOM and benchmark smoke. Update docs/STATUS/HANDOFF/NEXT_TASK and commit feature/p0-db-map; verify actual remote HEAD, committer and that main/develop remain unchanged.
5. Reassess broader MVP priority after CLI against initial roadmap: multi-DB map/metrics and end-user packaging vs optional experimental compression refinements.

## Deferred / never claim completed
Windows, Python3.11, actual browser E2E, physical sudden power loss, malicious signature/authentication, real customer DB, PostgreSQL connector, storage/resource metrics and long-lived incremental/scheduled backups. Customer data, overwrite/delete/retention, external transfer, paid services, public deploy or installer distribution require owner approval. ZIP/ZSTD and receipts are unencrypted and unsigned. Do not bypass Chromium managed policy.
