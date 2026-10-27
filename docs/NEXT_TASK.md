# NEXT_TASK — authentic frontend assets and full 199-case integration gate

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

## Latest first unfinished unit — 2026-10-26 KST synthetic owner self-check
- New code `dbvora/offline_selftest.py` and four test cases committed; source ZIP bundles checker, docs `OFFLINE_SELFTEST_20261026.md`. The new code was syntax-checked and 4/4 tests passed with a **stub export boundary only**; Git blob provenance verified. Current full suite minimum **199**, not yet executed at current HEAD.
- First action when full private checkout execution possible: run real `python -m dbvora.offline_selftest` (no test-double); then `python -m scripts.verify_release_gate` with >=199 tests and `python -m scripts.offline_html_browser_probe` if actual Chromium allowed. Fail-closed if incorrect.
- Native Windows separate gate: on authorized owner PC `py -3.11 -m dbvora.offline_selftest` from developer preview and `py -3.11 -B -m scripts.windows_ntfs_gate` from complete checkout. A browser file navigation and Windows NTFS publication proof are still **NOT VERIFIED**; self-check success cannot substitute.
- Do not ask user to operate local PC until this exact native-only blocker matters; do not use customer files, paid CI, public source, installer release, or disable durability fsync.

## Active next gate after real offline Python focus (2026-10-26 KST)
- The real GitHub `export_html.py`, `inventory.py`, `sqlite_reader.py`, `metrics.py`, `offline_selftest.py`, actual HTML skeleton and checked-in tests pass focused **17/17** with synthetic data; mock CSS/JS kept explicit. Old Python ResourceWarning from `tests/test_export_html.py` patched and revalidated. Full evidence: `docs/OFFLINE_SELFTEST_REAL_CORE_20261026.md`.
- Next safely available tasks: recover exact production `dbvora/web/style.css` and `app.js` into authenticated verification environment, then Chromium generated HTML and offline navigation checks; assemble complete authenticated repo and run `python -m scripts.verify_release_gate` (>=199) without paid CI. Do not report the 17 focused tests as full 199 success.
- Native Windows Python3.11 NTFS directory-fsync and Windows `file://` remain user-machine-only validation; run `py -3.11 -m dbvora.offline_selftest` from private preview and `py -3.11 -B -m scripts.windows_ntfs_gate` from complete checkout if/when owner at Windows PC. No customer DB access, source-publication, paid Actions, installer or forced promotion without prior approval.

## 2026-10-26 KST — next after authentic frontend Chromium validation
- Latest verified targeted code: real GitHub JS/CSS blobs, `node --check` PASS; 17/17 focused Python PASS (without placeholder frontend assets); owner synthetic selfcheck 9/9 PASS; expanded real Chromium `page.set_content` **13/13 PASS** at repo probe blob `1bc43ccad0b371c2412af5d90e749be3c2d617dd`. Report in `docs/FRONTEND_REAL_ASSETS_CHROMIUM_20261026.md`.
- A real `file://` navigation attempt returned Chromium `ERR_BLOCKED_BY_ADMINISTRATOR`, **not** product failure and **not** product validation. Leave `browser_file_navigation=false`. No policy bypass.
- **First unfinished**: authorized complete GitHub private checkout, then full `python -m scripts.verify_release_gate` (>=199 Python cases + local ZIP/ZSTD/fs preflight/Node); check in-memory Chromium 13 tests. No paid Actions or source publicization.
- **Next native-only**: Windows 3.11 NTFS durability `py -3.11 -B -m scripts.windows_ntfs_gate` (complete checkout) and `py -3.11 -m dbvora.offline_selftest` (private preview); native `file://` viewer launch. Do not treat Linux proof as Windows. Owner task only once ready at PC; no customer DB, installer, automated deletion, Production without approval.

