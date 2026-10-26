# DBVORA STATUS — P1-C3 read-only recovery audit (2026-10-26 KST)

Private hibi89/DBVORA, work branch feature/p0-db-map. Last verified parent SHA f49c8ac2225b096f8f4c55dab311a0db950e8d50; after commit, re-read actual remote SHA. main/develop unchanged 890f842e3ba0e13c901e785633bdd06eadc76cce.

| Feature | Actual state | Evidence |
| --- | --- | --- |
| P0 SQLite schema read-only inventory + localhost map | TESTED_LOCAL | HTTP and Node virtual DOM; real Chromium UI blocked by policy |
| P1-C0 SQLite consistent snapshot, ZIP and independent byte-exact restore | TESTED_SYNTHETIC | prior regressions |
| P1-C1 ZSTD CLI levels 1/3/9 + synthetic fair ZIP comparison | TESTED_SYNTHETIC_LINUX | previous 3-trial comparisons |
| P1-C2 filesystem fsync/new-file publish and explicit temp detection | TESTED_SYNTHETIC_LINUX | POSIX failure injection, no actual power cut |
| P1-C3 read-only post-restart archive catalog | TESTED_SYNTHETIC_LINUX | copy to separate temp + full sqlite/ZIP/ZSTD validation; incomplete/unsafe/invalid classified, never deletes |
| P1-C3 synthetic temp-only Windows/codec preflight script | TESTED_LINUX_ONLY | Linux hardlink+sync passes, windows_package_verified=false |
| Python unit tests | **96 PASS / 0 FAIL / 0 SKIP** | Python 3.13.5 SQLite 3.46.1, prior 76 + 20 new |
| JavaScript DOM test | PASS | Node 1/1 and syntax PASS |
| Python wheel packaging | PASS | recovery_catalog, ZIP, ZSTD and UI included; preflight script repo-only |
| Real Windows/NTFS + Python3.11 | NOT_TESTED | no real Windows machine |
| Power interruption / persistent commit record | NOT_IMPLEMENTED_OR_TESTED | content VERIFIED != durable publish |
| Customer live DB / production / CI | NOT_TESTED | no user data, hosted deploy or GitHub Actions |
| Real browser E2E | BLOCKED_ENV | managed Chromium URLBlocklist "*" |

Local commands:
python -W error::ResourceWarning -m unittest discover -s tests -q
python -m compileall -q dbvora tests scripts
node --test tests/test_ui_dom.cjs
python -m scripts.preflight_archiving

Security limits: audit never repairs/deletes source; snapshots and archives contain full data unencrypted; self-contained unsigned checksum is NOT malicious tamper authentication. A cleanly inspectable orphan archive after crash is marked CONTENT_VERIFIED_PUBLISH_UNPROVEN, never DURABLE. Temp identification is not permission for automatic cleanup. Filesystem race and disk consumption limits remain.

Details docs/P1_C3_RECOVERY.md. Next docs/NEXT_TASK.md P1-C4 evidence receipts/lineage and Windows runtime gates. No code was merged into main/develop or placed on public services.
