# NEXT_TASK — P1-C4 durable completion receipt + lineage evidence

Trigger: [디비보라 깃헙보고 작업해] or ㄱ. Verify actual GitHub feature/p0-db-map SHA and HANDOFF/STATUS/source. Never repeat already tested steps.

## Completed to P1-C3
- P0-01 SQLite readonly schema inventory and P0-02 localhost FastAPI/SVG viewer; HTTP and Node virtual DOM tested, actual browser GUI blocked by managed Chrome policy.
- P1-C0 online backup snapshot / ZIP new-path full restore; P1-C1 optional ZSTD CLI levels 1/3/9 with two controlled synthetic datasets; P1-C2 file/directory fsync, exclusive hardlink publish, failure rollback, explicit-only old temp cleanup and 8-process snapshot concurrency.
- P1-C3: dbvora.archive.recovery_catalog.inspect_recovery_catalog reads explicitly selected DBVORA archive output directory without writing to it, freezes candidates into external temporary directory, verifies SQL/ZIP/ZSTD SHA and integrity, reports CONTENT_VERIFIED_PUBLISH_UNPROVEN / FAILED_REVIEW / UNPUBLISHED_OR_ACTIVE. Bounded 512MiB, 250 recognized entries, 5000 total. scripts.preflight_archiving reports synthetic temp-only capabilities; never says ready for customer DB.
- Executed Python full 96/96 PASS /0 FAIL/0 SKIP, Linux Python3.13.5; Node DOM 1 PASS, wheel PASS, separate-process restart verified. Source details docs/P1_C3_RECOVERY.md.
- Unverified: Windows/NTFS/Python3.11, full browser GUI, actual power cuts, real customer DB and stored signed provenance. No public/Vercel deployment.

## Next P1-C4 safe implementation (synthetic only)
1. Design and implement an independently persisted *completion receipt* / catalog record for an existing verified artifact. Detect writer interrupted after publishing file but before receipt; state must be UNKNOWN/INCOMPLETE rather than SUCCESS. Store format version, artifact kind/basename/sha, standalone snapshot sha, completed verification UTC, chain anchor (if available) and provenance scope. No full source path or customer contents.
2. Receipt publication must be new-only/atomic where possible, fsync'd and fault-injection tested; never destroy/overwrite valid archives/receipts. On restart verify receipt hash against actual artifact and actual independent restore. Distinguish self-consistent unsigned receipt from authenticated provenance; do not claim signing without key/chain.
3. Test crash injection at each stage and concurrent writers; safe lookup/rebuild of missing receipt should be explicit, not automatic. No auto-delete, retention or source modification.
4. Package Windows/Python3.11 synthetic preflight instructions, assess NTFS dir sync/CLI-vs-wheel; if no Windows runtime available leave NOT_TESTED. No unapproved installer binary or distribution.
5. Rerun previous 96 tests and new tests, wheel/Node DOM and benchmark smoke. Update STATUS/HANDOFF/NEXT_TASK and verify actual GitHub HEAD + committer after commit; main/develop unchanged.

## Safety limits and approvals
Archive current SHA-256 and receipt have no trusted digital signatures and are not proof against a capable adversary. Physical sudden power loss and filesystem race safety are not established. Live customer data, delete/overwrite/retention, external transfer, public/paid deployment, keys or permission changes all require explicit user approval. On Linux only synthetic data used. Do not retry Chromium URLBlocklist '*' unchanged.
