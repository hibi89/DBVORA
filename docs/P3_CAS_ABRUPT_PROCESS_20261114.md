# CAS v2 forced-process-exit recovery verification, 2026-11-14 KST

A/B robustness choices: A injected Python exceptions are inexpensive and controlled, but they do not emulate an abruptly killed process. B uses a separate Python child process with real os._exit(71) during synthetic second-generation manifest publication, and os._exit(72) before an independent restore publishes output. Both are no-cost deterministic and run on Windows2025 plus Ubuntu24.04. B adds stronger process-crash evidence without pretending to simulate a computer losing power.

The tests/test_cas_abrupt_process.py suite uses only newly created disposable local SQLite fixtures and their snapshots. It validates: prior manifest SHA and existing first-generation recovery survive the first crash; the restored file's old SHA survives the second crash; there is no second published manifest or restored final file; no customer source, token, external upload, automatic deletion or resume. Crashed subprocesses may leave orphaned staging files that require manual review; that is not a successful backup.

This is not physically power-loss-safe storage, disk-full-after-fsync certification, exactly-once operation, customer archive acceptance, or commercial readiness. Requires explicit owner Windows10/11 QA and product rights/NOTICE review. The release status remains HOLD and official P100 UNASSESSED.
