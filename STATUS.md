# DBVORA STATUS — offline HTML CSP guard committed; full 195-case regression and Windows gate pending (2026-10-26 KST)

> **Current authoritative checkpoint is the latest dated section at the bottom.** Historical table and earlier test totals below describe older commits, not current HEAD acceptance.

Private hibi89/DBVORA, active feature/p0-db-map. Parent HEAD prior to this implementation: 0becc730722e218d79f8f294aeb8dfeeaaec78b6. Main/develop at 890f842e3ba0e13c901e785633bdd06eadc76cce. Confirm actual post-commit HEAD; no main/develop promotion.

| Capability | State | Evidence |
| --- | --- | --- |
| P0-01 schema inventory + P0-02 localhost map | SYNTHETIC_HTTP/DOM_PASS_PREVIOUS | Real browser blocked/unverified |
| P1-C0 online SQLite snapshot + ZIP restore | PASS_LOCAL_PREVIOUS | Prior P1-C4 handoff |
| P1-C1 ZSTD codec and comparison | PASS_LOCAL_PREVIOUS | Optional local zstd; Windows distribution missing |
| P1-C2 exclusive publication and simulated failures | PASS_LOCAL_PREVIOUS | No hardware power cut or NTFS proof |
| P1-C3 independent read-only recovery audit | PASS_LOCAL_PREVIOUS | No mutation of published artifacts |
| P1-C4 unsigned completion receipts + SHA chain | PASS_LOCAL_PREVIOUS | 125 Python tests prior to C5 |
| **P1-C5 explicit offline CLI** | **CODE_COMMITTED / INTEGRATION_UNVERIFIED** | snapshot, archive ZIP/ZSTD, restore, receipt, audit; synthetic and plaintext acknowledgements |
| P1-C5 newly written integration tests | NOT_RUN | 9 tests in tests/test_archive_cli.py |
| P1-C5 isolated mock boundary checks | 11 PASS / 0 FAIL | Local syntax compile + mock routing/guard tests, not actual codec tests |
| Full Python regression/ZIP/ZSTD live CLI | NOT_RERUN | Last known 125 PASS were for earlier C4 SHA |
| Windows/Python3.11/actual GUI/customer files/Actions | NOT_TESTED | Release blocked pending real runs |
| Vercel / Production | N/A | Local-only, no external deployment |

Code: dbvora/archive_cli.py. Tests: tests/test_archive_cli.py. Usage/caveats: docs/P1_C5_CLI.md.
New commands do not encrypt source/artifacts, do not schedule/delete or overwrite, and do not transmit data. --synthetic-only is an assertion, not an enforceable file-content proof.

**Next gate**: full source checkout test >=134 Python cases + Node DOM + compileall + preflight, inspect failures, then Windows/Python3.11 synthetic smoke if available. Do not claim CLI customer-ready without those checks. Need request-ID crash-safe idempotency before automation. Existing main/develop remain unchanged.

## P1-C5 synthetic CLI gate addendum (2026-10-26 KST)
- Added `scripts/synthetic_cli_gate.py`: runs the real CLI against an OS-temporary synthetic SQLite fixture when executed from a full checkout. Snapshot → ZIP → unsigned receipt → independent restore → read-only catalog → source SHA/mtime/size unchanged; optional local ZSTD is separately classified as PASS or SKIP. No customer DB, external upload, schedule, overwrite, or source deletion.
- This environment has **only the C5 CLI and isolated mock stubs**, not a full private checkout. `py_compile` of the new gate and CLI: PASS; 11 isolated CLI routing mocks + 3 isolated gate error-path mocks: PASS. These **do not prove actual ZIP/ZSTD integration**.
- New 3-test gate error suite was executed only in the temporary local workspace and is **not in GitHub**: repository upload safety validation blocked it twice; no third identical retry. GitHub contains the gate script, not these 3 tests.
- Previously committed 9 C5 integration tests and the earlier 125-regression test results are **NOT rerun**. No GitHub Actions run. Windows/NTFS/Python 3.11 and customer readiness remain NOT_TESTED. The gate deliberately reports `ready_for_customer_data: false` even if synthetic PASS.

