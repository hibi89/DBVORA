# DBVORA P4-02 — unsigned extracted package sidecar guard

**2026-11-12 KST | engineering target P95 | current P85 provisional unchanged | RELEASE HOLD**

## Scope and decision
The extracted-preview `dbvora.archive.portable_verify` previously omitted every unlisted `.pyc` file and scanned unexpected source only for `.py/.js/.html/.css`. Therefore the verifier could return PASS while an unlisted OS executable, Python startup hook, standalone bytecode or native extension existed. This is a local developer ZIP integrity reporting gap; **not a demonstrated RCE or vendor-signature bypass**. The unsigned manifest remains forgeable together with the payload.

- **A — continue SHA-only manifest verification:** minimal CPU and maintenance, but unexpected unlisted executables remain undetected. Rejected.
- **B — retain SHA verification and bounded O(N) extraction scan, reject unlisted executable sidecars; harden verifier launchers with Python `-S -B`:** no API, server, credential, customer data, schema, or auto-restoration changes. Selected, minimal performance overhead within existing 500-entry bound and package size limits. Publisher authentication remains unverified.

## Implemented (feature/p0-db-map)
1. `dbvora/archive/portable_verify.py`: an unlisted standalone `.pyc`, `.pth`, `.pyw`, `.cmd`, `.bat`, `.ps1`, `.sh`, `.exe`, `.dll`, `.pyd`, `.so`, `.com`, or `.vbs` now reports `UNLISTED_PACKAGE_SOURCE`. Existing `.py/.js/.html/.css` protection remains. Only generated `__pycache__/*.pyc` stays tolerated as before; symlinks remain rejected.
2. `scripts/build_portable.py`: the two extracted-source *verification* launchers invoke `py -3.11 -S -B` or `python3 -S -B`, reducing startup site-hook exposure. Normal customer inspection commands and archive writer behavior remain unchanged.
3. `tests/test_portable_verify.py`: 7 inert, temp-only negative sidecar cases, preserving positive cache behavior.
4. `tests/test_portable_build.py`: new actual package extraction/subprocess negative sidecar regression and launcher-content test. Tests are **committed but NOT RUN against complete original repository**.

## Verification ledger
- GitHub feature commits: initial production guard `b24b4128`, unit test `1713eb87`, launcher `eb94631e`, packaged regression `c01ab56a`, small runtime constant refactor `94e1b5dd`.
- Scoped local Python3.13.5 *reconstructed rule harness* in isolated OS temp: **8 PASS / 0 FAIL** (7 rejected inert sidecars, 1 accepted generated cache). It is not an exact complete original-source test or proof of new launcher behavior.
- GitHub remote changed source/test blobs and branch SHA require readback after documentation commits. Full original `python -m scripts.verify_release_gate` (>=553 discovered Python), original package ZIP extraction tests, Node, Windows Python3.11/NTFS/Edge, actual PostgreSQL TLS and customer acceptance: **NOT RUN**. No GitHub Actions workflow or paid verification started.
- No new vulnerabilities were deliberately executed; test sidecar bytes were inert. No customer data, credentials, original DB/ZIP, deployed application, main/develop, external APIs or payments modified.

## Safety and completion
The verifier is **unsigned**: an attacker controlling both code and manifest can forge apparent integrity, and Python startup/import trust remains outside this script. Hence no signed provenance, untrusted ZIP execution, customer readiness or sale claim. **P4-02 is a safety hardening only; weighted engineering score stays 85/100, target 95 NOT ACHIEVED, `[작업중]` must remain in the central Kmong scoreboard.**

## Next gate
1. Obtain the complete authorized original checkout and run full original `python -m scripts.verify_release_gate` and real `scripts.build_portable` ZIP build→extract→new subprocess regression. Fix any actual failures before raising completion.
2. Native physical Windows10/11 Python3.11, NTFS output and signed/owner-reviewed publisher provenance, browser file:// and actual cold restart. No customer archive operations.
3. Owner-approved test PostgreSQL read-only TLS case; packaging rights, license/NOTICE, genuine customer acceptance before shipping.

Rollback: Git history, no force push. Documentation may be reverted independently; code changes are isolated to the feature branch.
