# DBVORA process/volume resource provenance, 2026-11-14 KST

R02 final requirement: measured CPU/RAM/disk, no made-up per-database metrics.

A: third-party psutil + remote DB system-agent telemetry, requires extra dependencies/permissions, can falsely attribute host usage to database and risk credential sharing.
B (chosen): Python standard library exposes only this DBVORA Python process cumulative CPU time (not CPU utilization %), current process resident memory (Linux /proc/self/statm or Windows psapi.GetProcessMemoryInfo, unavailable when API cannot read), and total/free bytes of an explicitly selected existing local directory's VOLUME (not the SQLite file or PostgreSQL server). Zero network/credentials/DB operations, no new paid dependencies, path-free output and strict symlink refusal. Remote server CPU/RAM are always null and unsupported, never estimated.

Command: python -m dbvora.process_resources --local-dir ABSOLUTE_EXISTING_LOCAL_DIRECTORY. Sampling is explicit, not a scheduled background task. Repeated values can form an empirical series but no trend or CPU percent is invented here.

Tests: python -m unittest -v tests.test_process_resources and the complete exact SHA cross-platform CI. This is partial R02: remote DB server metrics and long-term customer monitoring remain unverified. Windows10/11, physical restart, commercial rights and purchase acceptance still PENDING. Official P100 UNASSESSED, RELEASE HOLD.
