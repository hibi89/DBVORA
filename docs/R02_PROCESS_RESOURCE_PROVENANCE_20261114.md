## 2026-11-14 리소스 실측 검증 결과
- 기능 source `2011d5fda1bd3d91b0010b5901fdf6149e0a31cc` [full Actions #43553401567](https://github.com/hibi89/DBVORA/actions/runs/43553401567) Ubuntu677PASS/0SKIP / Windows676PASS+1 OS-only SKIP, 0FAIL, both mandatory12/12 PASS. `python -m dbvora.process_resources --local-dir ABSOLUTE_EXISTING_DIRECTORY`는 실제 process CPU time / RSS / local volume total-free를 scope와 함께 내보낸다. HTTP/PG/고객 데이터 없이 유효 경로 한정. 소유자 Win10 실기기와 remote PG server CPU/RAM은 여전히 NOT TESTED/UNAVAILABLE.

# DBVORA process/volume resource provenance, 2026-11-14 KST

R02 final requirement: measured CPU/RAM/disk, no made-up per-database metrics.

A: third-party psutil + remote DB system-agent telemetry, requires extra dependencies/permissions, can falsely attribute host usage to database and risk credential sharing.
B (chosen): Python standard library exposes only this DBVORA Python process cumulative CPU time (not CPU utilization %), current process resident memory (Linux /proc/self/statm or Windows psapi.GetProcessMemoryInfo, unavailable when API cannot read), and total/free bytes of an explicitly selected existing local directory's VOLUME (not the SQLite file or PostgreSQL server). Zero network/credentials/DB operations, no new paid dependencies, path-free output and strict symlink refusal. Remote server CPU/RAM are always null and unsupported, never estimated.

Command: python -m dbvora.process_resources --local-dir ABSOLUTE_EXISTING_LOCAL_DIRECTORY. Sampling is explicit, not a scheduled background task. Repeated values can form an empirical series but no trend or CPU percent is invented here.

Tests: python -m unittest -v tests.test_process_resources and the complete exact SHA cross-platform CI. This is partial R02: remote DB server metrics and long-term customer monitoring remain unverified. Windows10/11, physical restart, commercial rights and purchase acceptance still PENDING. Official P100 UNASSESSED, RELEASE HOLD.
