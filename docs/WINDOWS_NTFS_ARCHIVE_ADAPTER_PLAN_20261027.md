# DBVORA Windows NTFS archive-adapter safety design (2026-10-27 KST)

## Scope and evidence boundary
- Current product: private local-first SQLite read-only map and separate lossless ZIP/ZSTD/archive CLI; the existing `safe_zip._publish_new` and `_sync_directory` fail closed on an OS without supported directory fsync. Do **not** weaken them.
- The approved Win32 Option B prototype is **synthetic OS-temp only**. Owner's actual Windows Python 3.11 result: old 12/12 test module PASS and 6/6 standalone NTFS probe PASS. New 15-test module with competing publishers and controlled child termination is **not yet run on native Windows**; entire Python discovery minimum 240 and unified Windows release gate are **not certified**.
- Verified API documentation does not prove sudden power-loss durability of a same-volume NTFS rename merely because `MOVEFILE_WRITE_THROUGH` succeeds. Microsoft specifically documents flushing for copy/delete moves. A successful `FlushFileBuffers` on the staging file is not automatically proof of a durable parent-directory namespace update.
- **Safety state**: production archive Windows publish unavailable, `ready_for_customer_data=false`, power-loss and directory metadata durability unverified. Do not enable customer files, scheduled backups, deletion, or overwrite.

## Two feasible architectures (no cash external service)
| Criterion | A. Switch existing `_publish_new` by `os.name` | B. Isolated experimental Win32 archive shadow adapter |
| --- | --- | --- |
| Initial engineering | Smaller code delta and fastest first success | Additional temporary module and separate tests |
| Runtime/price | Local; $0 external spend | Local; $0 external spend |
| Quality / regression risk | High: changes snapshot, ZIP, ZSTD, restore and receipt semantics at once; unsupported fsync could be concealed | Lower: original archiver and POSIX path preserved; synthetic-only module can fail closed |
| Maintainability | One function, but combined OS branches complicate invariants | More code initially, explicit platform boundaries and evidence |
| Rollback | Requires reverting a shared production primitive | Remove/disable opt-in synthetic module; archived production code unaffected |
| Risk of false durability claim | High unless separately gated | Lower, as long as report distinguishes byte-verification from namespace/power durability |

**Provisional selection: B for research only.** Production activation is **not approved** by this plan. B avoids premature weakening of the original durability contract while allowing a complete synthetic SQLite -> snapshot -> archive -> restore exercise after owner native 15-case results.

## Proposed boundaries and protocol (design, not implemented)
1. A dedicated synthetic adapter accepts **only a freshly created OS-temp NTFS directory** with an allowlisted DBVORA prefix; no arbitrary user-supplied paths or network shares. Production caller integration remains disabled. Initial implementation may require a test-only copy of the archive pipeline rather than patching `safe_zip._publish_new`.
2. Create entirely new generated staging and target names on the same validated volume, no existing target, no reparse points/symlinks, no filename traversal, bounded file bytes. Prefer OS-handle identity checks and exclusive temporary ownership. No `REPLACE_EXISTING`, `COPY_ALLOWED`, or delayed move.
3. Build a **synthetic SQLite database** with SQLite online backup API; record its SHA256 and `PRAGMA integrity_check`. Generate ZIP (and optional ZSTD when local codec is available) to fresh staged files; verify independent extraction into a separate generated location.
4. Before synthetic publish, flush staged data via writable file handle. Native move must create a new name without replacement. After move, verify exact size/SHA and independently restored SQLite integrity. Report observed content proof, *not* durable namespace proof.
5. Explicit states: `STAGED` -> `PUBLISHED_UNVERIFIED` -> `CONTENT_VERIFIED_POWER_DURABILITY_UNPROVEN`. On failure, never mark success, delete previous valid archive, or reuse an untrusted orphan without re-verification. The current proof-of-concept can leave a target after a failed post-publish digest; a future adapter must account for this without silent cleanup.
6. Restart scan should treat a valid generated-name archive without independently verified receipt as `ORPHAN_UNCONFIRMED`. Receipt and artifact are separate create-only publications; a process exit between them is expected and must be classified, not overwritten.
7. No automatic cleanup/retention; never modify a customer DB or older verified backup. JSON diagnostics must expose bounded stable codes and checks, no raw paths, DB records, tokens or file contents.

## Tests and acceptance order
| Stage | Minimum evidence | Current |
| --- | --- | --- |
| W0 native unit regression | Owner `py -3.11 -B -m unittest -q tests.test_windows_ntfs_publish` on updated private feature branch; exactly 15 tests, 0 failed | **PENDING** |
| W1 standalone source inspection | Ensure create-only flags, stage-handle identity and error codes; check concurrency, before-move and after-move process termination | Static inspection only; no new execution claimed |
| W2 synthetic end-to-end shadow adapter | SQLite online backup -> ZIP/ZSTD optional -> independent restore -> SHA/integrity exactly equal; never existing target overwritten | **DESIGN ONLY** |
| W3 restart and failure injection | Competing writers; crash before/after move; process exit before/after receipt; name collision; symlink; input corruption; missing parent; permission denial; injected I/O errors; no destructive cleanup | **DESIGN ONLY** |
| W4 genuine native persistence research | Separate NTFS metadata persistence/driver/hardware-backed evidence or documented limitation; safe reboot/restart tests; physical power-loss experiments only with an isolated sacrificial test device and explicit approval | **UNVERIFIED** |
| W5 full release acceptance | At least 240 real Python tests (update threshold only for added test code), Node TAP, CLI, preflight, compileall, independent file:// browser; Windows archive remains blocked until W4 policy acceptance | **NOT RUN / BLOCKED** |

**Stop condition:** A native 15-case failure, an unclassified existing-target replacement, path escape, post-move byte mismatch, or unclear filesystem durability must halt activation. Resolve exactly one proved error layer; do not disable checks to force test PASS.

## Immediate next
- Owner's authenticated `E:\DBVORA_GIT` checkout: `git status --short` -> `git pull --ff-only` -> `py -3.11 -B -m unittest -q tests.test_windows_ntfs_publish`. The separate six-step probe already passed and need not be repeated.
- After the actual 15-case result, implement W2 only in isolated synthetic test scope if approved by the existing Option B research authorization. **Any production routing, original `safe_zip` modification, real data, permission change, paid CI, or public release requires separate explicit approval.**

## Supporting official API documentation
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw
- https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers
- https://learn.microsoft.com/en-us/windows/win32/fileio/flushing-system-buffered-i-o-data-to-disk

## Provenance
Reviewed GitHub private feature `9112244781e91f155d0be0e7c706e532be9c72fe`: `dbvora/archive/windows_ntfs_publish.py`, `tests/test_windows_ntfs_publish.py`, `scripts/windows_ntfs_publish_probe.py`, `dbvora/archive/safe_zip.py`, `dbvora/archive/zstd_archive.py`, `dbvora/archive/receipts.py`, `dbvora/archive/recovery_catalog.py`. This document is design/static review only; **zero new runtime product tests**.