## 2026-10-26 KST — next after 201-case portable selfcheck addition
- New 0-argument Windows+Unix selfcheck launchers committed to unsigned source ZIP with both paths in `_REQUIRED`; two new packaged selfcheck tests and 201 Python test minimum added. 14 GitHub Python test files verified by SHA with **201 definitions**. See `docs/PORTABLE_SYNTHETIC_LAUNCHERS_20261026.md`.
- **First unfinished gate:** source-complete private checkout; run `python -m scripts.verify_release_gate` (>=201 cases; all six steps), including actual ZIP extraction and `dbvora.offline_selftest` subprocess test. Verify source ZIP SHA, no network/customer data; do not use mocked local directory as full checkout. If environment still cannot access complete private checkout, record this explicit blocker instead of claiming 201 PASS.
- **OS-only:** Windows Python3.11 `check_dbvora_windows.cmd` from private ZIP and native NTFS `py -3.11 -B -m scripts.windows_ntfs_gate` from complete repo, plus actual local browser `file://` opening. Linux simulated/Chromium `set_content` does not substitute for these. No customer DB, paid CI, public installer or permission changes without approval.

## 2026-10-27 KST — next after read-only C2 prototype
- GitHub branch implements `dbvora/archive/dedup_plan.py` only as **candidate byte reuse analysis**, plus 9/9 isolated synthetic tests. No chunk store/write path, refcount/GC, restore or deletion. All 15 test source files authenticated via Git blobs; **210 test definitions**, **not** 210 executed tests. See `docs/C2_DEDUP_PLAN_20261027.md`.
- Priority A: obtain authorized full private checkout and run `python -m scripts.verify_release_gate` (>=210 full Python cases, Node DOM, real ZIP/ZSTD synthetic CLI/restore and filesystem preflight), and `python -m scripts.offline_html_browser_probe` if installed Chromium works. The existing external QA kit v2 pins the **old** 201-case baseline and will intentionally reject the new branch; regenerate its SHA pins before using it. Do not disable pinning.
- Priority B: expand C2 to safe on-disk chunk manifests and independent restore only *after* complete regression, preserving original and previous verified backups. Physical dedup savings, customer restore and crash durability require independent measurement/gates; no auto-delete.
- Priority C: address `dbvora/web/app.js` resize-listener accumulation with an approved ordinary GitHub update (prior blocked), verify exact remote SHA and Chromium browser regression. No bypass of safety controls.
- Native-only Windows Python3.11 NTFS and `file://` remain a separate release blocker. No customer DB/paid CI/public installer/release without owner approval.

## 2026-10-27 KST — after UI resize handler patch (latest)
- DONE on `feature/p0-db-map`: source `dbvora/web/app.js` now installs window resize listener once outside `render()`, and `tests/test_ui_dom.cjs` guards repeated refresh registration. Commit chain `4c9f8b39dbd4` → `bf92b7d26e15`. Original 4 resize subscriptions after initial+three refreshes, revised 1; exact committed code + test executed in V8 with Node built-ins simulated and existing schema/XSS assertions PASS.
- **First uncompleted integrated gate:** authenticated full private checkout → `node --test tests/test_ui_dom.cjs` (real Node) → `python -m scripts.verify_release_gate` (>=210 Python discovered + ZIP/ZSTD synthetic roundtrip, Node DOM and temp FS) → generated HTML Chromium check if available. The V8 simulation is not a substitute for actual Node, complete regression, browser navigation or Windows testing.
- C2 `dedup_plan.py` remains read-only estimate only; no chunk persistence or real dedup restore. Native Windows3.11/NTFS, offline `file://` and power-cut remain blocking customer release. Do not promote main/develop, trigger paid CI, use customer DB, expose source/public site or relax fsync before approval and evidence.

## 2026-10-27 KST — Node runtime regression now verified; full Python gate pending
1. **DONE:** exact GitHub current `app.js` and `tests/test_ui_dom.cjs` Git blob hashes verified 2/2. Node v22.16.0 actual `node --check` PASS and `node --test tests/test_ui_dom.cjs` TAP **1 passed / 0 failed**, refresh resize listener remains one. Unlike earlier simulated Node shim, this pass used the genuine Node executable with checked-in source bytes.
2. **BLOCKED BY SOURCE AVAILABILITY (not product failure):** current **>=210** Python unittest + `python -m scripts.verify_release_gate` was not executed. The available old `dbvora-dev-preview-0.2.0.zip` lacks newer offline selftest and has older exporter; QA kit v3 pins source HEAD `31b8257` before live head; never weaken source SHA safeguards. Need full authorized current private source checkout for real suite, ZIP/ZSTD and package checks. Avoid rerunning the same unauthenticated GitHub clone known to fail.
3. **NEXT after complete checkout:** run current-source file hashes, `python -W error::ResourceWarning -m unittest discover -s tests -v` (>=210), `python -m scripts.verify_release_gate` (six stages), independently inspect failure/output. Then native Windows3.11/NTFS and `file://` tests, no customer data. Preserve main/develop, privacy, existing backups and source.

