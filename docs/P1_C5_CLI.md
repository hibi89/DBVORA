# DBVORA P1-C5 — explicit offline archive CLI (synthetic preview)

2026-10-26 KST. Work branch: feature/p0-db-map.

## Scope and safety
- Entry point: python -m dbvora.archive_cli --help (Python >=3.11 declared; Linux Python 3.13 only exercised).
- No network, scheduler, customer DB selection UI, deletion, overwrite, automatic retention or web API write operation.
- snapshot/restore produces **unencrypted SQLite records**. ZIP and ZSTD archives are **not encrypted**. Sidecar receipts are **unsigned/untrusted**, not an authenticated or power-loss durable proof.
- Each write demands --synthetic-only and --accept-plaintext (receipt: --accept-unsigned). These are *operator assertions*, not cryptographic proof input is synthetic. Never use customer files in this preview.
- Explicit absolute input paths and existing absolute output directories; paths are redacted to basenames in CLI success output. Archive and restore input must have DBVORA artifact filename. Output must differ from input parent. Existing archive functions enforce new-only publication and independent verification.
- Repeated valid commands create *different* new artifacts; this does not constitute exactly-once idempotency. No dedupe or retry ledger yet; see NEXT_TASK.

## Synthetic end-to-end example (source checkout)
1. Create the fixture and separate directories using Python:
   python -c "from pathlib import Path; from tests.fixtures.make_sqlite import create_fixture; r=Path('dbvora-cli-demo').resolve(); [(r/p).mkdir(parents=True,exist_ok=True) for p in ('source','snapshots','archives','restored')]; create_fixture(r/'source'/'fixture.sqlite')"
2. Inspect help: python -m dbvora.archive_cli --help
3. Create a snapshot (replace absolute paths with your demo folder):
   python -m dbvora.archive_cli snapshot --source ABS/source/fixture.sqlite --output-dir ABS/snapshots --synthetic-only --accept-plaintext
4. Use the resulting \`snapshot_path\` basename to construct the next absolute argument:
   python -m dbvora.archive_cli archive --snapshot ABS/snapshots/dbvora-UUID.sqlite --output-dir ABS/archives --codec zip --synthetic-only --accept-plaintext
   Optional codec: --codec zstd --level 3 (requires installed local zstd binary).
5. Restore and inspect:
   python -m dbvora.archive_cli restore --archive ABS/archives/dbvora-UUID.zip --output-dir ABS/restored --synthetic-only --accept-plaintext
   python -m dbvora.archive_cli receipt --artifact ABS/archives/dbvora-UUID.zip --synthetic-only --accept-unsigned
   python -m dbvora.archive_cli audit --output-dir ABS/archives

Output success JSON uses artifact basenames, SHA, metadata and status only; an error is JSON to stderr with return code 2 and no input path. Snapshot/ZIP/ZSTD operations use existing verified archive library; audit verifies stored bytes independently.

## Verification and limitations
- Offline local Python syntax compile (archive_cli.py and test_archive_cli.py): PASS.
- Isolated CLI argument/dispatcher mock tests: **11/11 PASS**; archive calls were mocked. This verifies only boundary behavior, not real codec integration.
- New \`tests/test_archive_cli.py\`: 9 real synthetic tests written, **NOT RUN against full repository in current environment** because connected Private GitHub content is available through connector, but container lacks GitHub network access. Previous remote HANDOFF records **125/125** Linux 3.13 passes on P1-C4; those 125 tests have **not been rerun** for C5.
- Windows/NTFS, Python3.11, actual browser, full CLI roundtrip, GitHub Actions, hardware power-loss, real customer DB: **NOT TESTED**. No client-ready claims.

## Gate to proceed
Run \`python -W error::ResourceWarning -m unittest discover -s tests -q\` on a checkout and confirm >=134 tests (125 existing +9 new), including ZIP receipt roundtrip and optional ZSTD when available. Run \`node --test tests/test_ui_dom.cjs\`, \`python -m compileall -q dbvora tests scripts\`, \`python -m scripts.preflight_archiving\`. Refuse release on failure; no unsigned receipt interpreted as proof of authorship.

Future: add durable request-ID idempotency ledger with collision/concurrency/crash tests before unattended or customer operations. Decide between Windows ZIP-only fallback vs opt-in zstd executable distribution; validate on Windows before promotion to develop/main.

## One-command synthetic end-to-end gate (added 2026-10-26)
Run from the repository root: `python -m scripts.synthetic_cli_gate`. Uses only a fresh OS-managed temporary directory, generates `tests.fixtures.make_sqlite` synthetic fixture, then calls the REAL `dbvora.archive_cli` snapshot/ZIP/unsigned receipt/new-path restore/audit. Compares SHA-256 and SQLite source mtime/size, and checks no `.part` remains. If installed, ZSTD level 3 is checked separately; missing ZSTD is explicitly `skipped_no_local_codec`. Always returns `ready_for_customer_data=false`; synthetic PASS cannot establish customer readiness, Windows durability, archive encryption or authenticated receipts.
**Evidence status**: syntax compile and 14 isolated mocks PASS. This gate has NOT yet been run against the full source checkout, so its expected success is a design/test target rather than verified integration. Do not promote feature branch or use real customer files on this basis.

## Single offline acceptance command (2026-10-26)
`python -m scripts.verify_release_gate` (from complete repository checkout). This runs the existing unittest suite with >=141 discovered cases, real `python -m scripts.synthetic_cli_gate`, Node DOM, compileall and synthetic temporary-folder filesystem preflight. Output has a step-by-step sanitized JSON status; incomplete source or missing tools returns FAIL_CLOSED and exit code 1. It never means customer data is ready. Decision logic tested 7/7 with mocked subprocess replies; locally available partial checkout correctly refused to pass. Full integration still NOT RUN. Windows Python3.11 and hardware power loss NOT TESTED.

## Independent verification and skip identity (2026-10-26)
The one-shot offline command remains `python -m scripts.verify_release_gate` from the complete feature checkout. Minimum Python unittest discovery is now **156**; it runs verbose so the only allowable skip when `zstd` is absent is `ArchiveCliTests.test_zstd_roundtrip_when_optional_codec_exists` for missing optional executable. The synthetic smoke explicitly rehashes saved .sqlite, .zip and optional .dbvz artifacts and independently rehashes restored SQLite files, rather than only trusting library-reported hashes. Generated basenames and suffixes must exactly match the temporary output tree, and symlinks are rejected.
Evidence is **22 focused PASS only** (14 subprocess-mock decision tests + 8 generated temporary-file validation and simulated CLI tests), Linux Python 3.13.5. Real full repo 156+ suite and actual archive engine end-to-end NOT EXECUTED in this environment. Customer readiness remains false regardless of synthetic result. Optional ZSTD installed locally does not prove its integration passed.
