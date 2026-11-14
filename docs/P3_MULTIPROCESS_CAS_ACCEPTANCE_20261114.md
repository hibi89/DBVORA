# DBVORA P3 — Separate-process CAS v2 race acceptance (2026-11-14 KST)

## Exact implementation scope

- Repository: `hibi89/DBVORA`; branch: `feature/p0-db-map`.
- Test source commit: `c1f41fdb32fde48e316b1f4b98336734e903e4a5`.
- New `tests/test_cas_multiprocess.py`, two unittest tests; **production CAS implementation is unchanged**.
- Existing `tests/test_cas_concurrency.py` only exercised two threads; this new harness uses `multiprocessing.get_context("spawn")` on *both* Linux and Windows.
- The process-level rendezvous occurs at each process's first new chunk staging allocation, after the missing-new-chunk check. A process-local mock does not weaken the production no-replace publish or digest checks.
- Every source/archive is generated in a disposable `TemporaryDirectory`. No customer DB, actual archive, secret, external API, auto-deletion, or physical power-off action.

## Design choices

| Option | Cost/maintenance | Correctness and risk |
| --- | --- | --- |
| A. Add a new cross-process global OS lock | New platform-specific locking and recovery handling; more code and time | May hide a broken no-replace publication path and introduce deadlocks |
| B. Exercise current POSIX/NTFS no-replace path from 2 spawned processes | No new dependency, no operating code change | Directly verifies contention and fails closed on unverified races |

**Chosen B.** Keep the existing immutable, checksum-verified architecture. Consider adding locks only if an independently reproduced failure demonstrates that the current safety contract is insufficient.

## Acceptance cases

1. Create an old verified CAS manifest, change the disposable SQLite fixture, create a fresh snapshot, and prove at least one genuinely missing chunk. Spawn two child processes, synchronize their first new chunk staging, require each to report rendezvous and process exit code 0, and accept either a verified publication or an explicit bounded HOLD error. Require >=1 independently verified publication. Reject unrecognized errors or unverified success.
2. Check old manifest bytes, old restore SHA, new published restore SHA, unchanged source/snapshot SHA and mtime, read-only CAS audit PASS, and absence of leftover `.dbvora-incomplete-*.part` files.
3. Spawn two more independent processes to restore the **same immutable manifest** concurrently to one output directory; require two distinct output names, full SHA256 matches, SQLite `PRAGMA integrity_check=ok`, source/manifest unchanged and no staging remains.
4. Child processes use spawn context on both OSes, process timeouts/forced cleanup and small result queue. No background job persists after test termination.

## Verification

- Exact source full gate: https://github.com/hibi89/DBVORA/actions/runs/43576862756
- Ubuntu24.04: **712 discovered, 712 PASS, 0 FAIL, 0 SKIP; 12/12 mandatory steps PASS**.
- Windows2025: **in progress at initial evidence write; do not label PASS until the exact job/log verifies the results**.
- Final blueprint evidence gate: https://github.com/hibi89/DBVORA/actions/runs/43576863080 (confirm exact conclusion before release decision).
- Latest real Chromium 17/17 per OS remains independently verified on earlier exact source `d5780ceece92f28508712aa2cdd2a6228c7e137c`; this change affects only Python tests, not frontend.

## Explicit exclusions

Long-running multi-process workload, crash/power-loss midway through fsync, arbitrary network filesystem semantics, client Windows 10/11 and customer backup restore are not tested. User final-blueprint weighted acceptance remains `UNASSESSED` (old internal technical 95 history only), `[작업중]`, `RELEASE HOLD`, real Kmong registrations 0, Production/Vercel not applicable. Next: finalize exact Windows result and sync STATUS/HANDOFF/NEXT_TASK/central ledger.