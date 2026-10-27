# P0-07 — Bounded JSON metadata input security (2026-10-27 KST)

## Scope
New `dbvora/safe_metadata_file.py` consolidates input safety for the local offline workspace's optional `--links-file` (16 KiB) and `--baseline-file` (512 KiB). The parser requires an existing absolute, regular, nonsymlinked path and rechecks the open descriptor's file type, size and device/inode after path stat; reads no more than the permitted byte ceiling plus one. Where supported, `O_NOFOLLOW` and `O_NONBLOCK` further narrow link/FIFO races. Duplicate JSON keys at any depth and nonstandard `NaN`/`Infinity`/`-Infinity` are now refused. Failures keep fixed path-free error codes. Synthetic demo now rejects `--save-observation` instead of silently discarding it.

## Actual tests
Local Linux Python 3.13.5, exact new/modified source under /mnt/data/dbvora_workspace_dev, with ResourceWarnings as errors:

```
python -W error::ResourceWarning -m unittest -q tests.test_safe_metadata_file tests.test_mvp_offline_gate tests.test_workspace tests.test_workspace_registry tests.test_workspace_links tests.test_workspace_storage
```

**Ran 70 tests in 0.638s, OK** (58 prior local P0 tests plus 12 security tests). Separate real P0 integration command `python -m scripts.mvp_offline_gate` reports **13/13 PASS**, `PASS_SYNTHETIC_P0_ONLY`. The shell's direct private GitHub clone remains DNS-blocked, so full checkout and full >=324 Python/Node/CLI gate **NOT RUN**.

Locally tested source blob hashes were independently matched to GitHub:
- `dbvora/safe_metadata_file.py` `3a2c2f97f149310a4a1f6757d44d1104e8941234`
- `dbvora/workspace_html.py` `3540f53399c9480f6e86e6cf21c7aef68a9a6a8b`
- `dbvora/workspace_observations.py` `54f58034565429488db17d891e4101988bcb78e0`
- `tests/test_safe_metadata_file.py` `c2c8fdca8041998d7e09ce3a230613438fcc2265`

The mandatory release gate now checks for the new source and test files and requires >=**324** discovered tests rather than 312. That threshold is not an execution result.

## Safety caveats and next task
Pre/post-open fd identity checking defends against replaced leaf files under ordinary local filesystem behavior, not a guarantee against concurrent privileged directory replacement, especially on Windows. User-supplied old observation files remain unsigned; their numbers are not cryptographic proof. SQLite originals, ZIP/ZSTD/receipt/archive logic, production state and main/develop were not modified. No real customer DB, internet data transfer, paid runner, scheduled deletion, or public release. Next: compensate safely for partial two-output write errors in `export_workspace`, preserve existing files, check malicious identifiers/render bounds, run complete release suite in an authorized source-capable runner and native Windows/browser tests.
