# P4-04 — trusted pre-import extraction audit and exact-source regression

**2026-11-12 KST · Goal P95 · DBVORA current 85/100 provisional engineering · RELEASE HOLD**

## Verified failure mode
On Linux Python **3.13.5**, a disposable `sample.py` was compiled into ordinary CPython timestamp bytecode. Replacing only the inert bytecode payload with an alternative `value='CACHED'` while preserving the original cache header, then running `python -S -B -c 'import sample; print(sample.value)'`, printed **CACHED**, not SOURCE. Thus `-B` prevents generating bytecode, **not reading preexisting bytecode**. A verifier imported **from the extracted package** cannot establish a pre-execution security guarantee, regardless of its own later checks. The cache was benign; no malicious code, customer data or external service used.

## Approaches / decision
- **A:** Continue existing `python -S -B -m dbvora.archive.portable_verify` inside extraction while tolerating cache names matching source. Cheap, but can execute cached code *before* inspecting it. Not sufficient for a safe pre-import workflow.
- **B (selected):** Reject **all** unmanifested cache/bytecode even when module name matches, plus run a new **separately trusted checkout's script** using `-I -S -B` and explicit imported verifier path against another extracted folder. No package import, no API/server/credentials, local read-only SHA and allowlist. O(total package bytes) hashing with existing 16MiB and 500-entry caps. Requires the caller to establish trusted GitHub source separately; unsigned manifest is not a signature.

## Changes (feature/p0-db-map)
1. `dbvora/archive/portable_verify.py`: any `__pycache__` regular file or `.pyc` gets `PACKAGE_BYTECODE_PRESENT`, hardlinks get `UNSAFE_PACKAGE_ENTRY`. No cache carve-out. Existing manifest SHA, name/path safety, no-write and source-file checks retained.
2. `tests/test_portable_verify.py`: previous accepting-cache test converted to negative, foreign cache and unknown extensions adjusted, one pre-existing failing expected-error regression fixed. The original exact Git Blob test was reproduced locally before and after correction: initial 19 PASS/1 FAIL (one subtest), then 20 PASS/0 FAIL.
3. `tests/test_portable_build.py`: extracted ZIP subprocess negative tests expect the correct fixed error and add same-name cache regression; **not run** against original full package source.
4. `scripts/build_portable.py`: package README requires clean extraction before other app commands and explains `-S -B` cache-read limitation. Does not silently change customer behavior or sign ZIP.
5. **New** `scripts/verify_trusted_extraction.py`: source-only checker in trusted checkout, not added to source ZIP builder. Reads absolute `--extracted` folder via trusted explicit module file; rejects trusted/extracted folder overlap and requires no package execution. JSON contains stable error codes only, no paths/credentials. Invoked `python -I -S -B /trusted/DBVORA/scripts/verify_trusted_extraction.py --extracted /separate/fresh_zip_extract`.
6. **New** `tests/test_trusted_extraction.py`: actual separate Python subprocess, positive unsigned-but-not-publisher-verification, modified source, matched filename cache, PYTHONPATH poison isolation, same-root/relative input HOLD and no-write paths.

## Actual local validation
Recreated **exact** GitHub committed source file bytes in an isolated Linux Python3.13.5 workspace and checked SHA using `git hash-object`:
- `dbvora/archive/portable_verify.py`: Git Blob `d8d3e67b28f3df86a4f45a0aee2e40d469dc34e6`, matched.
- `tests/test_portable_verify.py`: `56693b25a3878aee9f581f6f8761ac6996f55515`, matched.
- `scripts/verify_trusted_extraction.py`: `8430914e997d33d7e2e0d394f6bb88886b78c854`, matched.
- `tests/test_trusted_extraction.py`: `f7acd1840aee1868e31a611ac90bcc2c9244139d`, matched.
- Command: `PYTHONDONTWRITEBYTECODE=1 python -W error::ResourceWarning -m unittest -v tests.test_portable_verify tests.test_trusted_extraction test_scope`.
- **Original GitHub source/test methods: 27 PASS / 0 FAIL / 0 SKIP** (20 portable verify + 7 trusted extraction); **separate local scoped exact-module tests: 7 PASS / 0 FAIL / 0 SKIP**, combined **34 PASS**. Local `test_scope.py` is an isolated harness, **not committed** to GitHub and NOT a substitute for entire original product test suite.
- Additionally benign CPython `-S -B` old-cache execution demonstration **1 PASS**. No customer file and no external traffic.
- Code checkout is limited to the exact 4 GitHub files above plus synthetic test directories, not the complete DBVORA checkout. Actual `scripts.build_portable` complete package, `tests/test_portable_build.py`, release gate Python >=553+Node, actual PostgreSQL/TLS, Windows10/11 NTFS/Edge/file://, hardware power failure, signing/vendor original rights and customer acceptance **NOT RUN**.

## Security limits / next action
The new script is usable as a **pre-import auditor only when executed from a separately trusted, authenticated source checkout and Python installation**. A malicious source+unsigned manifest pair can still forge hashes, and an attacker may tamper with an unknown interpreter or trusted checkout. This is not a malware detector, legal publisher signature or Windows durability certification.

- Obtain authorized **full** private feature checkout, run `python -m scripts.verify_release_gate`, original ZIP build/extract/actual trusted audit, and all existing Node tests; record exact SHA and results.
- Native owner-controlled Windows10/11 Python3.11/NTFS/offline browser; independently approved read-only PostgreSQL TLS and physical restore. No external DB connection without explicit approval.
- Keep **85% provisional engineering, P95 NOT MET, RELEASE HOLD**. Central DBVORA `[작업중]` must persist until objectively verified P95. Other products/markers unchanged.

**Rollback:** GitHub feature history; main/develop, original archives, customer DB, credentials, billing, Vercel/Production, releases untouched. No new GitHub Actions workflow or paid CI triggered.
