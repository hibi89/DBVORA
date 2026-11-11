# P3-06 — Read-only request ledger and archive reconciliation

**2026-11-12 KST · hibi89/DBVORA@feature/p0-db-map · synthetic-only · RELEASE HOLD**

## Decision and boundaries
- **Option A (not selected):** automatically resume RESERVED requests or mark RECORDED archives successful. Faster unattended operation, but unsafe after process death: reservation alone cannot tell whether a ZIP/ZSTD file was durably published, and a matching unsigned SHA does not prove publisher identity.
- **Option B (selected):** owner-triggered *read-only* check. Open an existing ledger with SQLite `mode=ro`, validate application/user version, schema and integrity, and compare only recorded SHA-256 digests with an independently restored archive catalog from the existing `recovery_catalog`. No retry, approval, deletion, database mutation, network or customer data.
- No request IDs, SQL row data, DSNs, archive directories or credentials are included in output. Only status counts, not file paths. Explicit `--synthetic-only` is required; this is a caller declaration, **not** independent proof that inputs are synthetic.
- Catalog matching may return `RECORDED_MATCH_REVIEW_REQUIRED`, which is still NOT proof of origin, physical power-loss durability, or exactly-once execution. RESERVED always requires human review. No automatic use in existing customer CLI/scheduler.

## Local synthetic invocation
```sh
python -m dbvora.archive.request_audit --ledger-dir /absolute/existing/ledger --archive-dir /absolute/existing/archive --synthetic-only
python -W error::ResourceWarning -m unittest -v tests.test_request_audit
python -m scripts.verify_release_gate
```
Ledger must already exist and have the P3-01 `.dbvora-request-ledger-v1.sqlite` schema. Artifact directory must already exist; `inspect_recovery_catalog` verifies published generated ZIP/ZSTD content into a separate temporary folder. No files are created in ledger or archive directories by this audit.

## Evidence and incomplete gates
- Added `dbvora/archive/request_audit.py`, `tests/test_request_audit.py`. **Locally reconstructed isolated Linux Python test scope: 17 PASS, 0 FAIL**; syntax/compileall PASS. This is **not** an exact remote checkout whole-repository result.
- Source and tests committed to GitHub feature branch. Full release-gate Python minimum **460→477** and REQUIRED includes the new files; test runner's simulated count fixtures updated. **Full gate NOT RUN** due to private clone DNS resolution restriction in current environment; no GitHub Actions workflow runs exist for this branch.
- Original `request_ledger.py`, `request_service.py`, archive engines, actual customer files, existing main/develop, Windows/NTFS, PostgreSQL auth/TLS and production are untouched/unverified.
- Rollback is standard revert of new feature commits; no force push. New files only, except release-gate coverage floor and its test fixture.

## Reassessment
Baseline DBVORA **70% provisional** (P0 22, P1 8, P2 18, P3 13, P4 9). The owner-review diagnostic implements one P3 partial capability but cannot be counted as real crash-safe recovery, so overall **70% remains unchanged** pending full original-source and Windows integrated verification. Target **85% not met**. RELEASE HOLD.

## Next action
1. Full authorized source checkout, `python -m scripts.verify_release_gate` expected at least **477** discovered cases, Node TAP, ZIP+ZSTD and synthetic archive round-trip. Diagnose failures without relaxing gates.
2. Real Windows 3.11/NTFS synthetic ledger + ZIP/ZSTD recovery, safe file:// HTML, Windows packaged source compatibility.
3. Authorized read-only PostgreSQL test role and TLS verification, independent successful recovery after simulated termination. No external credentials/customer data/paid actions without owner approval.