## 2026-10-27 — latest next gate after strict audit
- Done: opt-in `archive_cli audit --require-all-verified` and 3 genuine synthetic CLI tests PASS. Normal `audit` remains a read-only report even if a receipt fails; its exit code alone does not certify content.
- `scripts.verify_release_gate` minimum now **213 Python tests**, with `tests/test_audit_strict.py` required. This full gate was NOT executed; earlier QA kit pins old Git SHA and cannot be treated as current.
- Next: acquire authorized full source at live feature SHA, independently verify all Git blob IDs, run `python -W error::ResourceWarning -m unittest discover -s tests -v` and `python -m scripts.verify_release_gate`, then actual browser and native Windows Python3.11/NTFS validation. Do not disable SHA pinning or infer customer readiness.
- No customer files, paid CI, archive deletion, main/develop promotion or public deployment without required approvals and test evidence. See `docs/P1_C6_STRICT_AUDIT_20261027.md`.

## 2026-10-27 KST — active next checkpoint after P1-C7
- DONE: additional orphan-receipt fail-closed safety guard in opt-in `archive_cli audit --require-all-verified`; default audit backwards-compatible. Real disposable SQLite + archived receipt Python tests **4/4 PASS**; combined exact-current-code focused 18/18 PASS. Current Python test *definitions* **214**, not 214 executed.
- BLOCKER: complete authenticated private checkout missing. `python -m scripts.verify_release_gate` on partial source deliberately emits `FAIL_CLOSED / INCOMPLETE_SOURCE_CHECKOUT, missing_count=10`; do not count as product bug or bypass. Prior QA kit SHA pins old feature head.
- NEXT A: secure full authorized current `feature/p0-db-map` files and prove Git blob integrity; then run Python >=214, real Node DOM, ZIP/ZSTD synthetic roundtrip and temp-FS preflight using `python -m scripts.verify_release_gate`. Then native Windows3.11 NTFS/file navigation/durable restore. No paid CI or Public source clone.
- NEXT B after real full gate: only then evaluate C2 content-addressed manifest and independent restore implementation. Do not write customer data or enable auto cleanup.

## 2026-10-27 KST — current after QA v4 (first unfinished task unchanged)
1. **Completed fallback:** SHA-pinned offline source QA kit v4 produced as local conversation artifact. 50 exact source Git blobs recorded in `docs/QA_V4_MANIFEST_20261027.md`; harness **16/16 PASS**, stale or nonexistent source ZIP **FAIL_CLOSED**, no private customer/source data in kit. Obsolete JS resize patch is retired.
2. **Unfinished:** full private feature checkout/source ZIP has NOT been made available to the runtime, so **214 real Python tests and six-stage unified acceptance NOT RUN**. Manifest hashes/QA harness checks are not proof of product acceptance.
3. **Action path:** owner-authorized private source ZIP (source baseline `318a49e3031b9d0aa052221e35ebdebbec70dedd`) checked against pins; run `run_dbvora_qa.py --zip <private-zip> --report <new-report.json>` in a fully available local Python3.11+/Node environment or separately approved CI. For a newer code blob, review changes and generate updated pinned kit, never bypass pinning.
4. **Next gates:** independently inspect results and fix failing code; real ZIP/ZSTD/Node/preflight + Windows Python3.11 NTFS durability and file:// GUI; then C2 actual chunk persistence only after base safety. No paid CI, customer data, force push, public repository or unapproved external upload.

