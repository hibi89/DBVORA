# DBVORA P1-C2 — durability and interrupted-work recovery evidence

Recorded: 2026-10-26 KST. Private hibi89/DBVORA, feature/p0-db-map. Scope: offline Linux and synthetic DB only.

## Changes
- dbvora/archive/safe_zip.py now makes _publish_new issue fsync on the verified, single-linked regular staging file, publish via exclusive same-directory hardlink, then fsync the parent directory. If the last sync fails, it tries to unlink *only that newly created link* and sync the directory again, and always raises PUBLISH_FAILED rather than declaring success. Pre-existing snapshots, archives and customer originals are never modified. This is a best-effort POSIX filesystem durability improvement, **not a proven sudden power-loss guarantee**.
- _sync_staged_file checks opened descriptor inode/device versus staged lstat and rejects symlink/non-regular/multi-hardlink paths. Directory sync that cannot be verified fails closed (including potentially Windows). TOCTOU and malicious co-tenant races are not fully eliminated.
- _staging_files allocates multiple new temporary files as a group and cleans the first allocations if a later allocation fails. ZIP/ZSTD paths now use it to reduce stray incomplete files on ordinary exceptions.
- inspect_stale_temps(existing_absolute_output_dir, older_than_seconds=86400) is read-only and reports only probable .dbvora-incomplete-XXXXXXXX.part regular files older than 1 hour and with one hardlink, same owner on POSIX.
- cleanup_stale_temps(..., confirm=True) is explicit-only, POSIX-dirfd scoped, never automatic; it rechecks candidate age/type/owner/hardlink count, then unlinks only a matching old temp basename and fsyncs the directory. Final dbvora-*.zip/.sqlite/.dbvz files are out of scope. Caller must first ensure **no writer is active**; an active 24-hour-old temp cannot be reliably differentiated from a stale one. Windows cleanup deliberately returns RECOVERY_UNSUPPORTED.

## Executed validation
Environment: Linux Python 3.13.5, SQLite 3.46.1, Node 22.16.0, zstd CLI 1.5.7.
- python -W error::ResourceWarning -m unittest discover -s tests -q: **76 tests passed, 0 failed, 0 skipped** (prior 62 plus 14 C2 tests).
- python -m compileall -q dbvora tests scripts/bench_codecs.py: pass.
- node --check dbvora/web/app.js; node --test tests/test_ui_dom.cjs: JS syntax pass and 1 DOM simulation pass.
- python -m pip wheel . --no-deps --no-build-isolation: pass; wheel contains safe_zip.py, zstd_archive.py, HTML/JS/CSS.
- python -m scripts.bench_codecs --trials 3 --rows 16: pass, two different synthetic SQLite datasets, raw/ZIP/ZSTD-1/-3/-9 all reconstituted identical snapshot SHA, 3 trials each. This is regression only, not a new commercial compression benchmark.
- Test cases: file-before-directory fsync ordering, directory-fsync-after-link failure cleanup, file fsync failure, name collision preserves earlier artifact, multi-temp allocation failure cleanup, stage symlink refusal, read-only orphan enumeration, no-confirm cleanup refusal, repeatable explicit-only cleanup, hardlinked temp cannot be removed, invalid age, subprocess os._exit(17) leaves incomplete temp without published final and manual cleanup, 8 unique snapshots concurrently across four processes, ZIP/ZSTD post-change restore hashes, os.fsync unsupported causes failure.
- Original synthetic source SHA-256 and mtime unchanged. Test created only ephemeral fixture files. No customer database, personal data, API secrets, archives or source content uploaded to GitHub.
- GitHub staged new Python files hash matched local git hash-object: safe_zip.py a58d2c3bfd3b95a98ada74f59e208b58e35d2e13, zstd_archive.py 94f638ce8a252f282229312d79dda95464b2a061, tests/test_durability.py 683e08918685f716905ee049805a93fabc1e1058.

## Windows codec distribution feasibility (research, no deployment)
- A. Bundle a separately verified native official ZSTD CLI binary in an approved installer, pinned checksum/version, with required license notice and Windows subprocess tests. Existing backend currently depends on CLI in PATH; binary not included.
- B. Implement alternate Python zstandard backend with pinned platform wheel and integration tests; the project documentation supports Python 3.11+ and Windows binary wheels are published. This would avoid separately invoking a CLI but demands new code/tests. There is NO Python zstandard dependency installed/validated in this environment.
- Prefer B for a future Windows packaging *prototype*, subject to actual Windows x64/Python 3.11 integration, license/security review and owner approval. Keep current offline CLI for Linux synthetic checks and ZIP fallback.
- Official upstream reference: https://github.com/facebook/zstd (BSD OR GPLv2); license https://github.com/facebook/zstd/blob/dev/LICENSE. Python bindings/install https://python-zstandard.readthedocs.io/en/latest/installing.html and wheels https://pypi.org/project/zstandard/. No binary downloaded or redistributed during P1-C2.

## Non-claims / remaining risk
No real sudden power interruption on production filesystem/NTFS, no Windows os.link and directory-fsync compatibility, no crash at arbitrary instruction points, no durable transaction ledger or restart recovery across partitions, no unattended GC/retention. Explicit manual cleanup may race malicious renames and must run with other writers halted; not a complete hardened filesystem sandbox. SHA manifests are unencrypted/unsigned, not adversary authentication. No live customer DB tests, continuous high-load WAL, Python 3.11, Windows packaging, full actual browser E2E or GitHub Actions. Vercel/Production not applicable.

## Next
P1-C3 further fault-state/manifest verification and cross-platform Windows opt-in installation gating, or user-approved real environment testing if separately authorized. Follow docs/NEXT_TASK.md.
