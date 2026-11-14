# R03-08 — synthetic CAS retention preview (2026-11-15 KST)

**Status: PASS_SCOPED** for a bounded, read-only synthetic CAS v2 preview at source/test SHA `1d7d5af74055e19717b73291328fca666c05ce63`.

- Full release [#43617576399](https://github.com/hibi89/DBVORA/actions/runs/43617576399) passed at the exact SHA: Ubuntu 756/756, 0 skips; Windows 756 passed plus the one named POSIX-only permission skip. All required synthetic CLI, package ZIP, filesystem preflight, Node DOM, recovery, PostgreSQL-to-HTML and archive comparison steps passed.
- Unsigned source preview ZIP [#43617576253](https://github.com/hibi89/DBVORA/actions/runs/43617576253) passed at the same SHA.
- Blueprint evidence gate [#43617576518](https://github.com/hibi89/DBVORA/actions/runs/43617576518) passed at the same SHA.
- Implementation: `dbvora/archive/retention_preview.py`; tests: `tests/test_retention_preview.py`.
- CLI requires explicit existing chunk and manifest directories, `--keep-generations N`, `--synthetic-only`, and `--accept-plaintext`.

## Preview behavior and limits

- Reuses the bounded read-only CAS audit and checks file/directory identities before and after inspection. A detected store change produces `HOLD_STORE_CHANGED` and no retention suggestions.
- Reports generation manifest basenames, snapshot sizes, chunk-reference counts, recognized compressed file lengths, and unreferenced hash-named chunk basenames. It does not report directory paths or read unknown-file contents.
- Manifest records contain no trusted generation timestamp. The preview labels filesystem `mtime_ns` as untrusted and uses it only for a proposed ordering. Any equal-time ambiguity when generations would be removed produces `HOLD_AMBIGUOUS_ORDER`.
- Damaged or missing chunks, orphan or unrecognized entries, and audit failures produce HOLD with an empty suggestion list. No state is automatically deleted.
- The estimated reclaimable amount is the sum of proposed manifest and no-longer-referenced compressed file lengths. Physical block allocation can differ; it is informational only and never an authorization to delete.

## Synthetic coverage

The six new tests cover: one older-generation suggestion with shared-chunk-aware storage estimate; orphan listing with manual-review HOLD; missing-chunk HOLD; equal-mtime ambiguity HOLD; mutation during preview HOLD; and acknowledgement/invalid-keep/path-redaction behavior. Tests assert that preview leaves existing artifact bytes unchanged.

No customer data, user PC, browser UI, physical full disk, actual power interruption, or real restore target was used. Filesystem mtime is not authenticated. Automatic deletion remains disabled, customer readiness is false, physical power loss remains unverified, R03-10 remains OWNER_GATE, and overall completion remains UNASSESSED / RELEASE HOLD.
