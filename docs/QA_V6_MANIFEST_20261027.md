# DBVORA offline QA kit v6 — current source pins

Updated 2026-10-27 KST for the private `hibi89/DBVORA` branch `feature/p0-db-map`. Exact **source-code baseline** `cafbd87e61f20cffe778692f8a29db541588eeaf`. Later docs commits must not be mistaken for source differences.

- Change over v5: source file `scripts/offline_html_browser_probe.py` has a new genuine Chromium resize-listener regression check. SHA-1 Git blob pin updated from `1bc43ccad0b371c2412af5d90e749be3c2d617dd` to `5a0767b12ae7e7a31c06f7f6ea5129ba7f586e0b`; other 49 executable/config pins unchanged and match remote HEAD. The trusted base SHA and browser blob assertion in the harness were updated together.
- Preserves v5 two-phase Git-blob checks: before extraction and during extracting bytes to the OS temporary test checkout; rejects ZIP swaps, extra executable files, unsafe archive members, nonmatching pins and missing source **before code execution**. Source ZIP must come from the authorized owner of the private repo. No paid CI, external upload, customer DB or source-mirror request.
- Local artifact `DBVORA_full_source_QA_kit_v6_20261027.zip`, **10,594 bytes**, SHA-256 `c80228f017c65c167ee00c345c5fe5b3caa02cb7080b0f8e142171a412abc594`. This ZIP remains a **conversation artifact**, not a file committed to GitHub; GitHub stores only documentation. It contains exactly `README.txt`, `pinned_git_blobs.txt`, `run_dbvora_qa.py`, `test_runner.py`, `test_source_pinning.py`.
- Real Python3.13.5 harness `python -W error::ResourceWarning -m unittest -q test_runner test_source_pinning` **19/19 PASS**, plus a fresh temporary extraction **19/19 PASS**; no failure or skip. Genuine current browser/HTML checks separately validated: **14/14 Chromium**, **13/13 Python HTML export**. Full 214-case product Python test suite **NOT RUN**.
- The earlier v4/v5 QA ZIPs deliberately reject this updated source file SHA. Do not disable/overwrite obsolete pins to force a pass; use v6 with this code baseline instead.

## Offline commands
```bash
python -W error::ResourceWarning -m unittest -v test_runner test_source_pinning
python run_dbvora_qa.py --zip /absolute/authorized/private-feature-source.zip --report /absolute/new-output.json --browser
```
The complete private source ZIP is not currently accessible to this runtime, so **actual complete 214 Python + six-stage gate remains blocked**. Native Windows Python3.11/NTFS, real `file://` navigation, hardware interruption and customer data remain UNVERIFIED. Use `docs/P1_C8_CHROMIUM_OFFLINE_REGRESSION_20261027.md` for browser evidence and `docs/QA_V5_POSTVERIFY_EXTRACTION_20261027.md` for safety design.