## 2026-10-27 KST — latest continuation after QA v5
- DONE: local QA v5 now hashes each pinned source member again while extracting, closing ZIP-replacement-before-execution gap. v5 selftests 19/19 PASS, previously built strict audit/gate focus 18/18 PASS. No DBVORA product/source logic changed. Evidence `docs/QA_V5_POSTVERIFY_EXTRACTION_20261027.md`.
- BLOCKED: full GitHub private source checkout unavailable to this runtime; entire **214-test** suite and full six-stage release gate remain **NOT RUN**. Existing GitHub manifest pins **50** reviewed sources at source commit `318a49e3031b9d0aa052221e35ebdebbec70dedd`; docs-only head can advance.
- NEXT: with authorized private source archive run the pinned QA v5 runner (zero-cost local), then investigate actual failed cases, verify Windows Python3.11 NTFS durability and native file browser. No automatic deletion, real customer data, Public repository changes, CI costs, or feature-to-main merge without necessary approvals.

## 2026-10-27 KST — current next checkpoint after P1-C8/QA v6
1. DONE: current Git-blob-matched export path 13/13 Python PASS, real Chromium `page.set_content` offline UI 14/14 PASS; negative control original JS 13/14 FAIL_CLOSED. Repeat-refresh listener protection committed to `scripts/offline_html_browser_probe.py`. Evidence P1-C8 doc.
2. DONE: offline QA kit **v6** rebased source SHA pins to `cafbd87e61f20cffe778692f8a29db541588eeaf`, SHA-256 `c80228f0...`, 19/19 harness selftests PASS, missing/outdated source ZIP FAIL_CLOSED. Earlier QA v4/v5 intentionally stale for current code.
3. UNFINISHED/BLOCKED: full authenticated private source checkout → all **214 Python tests** plus six-stage `python -m scripts.verify_release_gate` → independent failures/fixes. No full-release claim based on focused tests or QA selftests. Authorize complete source ZIP locally or separately approved CI; no paid CI automatically.
4. IMPORTANT ENVIRONMENT LIMIT: genuine `file://` opening produced Chromium `ERR_BLOCKED_BY_ADMINISTRATOR` in this runtime; do not circumvent policy and do not claim actual file navigation PASS. Test later in permitted native Windows3.11/NTFS + browser (no customer data), also verify crash durability and power interruption before release.
5. C2 actual dedup persistence/GC remains deferred until core integrated release gate; never auto-delete verified originals, weaken source checks or promote to main/develop prematurely.

## 2026-10-27 KST — current owner-local QA bridge first priority
- DONE: GitHub-exact source inventory 27/50 files restored from past trusted snapshots, remaining 23 missing in execution environment. No false full-suite claim.
- DONE: owner-local private source verification bootstrap v1 as temporary conversation ZIP, integrates QA v6 and Git clone (local credential manager)/existing clone, 50 Git blob pin verification and Git archive. Actual synthetic unit tests **5/5 PASS**; v6 harness **19/19 PASS** fresh extraction. No real customer data, source upload, paid CI, repository writes or source exposure. See `docs/OWNER_LOCAL_QA_BRIDGE_20261027.md`.
- BLOCKED: without an owner-authenticated private source checkout, the product's **214 Python tests, six-stage unified gate** and Windows NTFS durability remain NOT RUN. On owner-authorized Windows Python3.11/Node environment run the bootstrap once, review sanitized QA JSON and fix actual failures; do not infer PASS from harness tests.
- AFTER full verified checkout: Chromium browser file:// on permitted host; independent crash/NTFS recovery, then C2 actual dedup store design. No Git main/develop merge, paid GitHub Actions, public source or customer DB until appropriate authorization and evidence.

