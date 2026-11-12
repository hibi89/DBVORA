# DBVORA P4-03 — strict extracted ZIP inventory and cache provenance

**2026-11-12 KST | target: 95% | current: 85% provisional engineering | RELEASE HOLD**

## Scope and alternatives
The P4-02 verifier still tolerated unexpected package files without one of the enumerated executable suffixes, and all `__pycache__/*.pyc` including those without a manifest-listed source. In a local developer preview, unknown extensionless scripts or foreign cache data should never be silently described as complete extracted-source integrity.

- **A — extension-only sidecar filter:** cheap but fails on extensionless and unknown-suffix files, risks a misleading PASS.
- **B — bounded allowlist scan of every regular file:** every file is either manifest-listed, the manifest itself, or CPython-generated cache whose source `.py` is manifest-listed. Source-less/fake caches, unlisted files and linked caches fail closed. Selected; adds O(N) work bounded by existing 500-entry cap; zero external services and no customer input.

## Changes on `feature/p0-db-map`
1. `dbvora/archive/portable_verify.py`: full extracted file allowlist, `_generated_cache` source-match policy for `<module>.cpython-<version>[.opt-0|1|2].pyc` under an immediate `__pycache__`, hardlink rejection for an otherwise allowed cache. Existing SHA checks, manifest names/limits, symlink rejection and stable `UNLISTED_PACKAGE_SOURCE` error code preserved.
2. `tests/test_portable_verify.py`: update legitimate cache positive fixture, add foreign cache and unknown-format negatives, extensionless/config/hidden negatives, non-cache bytecode and cache hardlink negatives.
3. `tests/test_portable_build.py`: actual built developer ZIP→extract→subprocess verifier integration regression for extra extensionless file, unknown suffix and source-less cache. This regression is checked in but full original build/test is NOT executed in the current environment.

## Validation / limitations
- Linux Python3.13.5 synthetic OS temp reproduced the new scan/cache logic: **19 PASS / 0 FAIL** including valid manifested cache, extensionless/unknown file, fake cache, symlink/hardlink cases. This test exercises an independently reconstructed copy of the rule, **NOT the complete exact GitHub original module/package or 553+ test suite**.
- GitHub feature commits: full allowlist `4bbb83450aa65871c71e170f84730f160c0bca2e`, unit tests `a9fb4522736a22318b72ddfe7589985c739bc377`, ZIP integration tests `27261f7ce495251d6a9fa528cc825f628f7bdd75`, cache hardlink guard `4481c2f6aaa24d3f606532d4d10508f76829c622`, cache hardlink test `b1b80d52dc3c3461ba4ab8eb1ef7f12d6afd0a54`. Final GitHub HEAD and exact blobs must be read back after documentation.
- **Not run:** full original repository Python >=553+Node, real `scripts.build_portable` ZIP extraction against the current full source, native Windows10/11 Python3.11/NTFS/Edge, real authorized PG/TLS, signed source/release, physical restart, customer acceptance. `git ls-remote` from current container fails `Could not resolve host: github.com`, so the private repository cannot be checked out here. No arbitrary new GitHub Actions or paid CI.
- A SHA manifest inside an unsigned archive is not publisher authentication; execution of untrusted code, malware resistance or source validation before import are **NOT claimed**. An unlisted personal note in the extracted folder will now correctly cause fail-closed; verify a pristine extraction.

## Completion decision
P4-03 is a bounded integrity improvement and supplies regression cases. Without full exact-source QA and Windows/PG/customer gates, internal milestone **remains 85% provisional**, **P95 NOT ACHIEVED**, **RELEASE HOLD**, and the central DBVORA `[작업중]` marker must remain. Do not change other projects' progress.

## Next steps
1. In an authorized full checkout, `python -m scripts.verify_release_gate` and actual deterministic developer ZIP build/extract/verify + process smoke; record exact SHA, all PASS/FAIL/SKIP, package hash.
2. Physical Windows10/11 NTFS/Edge file:// and restart durability, source/package signature/license checks.
3. Separately approved PostgreSQL sandbox read-only role with TLS verify-full; no secret/DB snapshot committed.

Rollback via normal Git history; no force push, main/develop modifications, customer data, paid API or Production deployment.
