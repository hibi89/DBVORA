# DBVORA — P3 compressed CAS v2 multi-generation synthetic acceptance

**2026-11-14 KST / Verified source `7e3ba31590d93626e7c93afab342167606f29e97`**. User scope: backend + frontend P100, without publishing to Kmong.

## Scope and safe architecture
A) Keep two separate manifest-descriptor readers for restore and audit: superficially independent, but can drift on inode/ctime/size/TOCTOU policies. B) Reuse the already-tested restore reader in the audit, with fixed path-free `INVALID_MANIFEST` error when underlying content is unsafe. **B selected**, cost zero, standard Python only, read-only; no change to live customer/archive data. `dbvora/archive/cas_audit.py` now delegates to `compressed_cas._read_manifest_unchanged` and `_parse_manifest`.

## Regression coverage
- `tests/test_cas_generation_lifecycle.py`: create a real *synthetic* SQLite snapshot, publish 4 CAS manifests (one duplicate + two changed). Verify 4 immutable SHA manifests, read-only auditor, restore in nonchronological order to distinct new files, and unmodified stored chunks.
- Corrupt a chunk unique to the latest generation **within disposable temp fixture only**. The auditor must return `HOLD_DAMAGED_OR_MISSING` with 1 invalid + 1 valid generation; old generation independently restores, corrupt new one refuses publication.
- Inject a synthetic manifest publication failure after new chunks were created. Old manifest SHA is unchanged and can restore; unreferenced chunks must trigger `HOLD_MANUAL_REVIEW`. No deletion/GC or customer policy change.
- `tests/test_cas_audit.py`: swap same-sized/same-mtime manifest file immediately before descriptor open. Shared identity/ctime guard must return `INVALID_MANIFEST` rather than trusting replacement.
- These scenarios are *not* physical power failures, customer retention promises, malicious-user exhaustive race schedule proof, or encrypted/signed archives.

## Verified exact execution
[Source commit `7e3ba31590d9`](https://github.com/hibi89/DBVORA/commit/7e3ba31590d93626e7c93afab342167606f29e97), [full release gate #43565286637](https://github.com/hibi89/DBVORA/actions/runs/43565286637): Ubuntu24.04 Python3.11 **703 PASS, 0FAIL, 0SKIP**; Windows2025 Python3.11 **702 PASS, 0FAIL, 1 named POSIX-only SKIP**; full mandatory **12/12 PASS per OS**, Node DOM frontend smoke PASS. Workflows output contract `PASS_SYNTHETIC_ENVIRONMENT_ONLY` and `ready_for_customer_data=false`. `python -m scripts.verify_release_gate` reproduces in supported environment.

## Unverified and product state
No physical device/long-run disk aging, customer files, production PG, third-party license notices, actual buyer Win10/11 installer or signed package validation, support/pricing and user's official final 100-point acceptance. Historical internal95 is *not* official percentage. Remain **UNASSESSED**, `[작업중]`, RELEASE HOLD, Kmong registered 0, Vercel/Production not applicable. Existing original backup/manifest/branches unaffected and no owner PC task requested while mobile.
