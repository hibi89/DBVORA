# DBVORA P1-C6 — Strict read-only receipt audit (2026-10-27 KST)

## Issue and decision
The original `python -m dbvora.archive_cli audit --output-dir ...` exits zero with `ok:true` if scanning completed, even when an individual artifact has `receipt_status=RECEIPT_FAILED_REVIEW` and `receipt_error_code=ARTIFACT_MISMATCH`. This is existing *inspection completion* semantics, not proof that all artifacts passed. Any machine caller using only the exit code could misinterpret it.

Alternatives:
- A. Change the existing `audit` command to exit nonzero whenever an entry fails. Simple, but breaks consumers relying on read-only catalog enumeration.
- B. Keep ordinary `audit` unchanged and add opt-in `--require-all-verified` mode. Same read-only scan cost and zero additional dependencies, predictable compatibility, explicit automation safety. **Chosen B**.

## Implementation
- `dbvora/archive_cli.py`: `audit --output-dir DIR --require-all-verified` exits nonzero with sanitized `AUDIT_VERIFICATION_FAILED` when the catalog is empty or any record is not `RECORDED_AND_CONTENT_VERIFIED_UNSIGNED` with `receipt_status=RECEIPT_AND_CONTENT_VERIFIED_UNSIGNED`.
- It also rejects unresolved temporary entries, missing receipts, failed artifacts, and receipt/file mismatch by the same status rule. Default `audit` retains prior JSON report and exit semantics.
- New `tests/test_audit_strict.py` uses OS-temporary synthetic SQLite and subprocess CLI (no mocks): empty directory fails; receipt missing fails while default report works; verified unsigned receipt passes and independently tampered archive fails. No customer file, write to an existing artifact outside disposable test context, external transmission, or archive deletion.
- `scripts/verify_release_gate.py` requires the checked-in strict test file and raises the full Python test minimum **210 → 213**; `tests/test_verify_release_gate.py` default fixture now models 213 and rejects 212.

## Executed evidence
- Linux Python3.13.5, exact checked-in Git blobs `dbvora/archive_cli.py` **d06cedf5ef6dd96f9afd7335ead5b19a3b4f218d** and `tests/test_audit_strict.py` **6f64fab9b5b7920cd93601c54323bca2cba7c365** independently staged and executed: **3/3 genuine subprocess integration tests PASS**, no FAIL/SKIP/ResourceWarning. Python compileall PASS. First local attempt expected a non-existent `RECEIPT_NOT_FOUND` code instead of actual `MISSING_RECEIPT`; corrected test assertion, added explicit SQLite connection close/commit, then reran successfully. No production defect was inferred from that test assertion.
- Additional real synthetic proof from **unchanged Git-blob-matching** archive modules recovered from the prior unsigned developer preview: generated SQLite with WAL and 1,000 synthetic child records; real snapshot → ZIP/ZSTD compression → separate restored SQLite files; both restored files matched snapshot SHA-256 and `PRAGMA integrity_check=ok`, source SHA/size/mtime unchanged. Sample ZIP 6,776 bytes and ZSTD 5,664 bytes from 24,576-byte snapshot (single synthetic sample; no generalized compression claim).
- Original receipt catalog inspected a newly generated unsigned receipt and surfaced `ARTIFACT_MISMATCH` after disposable archive modification while retaining original `audit` exit 0, motivating strict option.
- Historical QA kit v3's self-tests **16/16 PASS** but it pins an older commit and does not certify current source. Historical source ZIP had 19/49 old pinned executable blobs, two old mismatches and 28 missing source/test files; it is **not** a complete current checkout.

## Unverified release requirements
- Full actual current **>=213** Python test suite / six-stage `python -m scripts.verify_release_gate` NOT RUN (no authenticated complete private checkout in container). The 3 strict tests **do not imply** the other 210 passed. Genuine Node DOM 1/1 was verified at prior checkpoint; current CLI change does not alter JS.
- Native Windows Python3.11, NTFS crash durability, hardware power cut, `file://` opening, real customer data, signing/installer/customer release NOT VERIFIED.
- Unsigned receipts are not cryptographic authenticity or NTFS crash durability evidence; a successful strict audit must not claim customer readiness. No paid CI/public source mirroring or main/develop promotion.

## Reproduction
```bash
python -W error::ResourceWarning -m unittest -v tests.test_audit_strict
python -m dbvora.archive_cli audit --output-dir /absolute/synthetic/archive --require-all-verified
python -m scripts.verify_release_gate
```
Last command requires an authorized complete private checkout; no results are claimed at current HEAD. Use ordinary `audit` to inspect detailed entry errors before retrying strict mode.
