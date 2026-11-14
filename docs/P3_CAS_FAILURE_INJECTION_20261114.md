# CAS v2 failure injection, 2026-11-14 KST

Purpose: verify preservation of the source, previously published manifest and last good independent restore through simulated storage and publishing failures. New unit test: tests/test_compressed_cas_failures.py.

Synthetic-only temporary SQLite fixture in each test. Injected failure cases include ENOSPC before chunk publication, ENOSPC on a new generation after an older generation exists, failed manifest publication, mismatched source hash, ENOSPC during restoration fsync, failed restore publication, missing chunk, and unsafe hardlinked chunk. The hardlink test explicitly skips when unsupported on a CI filesystem. This is **not** a physical power cut, an actual customer disk or a Windows10 owner test.

No existing archive/manifest is removed or overwritten, no customer files are accessed. If an operation fails, newly written orphaned test chunks may remain for manual review; a failed operation must not certify a successful backup. No automatic cleanup/retention or retry.

Execution: python -m unittest -v tests.test_compressed_cas_failures, then python -m scripts.verify_release_gate on Ubuntu24.04 and Windows2025 for exact source SHA. P100 is UNASSESSED and sale RELEASE HOLD pending owner acceptance.
