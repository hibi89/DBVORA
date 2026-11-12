# P4-05 — Mandatory trusted ZIP acceptance gate

**2026-11-12 KST · DBVORA P95 target · current 85% provisional · RELEASE HOLD**

## Why this matters
P4-04 introduced the separately trusted, pre-import ZIP verifier, but the full release orchestrator `scripts/verify_release_gate.py` did not call it. A normal 553+ Python/Node acceptance report could thus pass without proving that the **actual generated developer ZIP** survived separate extraction, trusted manifest inspection, synthetic execution and deliberate tamper rejection.

## Architecture choices
- **A: Keep the trusted audit as an optional manual command**. Zero orchestration work; lowest maintenance, but the mandatory release gate can omit the most important delivery step. Rejected.
- **B: Add one required local/offline portable E2E stage**. Higher Python test runtime but zero external API calls or infrastructure cost, deterministic temporary fixtures, no unapproved database access or installer. Selected.

## Implementation
1. `scripts/portable_acceptance_gate.py` creates an OS-temporary source ZIP using **the actual full-checkout `scripts.build_portable.build`** and verifies it with `verify_zip`. ZIP must report unsigned, not customer ready.
2. Extracts the previously verified ZIP to a new empty temporary destination, then uses **separately trusted checkout** `scripts/verify_trusted_extraction.py` via `python -I -S -B`. No extracted code is imported before this pre-check.
3. Only after pre-check PASS, executes **actual packaged** `dbvora.archive.review_selftest` against generated synthetic SQLite backup/ZIP/ZSTD; no customer paths. Both source and output reports must stay non-customer-ready.
4. Appends an inert comment to **temporary extracted copy only** of `dbvora/archive/request_service.py`; same trusted audit must then FAIL with `PACKAGE_DIGEST_MISMATCH`, not certify the altered package.
5. Structured JSON status: `PASS_SYNTHETIC_PORTABLE_ONLY` with four checks, archive SHA256 and explicit no-signature/no-Windows/no-customer claims; otherwise `FAIL_CLOSED` fixed error code (no output paths).
6. `scripts/verify_release_gate.py`: **new REQUIRED files**, new mandatory `trusted_portable_zip_e2e` final step. A valid status, checks>=4, digest format and no customer/signing/Windows claims are all required for the global synthetic result.
7. `tests/test_portable_acceptance_gate.py`: positive and fail-closed decision cases using a **real disposable one-file ZIP** and mocked original packager/child reports. `tests/test_verify_release_gate.py`: existing mocks updated for the new final mandatory step; missing evidence, false customer claim, invalid SHA rejected.

## Validation boundary
- In this session, exact new `scripts/portable_acceptance_gate.py` Git Blob `7e08838eae1d9d40937a34b5d7ebe41e291f6dca` was checked against the local source file hash.
- Linux Python3.13.5: original checked-in `tests/test_portable_acceptance_gate.py` Git Blob `81694c7b623edbf94894a195a11f924c0a5a41f9` was recreated with exact byte parity and executed as `PYTHONPATH=<isolated-miniroot> python -W error::ResourceWarning -m unittest -q tests.test_portable_acceptance_gate`: **7/7 PASS / 0 FAIL / 0 SKIP**, local temporary one-file ZIP, stubbed `build_portable` and mocked trusted child outputs. **This is an actual original test-file run, not a complete original checkout.**
- Linux Python3.13.5, local exact new gate module with stubbed builder/trusted child, **5/5 decision paths PASS** (success + ZIP verification failure + trusted audit failure + synthetic preview failure + tamper not rejected). The temp ZIP is real; the package builder/trusted subprocess and engine outputs are **stubs**. Python syntax compilation PASS.
- **Not executed**: checked-in `tests/test_portable_acceptance_gate.py` against complete DBVORA source (only exact test file with stubbed dependencies was run), and full `tests/test_verify_release_gate.py` against authentic complete DBVORA source; real `scripts.build_portable` from entire private repo; 553+ Python/Node; native Windows3.11 NTFS/browser; actual PostgreSQL TLS/customer data/physical restart/signing.
- GitHub Actions workflow absent in private repo; no workflow or paid runner created. Private full checkout remains inaccessible to local git DNS. The new gate is checked-in, not demonstrated as fully integrated PASS.
- Source branch functional commits: `99a47bc82bbfcab5065d374f96118f5d8adf9325` (new gate), `5f992036bf20d08390ad19a9f556535b139b77ab` (release orchestrator), `ff14d4dc3dd61a35353c472e0d6ebb5302150276` (gate tests), `a1e4578a6ca672d69a61e36eef56bcabbfc2045a` (release decision tests).

## Product completion
P4-05 adds a **required delivery-integrity test path** but neither executes the full test on the current GitHub SHA nor proves Windows durability/signatures. **Current DBVORA score remains 85/100 provisional, P95 NOT MET, RELEASE HOLD, [작업중] retain.** Do not change other product scores or override user release consent.

## Next required work
1. Obtain complete authenticated original source; run `python -m scripts.verify_release_gate` (>=553 Python tests plus Node and this new 4-check ZIP gate); fix failures, record complete PASS/FAIL/SKIP, exact SHA/zip digest.
2. On physical Windows10/11 Python3.11 NTFS, test extraction, first-run clean audit, file URL UI, cold restart/failure recovery. Do not claim durability from Linux results.
3. Separately approved read-only PostgreSQL verify-full TLS test and owner/legal rights/NOTICE assessment before any customer or public release.

Rollback via non-force Git history on feature branch. Main/develop, raw/customer data, archives, credentials, external APIs, Vercel/Production and permissions unchanged.
