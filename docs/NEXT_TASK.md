# NEXT_TASK — P1-C5 integration gate before further features

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
