# R03-07 — preview-bound safe restore workflow CLI (2026-11-15 KST)

**Status: PASS_SCOPED** for synthetic ZIP and ZSTD archive restore through the offline CLI workflow accepted by the execution plan.

## User flow

1. Run a read-only catalog preview on an existing synthetic archive directory:
   ```sh
   python -m dbvora.archive_cli preview --archive-dir /abs/synthetic-archives --synthetic-only --accept-plaintext
   ```
2. Choose one record whose status is CONTENT_VERIFIED_PUBLISH_UNPROVEN. Use its basename under the same archive directory and copy both SHA-256 values from that record.
3. Restore to an existing, separate synthetic output directory:
   ```sh
   python -m dbvora.archive_cli restore-selected \
     --archive /abs/synthetic-archives/dbvora-0123456789abcdef0123456789abcdef.zip \
     --artifact-sha256 <artifact_sha256_from_preview> \
     --snapshot-sha256 <snapshot_sha256_from_preview> \
     --output-dir /abs/new-restores \
     --synthetic-only --accept-plaintext
   ```

The generated restore filename is new and unique. The command does not overwrite the archive, source snapshot, or an existing restore file. Existing ZIP/ZSTD validators verify restored content and SQLite integrity; the preview snapshot SHA is checked before publication. Selection mismatch, malformed confirmation values, invalid archive content, or using the archive directory itself as output stops with a fixed error code and guidance. Local paths are not echoed in CLI errors or results; output uses the restored basename.

## Implementation

- Functional source/test SHA: b908e5aec99f98652a3a2f6fd3f9259ab06a85c8
- Files: dbvora/archive/recovery_catalog.py, dbvora/archive_cli.py, dbvora/archive/safe_zip.py, dbvora/archive/zstd_archive.py, tests/test_archive_cli.py.
- Preview uses the independent read-only recovery catalog and exposes only archive candidates with name, kind, size, status, artifact SHA-256, restored-content SHA-256, and the existing unsigned/unproven-publication caveats.
- Restore-selected requires both preview hashes, re-inspects the selected file, then invokes the existing ZIP/ZSTD restore implementation. Both restore implementations now accept an optional expected restored-content SHA and check it before publishing.
- Existing lower-level restore command remains compatible; the preview-bound command provides the stricter selection workflow.

## Exact-SHA evidence

- Full release gate [#43614189891](https://github.com/hibi89/DBVORA/actions/runs/43614189891) completed successfully at b908e5aec99f98652a3a2f6fd3f9259ab06a85c8. Ubuntu: 747/747 tests PASS, 0 skip, release checks PASS. Windows: 747 PASS, 1 named POSIX-only skip (`test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`), release checks PASS. ZIP and ZSTD synthetic round-trip checks passed.
- Unsigned owner preview ZIP [#43614189894](https://github.com/hibi89/DBVORA/actions/runs/43614189894) PASS at the same SHA.
- Blueprint evidence gate [#43614190193](https://github.com/hibi89/DBVORA/actions/runs/43614190193) PASS at the same SHA.
- First implementation SHA 0331b28f319062fbcbe3c1670959014e47bdcdf0 failed three new preview tests because the preview parser did not declare the required synthetic-only acknowledgement. That failure remains recorded in [#43613832902](https://github.com/hibi89/DBVORA/actions/runs/43613832902). Commit b908e5aec99f98652a3a2f6fd3f9259ab06a85c8 added the missing argument and the complete exact-SHA regression then passed.
- No browser run was required: R03-07 explicitly permits a safe workflow CLI. No customer DB/archive, user PC, physical restore, power loss, or external service was used.

Preview and restore evidence does not authenticate unsigned archives or prove publication durability on arbitrary user storage. Windows owner acceptance, real-device restore and physical power-loss behavior remain OWNER_GATE. Overall official completion remains UNASSESSED and RELEASE HOLD.
