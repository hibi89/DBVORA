# R03-09 — Windows NTFS publication boundaries (2026-11-15 KST)

**Status: PASS_SCOPED** for synthetic GitHub-hosted Windows/Linux regression at functional test SHA `4f3e0c8833735129c1e3c0dbf23c487220e3cf73`.

- Exact-SHA full release [#43618972951](https://github.com/hibi89/DBVORA/actions/runs/43618972951) passed: Ubuntu 760/760, 0 skips; Windows 760 passed plus the one named POSIX-only permission skip. Required filesystem preflight, CLI, Node DOM, archive restore, ZSTD, and other synthetic gates passed.
- Blueprint evidence gate [#43618973180](https://github.com/hibi89/DBVORA/actions/runs/43618973180) passed at the same SHA.
- Source change: clarify the shared Win32 `MoveFileExW(MOVEFILE_WRITE_THROUGH)` primitive used by the Windows archive publisher. Test changes: `tests/test_windows_ntfs_publish.py`.

## Evidence

- Windows tests exercise a short/case alias of the OS temporary parent and perform a real native create-only publication, then compare SHA-256 and confirm the stage name is gone.
- A mocked Win32 access-denied return maps to a fixed `MOVE_FAILED` without paths. The production `safe_zip._publish_new_ntfs` wrapper maps this to `PUBLISH_FAILED`, preserving the staged bytes and leaving the target absent.
- A simulated unsupported ReFS volume is rejected before native move. No ACL or security setting is changed by the tests.
- Existing checks still cover destination collision without overwrite, concurrent create-only publication, rejected symlink/outside-temp paths, tamper-after-publish, and child process exit before and after publication.
- The Windows production archive tests call the native filesystem-type check on the runner's temp output volume; the offline gate also reports temporary-filesystem publication PASS.

An earlier commit `83dcafba2626abeeb18eb5ce9d2522464b259785` failed the full gate [#43618687075](https://github.com/hibi89/DBVORA/actions/runs/43618687075) because the added test module had a doubled line-continuation backslash and could not be imported. The fix was limited to test syntax; no test behavior ran at that SHA. Corrected SHA `4f3e0c8833735129c1e3c0dbf23c487220e3cf73` passed the complete suite on both operating systems.

The Win32 access-denied case is injected, not caused by changing ACLs. CI did not exhaust a real disk, modify access control, certify user-machine NTFS behavior, or simulate physical power loss. ENOSPC injection and process interruption remain synthetic evidence from R03-06. R03-10 is OWNER_GATE; overall completion remains UNASSESSED / RELEASE HOLD.
