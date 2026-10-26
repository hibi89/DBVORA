# DBVORA STATUS — P1-C2 synthetic durability hardening

Updated 2026-10-26 KST. Private repo hibi89/DBVORA; active feature/p0-db-map. Parent verified head 855b10f94ae03e633b8437941d4cdc14a4c4f120; current final head MUST be re-read after commit. main/develop 890f842e3ba0e13c901e785633bdd06eadc76cce unchanged.

| Workstream | State | Evidence |
| --- | --- | --- |
| P0-01 SQLite read-only schema inventory | LOCAL_PASS | previous tests |
| P0-02 localhost API and clickable SVG map | HTTP_DOM_PASS_BROWSER_BLOCKED | managed Chromium URLBlocklist prevents GUI E2E |
| P1-C0 SQLite online snapshot + ZIP independent lossless restore | LOCAL_PASS | previous tests |
| P1-C1 ZSTD 1/3/9 ZIP comparative baseline | LOCAL_PASS | local official zstd executable and synthetic benchmarks |
| P1-C2 file fsync + parent directory fsync / exclusive publish | LOCAL_PASS | POSIX ordering and fault injection; no power loss proof |
| P1-C2 incomplete temp detection / opt-in recovery | LOCAL_PASS | 24h old file detection, manual confirm-only POSIX cleanup; NO automatic deletion |
| P1-C2 8 concurrent snapshots / crash simulation | LOCAL_PASS | 4 processes, 8 unique output paths and SHA matches; subprocess os._exit(17) leaves no published partial file |
| Entire Python regression | 76 PASS / 0 FAIL / 0 SKIP | Linux Python 3.13.5 SQLite 3.46.1 |
| JS DOM + Python wheel | PASS | Node DOM 1 PASS, wheel includes archive modules/UI |
| Synthetic benchmark smoke | PASS | two fixtures, 3 trials/raw/ZIP/ZSTD1/3/9, SHA equals original snapshot |
| Windows / Python 3.11 / actual power cut | NOT_TESTED | no Windows runtime or hardware fault injection |
| Live customer DB / high-concurrency WAL | NOT_TESTED | no authorization; synthetic only |
| Chrome GUI E2E / GitHub Actions | BLOCKED / NOT_RUN | managed browser policy and no CI job |
| Vercel and hosting | N/A | local-first software |

Note: A post-publication directory fsync failure attempts rollback of the new link. If rollback itself fails, status is failure and manual inspection may be required; no durable recovery journal exists. Symlink/path race not fully addressed. Windows filesystems may not support directory fsync; code deliberately fails closed if not verified. The recovery cleanup can race an extremely long-running writer, so it is NEVER automatic and requires coordination and explicit confirm. Any ZIP/ZSTD manifest is unsigned and archive contents unencrypted.

Commands: python -W error::ResourceWarning -m unittest discover -s tests -q; python -m compileall -q dbvora tests scripts/bench_codecs.py; node --test tests/test_ui_dom.cjs; python -m scripts.bench_codecs --trials 3 --rows 16.
Evidence: docs/P1_C2_DURABILITY.md. Next: docs/NEXT_TASK.md P1-C3 cross-platform recovery/manifest safety and packaging. All GitHub commits must be verified by branch SHA and author after publication.
