# DBVORA P1-C7 — Orphan receipt fail-closed check

**Checkpoint:** 2026-10-27 KST. Private `hibi89/DBVORA`, branch `feature/p0-db-map`.

## Issue / alternatives / decision

The previous opt-in `archive_cli audit --require-all-verified` examined the recognized published artifacts and their receipts, but `inspect_receipt_catalog` intentionally ignores unmatched file names. An additional `dbvora-receipt-<32 lowercase hex>.json` with no corresponding published artifact was invisible to the existing all-records check. A strict machine gate could return success while a prior recorded backup was absent.

- **A — change the ordinary catalog contract:** expose orphan receipts by adding new record types. Adds more downstream compatibility risks and maintenance work; not necessary for the narrow strict check.
- **B — inspect only DBVORA receipt *filenames* after existing verified-record checks:** preserves ordinary `audit` output and unrelated files, no dependency or substantial RAM cost; bounded by the existing `MAX_DIRECTORY_ENTRIES` limit. **Selected B**.

## Implemented

- `dbvora/archive_cli.py`: import the existing `RECEIPT` filename pattern and `MAX_DIRECTORY_ENTRIES` constant, derive expected exact receipt names from already verified generated artifact names, and fail `--require-all-verified` on unmatched receipt names or excessive directory entries.
- Strict verification does **not** open orphan contents or follow symlinks; no deletion, renaming, retention action, filesystem changes or external network. Its fixed `AUDIT_VERIFICATION_FAILED` response omits paths.
- Existing non-strict `audit` inspection and unrelated local file handling are unchanged. It still reports `ignored_entry_count` and is **not** a certification of all arbitrary non-DBVORA files.
- New regression in `tests/test_audit_strict.py`: positive verified receipt, unrelated note allowed, synthetic orphan receipt rejected, no local path leakage, default audit still returns normal recognized artifact report.
- Full release-gate discovery threshold incremented from **213** to **214**; `tests/test_verify_release_gate.py` mocked expectations and fail-closed 213-case test updated.

## Executed test evidence

On Linux Python 3.13.5, with newly generated disposable SQLite fixtures and actual archive/receipt subprocess calls:
- `python -W error::ResourceWarning -m unittest -q tests.test_audit_strict`: **4/4 PASS**, 0 FAIL/SKIP; no resource warnings.
- Reconstructed the exact GitHub source for `scripts/verify_release_gate.py` and `tests/test_verify_release_gate.py` from an already owned earlier reference JSON, applied only verified line-level changes, and checked local Git blob hashes against fresh authenticated GitHub: **2/2 match**.
- `python -W error::ResourceWarning -m unittest -q tests.test_audit_strict tests.test_verify_release_gate`: **18/18 PASS**, 0 FAIL/SKIP.
- Python syntax compileall for those four files: **PASS**.
- All 16 GitHub `tests/test_*.py` files have **214 static `def test_*` declarations**. This is *source inventory*, not execution.
- Real `python -m scripts.verify_release_gate` on the intentionally incomplete local workspace: exit 1, `FAIL_CLOSED / INCOMPLETE_SOURCE_CHECKOUT`, **missing_count=10**. This is expected refusal to claim integration from missing source, not a 214-test failure.

Source Git blob verification:
- `dbvora/archive_cli.py`: `ccc965d7d62d268143f0c43e40e96bb10345d77e`
- `tests/test_audit_strict.py`: `31e62c0de1fc6598aa3bd77b4d0860bfab4b1a12`
- `scripts/verify_release_gate.py`: `fd8d39c29b73bdc96a7bd3fff45ad0646d651c21`
- `tests/test_verify_release_gate.py`: `c5aa98d938afe5058ab989197a772fbb34dd62f1`

## Limitations and next gates

**NOT VERIFIED:** full 214-case Python run, complete six-step ZIP/ZSTD/Node/preflight gate from a Git-SHA-matched complete feature checkout, actual browser navigation on current code, Windows Python3.11 + NTFS durable publication, hardware power-loss, and any customer data or installer/Production. Previous archived source ZIP is old/incomplete and QA kit pins the pre-fix SHA. Do not disable source pinning, call unsigned receipts authenticated, or interpret a strict PASS as a durable, signed backup.

Next: obtain authenticated, *complete* private checkout/runner and run `python -m scripts.verify_release_gate` (214 minimum), then Windows/NTFS, actual offline browser and failure recovery tests. No paid CI, public mirroring, automatic deletion, main/develop merge, customer data or rights changes without explicit authorization.
