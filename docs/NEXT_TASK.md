# NEXT_TASK — P1-C2 durability, recovery and Windows codec packaging (synthetic only)

Trigger [디비보라 깃헙보고 작업해] or ㄱ. Before coding verify GitHub branch SHA, HANDOFF, STATUS, AGENTS, REQUIREMENTS, source and tests. Do not repeat finished steps.

## Verified so far on Linux (2026-10-26 KST)
- P0-01 SQLite readonly schema inventory, P0-02 localhost API+clickable DOM/SVG source (HTTP+Node DOM verified, **real browser blocked** by managed Chromium URLBlocklist).
- P1-C0 SQLite online standalone backup, ZIP baseline, strict verified independent restore; WAL fixture, failure injection.
- P1-C1 official local ZSTD CLI levels 1/3/9 with bounded .dbvz envelope, frame+uncompressed SHA-256 and SQLite integrity, fail-closed missing codec, no-shell subprocess, new-file publish and failure cleanup. tests/test_zstd_archive.py + scripts/bench_codecs.py.
- Combined Python 62/62 PASS, JS DOM 1/1 PASS, wheel packaging PASS (but does not bundle zstd binary). Same-source, same-machine three-run median benchmark for two 565248-byte synthetic SQLite snapshots, all restores match SHA; docs/P1_C1_BENCHMARK.md.
- ZSTD GUI/Windows and customer DB are NOT_VERIFIED. Main/develop deliberately unchanged.

## Next P1-C2 actual work (no real DB)
1. Audit existing _staging_file and _publish_new and new .dbvz file lifecycle. Design crash-recovery/incomplete artifact handling and durable publish including fsync file and parent directory where supported. Compare Linux/Windows filesystem semantics, do not claim atomic/durable where not measured.
2. Add synthetic fault injection around temp creation, content write, fsync, publish, cleanup and collisions; idempotent retries must not alter an existing archive or original. Validate no post-crash incomplete publication in supervised interruption test.
3. Validate multi-process concurrency, temp artifact scavenger safety (only DBVORA temporary naming, never arbitrary file deletion) and publish ref check.
4. Decide and document Windows codec distribution: bundle signed/verified native zstd executable in installer vs optional python zstandard wheel, compare license/maintenance/size/deployment compatibility. No unapproved external download/distribution.
5. Build reproducible Windows/Python 3.11 test commands and permissions check. If no Windows environment, leave NOT_TESTED. Do not retry managed Chromium URLBlocklist unchanged.
6. Run all prior 62 tests + extra fault tests, Node DOM, package and benchmark smoke. Update STATUS/HANDOFF/NEXT_TASK; commit and verify branch SHA/author. Develop PR only after review and executable confidence.

## Safety boundaries / blockers
Archive is unencrypted, manifests unsigned and not authenticated; SHA equality is NOT malicious tamper protection. The ZIP/ZSTD benchmark is two small synthetic fixtures, not a commercial promise. Continuous live WAL/locks, power loss, Windows, customer data and real browser remain unverified. External data transfer, real DB use, deletion or overwrite, paid or public deployment, permissions/security changes require owner approval.

Use docs/P1_C1_BENCHMARK.md and docs/COMPRESSION_PLAN.md for current measurements and test scope.
