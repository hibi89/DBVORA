# DBVORA complete synthetic regression baseline, 2026-11-14 KST

The prior full-gate minimum (553 tests) predated the current source tree. On source 7b9ee1e2ccb05fad64bd171cf858ce401c9da0fe, Ubuntu24.04 Python3.11 discovered 668 PASS and Windows hosted verification was pending at the time of this update.

New minimum is 668 discovered tests (not an assertion that all final user requirements have passed). Required checkout also includes actual compressed CAS fault injection, abrupt process exit safety, daily/weekly slots and the existing daily synthetic tests. If those files disappear or test coverage falls below 668, release gate fails closed. Unit tests mock 668 tests and independently check that 667 fails, including optional ZSTD skip identities. The baseline controls regression coverage, not official product completion percentage, signed release, physical power-loss, Windows10 acceptance, licence status or customer data safety.

Windows2025 may skip exactly the separately named POSIX chmod 0600-only case; no other silent skip is allowed. Real outcome must be re-read at exact GitHub SHA. P100 UNASSESSED, [작업중], RELEASE HOLD, commercial registration0.
