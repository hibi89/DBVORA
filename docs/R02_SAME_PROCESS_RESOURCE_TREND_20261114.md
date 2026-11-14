# DBVORA R02 — Local Python process two-sample resource comparison (2026-11-14 KST)

## Goal and scope
Offer a **measured two-sample delta** for the local DBVORA Python process CPU time (nanoseconds) and resident memory (bytes), without claiming SQLite/remote PostgreSQL service CPU or memory usage. Local volume totals/free are captured by the existing single-sample method and **are not** automatically treated as database bytes or compared across volumes.

Code: `dbvora/process_resources.py` (`observe`, `compare_local_samples`, CLI).
Tests: `tests/test_process_resources.py`.
Feature+test SHA: `eedd7db4578f4665e38c4d3b32e0a541ee1a7ed4`.

## Options reviewed
| Alternative | Accuracy | Cost | Operational burden | Decision |
|---|---|---|---|---|
| A. Compare two separate CLI/JSON runs over time | Process IDs can change or be reused; monotonic CPU process counters reset | 0 KRW | Disk persistence/identity trust needed | Rejected as a possible false trend |
| B. Sample twice in the same live Python process using a random ephemeral instance ID plus PID | Both counters share the same live process; handles reset/mismatch by refusing a trend | 0 KRW; standard library only | No persistent history or agent needed | **Selected** |

## API contract and safeguards
- `observe(existing_absolute_local_directory)` retains the single-sample `dbvora.local-process-resources.v1` contract; adds `process_id` and random per-process `process_instance_id` (not a permanent machine ID). No customer file contents, passwords, filenames or DB rows.
- `compare_local_samples(previous, current)` requires matching instance token + PID, valid counter types (boolean rejected), process-only provenance, strictly increasing monotonic time, and nondecreasing CPU time.
- Reports `elapsed_ns`, `process_cpu_delta_ns`, and `resident_ram_delta_bytes` only if resident memory provenance is comparable; otherwise memory delta is `null` and explicitly unavailable.
- **Not** a database server CPU/RAM meter, OS CPU utilization %, capacity forecast, wall-clock history, automatic scheduler, persistent collector, or customer safety certificate. Raw process CPU nanoseconds may be greater than elapsed nanoseconds on multicore workloads.
- Different processes, counter resets, legacy snapshots and malformed input return a fixed `unavailable` reason with `null` values. No previous file or customer DB is read, changed or transmitted.

## Operator examples (local-only; existing explicitly selected directory)
Single snapshot (backward compatible):

```powershell
py -3.11 -m dbvora.process_resources --local-dir "C:\\ExistingLocalFolder"
```

Two sequential samples from the **same process** separated by 250 ms:

```powershell
py -3.11 -m dbvora.process_resources --local-dir "C:\\ExistingLocalFolder" --sample-interval-ms 250
```

The optional interval is bounded to 100–5000 ms, never creates a schedule, and outputs a compound report containing the latest sample and comparison. Output contains process-local metadata only, not a database capacity/CPU-percentage estimate.

## Verification boundary
- Added unit checks for real two samples, deterministic deltas, process/session mismatch, bad clock/counters, old/malformed snapshots, missing resident memory, bounded CLI and path-free errors.
- **Verified** final exact SHA [`6b9d7700b529`](https://github.com/hibi89/DBVORA/commit/6b9d7700b529f7cf00e38f6410d94d412a04f9da): [full Windows2025 + Ubuntu24.04 #43561622382](https://github.com/hibi89/DBVORA/actions/runs/43561622382) **2/2 SUCCESS**. Both OS discovered 698 Python tests; Ubuntu 698 PASS/0 FAIL/0 SKIP, Windows 697 PASS/0 FAIL/1 POSIX permission-only SKIP; full release steps **12/12 each**; CLI/Node synthetic checks PASS.
- **Windows correction evidence:** initial #43560870440 and diagnostic #43561330045 failed two new real-sample tests because consecutive samples could share the same Windows monotonic clock tick. [Final test-only change](https://github.com/hibi89/DBVORA/commit/6b9d7700b529f7cf00e38f6410d94d412a04f9da) lets real sample time pass and does not mock the 100ms CLI sleep. `compare_local_samples` continues to HOLD equal/non-increasing timestamps. Failure-only CI diagnostics now include path-free process-resource tests.
- Previous actual user Windows owner QA covers **offline HTML/ZIP synthetic preview**, not this newly added R02 CLI or real DB server monitoring.
- Official final blueprint percentage remains `UNASSESSED`. Historical internal 95 is not a new official score. Work in progress, RELEASE HOLD, no customer data or paid deployment, Kmong registration 0.
