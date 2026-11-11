# DBVORA P3-05 — Synthetic-only request authorization + independent archive verification

**Date/branch:** 2026-11-11 KST, `hibi89/DBVORA@feature/p0-db-map`.
**Status:** experimental feature source; RELEASE HOLD, no customer data access/auto-scheduler.

## Goal and design options
The existing archive CLI creates a distinct, safe new artifact on each invocation, while P3-01 only reserves a request and the P3-02/P3-03 request flow exercises temporary test fixtures. User-facing automatic retries cannot be called idempotent.

- **Option A — selected:** add a **separate, explicitly opt-in synthetic-only Python service module** `dbvora.archive.request_service.archive_once`. Keep existing archive_cli, automatic scheduling, and stored artifacts unchanged. Plan binds SHA-256 of the generated SQLite snapshot, destination, codec and compression level, so a request replay or changed plan cannot silently publish another artifact. After creation, invoke the existing independent read-only recovery verifier; do not mark ledger as authenticated/power-loss-safe. This has low maintenance and test cost, no new dependency or network.
- **Option B — deferred:** add request ID flags to the existing user-facing CLI and enable automatic recovery/retry. This changes publication semantics and requires native Windows/NTFS crash-recovery validation, signing/strong receipt review and installer acceptance. Too risky before those gates.

## Implementation
1. Require `synthetic_only=True`, `accept_plaintext=True`, an exact DBVORA-generated standalone SQLite snapshot, and distinct pre-existing absolute source/ledger/destination directories.
2. Refuse linked or nonregular snapshots, capture file identity, check SQLite integrity, bounded hash, and SHA-based immutable request plan.
3. Reserve transactionally through P3-01 SQLite ledger **before archive execution**. A replay returns `REQUEST_REPLAY_HELD`; a conflicting codec/snapshot/destination is `REQUEST_PLAN_CONFLICT`. No automatic retry.
4. Run real ZIP or installed local ZSTD archive engine. Independently inspect the published bytes through `recovery_catalog._verify_one`, compare artifact SHA and restored SQLite SHA with the source plan, recheck source identity and bytes.
5. Record SHA in ledger only with `RECORDED_UNVERIFIED` status and explicitly report `ready_for_customer_data=False`, `exactly_once_verified=False`, `power_loss_verified=False`, `windows_ntfs_verified=False`. A publication or ledger-record failure leaves the original request reserved; any published artifact requires manual review.

## Exact local verification
- The first eight original source-exact GitHub test modules at parent `47459828171439a59045f9ed44d7b1862a7cdd0f`: **115/115 PASS**, Linux Python3.13.5, strict ResourceWarning; real SQLite/ZIP/ZSTD/receipt/recovery and read-only inventory.
- New source `request_service.py`: Git Blob `1ccfa25f7e75f2bc9fe4f0387f019b313b3162cd`, 17 new tests `test_request_service.py`: Blob `9290de8772ee65242135f960b94e60dfaa55986c`. Local Git hash-object verified each exactly. 17/17 PASS, 0 FAIL/SKIP, including parallel same-ID 1 reservation, ZIP/ZSTD restore, altered plan, refused path/links, tampered ZIP, source mutation, injected publish and ledger-record failures, no secrets in failure codes.
- Combined original modules + new tests: **132/132 PASS**, 0 FAIL/SKIP. `python -W error::ResourceWarning -m unittest -q tests.test_safe_zip tests.test_request_ledger tests.test_request_archive_gate tests.test_archive_cli tests.test_zstd_archive tests.test_recovery_catalog tests.test_audit_strict tests.test_inventory tests.test_request_service`
- Original `python -m scripts.synthetic_cli_gate`: 10/10 checks, ZSTD PASS. Original `python -m scripts.request_archive_gate`: 9/9; OS temp filesystem preflight passed.
- These runs are **Linux-only partial checkout**. New GitHub code had matching file byte SHAs but **full source checkout gate >=414, browser React/UI/Node and native Windows Python3.11 NTFS/installer have not been run**. Zero customer files and credentials tested.

## Non-goals and remaining steps
Do not treat synthetic-only acknowledgement as proof that input is a real customer-allowed fixture. No signed/authenticated receipts, no source deletion, no scheduling, no incremental chain or power-loss exactly-once semantics. To advance toward 70%, run the complete source release gate (minimum Python 414) and browser/Windows tests, then verify PostgreSQL read-only and native customer use only with owner consent.

Rollback: revert the new feature commit on `feature/p0-db-map`; `main` and `develop` are unchanged.
