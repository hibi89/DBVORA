# P3-08 — exact-source synthetic backup → restore audit → manual review gate
**2026-11-12 KST · feature/p0-db-map · local Linux Python3.13.5 / ZSTD CLI present · RELEASE HOLD**

## User objective / two choices
The product owner requested 85% for DBVORA. Option A: enable unattended replay/retention after interruption; this risks duplicate archives, customer data loss and misleading durability. **Rejected.** Option B: real synthetic-only ZIP + optional ZSTD archive -> independent restored-content and ledger hash checks -> offline manual review -> deliberate corruption detection, with no customer inputs. **Implemented.** Zero API calls, scheduling, backups of customer files or paid services.

## Implementation
- **New** `scripts/recovery_review_gate.py` (Git Blob `745e8c9edfa536a4feda7fe4f3e6f340737ae98b`): generates its own disposable SQLite fixture and folders. For each installed codec, runs original SQLite online snapshot, `request_service.archive_once`, independent `inspect_and_reconcile` (real `recovery_catalog`), and `review_html.publish`. Asserts recorded state is **not authorized**, HTML has no script, duplicate request is held, source+snapshot hash/size/mtime unchanged, exactly one archive published. Then corrupts **only the temporary synthetic generated archive** and requires the recovered audit to flag `RECORDED_NOT_VERIFIED`. Never cleans customer files or accesses network.
- **New** `tests/test_recovery_review_gate.py` (Blob `c24051c38589fcd8e441556ba1aa450d257d4bd7`): 15 negative/control flow and optional ZSTD unit cases; exact GitHub blob matches locally tested bytes.
- **Fixed** actual `dbvora/archive/request_ledger.py` (Blob `0423d576c354bd7efd91484d0399c43a29f6b64d`): `_connect(create=False)` no longer calls `O_CREAT|O_EXCL`; a record-only check followed by ledger disappearance cannot create a replacement empty ledger. Two new regression tests in `tests/test_request_ledger.py`; no existing ledger format or schema change.
- Full `scripts.verify_release_gate` now **requires** new gate, 518 Python tests minimum, rejects skipped/falsified evidence and any customer-ready claim. The extra step is not authorization to sell.

## Executed and verified (precise scope)
1. Reconstructed a **limited** Python runtime in local sandbox from the actual GitHub source bytes, then compared `git hash-object` with GitHub's exact blob SHA for source modules `sqlite_reader.py` (`1d663d9d`), `errors.py` (`03649675`), `safe_zip.py` (`a58d2c3b`), `zstd_archive.py` (`94f638ce`), `request_ledger.py` (`0423d576`), `request_service.py` (`1ccfa25f`), `recovery_catalog.py` (`056abad6`), `request_audit.py` (`e49cf0fa`), `review_html.py` (`ec499170`), `tests/fixtures/make_sqlite.py` (`7f407189`), and new gate/test SHA above.
2. **Actual engine end-to-end** `python -m scripts.recovery_review_gate`: **PASS**, 16 synthetic check assertions across both ZIP and installed ZSTD, no skip. Original SQLite content unchanged; digest-matched unapproved archive transitions to **NOT_VERIFIED** when corrupted; duplicated request blocked; report generated in separate temp folder. Real ZIP restore and real ZSTD restore separately executed and SHA matched.
3. `python -W error::ResourceWarning -m unittest discover -s tests -q` on **limited local reconstructed tree**: **58 PASS / 0 FAIL / 0 SKIP** (P3-06 17, P3-07 22, P3-08 15, local-only ledger race/normal/concurrency 4). `python -m compileall -q dbvora tests scripts` PASS. Remote whole original 518 tests **NOT RUN**; new remote two ledger regression tests were mirrored as local scenarios but the complete remote `tests/test_request_ledger.py` has NOT RUN.
4. GitHub full checkout is blocked in this sandbox by DNS (cannot resolve github.com); authenticated GitHub connector was used to read and update exact files. No private GitHub Actions workflow was run or incurred costs. Native Windows3.11 NTFS/fsync/power-cut, PostgreSQL real TLS/role, Node full browser, installation, customer data and sale remain **NOT VERIFIED**.

### Example
```sh
python -W error::ResourceWarning -m scripts.recovery_review_gate
python -m scripts.verify_release_gate
```
The first command takes no external input paths and generates all fixtures in an OS temporary directory. PASS is a scoped **synthetic evidence** result, not hardware power-loss durability or customer readiness.

## Re-scoring (internal, not certification)
Previous rubric 72 = P0 22/25 + P1 8/15 + P2 18/20 + P3 14/20 + P4 10/20.
New provisional **77/100** = P0 22 + P1 8 + P2 19 (+1 original engine ZIP/ZSTD byte-exact restore) + P3 17 (+3 real archive→ledger→independent recovery & corruption/replay review, no-create race fix) + P4 11 (+1 enforceable synthetic release gate). **85 still 8%p away.** These are engineering-scope estimates, not 77% proven tests nor commercial acceptance. **RELEASE HOLD.**

## Next non-optional
- Run complete GitHub original-source `python -m scripts.verify_release_gate` >=518 Python+Node, fixing any actual failures.
- Windows Python3.11/NTFS portable browser and production filesystem publication/restart evidence, signed distribution/installable acceptance.
- Owner-approved synthetic non-production real PostgreSQL read-only TLS/role metadata+metrics; no credentials in GitHub.
- Confirm independent restore, power interruption and source preservation with actual hardware before customer archive writing or auto-retention.

Rollback: standard non-force revert of P3-08/ledger race commits, original source DB/snapshots and owner data untouched. Production/Vercel: N/A. Confirm current branch/head after documentation updates.