## 2026-10-26 KST follow-up — P1-C5 unified offline release gate
- Added `scripts/verify_release_gate.py` one-command orchestrator + `tests/test_verify_release_gate.py` 7 decision tests. All 7/7 PASS locally under mocked subprocess outputs. Python syntax PASS.
- Gate requires complete checkout, >=141 discovered tests (125 C4 + 9 C5 + 7 new), actual `scripts.synthetic_cli_gate` real ZIP/receipt/restore SHA verification, conditional ZSTD verification, Node DOM, compileall, and temporary filesystem preflight. Missing requirements cause FAIL_CLOSED; reporting always `ready_for_customer_data=false`.
- Running gate on local **partial** source returned FAIL_CLOSED / INCOMPLETE_SOURCE_CHECKOUT (4 required files unavailable). This is a verified negative gate test, NOT a repo integration PASS. Private full checkout remains unavailable from current container due to GitHub DNS; previous Actions runs remain zero.
- Previously recorded 125 test PASS refers to an EARLIER GitHub SHA, not current. 9 C5 real tests and all 141 on full checkout NOT RUN. No Windows/NTFS, Python3.11, real browser, customer DB or Production validation. Main/develop unchanged. Commit parent before this update: 4c0d6ecd1f5df504502fe7acbfcac9ff39cec413.

## 2026-10-26 KST — P1-C5 gate hardening
- Python regression gate now requires at least **145** discovered tests and checks skip counts: ZSTD installed => 0 skips; absent => at most 1 optional skip.
- Node DOM exit 0 alone is insufficient: require TAP exactly 1 test / 1 pass / 0 fail.
- Exact GitHub source blobs were tested locally with mocked subprocess responses: `tests.test_verify_release_gate` **11 PASS, 0 FAIL** on Linux Python 3.13.5; py_compile PASS.
- Actual 145-test suite and real ZIP/ZSTD CLI roundtrip remain **NOT RUN**: checkout is incomplete and git clone cannot resolve github.com. The negative gate returns FAIL_CLOSED with 4 required files missing; not evidence of product failure.
- No Windows, Power-cut, customer DB, Production or GitHub Actions validation. Do not mark P1-C5 complete. Code commit `ed382b4f80d5bc894558ba31d7cb06dd9f3d940a` on feature branch; main/develop unchanged.

## 2026-10-26 KST — P1-C5 synthetic evidence hardening (source commit 50a76e905af5399d822c2beaab5e02a43dca237b)
- `scripts/synthetic_cli_gate.py`: independently SHA-256 checks generated snapshot bytes, ZIP archive bytes, restored ZIP file bytes, optional ZSTD envelope and restored ZSTD bytes. Requires exact generated basename and expected codec; rejects basename traversal, missing files and symlinks. Previously ZSTD trusted only lower-layer reported restored hash; now independent file check.
- `scripts/verify_release_gate.py`: Python unittest is run in verbose mode. When ZSTD is absent, the single allowed skip must explicitly identify `ArchiveCliTests.test_zstd_roundtrip_when_optional_codec_exists` with the expected reason; any unrelated/silent skip fails closed. Total expected discovery now >=156 tests.
- Added `tests/test_synthetic_cli_gate.py` (8 tests, prior local-only error tests plus five generated-file checks); expanded `tests/test_verify_release_gate.py` to 14 tests. Tests of these two modules in an isolated local stubbed harness: **22 passed / 0 failed / 0 skipped**, Linux Python 3.13.5. All four tested files' Git blob SHAs matched GitHub exactly. The stub harness and temporary fixture tests are NOT real end-to-end archive execution.
- **Still blocked**: full private GitHub checkout unavailable to local runtime; `python -m scripts.verify_release_gate` fails closed with 4 missing files as expected. Existing 125 prior PASS from older commit; full >=156 real suite, ZIP/ZSTD end-to-end, Windows/Python3.11, real-browser, power cut, production and customer data NOT tested. `main` and `develop` untouched. No paid CI triggered.

## 2026-10-26 KST real DBVORA archive-engine smoke (not mocks)
- Reconstructed GitHub-sha-matched actual safe_zip.py, sqlite_reader.py, zstd_archive.py, errors.py and the synthetic fixture into a private local temporary workspace. Five source SHA matches confirmed.
- Actual ZIP snapshot/compress/restore: **17 independently authored synthetic local unittest scenarios PASS, 0 FAIL, 0 SKIP**; tests covered WAL, byte+row preservation, hash, path traversal, tampering, failed publication cleanups, original unchanged. These 17 tests are not the checked-in 18 test_safe_zip methods.
- Actual official local ZSTD CLI v1.5.7 levels 1/3/9: **all three compression+restore SHA and integrity checks PASS**. Sample source 24,576 B; ZIP 1,006 B, ZSTD 906/877/867 B. No general compression claims.
- Evidence doc: docs/P1_C5_REAL_ENGINE_SMOKE_20261026.md. **Full 156 checked-in Python suite, receipts/CLI integration, Windows, browser, power loss and customer data still NOT TESTED**. No GitHub Actions run or Production deployment.

