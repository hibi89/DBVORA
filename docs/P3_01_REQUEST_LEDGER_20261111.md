# DBVORA P3-01 — Offline Request Reservation Ledger (2026-11-11 KST)

## Objective and alternative designs
The current archive CLI emits unique artifacts on each run. A caller retry is not safely idempotent; automated backup scheduling or retry must not be enabled before collision/resume handling.

- **A: one exclusive JSON marker per request**: no DB connection and convenient file inspection, but multi-step reserve/result transitions, crash recovery, replay and concurrent readers require more per-file atomicity rules.
- **B: separate SQLite transaction ledger (selected for a staged prototype)**: Python stdlib only, `BEGIN IMMEDIATE` serializes local reservations, fixed schema and max 10k requests, `journal_mode=DELETE`, `synchronous=FULL`, digest-only request identity. Extra file-local durability/Windows checks are needed before integration.

## Implemented bounded contract
- `reserve(existing_absolute_directory, request_id, plan_sha256)`: first call records `RESERVED_NOT_EXECUTED`; subsequent same-request reservations return `REPLAY_REQUIRES_MANUAL_REVIEW` or `RECORDED_REQUIRES_ARTIFACT_VERIFICATION` (never automatically execute again). Different plan for same request rejects.
- `record_artifact(..., artifact_sha256)`: only persists caller-provided digest. It reports `RECORDED_UNVERIFIED`; **does not verify** a file, prove provenance, publish archive, or make a customer backup.
- Existing unknown SQLite file at the dedicated ledger name is refused by application ID/version before any write. Symlink and hard-link ledgers, missing/relative root paths, invalid digests and IDs, capacity excess and state conflicts fail closed.
- The current archive CLI, dedup planner, restore, scheduling and retention remain **unchanged**. No customer data is accessed and this module is not yet in the customer execution path.

## Test evidence and failure correction
Exact module blob `ac8e7f830ae8d09a38775cdbd17b1342f02b5d66` and test blob `2968c436ecc4e0bdccbe7d19c3188280da89b426` match local Git hashes.
- Linux Python3.13.5 strict ResourceWarning **15/15** new ledger tests PASS, including duplicate reservations, restart hold, foreign DB/links, changed hash, invalid inputs and four concurrent callers.
- Initial concurrency test failed once when a second process saw the newly created file before its application marker was initialized. Improved by bounded read-only header checking, then **15/15 PASS** and 20 repeated concurrent first-reservation scenarios PASS.
- Combined source-exact bounded P0 schema 15 + ledger 15 = **30/30 PASS**; compileall PASS. GitHub full feature checkout >=376 Python, actual archive module integration, Node/browser, Windows3.11/NTFS, abrupt power loss, real customer data **NOT RUN**.

## Precise readiness limitations
A request reservation is not an archive execution guarantee; the artifact digest is unverified caller input. The source path race model is local trusted-folder only and not certified against malicious in-directory concurrent rename/hardlink manipulation. SQLite synchronous FULL is not physical power-loss certification. Do not call this exactly-once scheduling, safe automatic retry, real backup verification, or customer-ready archiving. Commercial **RELEASE HOLD** and final product **55%** unchanged.

## Next
On a complete authorized private checkout run `python -W error::ResourceWarning -m unittest -v tests.test_request_ledger tests.test_schema_review tests.test_schema_review_identifier_case`, then `python -m scripts.verify_release_gate` (minimum 376), Node DOM, native Windows/NTFS. Once validated, design an integration boundary: reserve before snapshot, never blindly retry pending requests, verify independent restored bytes and receipts before marking success, and test crashes between every publication transition. No paid CI or real customer backups without approval.