## 2026-10-27 KST — current first gate after owner Windows v1 ZIP mismatch
- Owner authenticated private Git clone and 50 current Git blob hashes **PASS**, but v1 `git archive` ZIP QA **FAIL_CLOSED SOURCE_BLOB_MISMATCH before execution**. Preserve its output and don't repeat v1 unchanged or waive SHA checks.
- New standalone owner-local QA **v2** (raw Git-object content instead of `git archive`): synthetic Linux **6/6** plus unchanged QA v6 **19/19** after extraction; no live Windows v2 test. See `docs/OWNER_LOCAL_QA_BRIDGE_V2_20261027.md`.
- NEXT on authenticated owner's Windows machine: unzip v2 package to clean local directory and execute `py -3.11 verify_private_source_v2.py --clone --qa-kit qa_v6 --output .`; inspect sanitized `DBVORA_QA_v2_<sha12>.json`. A host synthetic PASS is NOT customer-ready. After full Python 214 tests and gate, validate native Windows Python3.11/NTFS + file:// + restoration and power-interruption separately.

## 2026-10-27 KST — immediate task: owner direct-Git Windows UTF-8 gate rerun
- The owner **successfully cloned** `feature/p0-db-map` directly via Git. Stop requiring v1/v2 zipped QA bridges: they are unnecessary and source pins are obsolete after the code/test update.
- Windows Python3.11 gate crashed due to CP949 decoding Node's UTF-8 test output and downstream `None + str`. The feature branch fixes strict stream handling and requires >=**218** Python tests. Isolated revised routine 6/6 and real Unicode Node TAP 1/1 PASS on Linux; **full Windows gate still NOT RUN**.
- Next owner PowerShell (existing checkout): `cd E:\DBVORA_GIT`; `git status --short`; `git pull --ff-only`; only after success, `py -3.11 -B -m scripts.verify_release_gate`. Receive JSON and fix only identified failures. No new clone/ZIP/payment/customer DB; keep main/develop untouched.
- After 218-case six-step synthetic PASS: separate Windows native NTFS/power recovery and file:// browser tests; no sales or public release before evidence. Incident doc: `docs/WINDOWS_CP949_RELEASE_GATE_20261027.md`.

## 2026-10-27 KST — next exact gate after owner Windows FAIL_CLOSED
- Owner's Windows Python3.11 218-case run at `a867f744...`: checkout & compileall PASS; Python unit/CLI/Node/preflight all FAIL. It returned no failure IDs/codes; do not infer all independent product faults. The `safe_zip._sync_directory` POSIX directory fsync path is a plausible shared native-Windows blocker, but **not proven on owner host**.
- Added fail-closed path-free JSON diagnostics: min **223** Python tests (23 in gate unit module), returns failure test IDs, CLI safe error code, Node TAP counts, filesystem publish code, stage exit codes. Original guards unchanged. See `docs/WINDOWS_RELEASE_GATE_DIAGNOSTICS_20261027.md`.
- NEXT (owner existing Git checkout; no ZIP): `cd E:\DBVORA_GIT`, `git status --short`, `git pull --ff-only`, `py -3.11 -B -m scripts.verify_release_gate` only if pull succeeded. Review sanitized JSON and fix specifically reported failures. No direct customer database, path export, public mirror, paid CI, main/develop merge, weakened fsync, or destructive archive change. Native Windows/NTFS recovery/Power-cut/file:// still separate.

## 2026-10-27 KST — current after Windows 223-case fail-closed
- Owner direct-Git real Windows Python3.11 gate: **223 discovered, 9 skipped, Python EXIT1**, `CLI_PUBLISH_FAILED`, filesystem `PUBLISH_FAILED`, Node EXIT0 `TAP_SUMMARY_MISSING`; checkout and compileall pass. Old 218 result superseded. No 223 PASS claim.
- Feature code now explicitly forces Node TAP `--test-reporter=tap` and reports bounded skipped test IDs; **225 discovery** (25 gate regression tests). New full Windows 225 suite remains NOT RUN. Synthetic Node v22 explicit TAP 1/1 PASS; Git-authenticated old `safe_zip` blob injected unsupported directory-open yields fail-closed `PUBLISH_FAILED`.
- First safety-critical next work: select between Windows archive fail-closed (no writes) vs separately gated native create-only publication design. Proposed B, but **require owner's explicit approval** before changing durable-archive write behavior. See `docs/WINDOWS_NTFS_PUBLICATION_OPTIONS_20261027.md`. Do NOT bypass `_sync_directory`, lower skip policy, or enable customer use merely to pass tests.
- After design approval and local synthetic implementation validation, owner uses existing `E:\DBVORA_GIT`, `git pull --ff-only`, and one `py -3.11 -B -m scripts.verify_release_gate` for refreshed failure IDs & Node TAP result. No ZIP, new clone, paid CI, public repo, main/develop promotion, deletion or real customer data.

