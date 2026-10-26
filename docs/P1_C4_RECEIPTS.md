# DBVORA P1-C4 — Offline unsigned completion receipts and lineage

Date: 2026-10-26 KST. Private repository hibi89/DBVORA, feature/p0-db-map. All executed checks used synthetic SQLite, ZIP and optional local ZSTD on Linux only.

## Implementation
- dbvora/archive/receipts.py is independent of the viewer HTTP API. create_receipt(absolute_published_artifact_path, parent_receipt_name=None) must be called explicitly, AFTER creation of a new published DBVORA artifact. It DOES NOT automatically rebuild missing receipts.
- Each saved receipt is a NEW deterministic sidecar named dbvora-receipt-<artifact_uuid>.json in the selected archive directory. Receipt publication: new temp -> flush + fsync -> same-filesystem exclusive hardlink -> parent directory fsync. The link must never overwrite an existing receipt, including in concurrent calls. A post-link failure attempts removal of only the newly created sidecar. Prior archives and other receipts remain untouched. No automatic cleanup/repair.
- Fields: format, artifact_name, artifact_kind, artifact_sha256, snapshot_sha256, verified_at_utc, provenance, parent_receipt_name, parent_receipt_sha256. No customer rows, absolute path, original DB source path or credentials. The optional parent is an exact earlier receipt filename plus SHA-256 of its bytes. It allows an explicit lineage chain, not a proof that incremental data logically derives from its parent.
- Receipt creation independently restores/validates the standalone SQLite, ZIP or .dbvz archive using the existing read-only catalog implementation. Records are bounded to 4096 bytes; anchored to matching artifact basenames, no followed symlinks/multilinks, check file timestamps and inode identity around copying.
- inspect_receipt(output_dir, artifact_basename) verifies the actual stored receipt, actual archive and all referenced ancestor receipts and their archives, up to 12 levels. Tampered, missing, corrupted, mismatched or cyclic references fail closed. inspect_receipt_catalog(output_dir) joins the previous read-only recovery inventory with unsigned receipt results; no receipt = CONTENT_VERIFIED_PUBLISH_UNPROVEN / MISSING_RECEIPT. Valid receipt plus full recheck = RECORDED_AND_CONTENT_VERIFIED_UNSIGNED; damaged archive never promotes.
- If a process exits after archive creation but before recording receipt, the archive is still present and restorable, yet the next audit classifies it as unrecorded. Only an explicit create_receipt call after independent verification creates new evidence. If process exits after publishing receipt, future independent inspection can recover the evidence, but NOT prove the original physical power-loss commit.

## Executed tests / evidence
- Linux Python 3.13.5, SQLite 3.46.1, official zstd CLI 1.5.7.
- python -W error::ResourceWarning -m unittest discover -s tests -q: **125 PASS, 0 failures, 0 skipped** (previous 96 + 29 new receipt/lineage/audit tests).
- Tests cover independent SQLite/ZIP/ZSTD receipt checks, 3-level lineage, parent SHA tampering, missing parent/artifact, corrupt archive, receipt size/name/JSON constraints, symlink/hardlink prevention, five concurrent receipt writers (one winner), duplicate write refusal, fsync and publication fault injection preserving earlier files, process exits before/after receipt creation and later independent revalidation, no original file writes, no absolute path leaks.
- node --check dbvora/web/app.js and node --test tests/test_ui_dom.cjs: PASS (1 DOM simulation).
- python -m compileall -q dbvora tests scripts: PASS.
- python -m pip wheel . --no-deps --no-build-isolation: PASS. New dbvora.archive.receipts module included in wheel (scripts remain repository-only). GitHub staged new Python code and 29 tests matched local git blob SHA.
- python -m scripts.preflight_archiving: PASS only on synthetic Linux TEMP filesystem, ready_for_customer_data=false.
- python -m scripts.bench_codecs --trials 3 --rows 16: two 147456-byte synthetic snapshots, raw/ZIP/ZSTD 1/3/9 all restored exact SHA. Regression smoke only, not realistic compression performance.

## No security or production overclaims
- Sidecars and archives are unsigned and unencrypted: a capable adversary can change both and forge a self-consistent chain. The SHA lineage is not an authenticated transparency log or trusted provenance. Receipt timestamp is local self-report, not independently attested.
- Filesystem power-cut durability not proven; Linux fsync tests and subprocess abrupt exits are not hardware power-loss tests. A receipt can remain after crash despite no proof of previous fsync durability. Windows/NTFS and Python 3.11 remain NOT TESTED.
- C4 does not add automatic backups, retention/deletion, full customer archive use, remote replication, customer encryption, external upload, hosted deployment, real browser E2E or customer DB access.
- Browser E2E previously blocked by Chromium managed URLBlocklist; do not circumvent. Existing source code/API should be reviewed on a permitted machine before customer use.

## Next
P1-C5 usability: explicit local CLI for synthetic snapshot/ZIP/ZSTD/receipts/verification, Windows Python 3.11 build and capability gate where possible, then architecture roadmap re-evaluation. See docs/NEXT_TASK.md.