## 2026-10-26 KST — actual CLI + unsigned receipts now verified (not full release)
- Exact GitHub-sha-matched actual `archive_cli.py`, `safe_zip.py`, `zstd_archive.py`, `recovery_catalog.py`, `receipts.py`: checked-in `tests.test_archive_cli` **9/9 PASS, 0 FAIL, 0 SKIP** on Linux Python 3.13.5 with installed ZSTD CLI 1.5.7. All checks use generated temporary synthetic SQLite, no stubs in final 9-test run.
- Actual `python -m scripts.synthetic_cli_gate`: **PASS_SYNTHETIC_ONLY, 8/8 checks, ZSTD passed, ready_for_customer_data=false**; real snapshot ZIP/ZSTD, unsigned Receipt, read-only catalog, source hash/mtime, no staging leftovers.
- Checked-in `tests.test_synthetic_cli_gate` + `tests.test_verify_release_gate`: **22/22 PASS**; isolated additional real Receipt/corruption/audit assertions **12/12 PASS** (not checked-in). Total **31/156 checked-in Python test cases executed** in this turn; full 156 and Node/Windows/browser/physical-power tests still NOT RUN.
- Full source evidence: `docs/P1_C5_REAL_CLI_RECEIPTS_20261026.md`. P1-C5 CLI integration on synthetic Linux now PASS, but broader release gate still NOT COMPLETE; do not promote to main/develop or claim customer readiness.

## 2026-10-26 KST — All 156 checked-in Python tests + unified synthetic Linux gate PASS
- Supersedes the older partial 31/156 checkpoint. Reconstructed 36 code/test/UI/config files from private GitHub, verifying git SHA 36/36, zero mismatches. Input source commit 1c2f2dae6779bd391ae5922b7094535a0b2323fc.
- Real Python 3.13.5 unittest discover -v with ResourceWarnings elevated: **156 PASS, 0 FAIL, 0 SKIP**. All 10 test modules included; no stubs for actual archives, API, receipts or recovery.
- Unified python -m scripts.verify_release_gate returned status PASS_SYNTHETIC_ENVIRONMENT_ONLY exit 0: checkout, unittest, 8-check actual ZIP/ZSTD CLI roundtrip, Python compile, Node DOM TAP 1/1, and temp-FS preflight ALL PASS.
- Evidence: docs/P1_C5_FULL_SYNTHETIC_GATE_20261026.md. Node v22.16.0, ZSTD v1.5.7, SQLite 3.46.1. NOT customer-ready, no Actions/Vercel.
- Windows Python3.11/NTFS, real browser, packaging, hardware power loss and customer file safety NOT TESTED. Do not promote main/develop or claim commercial release.

## 2026-10-26 KST — Windows/NTFS diagnostic added; Linux synthetic suite 167 PASS
- Created `scripts/windows_ntfs_gate.py` with strict Windows, Python3.11, OS-temp NTFS, genuine temp-file durable publication and full six-step synthetic release gate; sanitized fail-closed JSON, no customer path, never marks power-loss/customer-safe.
- Added `tests/test_windows_ntfs_gate.py`: **11/11 PASS** isolated decision tests (not actual Windows). Updated `scripts/verify_release_gate.py` and its 14 tests to enforce **167** discovered Python cases.
- Real **Linux** Python3.13.5 entire unittest suite **167/167 PASS**, 0 failure/skip; six-step Linux synthetic gate PASS, real CLI ZIP/ZSTD 8/8; Node DOM/compileall/temp preflight PASS. Tested Git SHA of four changed source files matched remote staged Git blobs.
- Executing Windows gate on Linux returned **BLOCKED_UNVERIFIED / WINDOWS_HOST_REQUIRED**, exit1 as designed. **Windows/NTFS not actually executed.** Existing Windows directory metadata fsync not proven; do not bypass the durability check.
- Evidence/commands: `docs/WINDOWS_NTFS_VALIDATION_20261026.md`. main/develop unchanged, no Actions/Production/customer data.