## 2026-10-27 KST — approved Windows option B, next first native check
- **DONE**: isolated NTFS create-only Win32 proof-of-concept in `dbvora/archive/windows_ntfs_publish.py`, `scripts/windows_ntfs_publish_probe.py`, `tests/test_windows_ntfs_publish.py`. No production backup code integration, no fsync bypass. Local Linux3.13.5 synthetic **12/12 PASS**, Git blob SHA 3/3 verified, compileall PASS, standalone non-Windows fail-closed. Gate now expects **237** Python cases; real integrated 237 NOT RUN.
- **IMMEDIATE NEXT**: owner authenticated existing `E:\DBVORA_GIT` only: `git status --short` → `git pull --ff-only` → `py -3.11 -B -m unittest -q tests.test_windows_ntfs_publish` → `py -3.11 -B -m scripts.windows_ntfs_publish_probe --synthetic-only`. Requires no ZIP, new clone, secrets, paid CI, or real/customer DB. Report full sanitized probe JSON, do not treat PASS_SYNTHETIC_ONLY as power-cut/customer proof.
- Afterwards assess real NTFS API behavior, create-only failure handling, concurrent publication and crash integrity, then integrate only if metadata/backup durability can be honestly supported; retain old Windows `PUBLISH_FAILED` otherwise. Separate earlier Node TAP and OS-dependent 9 skips from archive issues. No main/develop merge or commercial release pending validation. See `docs/WINDOWS_NTFS_NATIVE_PROTOTYPE_20261027.md`.

## 2026-10-27 KST — Windows native 12/12 + 6/6 PASS, now 15-case concurrent/exit gate
- **DONE owner actual Windows**: 12/12 `tests.test_windows_ntfs_publish` PASS 0.111s, `scripts.windows_ntfs_publish_probe --synthetic-only` PASS_WINDOWS_NTFS_SYNTHETIC_ONLY with six PASS steps. Actual Python3.11 + OS temp NTFS native tested; no source ZIP. Both crash power-loss and metadata durability remain unverified, customer_ready=false.
- **DONE code**: Added three isolated create-only checks: concurrent competing publication, child exit before publish, child exit after native move. Total isolated NTFS **15 tests**; full discovery minimum now **240**. Local Linux stand-in of new three test scenarios 3/3 PASS, but newly checked-in complete 15 and native 15 NOT yet executed.
- **IMMEDIATE next owner-native check**: in existing Git checkout, ensure clean `git status --short`, `git pull --ff-only`; then `py -3.11 -B -m unittest -q tests.test_windows_ntfs_publish`; share result. No need rerun original 6-step probe. See `docs/WINDOWS_NTFS_NATIVE_OWNER_EVIDENCE_20261027.md`.
- **AFTER native 15 check**: plan independent Windows NTFS safe archive adapter with atomic create-once, metadata persistence limitations, SHA restore, process failure/restart/concurrency tests, opt-in only. Do **not** remove `safe_zip._sync_directory`, enable real DB, claim backup durability, promote main/develop, incur paid CI or publicize.

## 2026-10-27 KST — next W0/W2 Windows NTFS research gates (design checkpoint)
- Reviewed all current Win32 and legacy archive publication/receipt boundaries at Git SHA `9112244781e91f155d0be0e7c706e532be9c72fe`. Detailed A/B cost-maintenance-risk comparison and W0-W5 acceptance: `docs/WINDOWS_NTFS_ARCHIVE_ADAPTER_PLAN_20261027.md`.
- W0 first unfinished: owner Windows Python3.11 existing `E:\DBVORA_GIT`, clean `git status --short`, `git pull --ff-only`, then `py -3.11 -B -m unittest -q tests.test_windows_ntfs_publish` **only**. Native 15 results PENDING; original 12+6 PASS is not a substitute. Do not repeat six-step probe without new failure.
- W2 after W0: synthetic OS-temp-only shadow adapter with SQLite backup + archive + byte-exact independent restore, no production `safe_zip` rewrite, no customer DB, no overwrite, and no durability success claim from API flags. Production connection needs separate approval.
- Status of this checkpoint: design documentation committed, no new execution or product-code modifications. Full >=240 suite, original Windows archival failures, physical power durability, file:// and customer use remain BLOCKED/UNVERIFIED.

