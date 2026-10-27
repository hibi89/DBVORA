# P1-C8 — Genuine Chromium offline HTML regression guard

**Date:** 2026-10-27 KST. **Repository:** private `hibi89/DBVORA`, `feature/p0-db-map`. **Source code baseline:** `cafbd87e61f20cffe778692f8a29db541588eeaf` (documentation commits may advance HEAD).

## Context and decision
The earlier resize-listener leak was fixed in `dbvora/web/app.js`, but the actual Chromium offline schema-view probe did not assert it. Existing Node simulated-DOM tests cover the case but not browser UI events and redraw. Kept the existing offline synthetic `page.set_content` probe, added an instrumented window resize-event registration counter **after initial boot** and required three manual refreshes to register zero additional handlers. No product runtime logic or customer data changed.

## Code change
`scripts/offline_html_browser_probe.py` now adds `checks.refresh_does_not_add_resize_listeners`, instrumenting the real Chromium window's `addEventListener('resize',...)` before three `#refresh` clicks. It fails closed if the count is nonzero. Git source blob `5a0767b12ae7e7a31c06f7f6ea5129ba7f586e0b`, commit `cafbd87e61f20cffe778692f8a29db541588eeaf`. Prior blob `1bc43ccad0b371c2412af5d90e749be3c2d617dd`.

## Actual tests
- Reviewed, reconstructed and verified actual remote Git blobs in an isolated local checkout: `dbvora/export_html.py` `ce0accd9939e7174c1cdee27a8ea9a2b4a953901`, `dbvora/web/app.js` `c448d89782ef2ab5bd6440549365b7c9fda1739b`, `dbvora/web/index.html` `16ddbbf4ef7144dec2c7428af71cec877a5e27b0`, `dbvora/web/style.css` `4601a7cbdc0320e554cbf59966e3b99046b06483`, `dbvora/inventory.py` `f40135add5cd8106b1ae722a0b799ec88a842cbd`, `dbvora/connectors/sqlite_reader.py` `1d663d9d8243b75dbca0e697428870328bd87509`, `tests/fixtures/make_sqlite.py` `7f407189ba98b70be22f52b7ca45b53c935f63e3`, `tests/test_export_html.py` `cb524f88f8a11f7cc25fe0e539f05c756c4d0563`, and the new probe `5a0767b12ae7e7a31c06f7f6ea5129ba7f586e0b`.
- **Actual Python3.13.5** `python -W error::ResourceWarning -m unittest -q tests.test_export_html`: **13/13 PASS**; compileall PASS. Synthetic fixtures only.
- **Actual Chromium /usr/bin/chromium through installed Playwright** `python -m scripts.offline_html_browser_probe --chromium /usr/bin/chromium`: **14/14 PASS**, 0 failed checks. Includes safe schema-only export, source bytes/mtime unchanged, report SHA256/size, embedded CSS/JS/CSP, no DB row data/paths, FK edges, XSS hostile identifiers, selection, repeated refresh, no JS error/outbound requests and mobile overflow.
- **Negative control:** replacing only JS with the historical committed `0703e9b8a87c6a07d0ddfe45e350a065c7632e04` produced `FAIL_CLOSED`, **13/14 PASS**, with the sole failed check being `refresh_does_not_add_resize_listeners=false`. Restored exact current JS; **14/14 PASS**. Confirms the regression detects the original bug, not just browser startup.

## Scope and environment limits
- An additional experimental `page.goto(file:///tmp/.../dbvora-map-....html)` request was blocked by the harness/browser administrator policy: `net::ERR_BLOCKED_BY_ADMINISTRATOR`. The real Chromium **`page.set_content`** result remains valid but **`file://` direct navigation is NOT VERIFIED** and the refusal is NOT claimed as a DBVORA app bug. Do not circumvent administrator restriction.
- No HTTP server e2e, native Windows Python3.11/NTFS filesystem durability, hardware power loss, installer/customer data, cryptographic signing or commercial release tested.
- Full **214** Python suite and six-stage synthetic release gate remain **NOT RUN** due private source transport limitation; the 13-case focused test does not imply full suite PASS.
- No paid CI, public repo, customer DB, branch promotion or destructive action.

## Reproduction on authorized full feature checkout
```bash
python -W error::ResourceWarning -m unittest -q tests.test_export_html
python -m scripts.offline_html_browser_probe --chromium /usr/bin/chromium
python -m scripts.verify_release_gate
```
For genuine `file://` navigation, use an owner-controlled native browser environment that allows local file navigation and verify no outbound requests. Keep `ready_for_customer_data=false` pending Windows safety gates.
