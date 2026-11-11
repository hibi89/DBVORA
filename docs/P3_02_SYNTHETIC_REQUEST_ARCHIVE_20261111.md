# DBVORA P3-02 — Synthetic request ledger ↔ actual archive CLI flow (2026-11-11 KST)

## Purpose and chosen design
Existing `scripts.synthetic_cli_gate` already performs real CLI snapshot → ZIP → unsigned receipt → independent restore SHA → audit on a disposable SQLite fixture. P3-01 introduced an independent request reservation ledger but did not use it with the actual CLI.

Two options evaluated:
- A (selected): add opt-in **synthetic gate-only** reservation before calling the current CLI and record/replay review after independently checked ZIP/restore; code change is narrow, no extra dependency, no customer-visible behavior change.
- B (deferred): add `--request-id` and a ledger to the production-facing archive CLI. This requires verification of crash boundaries, durable artifact receipts, file locking and Windows/NTFS behavior; modifying user-facing write semantics prematurely risks false exactly-once claims.

## Implementation
- `_reserve_new_request` requires exactly `RESERVED_NOT_EXECUTED` and does not call the CLI for an existing request, a changed plan or a ledger failure.
- The ZIP archive is checked by existing independent SHA, real CLI restore, and read-only receipt audit. Only afterward `_record_then_hold_replay` writes a caller-supplied archive digest, explicitly `RECORDED_UNVERIFIED`, and confirms any replay returns `RECORDED_REQUIRES_ARTIFACT_VERIFICATION`.
- A replay never triggers a new archive operation in this gate. The fixture, all archives and the ledger are created inside one OS temporary directory and automatically discarded.
- ZIP-only prior count: at least 7 checks, now at least 9. Optional ZSTD remains optional; no customer database path input, no auto scheduler, no actual durable customer request ledger integration, no previous backup artifact overwrites.

## Test status
The new narrow reservation/replay decision logic was independently exercised in a local Python3.13.5 stub harness: replay before write was rejected; recorded request required manual verification, 2/2 PASS. The newly committed two test cases use the real P3-01 SQLite ledger on complete source checkout but **have not been executed on this Git commit**. Prior isolated 30/30 Linux PASS belongs to earlier HEAD `65095569`; it is not a new 378/378 proof.

**NOT RUN**: complete Python >=378, original GitHub `synthetic_cli_gate` with genuine `archive_cli` and real ZIP/ZSTD restore, Node browser, actual Windows Python3.11/NTFS, power loss, customer/source data, release approvals. Commercial 55% provisional, RELEASE HOLD, no production.

## Next gates
- `python -W error::ResourceWarning -m unittest -v tests.test_synthetic_cli_gate tests.test_request_ledger tests.test_archive_cli`
- `python -m scripts.synthetic_cli_gate` (now requires ledger replay checks and >=9 gate checks)
- `python -m scripts.verify_release_gate` (minimum 378 Python)
- Independently validate Windows/NTFS ledger/archiver publication and restore before adding user-facing `--request-id` or claiming exactly-once behavior.

Only existing `feature/p0-db-map` branch, synthetic test logic, documentation and gate floors changed. Real user data, original archives, `main`, `develop`, paid CI, credentials, permissions and deployments remain unchanged.
