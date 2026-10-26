# P1-C0 evidence — SQLite online snapshot and ZIP baseline

Updated 2026-10-26 KST. Scope: offline synthetic SQLite only. ZIP baseline is NOT evidence of superiority versus ZSTD or a hardened backup product.

## Implemented
- dbvora/archive/safe_zip.py exposes create_snapshot(source_absolute_path, existing_output_dir), make_zip_archive(snapshot_absolute_path, existing_output_dir), restore_zip_archive(zip_absolute_path, existing_output_dir).
- Inputs must be explicit absolute local paths. Output directory must exist and not be a symlink. No scanning, HTTP endpoint, raw customer data uploads or external calls.
- Source connection opened SQLite mode=ro and query_only. Connection.backup creates consistent standalone snapshot in new temporary file. Integrity check and SHA-256 precede exclusive same-filesystem publication, without overwriting originals or prior outputs.
- ZIP contains exactly snapshot.sqlite (DEFLATE) and manifest.json (STORED). Manifest stores snapshot hash, bytes, codec and UTC time; no original path. Before archive publication it is independently unzipped and checked for SHA and SQLite integrity.
- Restoration rejects extra, duplicate, traversal, malformed, oversized, encrypted, checksum-mismatched entries. Streams under a 512 MiB prototype cap, checks SQLite integrity, publishes new file only. Failed attempts clean temporary files. Error messages contain no source path.

## Executed tests (Linux Python 3.13.5 / SQLite 3.46.1)
Command: python -W error::ResourceWarning -m unittest discover -s tests -q
Result: 46 PASS / 0 FAIL / 0 SKIP: 28 prior P0 tests plus 18 P1-C0 tests.
Additional: python -m compileall -q dbvora tests PASS; python -m pip wheel . --no-deps --no-build-isolation PASS (archive module plus web assets included); node --check dbvora/web/app.js PASS; node --test tests/test_ui_dom.cjs 1 PASS.
Specific coverage: snapshot and SQL row equality, original hash+mtime invariance, SQLite WAL committed data, two unique snapshots/multiple restores, archive entry/manifest, truncated ZIP, changed checksum, traversal, duplicate entries, random invalid file, relative/missing/symlink destinations, simulated publication failures and cleanup, invalid size caps and bad manifest types.
Fixture example: source/snapshot 24,576 bytes, ZIP 1,006 bytes, restored SHA equals snapshot SHA. This highly compressible synthetic fixture is NOT a customer savings benchmark.

Local Git hashes verified equal GitHub uploaded blobs:
- dbvora/archive/safe_zip.py: 9c3f2e98b8dc6d2e40943c06d675bbea08c51cb3
- tests/test_safe_zip.py: d81c4756c0bddd0a3843ad27738a1423ff762b92
- dbvora/archive/__init__.py: f68c3e061275f5802621deff0a7dc365e5ad2876

## Risks and unverified
- ZIP is UNENCRYPTED and contains source row data; it must remain in authorized local storage, never committed or transmitted. Manifest hashes detect mismatch relative to contents but are NOT signed: tampered payload plus tampered manifest can bypass provenance validation.
- On Windows, os.link publication and filesystem locking require testing. No guarantee of power-failure durability, concurrent-writer stress resilience, malicious symlink replacement defense, complete disk-failure cleanup or long-lived idempotent recovery.
- Live SQLite DB file bytes may differ from a valid consistent backup when WAL is in use; compare restored snapshot bytes against completed standalone snapshot instead. The code only says no original write was performed by itself, not that other applications stopped writing.
- No ZSTD benchmark, compression scheme superiority, authenticated restore, multi-day scheduling, PostgreSQL, Windows test or customer-facing validation.
- Browser P0 E2E remains unverified due previously observed managed Chromium policy. Production/Vercel not applicable.

## How to reproduce on synthetic data only
1. From repository root run the full unittest command; fixtures are generated automatically in temporary directories.
2. For controlled Python usage, import create_snapshot, make_zip_archive, restore_zip_archive from dbvora.archive.safe_zip, choose a synthetic SQLite fixture file and three separate existing absolute output directories.
3. Assert snapshot result's snapshot_sha256 matches restored result's restored_sha256; SQLite integrity_check returns ok.
No paid libraries are needed for this ZIP baseline. Next: docs/NEXT_TASK.md P1-C1 for optional ZSTD comparison.