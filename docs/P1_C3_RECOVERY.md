# DBVORA P1-C3 — post-restart archive audit & Windows preflight (2026-10-26 KST)

Branch: feature/p0-db-map of private hibi89/DBVORA. Synthetic SQLite and Linux only.

## New capabilities
- dbvora/archive/recovery_catalog.py: inspect_recovery_catalog(existing_absolute_directory). It NEVER changes, cleans, renames or restores any file under that directory. It only scans recognizable DBVORA names: dbvora-<32 lowercase hex>.(sqlite|zip|dbvz), plus .dbvora-incomplete-XXXXXXXX.part files. Other entries are ignored. Max 250 matching entries/5,000 directory entries. No customer DB scanning.
- For each candidate: reject symlinks, non-regular and multi-hardlink files; open without following final symlinks where supported; compare inode/size/mtime/ctime around bounded copy to a different system temporary directory. If file changed during copy, mark RACE_DETECTED. Max prototype inspection 512 MiB/file.
- The frozen copy is independently validated. SQLite -> PRAGMA integrity_check; ZIP -> fixed entry, manifest SHA, full restore and SQLite integrity; .dbvz -> bounded frame SHA, restored SHA and SQLite integrity. No change to original archive source. Archive file size/hash and restored snapshot SHA appear in a JSON-serializable report (no absolute paths, rows or secrets).
- Returned states: CONTENT_VERIFIED_PUBLISH_UNPROVEN, FAILED_REVIEW(error_code), UNPUBLISHED_OR_ACTIVE, UNSAFE_TEMP_ENTRY. Never automatically delete a corrupt, incomplete or unknown file. A verified content hash DOES NOT establish provenance or successful durable fsync of the original writer; all records explicitly say publication_durability unknown_no_persisted_commit_evidence and authentication unsigned_untrusted.
- scripts/preflight_archiving.py: python -m scripts.preflight_archiving, a stand-alone synthetic temp-only capability probe. Reports OS, Python/SQLite version, whether optional zstd CLI is on PATH, and whether hardlink+file/parent sync publication works on this TEMP filesystem; ready_for_customer_data is always false. No binaries installed or downloaded; no customer folders or databases inspected.

## Test evidence (executed in Linux container)
- python -W error::ResourceWarning -m unittest discover -s tests -q -> 96 tests passed, 0 failures, 0 skips. Previous 76 plus 20 recovery-catalog/preflight tests.
- Independent Python subprocess restart test: create verified synthetic ZIP, launch new Python process, enumerate and re-verify same saved archive without changing it.
- Snapshot/ZIP/ZSTD full verified content checks; corrupt SQLite/ZIP/ZSTD refused but left intact; injected change/permission denial; named symlink and multi-hardlink rejection; capped sizes and list count; unknown files ignored, orphan .part preserved, symlink pretending to be .part flagged UNSAFE_TEMP_ENTRY. Missing optional zstd results CODEC_UNAVAILABLE and NEVER verified.
- python -m compileall -q dbvora tests scripts: PASS.
- node --check dbvora/web/app.js and node --test tests/test_ui_dom.cjs: PASS, DOM 1/1.
- python -m pip wheel . --no-deps --no-build-isolation: PASS; wheel contains archive/recovery_catalog.py, ZIP, ZSTD modules and the HTML/JS/CSS assets. scripts/preflight_archiving.py is a *repository script* and is not part of the Python wheel package.
- python -m scripts.preflight_archiving: platform Linux, Python 3.13.5, SQLite 3.46.1, local zstd CLI available, synthetic temp filesystem archive publish test passed. Windows_package_verified=false, ready_for_customer_data=false.
- Remote staged blob hashes match local source: recovery_catalog.py 056abad676b13781778993a46c3ae7dd7da77660; scripts/preflight_archiving.py cc66798c7fc91b10050fffe24e1601019190671e; tests/test_recovery_catalog.py a30e1158d0d87e848800a3491ef57e4d28178e9b.

## Boundaries and risks
- This is a **read-only recovery audit**, not a durable commit ledger. An archive left by an interrupted post-link fsync may independently pass integrity inspection but cannot be certified durably published. A forged ZIP/ZSTD manifest and payload can be mutually consistent because there is no signature or trusted external checkpoint.
- Matching snapshot SHA across archives proves identical restored bytes, NOT that original source history/consent/authorization are proven.
- No automatic repair/delete/quarantine, retention, incremental chains or customer DB use. The prior POSIX explicit-only temp cleanup remains a separate gated function.
- Race checks reduce accidental concurrent-change errors but cannot prove correctness against malicious same-directory name replacement or privileged filesystem attacker. Directory aliases, network/shared filesystems and hard power removal not validated. The verifier can allocate up to prototype size in *external temporary storage* per artifact; disk exhaustion and transient IO errors fail audit rather than modifying archived data.
- The probe runs on the OS temporary filesystem, not the user's intended backup disk; successful Linux probe is not a Windows/NTFS validation. The CLI ZSTD executable is not bundled and Windows/Python3.11 install is NOT verified; no Windows system was available in this turn.
- Previously observed Chromium managed URLBlocklist '*' means real browser GUI E2E remains blocked; node DOM simulation is not a substitute for actual display. No GitHub Actions, production, paid service, public release or real customer data access occurred.

## Next architecture decision
Introduce a versioned *separate* durable commit/lineage evidence record with crash-safe publish and independent verification; do not treat current self-reported manifest as proof of trusted history. Then Python3.11/Windows runtime+packaging tests and user-approved real-device validation, before any customer data. See docs/NEXT_TASK.md.
