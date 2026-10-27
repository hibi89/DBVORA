# DBVORA — owner Windows NTFS synthetic evidence, 2026-10-27 KST

## Verified owner-supplied output, **pre-race-regressions**
The authorized user ran on their existing private Windows checkout (`feature/p0-db-map`, source baseline `a10e5341340bf4449de9ec6c857807e00d659800`):

```text
---------------------------------------------------------------------
Ran 12 tests in 0.111s

OK
{"contract":"dbvora.ntfs-create-only-probe.v1","directory_metadata_durable_verified":false,
 "native_windows_tested":true,"power_loss_durable_verified":false,
 "ready_for_customer_data":false,"scope":"OS_TEMP_SYNTHETIC_ONLY",
 "status":"PASS_WINDOWS_NTFS_SYNTHETIC_ONLY",
 "steps":[
 {"step":"windows","status":"PASS"},
 {"step":"python_3_11","status":"PASS"},
 {"step":"temp_ntfs","status":"PASS"},
 {"step":"create_only_and_sha256","status":"PASS"},
 {"step":"collision_preserves_both","status":"PASS"},
 {"step":"failure_preserves_source","status":"PASS"}]}
```

**Interpretation:**
- Actual Windows Python3.11, temporary filesystem NTFS: checked.
- Synthetic-only native Win32 create-once publication, post-publish byte integrity, existing name collision preservation, and injected failure preserving staged bytes: passed.
- The isolated 12 tests completed in 0.111 seconds. Quick execution is expected; **this is not the full 237- or 240-test gate**, and does not certify every other archive path.
- `directory_metadata_durable_verified=false`, `power_loss_durable_verified=false`, `ready_for_customer_data=false` are intentionally still false. Neither a real power interruption nor customer database use was performed.

## Additional implementation after that owner evidence
To cover previously untested failure windows without modifying archive safety semantics, `tests/test_windows_ntfs_publish.py` gained:
1. **Two concurrent publishers / one target name:** exactly one must win, loser retains original staging bytes. On native Windows, selects actual Win32 mover; on Linux it uses a create-only simulated hard-link mover.
2. **Controlled child exit immediately before publish:** no target appears and original stage SHA remains.
3. **Controlled child exit immediately after native publish but before parent verification:** target SHA survives a **process** exit. This does *not* emulate sudden power cut or guarantee durable NTFS metadata.
- Linux3.13 local isolated stand-in implementation exercised these three new test scenarios: **3/3 PASS**. This local smoke used an equivalent minimal publication module, **not a full Git blob identical checkout**; therefore the checked-in **15 test cases require a real Windows rerun**.
- `scripts/verify_release_gate.py` now requires >=**240** cases; test fixtures updated to match. The existing `safe_zip.py` and customer archival CLI were not modified, and unsafe Windows archival release remains blocked.

## Next isolated owner Windows recheck
Use the existing private checkout, no ZIP/new clone:
```powershell
cd E:\DBVORA_GIT
git status --short
git pull --ff-only
if ($LASTEXITCODE -eq 0) {
    py -3.11 -B -m unittest -q tests.test_windows_ntfs_publish
}
```
Expected 15 discovered tests; actual PASS/FAIL **not yet observed**. Report output only. If 15 PASS, the next engineering task is a separately gated native NTFS durability and end-to-end SQLite restore design; do not activate archived-backup writes or remove fail-closed `_sync_directory` based on unit/short process-exit testing alone.

No data exfiltration, external billable CI, real customer database, destructive user action, main/develop merge or public hosting.
