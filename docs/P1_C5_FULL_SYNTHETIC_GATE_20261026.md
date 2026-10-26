# P1-C5 — Complete offline Linux synthetic gate evidence (2026-10-26 KST)

## Scope and provenance
- Private repository: hibi89/DBVORA, feature/p0-db-map; input source commit: 1c2f2dae6779bd391ae5922b7094535a0b2323fc
- Source/test/UI files were retrieved through the authorized private GitHub connector into a temporary Linux workspace because direct git clone DNS failed.
- 36 of 36 locally used code, UI, tests, package initializers, and pyproject files were checked with git hash-object against source Git blobs; 0 mismatches. The entire git history, documentation, and unused benchmark files were NOT cloned.
- No customer database, user credentials, remote data transfer, production environment, paid GitHub Actions, or destructive file operation occurred.
- Linux Python 3.13.5; SQLite 3.46.1; Node v22.16.0; external ZSTD CLI v1.5.7.

## Full checked-in Python unittest regression (real modules, synthetic SQLite)
Command: python -W error::ResourceWarning -m unittest discover -s tests -v
Result: Ran 156 tests in 7.552s; OK. Exactly 156 PASS, 0 FAIL, 0 SKIP.

| Checked-in file | Tests passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| tests/test_api.py | 12 | 0 | 0 |
| tests/test_archive_cli.py | 9 | 0 | 0 |
| tests/test_durability.py | 14 | 0 | 0 |
| tests/test_inventory.py | 16 | 0 | 0 |
| tests/test_receipts.py | 29 | 0 | 0 |
| tests/test_recovery_catalog.py | 20 | 0 | 0 |
| tests/test_safe_zip.py | 18 | 0 | 0 |
| tests/test_synthetic_cli_gate.py | 8 | 0 | 0 |
| tests/test_verify_release_gate.py | 14 | 0 | 0 |
| tests/test_zstd_archive.py | 16 | 0 | 0 |
| **TOTAL** | **156** | **0** | **0** |

## Unified release gate
Command: python -m scripts.verify_release_gate
Return code: 0; status: PASS_SYNTHETIC_ENVIRONMENT_ONLY; ready_for_customer_data: false.
Six steps: checkout PASS, python_unittest PASS (156 discovered, 0 skipped, skip identity checked), real_cli_roundtrip PASS (8 checks; optional_zstd=passed), compileall PASS, node_dom PASS, filesystem_preflight PASS.
Node: node --test tests/test_ui_dom.cjs reports exactly tests 1, pass 1, fail 0; this is simulated Node DOM, not a real graphical browser.
Filesystem preflight: archive_publish_test=passed_on_temporary_filesystem; windows_package_verified=false. Actual synthetic snapshot -> ZIP/ZSTD -> unsigned receipt -> independent restore -> read-only catalog -> source immutability all passed.

## Limits and next work
- This certifies Linux synthetic functionality only. It does NOT certify Windows Python 3.11 / NTFS behavior, real browser visuals, sudden physical power loss, large datasets, packaging, authentication, encryption or signing.
- Receipt provenance remains unsigned_untrusted. All archive and restored data remain plaintext. No production or customer data readiness claim. Main and develop must remain untouched.
- Next: prepare non-destructive Windows Python 3.11 / NTFS synthetic test and run on an authorized host; verify fail-closed directory sync/hardlink behavior, actual browser interaction and installer packaging. Only afterward move toward M2 deduplication/idempotent scheduling and product release.
