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
