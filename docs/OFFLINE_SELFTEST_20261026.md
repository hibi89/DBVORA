# DBVORA Offline HTML owner self-check — 2026-10-26 KST

## Purpose and scope
Use a single **no-pip**, synthetic-only smoke command from the **private** source checkout or extracted unsigned developer preview:
```powershell
py -3.11 -m dbvora.offline_selftest
```
On Linux/macOS: `python3 -m dbvora.offline_selftest`.

The checker builds a throwaway SQLite database in the OS temp directory, inserts a fake row canary, runs the **actual DBVORA exporter** when executed from a complete checkout, checks the generated self-contained HTML, and deletes the temporary files. It does not accept a customer DB path, access credentials, network, cloud, archive directories, or real customer data.

Nine success conditions: export status; explicit no-customer/no-row status; exact HTML bytes/size hash; CSP presence and `connect-src 'none'`; no original external asset links; synthetic row canary absent; source filesystem path absent; two synthetic table names and one declared FK edge present; original synthetic SQLite hash and mtime unchanged. Invalid generated filenames (including traversal) fail closed before a report is read. JSON output has no source path or exception text.

A PASS means **synthetic offline HTML generation**, not Windows `file://` browser rendering, Windows NTFS crash durability, SQLite archive publication, power-cut survival, actual customer data approval, signatures, encryption, or an EXE installation.

## Changes
- `dbvora/offline_selftest.py`: new self-contained Python standard-library driver.
- `tests/test_offline_selftest.py`: 4 new tests (positive generated HTML, exception sanitization, invalid filename, missing filename).
- `scripts/build_portable.py`: self-check required as a bundled `.py` file; README_PORTABLE embeds the command and scope.
- `scripts/verify_release_gate.py` and its mock decision tests: minimum checked-in Python discovery **195 → 199**, and required source/test-file presence.

## Evidence
- Locally compiled **the exact two new file contents** with Python `py_compile`: PASS.
- Ran four checked-in new test cases **4 PASS / 0 FAIL / 0 SKIP** against a clearly identified **test-double HTML export boundary**, exercising the self-test runner and negative cases. CLI returned `PASS_SYNTHETIC_OFFLINE_HTML_ONLY` with 9 checks in that stubbed environment. **This is not real DBVORA export integration.**
- Checked exact Git blob IDs after publishing: source `290e1f61a8d87f130c662ac15d6582c150575835`, tests `f52b3bc90d58027cf7d0e3a8b5267c81f4d0ce2d`, matching locally syntax-checked and mock-tested files.
- **NOT RUN** on the post-change feature SHA: 199-case full Python suite, complete `scripts.verify_release_gate`, actual `dbvora.export_html.export` integration inside the new smoke command, native Windows Python3.11/NTFS, `file://` browser launch, customer input, signed/installed distribution. Earlier historical 194/194 Linux Python and Chromium 7/7 belong to a prior SHA.

## Next gates (fail closed)
1. Complete authorized private checkout: `python -m dbvora.offline_selftest` with the real original `dbvora.export_html`, then `python -m scripts.verify_release_gate` (>=199 checked-in Python tests), independent generated HTML browser probe if available.
2. On authorized Windows PC with Python3.11, from complete checkout or extracted developer preview: `py -3.11 -m dbvora.offline_selftest`, and separately for a **complete checkout only**, `py -3.11 -B -m scripts.windows_ntfs_gate`. The Windows archive test may fail closed because directory fsync is unsupported; do not bypass it.
3. Native Windows browser opening of the generated offline HTML and installer evaluation only after independent results; no customer DB or paid CI without prior approval.