## 2026-10-27 KST — current next step W2 native and W3 synthetic recovery research
- **W0 PASS**: owner Windows isolated native 15/15 twice; second run after updated feature checkout `5ef6187`. No repeat needed.
- **W2 code + simulated verification PASS**: synthetic temporary SQLite online snapshot + ZIP, independent exact restore, original source unchanged. Eight Linux3.13 local tests PASS. Exact-source hashes recorded in `docs/WINDOWS_NTFS_SHADOW_EVIDENCE_20261027.md`. The new CLI accepts only `--synthetic-only` and no file paths; not integrated with production.
- Next native-only evidence when a Windows runner is available: `py -3.11 -B -m scripts.windows_ntfs_archive_shadow --synthetic-only` and `py -3.11 -B -m unittest -q tests.test_windows_ntfs_archive_shadow`. Do not require the owner to repeat the old 15 or six-step native probe. This native W2 gate is pending, **not** required for us to continue designing and testing W3 synthetic restart/receipt-gap logic offline.
- In parallel GPT-6 can independently review and construct W3 process-exit/restart/orphan receipt negative tests on a synthetic filesystem; production activation and real/customer data require distinct approval.
- Release minimum now >=248; the **full** native Windows CLI/test/browser gate is still fail-closed/unverified. No paid CI or privilege/production changes without owner approval.

## 2026-10-27 KST — MVP-first next unit
- Current feature includes new synthetic-only `dbvora.demo_preview`, six regression tests, and `docs/MVP_GAP_MATRIX_20261027.md`. Full gate minimum **254**, but complete source test not executed. One-command preview requires Python3.11+ and an existing absolute output folder; generates no customer DB copy.
- NEXT: read full product at latest SHA, verify real `tests.test_demo_preview` + `tests.test_export_html` + `tests.test_offline_selftest` and browser if environment allows; then implement missing multi-DB topology with explicit connectors/evidence. Avoid repeatedly asking owner to run unit tests where local/CI synthetic runners are available.
- Keep archive Windows fail-closed; only revisit NTFS zip restore after P0 visual MVP is demonstrably stable. No production/customer DB, installer, paid CI, automatic archive delete or public release without approval. User can issue `ㄱ` to continue.

## 2026-10-27 KST — accelerated P0-03 multi-DB registry integrated (workspace HTML pending GitHub integration)
- DONE in current feature: `dbvora/workspace.py` merges 2–8 explicitly selected read-only SQLite inventories into path-free schema/fk/size workspace; source SHA `643d2741f0b3e1dd8edb5ae23c794ee45ce5128d`.
- DONE tests: `tests/test_workspace_registry.py` seven real synthetic cases, source SHA `0a52ae3cd66027b92f96703de85c6b419055167a`; Linux Python3.13.5 local total **22/22** over registry seven + prototype 15 (full current GitHub checkout and production NOT RUN). Release required minimum >=261.
- SEPARATE LOCAL PROTOTYPE: `dbvora/workspace_html.py` offline multi-DB viewer with actual Chromium set_content DB/table clicking **12 checks PASS, 0 pageerrors**, plus 15 source integration tests. Source/test **NOT YET IN GITHUB**, preserved in conversation developer ZIP `DBVORA_P0_multidb_source_20261027.zip` and working container path. See `docs/P0_03_WORKSPACE_EVIDENCE_20261027.md`.
- NEXT highest priority: upload tested HTML viewer/test source into feature with exact hashes, real full-source integration, then native `file://` as supported. Do not mark multi-DB UI shipped before that. Original archive Windows durability/production release remains fail-closed and unverified.
