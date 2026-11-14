## 2026-11-14 실제 Windows2025·Linux 시간 측정 확인
Source SHA `ff20658b2d9db099eea6386d354e90f5c0dc5264`, [full gate run #43552745227](https://github.com/hibi89/DBVORA/actions/runs/43552745227) Windows·Ubuntu 두 job SUCCESS. 671 Python tests discovered, Ubuntu671PASS, Win670PASS+1 POSIX-only SKIP, 12/12 each.

| 동일 2세대 합성 DB 작업 (wall-clock 1회, ms) | Ubuntu24.04 | Windows2025 |
|---|---:|---:|
| ZIP 두 세대 저장 | 15.261 | 86.893 |
| Raw CAS v1 두 세대 저장 | 14.397 | 273.244 |
| zlib CAS v2 두 세대 저장 | 19.920 | 245.156 |
| ZIP 두 세대 독립 복원 | 7.168 | 47.808 |
| Raw CAS v1 두 세대 독립 복원 | 6.849 | 63.310 |
| zlib CAS v2 두 세대 독립 복원 | 8.137 | 66.871 |

**No speed guarantee.** These are single wall-clock samples including test-time SHA and new-only publisher overhead. Warm cache, hardware and runner load differ. v2 saves only this workload's emitted storage bytes vs ZIP but is slower in these single observed runs. Avoid purchase claims. Independent real buyer QA not done; official status UNASSESSED and commercial RELEASE HOLD.

# DBVORA exact-synthetic A/B storage and process timing (2026-11-14)

Design comparison: A) only compare ZIP, raw CAS v1 and zlib CAS v2 storage bytes (existing benchmark), low complexity but no measurement of CPU tradeoff; B) add real monotonic wall-clock intervals for each pair of create+restore calls on the same two snapshot generations, no new dependencies or data. Chosen B with one-sample-only caveat. This is not enough to claim latency advantage. The result remains deterministic in *structure* but time values will vary by machine and CI load.

scripts/benchmark_synthetic_archives.py reports six keys under timings_ns (zip_write, raw_write, zlib_write, zip_restore, raw_restore, zlib_restore). Each number is an actual perf_counter_ns delta around the TWO generations, including new-only file publishing and SHA checks. It is not CPU process time or thread throughput and does not control warm filesystem caches. The full gate checks all six are positive integers and uses timing_scope=one_sample_two_generations_wall_clock_only. It does NOT compare them against each other or imply a speed SLA.

No customer database, connection string, network, upload, archive delete or automatic migration. All test data exist only in disposable synthetic temp folders. Measurements cannot certify disk wear, peak RAM, real Windows10 performance, power failure resistance, financial savings or commercial license. User acceptance and RELEASE HOLD remain.
