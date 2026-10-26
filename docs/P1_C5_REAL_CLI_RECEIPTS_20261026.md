# DBVORA P1-C5 real CLI and Receipt integrated evidence — 2026-10-26 KST

## Source identity and execution context
- Private repo `hibi89/DBVORA`, branch `feature/p0-db-map`, Git HEAD before evidence commit: `506ca9fe0aea6a3a92bc07ebdda8c743dc556176`.
- Local Linux Python **3.13.5**, SQLite **3.46.1**, officially installed ZSTD CLI **1.5.7**. Files were retrieved through connected private GitHub, reconstructed in a local offline temporary working directory, and validated using `git hash-object`. Real source modules **unmodified**, not simulated:
  - `dbvora/archive/safe_zip.py`: `a58d2c3bfd3b95a98ada74f59e208b58e35d2e13`.
  - `dbvora/archive/zstd_archive.py`: `94f638ce8a252f282229312d79dda95464b2a061`.
  - `dbvora/archive/recovery_catalog.py`: `056abad676b13781778993a46c3ae7dd7da77660`.
  - `dbvora/archive/receipts.py`: `82e5782001a407a111bb385c1782bbbcd4ef9f00`.
  - `dbvora/archive_cli.py`: `818806730370868005b4723cc51677adea60960c`.
  - `tests/test_archive_cli.py`: `7aefaab7c405c702ba2d476c7e9c1a9b35fd4afd`.
  - `scripts/synthetic_cli_gate.py`: `e4d41c73b599300746136b5ed574e080781f4f1e`.
  - `tests/test_synthetic_cli_gate.py`: `a2bef5a06ae9f640dddaa4534374cabd901c4539`.
  - `scripts/verify_release_gate.py`: `7088b2a36cb797f6a5ccb5f6dc05c97fa6217545`.
  - `tests/test_verify_release_gate.py`: `a4310f3ae3279b7adec6318e001956752428f9f7`.
- Real SQLite connector, errors and fixture verified against earlier documented source SHA. Tests used only `create_fixture` synthetic SQLite and fresh OS temporary paths, **not real databases or credentials**.

## Checked-in P1-C5 CLI tests: actual engine
Command (from local reconstructed code checkout): `python -W error::ResourceWarning -m unittest tests.test_archive_cli -v`

Result: **Ran 9 tests, OK; PASS 9, FAIL 0, SKIP 0.** No stub modules were used for the 9-test run. An initial focused run of eight CLI cases used test-only Receipt imports and is NOT counted as real Receipt evidence; it was superseded by the full exact-source 9/9 test run. The ninth test covers ZIP snapshot -> archive -> unsigned receipt -> restore -> read-only receipt audit, original hash and mtime preservation. Other cases include ZSTD CLI roundtrip with installed codec, guard acknowledgements, distinct new-name snapshots, invalid args and no source path echo.

## Synthetic gate: full real CLI roundtrip
Command: `python -W error::ResourceWarning -m scripts.synthetic_cli_gate`.
Result JSON: `status=PASS_SYNTHETIC_ONLY`; `check_count=8`; `optional_zstd=passed`; `ready_for_customer_data=false`.
Eight checks: online snapshot, ZIP verified, unsigned receipt recorded, independently SHA-hashed ZIP restore, read-only receipt catalog audit, independently SHA-hashed ZSTD restore, original hash/mtime/size unchanged, zero incomplete staging files. This uses actual source modules; not an isolated mock result.

## Additional focused tests
- Command: `python -W error::ResourceWarning -m unittest tests.test_synthetic_cli_gate tests.test_verify_release_gate -q`. **22/22 PASS, FAIL 0, SKIP 0.** These are checked-in tests; some cases mock subprocess outputs to validate the fail-closed gate, and some use real synthetic temporary files for hash/path checks. They are not full external archive integration by themselves.
- Separate, ephemeral adversarial synthetic harness against actual `create_receipt`, `inspect_receipt_catalog`, and `inspect_recovery_catalog`: **12/12 assertions PASS** (not checked-in unittest cases). Receipt chaining SHA, unsigned status, duplicate Receipt refusal and immutability, independent ZIP/ZSTD receipt audit, missing Receipt not certified, read-only audit leaves files unchanged, tampered parent receipt refused, corrupt ZSTD rejected, source SHA/mtime/size preserved.
- Additional direct CLI codec smoke against actual snapshot/archive/restore but test-only Receipt module at import time: ZIP 1,006 B and ZSTD level 3 877 B; both independently restored and original unchanged. These sizes refer to a tiny synthetic fixture, not representative efficiency.

## Release and remaining gates
- **31 checked-in Python test cases exercised** across 9 CLI + 8 synthetic-gate helper + 14 unified gate-helper cases (all PASS); actual synthetic gate eight checks and separate 12 adversarial assertions also PASS. The **remaining 125 checked-in Python tests** were not run as part of the complete **156-case** repository regression suite. Do not call entire 156 PASS.
- `python -m scripts.verify_release_gate` **NOT RUN on a complete checkout**; current isolated checkout lacks other P0/API/UI/modules. Previous baseline P0 and durability checks reported in earlier handoff, not re-proven on current head.
- No Windows Python3.11/NTFS tests; no real Chromium browser, power-cut test, customer data, signed-authenticated provenance, encrypted archive, production, public distribution, or GitHub Actions run.
- Next work: reconstruct remaining private GitHub modules and checked-in tests or use an authorized full checkout, execute real 156-case regression and Node DOM/fs preflight; resolve any failures, then Windows/Python3.11 synthetic verification. No paid CI or customer DB without approval.
