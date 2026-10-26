# DBVORA P1-C2 — byte-identity deduplication planning prototype (synthetic scope)

Date: 2026-10-27 KST. Private repository: `hibi89/DBVORA`, branch `feature/p0-db-map`.

## What is implemented

New `dbvora/archive/dedup_plan.py` is a **bounded, read-only candidate reuse estimator**, not an actual deduplicated archive or backup. The standard-library-only module accepts an explicit list of 1–8 absolute, regular-file paths and compares fixed-size chunks (power of two, 4 KiB–1 MiB; default 64 KiB). SHA-256 narrows lookup; reuse is **credited only after reading and comparing the actual bytes from a prior occurrence**, even in an artificially forced identical-hash scenario. Paths, data bytes and hashes are omitted from the returned report.

Safety controls:
- Opens read-only and rejects symlinks, non-regular files, duplicate device/inode, relative paths, invalid chunk sizing, and missing/unavailable sources.
- Limits individual files to 128 MiB and combined file sizes to 256 MiB; only up to eight inputs, with at most chunk-size read buffers and digest+offset metadata in memory.
- Compares fstat device/inode/size/mtime/ctime before and after scan. This mitigates ordinary source mutation but is not a guarantee against malicious concurrent edits, OS crashes or snapshot inconsistencies.
- Does not write or create archives, chunks, manifests, reference counts, restore chains, retention/deletion jobs or production backup metadata. It reads named files only when explicitly called as an API. The CLI accepts **only `--synthetic`** and creates disposable synthetic fixtures in the OS temp directory.

Output `candidate_reusable_bytes` measures potential *fixed-size byte-identical chunk reuse*, not verified compressed size, CPU cost, logical record-level deduplication, deletion permission, or guaranteed physical disk saving.

## Tested exact GitHub source bytes
- `dbvora/archive/dedup_plan.py` Git blob `51f3bcca0826f530712e7c9ac57040caae1e026b`.
- `tests/test_dedup_plan.py` Git blob `73e63048dd4a144d56cc62dca32638d7fd28e3e6`.
- Local Python 3.13.5 `python -W error::ResourceWarning -m unittest discover -s tests -v` from isolated staging with just the two exact files: **9/9 PASS**, 0 FAIL/SKIP/ResourceWarning.
- `python -m dbvora.archive.dedup_plan --synthetic` **PASS**: three synthetic 8,192-byte files produce 24,576 bytes total, 12,288 bytes unique and 12,288 candidate reusable (3 unique chunks + 3 repeat chunks at 4,096 bytes). This is an intentionally repetitive fixture; do not extrapolate a 50% saving to any customer DB.
- Adversarial tests cover: forced SHA-256 collision with distinct underlying bytes, symlink and duplicate-inode rejection, size and chunk limits, empty file, repeated chunks inside one file, mtime/content source immutability and no leaked path.
- New 9 tests raise the expected full Python suite baseline **201 → 210**. The `scripts.verify_release_gate` threshold and mocked fixtures updated; the unsigned portable source ZIP requires the new module in `scripts/build_portable.py`.

## Not yet verified and required next

**Full 210-case checkout regression and unified ZIP/ZSTD archive/restore gate NOT EXECUTED at this SHA**; full private source ZIP unavailable to the current local runner. Prior Python 201-test count was a GitHub-source inventory, NOT 201 executed PASS. The 9 new isolated tests are the *only newly executed* C2 tests.

Real content-addressed chunk persistence, collision-secure chunk lookup under concurrency, reference integrity, independent restore of parent chains, crash-safe idempotent publication, cleanup/GC, user opt-in and deletion safeguards are **NOT IMPLEMENTED**. C2 compression and economic benefits are not proven. Native Windows Python 3.11/NTFS, browser `file://`, physical power-loss, installer/customer data validation remain independent blockers.

Next steps: run full 210 cases on authorized complete private source; then design chunk-store manifest + independent restore test before any actual backup-dedup write path; never enable automatic deletion. The previously discovered `app.js` refresh event-handler duplication remains an **uncommitted local patch** because GitHub file update was blocked; do not imply it is fixed remotely.
