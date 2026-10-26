# NEXT_TASK — active 195-case CSP guard regression + native Windows/NTFS gate

> **Latest active work is the final section of this document.** Older first-unfinished headings below are preserved as historical checkpoints and must not be repeated.

Trigger: ㄱ / [디비보라 깃헙보고 작업해]. Read feature/p0-db-map latest remote SHA, HANDOFF, STATUS, AGENTS, REQUIREMENTS and docs/P1_C5_CLI.md before acting. Do not repeat P0/C0/C1/C2/C3/C4.

## Implemented this turn
- New dbvora/archive_cli.py subcommands: snapshot/ZIP or ZSTD archive/independent new-path restore/unsigned receipt/read-only receipt audit. Explicit --synthetic-only and --accept-plaintext / --accept-unsigned; no default customer access, overwrites, server write API, deletion, schedule or uploads.
- New tests/test_archive_cli.py 9 synthetic integration tests. Local code compile PASS, independent mock CLI checks 11 PASS, but actual existing archive modules and 125 regression tests NOT RUN in this current container (no private GitHub checkout/network).
- docs/P1_C5_CLI.md records end-user commands, limitations and lack of true idempotency.

## First unfinished gate (mandatory)
1. Obtain full current feature branch checkout in an environment with private repo access, run \`python -W error::ResourceWarning -m unittest discover -s tests -q\` (expected >=134 cases if all tests discovered), \`python -m compileall -q dbvora tests scripts\`, \`node --test tests/test_ui_dom.cjs\`, \`python -m scripts.preflight_archiving\`; record exact pass/fail/skip and fix any integration errors. Do not infer PASS from mock smoke.
2. Test actual synthetic ZIP/receipt/audit roundtrip; ZSTD optional only when locally present. Confirm source bytes/mtime unchanged, fail-closed on corrupt/nonexistent args, no source paths in CLI output; verify no unintended files outside designated demo directories.
3. Review Windows/Python 3.11 and NTFS support; existing safe publish currently fail-closed if dir fsync unsupported. Use ZIP-only fallback if optional zstd missing, never quietly claim success. No unmanaged browser policy bypass.
4. Add retry request-ID ledger or explicit deduplication with concurrency/power-loss tests BEFORE calling any automated operation idempotent. CLI retries currently create distinct new artifacts, never overwrite existing; classify as not idempotent.
5. Update STATUS/HANDOFF/next task with real test evidence + SHA and assess product roadmap priorities: PostgreSQL read-only, multi-DB map, metrics, packaging vs compression refinements.

## Prohibited without approval
Real customer DB access, deletion/retention/overwrite, network/third-party uploads, external paid service, public distribution, installed local credentials or Windows installer release. Signed provenance and physical power-loss guarantee are NOT provided.

## P1-C5 synthetic gate added (2026-10-26 KST)
- `python -m scripts.synthetic_cli_gate` on a **complete local checkout** is now the short one-shot offline acceptance smoke: it exercises *real* CLI snapshot, ZIP, unsigned receipt, restore, audit and source immutability using ONLY an OS-temp generated SQLite fixture. ZSTD is optional; output is JSON, always `ready_for_customer_data=false`.
- **NOT yet executed end-to-end in this environment**: the container can only access separate CLI files and mocks; private GitHub clone cannot resolve, and paid/private Actions have not been authorized or run. New script py_compile PASS, CLI 11 mocks PASS, gate error handling 3 isolated local mocks PASS. The standalone gate mock test file could not be uploaded due to two security validation blocks; do not assume it is in GitHub.
- Mandatory gate: real `python -m scripts.synthetic_cli_gate`, full `unittest` >=134, Node DOM, compileall, preflight. Inspect failures; preserve previous code/data and fix minimal problems. On any failure keep P1-C5 as PARTIAL and no customer release. Windows 3.11 filesystem semantics remain NOT_TESTED.

## 2026-10-26 KST next mandatory gate (no additional feature creep)
- Execute `python -m scripts.verify_release_gate` from a **complete** feature/p0-db-map checkout. It fails unless >=141 tests discovered, actual synthetic CLI ZIP+receipt+restore+audits PASS, conditional ZSTD PASS or explicit absent skip, JS DOM/compileall/preflight PASS. Reports `ready_for_customer_data=false` even if all synthetic checks pass.
- Executed only 7/7 mocked runner logic unit tests (PASS), new Python compile PASS, and negative incomplete checkout test (FAIL_CLOSED, expected). **Full 141-test suite has not run** and must not be reported as success. The incomplete source is a tool environment constraint rather than an observed product failure.
- If full checkout available, collect JSON gate result and test summary with exact failures, fix first failing code, then update STATUS/HANDOFF with SHA. No actual customer DB, public release, or paid CI without approval.

## First unfinished task after latest 2026-10-26 gate hardening
- Run `python -m scripts.verify_release_gate` from a complete authorized `feature/p0-db-map` checkout. It now requires >=145 Python cases, 0 skips when ZSTD is present (otherwise <=1 optional skip), Node TAP exactly 1 PASS, real synthetic SQLite ZIP/ZSTD restore, compileall and temporary filesystem preflight. Gate still never authorizes customer data.
- Latest executed evidence: 11 focused mocked decision tests PASS, Python syntax PASS, exact blob SHA matched committed code. Full suite and real archive end-to-end have not run due unavailable complete checkout. A partial checkout correctly returns FAIL_CLOSED; do not mislabel as functional breakage.
- Next once checkout works: capture full pass/fail/skip and failing names; repair root causes, run Windows Python3.11/NTFS synthetic trial, reassess remaining product roadmap. Do not promote, deploy, or invoke paid CI without approval.

## First unfinished gate after 2026-10-26 P1-C5 evidence hardening
- **Required**: from complete private feature checkout run `python -m scripts.verify_release_gate`. It now requires **>=156** Python tests; when optional ZSTD is absent, only the explicitly named CLI ZSTD roundtrip skip with the documented reason is allowed. It also independently hashes generated ZIP/ZSTD archive and restored files in the synthetic gate, checks Node TAP, compileall and temp filesystem preflight.
- **Current evidence only**: Linux Python3.13.5, 14 release-gate mocked process tests PASS + 8 real temporary-file helper/mocked-CLI tests PASS = 22; exact 4 source Git blobs matched local tested SHA. Actual full unittest >=156, real ZIP/ZSTD end-to-end, Windows/NTFS remain NOT RUN due incomplete private checkout. Existing prior 125 tests belong to earlier git revisions.
- Next: obtain complete authorized checkout/runner, run the 156+ gate and fix real failures. Do not run customer DB operations, paid CI, public source mirroring, or Production without explicit approval. Preserve main/develop and existing data.

## NEW EVIDENCE 2026-10-26: real ZIP/ZSTD engine executed
- Actual GitHub SHA-matched local modules directly executed: ZIP synthetic smoke **17/17 PASS**; ZSTD levels 1,3,9 actual independent restore **all PASS**. Detailed reproducible source provenance, environment, cases, sample sizes in `docs/P1_C5_REAL_ENGINE_SMOKE_20261026.md`.
- **First remaining task changes**: acquire `recovery_catalog.py`, `receipts.py`, checked-in `archive_cli.py`, and `test_archive_cli.py` in the same isolated workspace; validate exact Git SHA; run the 9 real CLI tests (ZSTD binary available). Next verify read-only catalog and receipt SHA lineage, then assemble/run complete 156 tests. Do not mark any unexecuted case PASS.
- Still require Windows Python3.11, real browser and power-loss/prod security gates; no customer DB or paid CI without approval.

## 2026-10-26 KST — P1-C5 real CLI+Receipt Linux gate completed
- Exact original modules: `tests.test_archive_cli` **9/9 PASS** with real Receipt and catalog, no stubs. `scripts.synthetic_cli_gate` **8 checks PASS** with ZSTD. `tests.test_synthetic_cli_gate` + `tests.test_verify_release_gate`: **22/22 PASS**. Extra actual Receipt/lineage/corrupt-audit synthetic checks **12/12 PASS**, not committed as tests. Details/source Git blobs in `docs/P1_C5_REAL_CLI_RECEIPTS_20261026.md`.
- 31 of 156 checked-in Python tests exercised, full 156 not run. Next: acquire remaining 125 checked-in test code and P0/API dependencies, complete unified `python -m scripts.verify_release_gate` and Node DOM and preflight, then Windows3.11/NTFS. No commercial release or customer DB operations, no unapproved paid Actions or public source mirror.

## 2026-10-26 — COMPLETED Linux synthetic 156-case release gate; NEW next step
- Supersedes all above old 31/156 and missing-source notices: Git-SHA-matched source workspace 36/36, actual checked-in Python regression 156/156 PASS (0 FAIL, 0 SKIP), unified six-step synthetic gate PASS, CLI ZIP/ZSTD+receipt/audit 8 checks, Node DOM 1/1, compileall and filesystem preflight.
- New first blocker: Windows Python3.11/NTFS fail-closed durability/hardlink/restore compatibility on an authorized actual Windows host, plus real-browser GUI, packaging and hardware power-loss evidence. No client files or paid Actions without approval.
- Full evidence at docs/P1_C5_FULL_SYNTHETIC_GATE_20261026.md. Linux synthetic PASS is not customer data readiness. Main/develop not promoted.

## First unfinished task after 2026-10-26 Windows diagnostic implementation
- Linux **167/167** Python suite PASS and full six-step synthetic gate PASS; 11 Windows preflight decision tests PASS (mocked OS facts). Windows diagnostic code complete but **not executed on native Windows**; Linux run correctly refused.
- On authorized private Windows Python3.11 NTFS machine: run `py -3.11 -B -m scripts.windows_ntfs_gate`. On `DURABILITY_NOT_PROVEN_FAIL_CLOSED`, preserve strict failure, investigate native Windows file+directory persistence and rollback, only then adapt writer with Windows-proven tests. See `docs/WINDOWS_NTFS_VALIDATION_20261026.md`.
- Next after Windows: actual GUI browser and packaging. No customer data, Public mirror, paid Actions, destructive cleanup or Production without approval.

## 2026-10-26 — developer preview + Chromium DOM completed
- **180/180** Python full source regression PASS (0 fail/skip), 6/6 synthetic Linux release gate PASS, optional real Chromium injected synthetic browser DOM 5/5 PASS; tested original source version alignment and deterministic 23-file unsigned portable developer ZIP. See `docs/PORTABLE_BROWSER_PREVIEW_20261026.md`.
- **First unresolved**: genuine Windows Python3.11/NTFS synthetic durability and independent restore (`py -3.11 -B -m scripts.windows_ntfs_gate`); current archive fsync may fail closed as designed. Then Windows actual localhost HTTP browser and standalone installer/offline UI dependency packaging.
- Browser local URL navigation blocked by current sandbox. Do not confuse Chromium `set_content` + fetch stub with HTTP browser E2E, though actual render and user interaction verified. No customer data, paid CI, main/develop promotion or public release.

## 2026-10-26 — offline HTML preview implementation complete
- New local one-file read-only schema HTML without FastAPI/Uvicorn/HTTP, now bundled in developer source ZIP with Windows & Unix map exporters. Full **194/194** Python Linux suite PASS, all six offline synthetic release stages PASS. Optional real Chromium generated HTML **7/7 PASS**: correct FK & table cards, text-safe hostile names, no external network requests, no mobile overflow.
- Full steps, asset safety, explicit SHA, privacy limits: `docs/OFFLINE_HTML_PREVIEW_20261026.md`. Single-file HTML contains schema identifiers so user must authorize sharing; no rows, DB paths or customer data tested.
- Remaining actual Windows3.11/NTFS archive durability and portable Windows launcher/browser open, native installer, browser HTTP E2E unverified. No production or customer data authorization.

## Current next work — after CSP fail-closed hardening (2026-10-26 KST)
- The new HTML template marker security guard is committed on feature/p0-db-map, with one new checked-in Python test and revised **195-case minimum**. Prior **194/194** remains valid only for the preceding commit; current-HEAD full regression is **NOT RUN**.
- First reproducible gate on an authorized complete branch checkout: `python -W error::ResourceWarning -m unittest discover -s tests -v` (expect >=195, zero failures), `python -m scripts.verify_release_gate`, and `python -m scripts.offline_html_browser_probe` when an allowed Chromium environment is available. Verify HTML CSP actually exists, network stays disabled, source hash/mtime unchanged.
- Highest OS blocker still native Windows Python3.11/NTFS `py -3.11 -B -m scripts.windows_ntfs_gate` and real Windows offline HTML launcher/`file://` browser. Do not bypass directory sync, use customer DB, release a Windows installer, pay for CI, or promote main/develop without approval and supporting evidence.
