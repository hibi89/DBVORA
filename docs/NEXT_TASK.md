# NEXT_TASK — P1-C3 cross-platform safe archive recovery + Windows readiness

Trigger [디비보라 깃헙보고 작업해] / ㄱ. Verify remote feature/p0-db-map SHA, HANDOFF, STATUS, AGENTS, REQUIREMENTS and executable tests. Preserve main/develop. No repeat of P0/P1-C0/C1/C2.

## Completed through 2026-10-26 KST
- P0 SQLite readonly schema inventory and localhost FastAPI/SVG UI; HTTP and simulated Node DOM PASS; actual Chromium browsing blocked by managed URLBlocklist '*'.
- P1-C0: SQLite Connection.backup -> standalone integrity-checked snapshot; ZIP manifest, dry-run restore and SHA-256-verified independent restore.
- P1-C1: ZSTD CLI levels 1/3/9 and comparison of repeated vs random synthetic SQLite with three-run identical-snapshot trials; 62 pre-C2 Python tests.
- P1-C2: fsync verified staging file + parent directory around exclusive hardlink publication; best-effort rollback on post-link fsync failure; grouped allocation rollback; strictly opt-in POSIX old-temp cleanup and read-only listing; crash before publication subprocess os._exit(17) scenario; four-process eight-snapshot concurrency. Full Python 76 PASS/0 FAIL/0 SKIP, Node DOM 1 PASS, wheel PASS and two-fixture benchmark smoke SHA all PASS. See docs/P1_C2_DURABILITY.md.
- Windows/Python3.11, physical power loss, customer DB, signed archives, real browser and GitHub CI still NOT_TESTED. Windows directory fsync may fail closed. No customer/user local device work required so far.

## Next safe unit P1-C3, synthetic only
1. Inspect code and test published artifact verification on restart. Distinguish independently verifiable complete archive from incomplete temp, especially post-link failure; establish a manifest/commit-record strategy, avoid modifying or deleting existing backups.
2. Tighten failure injection across fsync/metadata publish/cleanup, archive symlink/directory races, orphan scanning under concurrent writers, permission-denied errors. Reconcile exceptional states without touching originals. Do not claim power loss proven by simulated os._exit.
3. Build optional Windows-specific test harness/packaging plan: Python3.11 x64 + directory-sync/NTFS behavior, CLI zstd vs pinned Python zstandard wheel. Do not introduce a download or ship binaries without consent and verified licensing.
4. Add report with security scope, provenance. Unsigned SHA manifests are not authenticated; controlled attacker could modify both payload+manifest. Restore must be to new path, never replace original.
5. Run existing 76+ tests, wheel, Node DOM, representative benchmark; update STATUS/HANDOFF/NEXT_TASK and verify remote GitHub commit SHA + committer. CI/develop merge only after evaluation.

## Gate
Real customer DB, account credentials, external sending, original deletion/overwrite, retention policy, destructive migrations, public app/installer distribution, paid services or permission changes require explicit owner approval. Browser policy should not be bypassed. Archiving requires testing on actual hardware before customer use. Current full commercial-product completion is NOT claimed.
