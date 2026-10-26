# DBVORA authentic frontend assets and Chromium synthetic verification — 2026-10-26 KST

## Source provenance

Private repo `hibi89/DBVORA`; active branch `feature/p0-db-map`. Baseline branch HEAD before this probe improvement: `f85d1c9080e3ccb6ecf429ce9e179fb7fb36be7d`.

Actual source bytes obtained from the authenticated private GitHub connector and locally compared using `git hash-object`:

| File | Matching Git blob SHA |
| --- | --- |
| `dbvora/web/app.js` | `0703e9b8a87c6a07d0ddfe45e350a065c7632e04` |
| `dbvora/web/style.css` | `4601a7cbdc0320e554cbf59966e3b99046b06483` |
| `dbvora/web/index.html` | `16ddbbf4ef7144dec2c7428af71cec877a5e27b0` |
| `dbvora/export_html.py` | `ce0accd9939e7174c1cdee27a8ea9a2b4a953901` |
| `dbvora/inventory.py` | `f40135add5cd8106b1ae722a0b799ec88a842cbd` |
| `dbvora/connectors/sqlite_reader.py` | `1d663d9d8243b75dbca0e697428870328bd87509` |
| `dbvora/offline_selftest.py` | `290e1f61a8d87f130c662ac15d6582c150575835` |
| `scripts/offline_html_browser_probe.py` | `1bc43ccad0b371c2412af5d90e749be3c2d617dd` (new commit) |

The browser probe source was verified locally against the source Git blob, enhanced in the temporary environment and run, then committed; published GitHub resulting Git blob equals the tested `1bc43...` SHA. Commit: `715b1b96567c333e0907ea947f26bd0f3afcc193`.

**Unlike the preceding `OFFLINE_SELFTEST_REAL_CORE` verification, no CSS or JS substitution was used.** Other needed Python/fixture/test sources remain authentic GitHub bytes as described in that earlier document. This was still a focused, incomplete test checkout; do not call it a full Git clone or complete source regression.

## Commands and observed results

Environment: Linux, Python 3.13.5, Node 22.16.0, installed Playwright and `/usr/bin/chromium`. Synthetic SQLite files under an OS-temp directory; no real user/customer DB, cloud transfer, hosted server, paid GitHub Actions or installers.

```sh
node --check dbvora/web/app.js
python -W error::ResourceWarning -m unittest discover -s tests -v
python -m dbvora.offline_selftest
python -W error::ResourceWarning -m scripts.offline_html_browser_probe --chromium /usr/bin/chromium
```

Results:
- Real GitHub JavaScript syntax checked **PASS**.
- **17/17 focused Python HTML/selfcheck tests PASS**, 0 fail/skip or ResourceWarning, using authentic CSS, JS, exporter, inventory and SQLite reader.
- Standalone synthetic self-check **9/9 PASS**; `ready_for_customer_data=false` and both Windows-native flags false.
- Existing official browser probe **7/7 PASS** on real assets before strengthening.
- Enhanced checked-in official browser probe **13/13 PASS** using Chromium `page.set_content()` of the generated HTML. Checks: 4 schema buttons; one declared FK SVG edge; clicking selected table; hostile `</script>` and SVG identifiers rendered inert as text; zero JS errors; zero external requests; 390px mobile no horizontal overflow; source byte hash+mtime unchanged; exact HTML hash+length; CSP present and external link/script references absent; database rows/path excluded; actual CSS computed style loaded; refresh without HTTP server. JSON output explicitly reports `browser_http_e2e=false`, `browser_file_navigation=false`, `ready_for_customer_data=false`.
- Separate exploratory browser check using the same actual assets and three custom tables returned **11/11 PASS** with in-memory HTML. It is not checked-in release acceptance.

### Hard browser limitation

Attempted `page.goto(file:///tmp/.../dbvora-map-*.html)` with generated synthetic report. This environment enforced `net::ERR_BLOCKED_BY_ADMINISTRATOR`. No attempts to bypass administrative policy; legitimate fallback `page.set_content()` validates real HTML/CSS/JS rendering, but not native `file://` navigation. **Do not claim the browser opened local files.**

## Remaining gates

- Full authenticated private checkout with all modules/scripts/tests: `python -m scripts.verify_release_gate` requiring **>=199** Python tests and multi-stage synthetic archival checks remains **NOT RUN on current feature SHA**.
- Native Windows3.11 NTFS archive publication/directory-fsync and independent recovery, native Windows browser `file://` launch, real localhost HTTP E2E, customer data and hardware power-cut scenarios **NOT TESTED**.
- Source preview is unsigned; no production/installer release, customer readiness or `main`/`develop` promotion. No paid CI, external hosted tool, public code or destructive data tasks.

## Follow-up

1. Assemble authorized complete private checkout in a permitted test environment and run complete 199+ Python tests, Node DOM and archive roundtrip/unified gate; record evidence at final feature SHA.
2. Native Windows synthetic-only owner validation when the owner is at the PC: `py -3.11 -m dbvora.offline_selftest` on private preview and, on the complete checkout, `py -3.11 -B -m scripts.windows_ntfs_gate`; ensure real file-based browser opening before Windows distribution.
3. Keep approvals for installer/public distribution, client DB, paid CI and permissions separate.