## 2026-10-26 KST — Portable source developer preview & real Chromium DOM
- Linux Python3.13.5 regression **180/180 PASS**, 0 failures/skips, including **13 new portable builder tests**; all 6 real synthetic release-gate stages PASS, ready_for_customer_data=false.
- Actual headless Chromium real HTML/CSS/JS DOM against injected synthetic SQLite inventory: **5/5 browser checks PASS**, desktop 1440px and mobile 390px, no horizontal overflow, XSS identifier safe, no JS console page errors. Local HTTP and file:// Chrome navigation BLOCKED_BY_ADMINISTRATOR; HTTP browser E2E remains NOT_TESTED.
- Added offline deterministic **unsigned source ZIP builder** `scripts/build_portable.py` (23 files + manifest) and optional real Chromium probe `scripts/browser_visual_probe.py`; package is Python-source preview, NOT executable installer or customer-ready build. Actual extracted read-only CLI works with synthetic DB.
- Built `dbvora-dev-preview-0.2.0.zip` with SHA-256 `aeaeb43d4c6ce59d2a65849f253e3528fe94d8e7624bec20e13924bf13057f2f`; no customer DB/keys included; ZIP manifest detects accidental corruption but no cryptographic signature.
- Aligned `dbvora.__version__` and UI header to pyproject 0.2.0. Seven Git blobs matched local tested source SHA. Evidence: `docs/PORTABLE_BROWSER_PREVIEW_20261026.md`.
- Windows Python3.11/NTFS, power-cut, actual localhost browser HTTP, offline dependency installers, security signatures, Production and customer data remain NOT_TESTED. main/develop unchanged.

## 2026-10-26 KST — Offline standalone HTML map, no FastAPI dependency
- Added `dbvora/export_html.py` to create a **single new local self-contained HTML** from authorized SQLite schema, with embedded CSS/JS, Base64 metadata, Content-Security-Policy forbidding network, no table rows or raw source path. New-only exclusive output, no overwrite. HTML report itself is not a backup.
- Updated deterministic unsigned source ZIP to contain offline map CLI, Windows/Unix launcher templates and usage notes. ZIP: 26 source/payload files + unsigned manifest (27 entries), **43,307 B**, SHA-256 `7845f5f0e2780e22daa9ad27232879b51c78b97a9935847a75c30c8e9ac093b9`; synthetic example HTML 22,907 B SHA `618b7d9f7141d16e6445075f99f2d4666a9e1b60a1146b4770856c4d763c76c1`.
- Real Linux Python3.13.5 regression **194/194 PASS, 0 FAIL/SKIP** (12 new offline exporter tests +2 new package tests), unified synthetic six-stage release gate PASS. Headless Chromium real generated HTML DOM **7/7 PASS**, zero network requests, safe `</script>` identifiers, 390px mobile no overflow. Renderer tested via `page.set_content`, **NOT native file:// browser navigation nor HTTP e2e**.
- Detail: `docs/OFFLINE_HTML_PREVIEW_20261026.md`. Windows Python3.11 NTFS durability, native Windows HTML launch, customer-data release, Power-loss, EXE installer NOT TESTED. `main` and `develop` untouched, Actions/Production not triggered.

## 2026-10-26 KST — Offline HTML CSP anchor fail-closed hardening (current branch checkpoint)
- Previous Linux synthetic 194/194 Python PASS and Chromium generated HTML 7/7 PASS were measured on an **earlier feature commit**. They must not be relabeled as current-HEAD results.
- Found a source-review failure mode in `dbvora/export_html.py`: if `<meta charset="utf-8">` disappeared from the HTML template, the `str.replace(...)` CSP injection could silently be skipped while an HTML report was still generated. The same risk applied to a missing or duplicated `</body>` insertion anchor.
- Changed generator to reject missing/duplicated CSP and body anchors with `UNSAFE_WEB_ASSET`. Added one checked-in regression method exercising four template mutations; raised `scripts/verify_release_gate.py` minimum required Python discovery from **194 to 195** and updated mocked gate fixtures.
- Local standalone guard-condition exercise: **5/5 PASS, 0 FAIL** for valid template plus missing/duplicate charset/body markers. This does **not** execute the complete updated DBVORA module, checked-in test method, 195-test suite, or browser.
- **Current feature SHA integration acceptance: UNVERIFIED** until complete checkout runs `python -m scripts.verify_release_gate` (>=195) plus generated offline HTML browser checks. No Windows Python3.11/NTFS, native `file://`, customer DB, power-cut or release certification. No changes to `main`, `develop`, customer data, production, paid CI or permissions.
