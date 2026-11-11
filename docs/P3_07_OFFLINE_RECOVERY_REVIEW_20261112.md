# DBVORA P3-07 — offline synthetic owner recovery review (2026-11-12 KST)

Goal: move toward 85% provisional product engineering without customer data or live DB connections. A automatic replay would risk duplicate backups and unjustified durability claims. B explicit read-only ledger/catalog audit followed by optional local HTML output is selected: no payment, API, background run, deletion or customer DB reads.

## Source

New `dbvora/archive/review_html.py`: explicit `--synthetic-only --accept-plaintext-summary`, three existing separate absolute directories, invokes P3-06 `inspect_and_reconcile` with independent P1-C3 recovery catalog. Validates contract/counts and all readiness booleans false. Generates static Korean owner table and clear manual-review banner, CSP default-src none, no JS/remote resources. Creates report with O_EXCL, mode0600 on POSIX, file fsync, no overwrite. On failure only its own newly created inode can be cleaned. Does not prove physical power-loss survival, source identity or signed authenticity.

`tests/test_review_html.py`: 22 new isolated tests covering actual temporary SQLite ledger through CLI, mock independent recovery catalog, report creation, inaccessible paths, invalid summaries, duplicate-safe new files and access gates. No real archive engine E2E.

## Use (synthetic only)

```
python -m dbvora.archive.review_html --ledger-dir /absolute/existing/synthetic-ledger --archive-dir /absolute/existing/synthetic-archives --output-dir /absolute/separate/reports --synthetic-only --accept-plaintext-summary
python -W error::ResourceWarning -m unittest -v tests.test_request_audit tests.test_review_html
python -m scripts.verify_release_gate
```

## Evidence

- Local Linux Python3.13.5 scoped current P3-06 reconstruction plus exact P3-07 new files: **39 PASS / 0 FAIL / 0 SKIP**, compileall PASS. New module Git blob `ec49917030b7f0158307084365803ffbc33abc8c` and test blob `54399a5562660e7971e067f6dce851e2d7d95e04` are exact local-tested byte matches.
- Chromium headless generated static HTML via set_content: title correct, 5 table rows, 0 network requests, 0 JS errors. Direct file:// navigation blocked by ERR_BLOCKED_BY_ADMINISTRATOR; native file opening is unverified.
- Full exact-source Python >=499 gate and Node, real ZIP/ZSTD integration, real PG/TLS, Windows3.11/NTFS/browser/installer/customer and production **NOT RUN**. No GitHub Actions triggered. No claim of actual crash durability.

## Scoring and rollback

Prior rubric P0 22 + P1 8 + P2 18 + P3 13 + P4 9 = 70. P3 owner-facing manual review routing +1 and P4 offline readable report with new-only publishing +1 = **72% provisional engineering scope**, not acceptance/commercial readiness. Target 85% **not reached**; **RELEASE HOLD**. Existing archive_cli, engines, ledger, main/develop, customers/credentials/permissions/production untouched; revert new P3-07 feature commits to roll back. 

Next: full original-source checkout Python >=499 + Node and actual original archive recovery E2E, Windows3.11 NTFS native synthetic tests, explicit owner-approved read-only PG TLS sandbox. Do not enable retention, scheduler, auto-replay or customer production access.