# DBVORA portable synthetic self-check launchers — 2026-10-26 KST

## Change

Private repo `hibi89/DBVORA`; branch `feature/p0-db-map`. The previous `dbvora.offline_selftest` Python-only CLI is now presented as dedicated scripts inside the existing **unsigned, uninstalled source ZIP**:

- `check_dbvora_windows.cmd`: `cd /d "%~dp0"`, reject nonzero arguments, run `py -3.11 -m dbvora.offline_selftest`, propagate exit code. No path to client database accepted.
- `check_dbvora_unix.sh`: reject nonzero arguments, change to its own directory, exec `python3 -m dbvora.offline_selftest`. Run with `sh check_dbvora_unix.sh` (ZIP does not promise executable Unix file bits).
- `README_PORTABLE.txt`: operator instructions for both.
- `scripts/build_portable.py`: both launchers required in the deterministic package manifest; any missing launcher fails closed in ZIP verification.
- `tests/test_portable_build.py`: two new tests (1) create/extract source ZIP and execute **actual** self-check in the extracted package with no `pip` or customer path; require 9 checks and no customer-ready claims; (2) inspect both scripts for no external-download/installation commands and no arguments.
- `scripts/verify_release_gate.py` / `tests/test_verify_release_gate.py`: minimum checked-in Python cases **199 → 201**, fail if 200; mock decision fixtures revised.

All changes were written via authenticated GitHub connector on the feature branch. No `main`/`develop` promotion, hosted production, Actions execution, installation, customer DB, telemetry or paid features.

## Observed validation — scope matters

- Fetched **all 14 actual Python test source files** from the private GitHub branch, verified all Git blob IDs against the branch tree, and counted exactly **201** `def test_...` definitions. Matching the threshold only proves cases are present; it is **not** an execution result.
- In the available previously reconstructed source staging directory, reran the unchanged authentic SQLite/HTML components and existing tests on Linux Python 3.13.5:
  - `python -W error::ResourceWarning -m unittest discover -s tests -v`: **17 focused tests PASS**, 0 FAIL/SKIP.
  - `python -m dbvora.offline_selftest`: **9/9 PASS**, `ready_for_customer_data=false`.
  - `python -W error::ResourceWarning -m scripts.offline_html_browser_probe --chromium /usr/bin/chromium`: **13/13 PASS**, real CSS/JS on Playwright in-memory page; `browser_file_navigation=false` and `browser_http_e2e=false`.
- Executed the newly packaged **Unix launcher template** copied into the local staged source tree with `sh check_dbvora_unix.sh`: returns 0 and 9/9 synthetic-only check PASS. Calling it with a fake user DB argument returns code 2 without executing the self-check. This was a **template test**, not proof that a generated ZIP is valid.
- **Not run** on latest GitHub HEAD: the two new checked-in `tests/test_portable_build.py` cases, complete ZIP build/extract/execute test, unified synthetic archive and Node release gate, or all 201 Python cases. The test execution workspace is an incomplete authenticated-reconstructed checkout, not a full private clone. No native Windows cmd execution, Windows Python3.11/NTFS, native `file://` browser launch, power-cut recovery, signed installer or customer-data validation.

## Next

1. On a complete authorized private checkout, run `python -m scripts.verify_release_gate` and require >=201 tests, six release steps including Node, synthetic archive roundtrip and fs preflight; specifically confirm the two new packaged self-check tests.
2. Separately, on user-authorized Windows Python3.11, extract the source developer preview, invoke `check_dbvora_windows.cmd` with **no arguments** and `py -3.11 -B -m scripts.windows_ntfs_gate` from complete checkout. Neither script changes customer DB; Windows archive durability still fails closed on unsupported filesystem sync.
3. Real `file://` navigation and independent restore validation remain OS gates. Never promote to customer readiness or Production from Linux synthetic-only evidence.
