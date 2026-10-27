# DBVORA owner-local source verification bridge — 2026-10-27 KST

## Context / blocker
- Private repo `hibi89/DBVORA`, `feature/p0-db-map` source-code baseline `cafbd87e61f20cffe778692f8a29db541588eeaf` (latest docs-only HEAD before this update `136aa8d5a88c047ccb9d465e12d2f21eb28a4878`).
- The execution container cannot authenticate/download full private GitHub code by shell: external GitHub hostname DNS resolution fails. A local inventory of previously verified snapshots matched exactly **27/50** executable Git blob pins from QA v6; other **23 source/test files are missing**, so a complete **214-case** product Python run and the unified six-stage release gate are **NOT RUN**. No attempt was made to weaken source verification.
- Rejected alternatives: repeated unauthenticated clone; paid CI/workflow without owner approval; public source mirror; copying private code into third-party services; claiming focused tests as full release PASS.

## Artifact created
An owner-machine-only, offline synthetic QA bridge package was created as a **temporary ChatGPT conversation attachment**, not as a GitHub repository code file:

`DBVORA_owner_private_verify_v1_20261027.zip`
- SHA-256: `09d13c823a03d8f425d2965ef3ddad74dc247522ce40043aae93b602d5fdd765`
- Size: **16,425 bytes**.
- Files: `README.txt`, `verify_private_source.py`, `test_private_verify.py`, and bundled `qa_v6/{run_dbvora_qa.py, test_runner.py, test_source_pinning.py, pinned_git_blobs.txt, README.txt}`. No DBVORA product source, customer databases, secrets or credentials included.
- Uses the owner's locally configured **Git credential manager** for an optional private `git clone --depth 1`, or a pre-existing private checkout (`--repo`). Never asks for or emits a token; no code upload to ChatGPT or third parties; no GitHub pushes, repo mutations, paid Actions, pip installs or deletion of customer/source files.
- Checks all **50 pinned Git blob IDs** against the local committed `git ls-tree HEAD`, refuses extra unreviewed executable paths and wrong pins, then runs `git archive --format=zip --prefix=dbvora-source/` to a new local output file (avoids PowerShell binary redirection). Invokes the bundled QA v6 runner to verify the archive again and run `>=214` Python tests and the six-stage synthetic gate; returns fixed path-free `FAIL_CLOSED` for unavailable/mismatched source or failed QA. Output remains local.
- Windows example after extract, with local Git credentials configured: `py -3.11 verify_private_source.py --clone --qa-kit qa_v6 --output .`. Existing checkout: `py -3.11 verify_private_source.py --repo C:\path\to\DBVORA --qa-kit qa_v6 --output .`. No Windows execution is claimed.

## Actual verification evidence
- Actual Linux Python3.13.5 and local synthetic Git repository: bridge **5/5 PASS**, testing exact source pins, documentation-only commits, altered blob FAIL_CLOSED, unreviewed shell executable FAIL_CLOSED, and `git archive` single-prefix ZIP binary integrity.
- New bundle freshly extracted and both test groups run: bridge **5/5 PASS** and bundled QA v6 **19/19 PASS**, 0 failures/skips. One packaging-only import-name error was detected on first extraction; fixed and repeated both sets successfully.
- Actual current private **214 Python product tests and native Windows3.11/NTFS remain NOT RUN**, as does the whole ZIP/ZSTD/Node release gate in this execution environment. The bridge is an execution/transport preparation tool, **not product release acceptance**.

## Next priority
On an authorized owner-controlled PC, run the package once with pre-existing Git authentication, locally inspect sanitized `DBVORA_QA_<head>.json`; only if the `PASS_HOST_SYNTHETIC_ONLY` gate succeeds proceed to native Windows NTFS failure/recovery and true `file://` browser validation. If the report fails, reproduce and fix specific product test failures in `feature/p0-db-map`. Only after complete restore/integrity evidence consider actual C2 chunk persistence and later customer-facing release.

Keep `main` and `develop` unchanged, and do not enable paid CI, public source, customer DB access or archive deletion without appropriate authorization.
