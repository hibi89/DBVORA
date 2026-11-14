# DBVORA CAS v2 concurrent writer / restore synthetic acceptance

**Date:** 2026-11-14 KST
**Verified feature/test SHA:** `60e99bb40d5542248cd4c210963979e4adacff6d`
**CI:** [Windows2025 + Ubuntu24.04 full release #43569112618](https://github.com/hibi89/DBVORA/actions/runs/43569112618)

## Alternative designs
**A: Add an exclusive shared directory lock and retry policy** on every CAS write. Could force serial progress, but adds cross-platform lock lifetime/abandoned-lock recovery and a new state to keep safe after process death; no existing multi-process acceptance evidence, greater maintenance risk.
**B: Retain the immutable no-replace chunk publication + digest checks** and add deterministic simultaneous synthetic writer/restore tests to establish what current code safely does, without new retention/deletion semantics. **Selected B**: zero extra dependencies, no additional user data collection, fail-closed races permitted.

## Checked
- `tests/test_cas_concurrency.py` creates a *disposable synthetic SQLite* snapshot and a baseline compressed CAS. Changes the data to force a different snapshot digest, proves at least one chunk is new, and intercepts the first two staging calls with a two-thread barrier. Each writer attempts `create_compressed`. Require at least one verified winner; a second publisher may also succeed or fail closed on a no-replace race. Assert the previous baseline manifest bytes are identical, old generation independently restores, every published new generation SHA matches the changed snapshot, read-only full-store audit PASS, and no temporary stages persist. This proves only controlled **threads** on CI filesystems.
- Two simultaneous `restore_compressed` calls publish distinct new verified SQLite files and leave the input immutable.
- A pre-existing filename that matches a raw digest but stores a mismatching zlib payload triggers `CHUNK_HASH_MISMATCH` and cannot be overwritten or used; old healthy generation still restores.

## Actual Windows failure and diagnostic evidence
- [Initial source `3229b874` CI #43568460809](https://github.com/hibi89/DBVORA/actions/runs/43568460809): Linux709 PASS, Windows FAIL one new race test.
- [Diagnostic workflow source `a669b72b` CI #43568761086](https://github.com/hibi89/DBVORA/actions/runs/43568761086): Windows detailed unittest traceback line87 `AssertionError: False != True` at `entered[0]>=2`. The test filtered staging by Windows path comparison, which did not fire the barrier. This does not establish a data-loss defect.
- [Final source `60e99bb40d55` CI #43569112618](https://github.com/hibi89/DBVORA/actions/runs/43569112618): removes the path-name injection condition; the first two staging calls always rendezvous. Adds assertions that the source snapshot changed and the target chunk is absent. **Windows/Ubuntu 2/2 SUCCESS**, 709 discovered (Ubuntu709 PASS/0 FAIL/0 SKIP, Windows708 PASS/0 FAIL/1 approved POSIX-only SKIP), mandatory12/12 each. Node DOM PASS; no release gate reduced.
- Exact product source under `dbvora/archive/compressed_cas.py` remains unchanged in this round; only synthetic tests and CI diagnostic list changed.

## Release boundaries
Does not certify separate-process writers, physical power cutoff, all possible scheduling orders, customer DB, buyer's Windows, signing, license notices or official owner 100-point acceptance. Historical 95 is not official. Remain **UNASSESSED**, `[작업중]`, RELEASE HOLD, actual Kmong registration 0, Vercel/Production not applicable. Source/customer backups and secrets unchanged.
