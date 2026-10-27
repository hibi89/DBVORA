# W0 native Windows 15-case evidence and W2 simulated shadow archive (2026-10-27 KST)

## W0 owner Windows result — verified from the supplied PowerShell output
- First native run: `Ran 15 tests in 0.637s / OK`.
- Owner then ran clean `git status --short`, `git pull --ff-only` updating `9112244..5ef6187` on `feature/p0-db-map`, and reran the same isolated module: `Ran 15 tests in 0.444s / OK`.
- Both are real Windows native Python 3.11 tests on the existing owner's NTFS working machine; the original six-step native synthetic probe already passed in the previous checkpoint.
- This is **process termination and competing publication behavior**, not a physical power-cut durability certification or permission to operate on real/customer databases.

## W2 synthetic-only shadow archive implementation
- Files: `scripts/windows_ntfs_archive_shadow.py`, `tests/test_windows_ntfs_archive_shadow.py`.
- All input created inside OS temporary folder using DBVORA-specific prefix; CLI only accepts `--synthetic-only`. No arbitrary source or output path; no local customer DB, network, credentials, global configuration, or deployed service.
- W2 pipeline: generated WAL SQLite 48-row fixture -> `sqlite3.Connection.backup` to a fresh staged file -> `PRAGMA integrity_check` and exact row contract -> existing isolated create-only publisher -> ZIP with only `manifest.json` and `snapshot.sqlite` -> bounded manifest/SHA/size checks -> independent extraction to new SQLite -> SHA256, SQLite integrity and rows compared -> original synthetic source SHA unchanged.
- The experiment uses ZIP only, not optional ZSTD. ZIP verification rejects duplicate/unexpected entries and oversized/deviating archive content. Existing `safe_zip.py`, `zstd_archive.py`, CLI, receipts and production publication remain **unchanged and fail-closed** on Windows.
- Native execution distinguishes `PASS_WINDOWS_NTFS_SYNTHETIC_ONLY` from `PASS_SIMULATED_ONLY`. Report fields `ready_for_customer_data`, `power_loss_durable_verified`, `directory_metadata_durable_verified`, `production_archive_integrated` remain false.
- No code path from the real archive API or UI calls this shadow experiment.

## Verified local evidence on Linux
- Reconstructed original `dbvora/archive/windows_ntfs_publish.py` from the exact GitHub blob and verified local `git hash-object` **7bb78a23fe1fe7dd17b89a5542c6de358409b0c9** equals repository.
- Executed the new shadow module **8/8 unittest PASS**, `PYTHONDEVMODE=1`, Python 3.13, ResourceWarning treated as errors. The first local run exposed SQLite connection close warnings; corrected with `contextlib.closing`, then clean 8/8 PASS.
- Covered simulated ZIP restore, source unchanged, Linux/Python/FS blocked entry, ZIP invalid manifest, duplicate entries, injected move failure, tampered published ZIP bytes. Module source Git blob: `3bcde6cab4dc7de7a5ac3a85a7077cbd0529105a`. Test source Git blob: `e94f82d40f8b3bb0c2900d4e940f712d83595b8b`. Both verified against local tested source hashes.
- Native W2 Windows probe, integrated full >=**248** product tests, existing Windows CLI/release gate and physical power loss **NOT RUN** on new SHA. Windows product archive remains blocked.

## Integration and next priorities
- Updated `scripts/verify_release_gate.py` source presence check and discovery minimum 240 -> **248** to require eight new tests. Mock gate fixtures were updated to 248 and negative threshold 247, but the full gate test module **was not executed** in a complete private checkout after this change.
- Under already approved Win32 Option B research, next work is non-customer W2 native platform verification and W3 restart/receipt-gap and failure-injection research. Do not patch the production `safe_zip._sync_directory` in order to pass Windows CLI without a separate durability decision.
- User PC should no longer be needed for every design/code/test iteration. Native NTFS and hardware-only validation remain independent gates; a GitHub Actions Windows runner would require explicit approval of build-minute budget/permission/trigger policy before enabling.
- Production/Vercel N/A; no paid CI, real DB access, public release, auto-delete, force push or original backup modification.
