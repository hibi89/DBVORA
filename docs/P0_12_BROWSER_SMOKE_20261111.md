# DBVORA P0-12 — Node TAP and Chromium offline graph verification (2026-11-11 KST)

## Objective and validation approach
Verify the previously committed P0-11 offline SQLite FK graph without using a customer database or paid hosted CI. Two methods considered:
- A (used): extract the exact inline JavaScript from existing private GitHub source and run locally using a reconstructable synthetic DOM shell, Node TAP, then an installed headless Chromium browser. No external service or data export.
- B (deferred): a complete private repository checkout and actual Windows local-file navigation. Higher fidelity but unavailable from the current tool runtime; existing environment blocks file:// navigation by administrator policy. B remains necessary for release, not silently replaced by A.

## Exact source identity and executed tests
- Remote branch at start: hibi89/DBVORA feature/p0-db-map, SHA 1b16d7e97de4830d04c4b46e13efe140fe1c1e6f.
- Actual GitHub test Git blob hashes matched locally:
  - tests/test_ui_dom.cjs = c932516f73c02a7ed598a23865e3ec921eac6380
  - tests/test_workspace_html_dom.cjs = 6c81e20d72c1bf9a40c5c27907419f5919cb9fb4
  - dbvora/web/app.js = c448d89782ef2ab5bd6440549365b7c9fda1739b
- Offline HTML inline JavaScript extracted from GitHub blob dbvora/workspace_html.py a2a2f77a59077f95075f5dd62058749c347bb40b. Local extracted source script matched remote UTF-16 character count 6575 and FNV-1a 32-bit fingerprint 6e298a23 (checksum corroboration, not cryptographic verification). The surrounding HTML/CSS was **synthetically reconstructed**, not the exact complete HTML source; do not mislabel as an end-to-end original-template test.
- **Actual Node22 TAP:** node --test tests/test_ui_dom.cjs: tests 1, pass 1, fail 0, skip 0. This invokes both original UI behavior checks and P0-11 offline graph VM checks. Source JS/test blob identities checked as above.
- **Actual Chromium / Playwright Python3.13:** 3 synthetic document-injection scenarios PASS (ASCII-case FK link drawn; Unicode name distinction remains unlinked; hostile identifier rendered as inert text), database and table click/reselection, schema-review panel, console exceptions 0, externally outbound HTTP/WS requests 0, injected img elements 0.
- A separate strict file:/// navigation attempt returned net::ERR_BLOCKED_BY_ADMINISTRATOR. This is an **environment policy block**, not proof of an app fault. Explicitly used page.set_content to verify JavaScript/DOM as a fallback; **real file:// access NOT VERIFIED**. Repeated blind file navigation is not required.
- Previous P0-08/09/10 isolated Python cases 22/22 PASS belong to an earlier independent run; do not add to current test count as though re-executed here.

## Added reusable code
- New optional scripts/browser_workspace_smoke.py in private feature branch, exact Git blob 8e31d54be3be33ff8a0e394c096baf53f228e8aa, code commit 55749bfc687acb114d62b359ecf2abe1c5e9c120. Reads Python _PAGE literal via AST (does not import DB modules), injects three synthetic catalog fixtures, verifies rendered SVG, click interactions, review panel, no img injection / JS console error / outbound HTTP(S), and emits bounded JSON.
- Run, with installed Playwright Python & Chromium:
  - python -m scripts.browser_workspace_smoke --chromium /path/to/chromium
  - For restricted execution only: python -m scripts.browser_workspace_smoke --chromium /path/to/chromium --document-only
- Modes deliberately report PASS_FILE_NAVIGATION vs PASS_RENDER_ONLY; NOT_RUN when file:// is policy blocked, Playwright is absent, or no browser. Script is **optional**, not integrated as a mandatory release gate and does not add an installation dependency.
- Local script exact blob matched GitHub, and document-only mode passed 3/3 against a **reconstructed HTML shell whose embedded JS matched the GitHub script fingerprint**. Full-source actual template run of this newly committed script is not yet verified; it remains a next step.

## Risks, remaining validation and readiness
- Complete private Python >=355 release suite, full source-generated HTML/SQLite export integration, Windows 3.11, real browser file navigation, NTFS/power-loss archive durability and real customer acceptance all NOT RUN.
- No customer DB, backup archive, secrets, account/billing, permissions, public deploy, main/develop, or other product were changed. Temporary synthetic files only; no external network. Restore by reverting the optional script commit; earlier release code untouched.
- **DBVORA commercial final completion 55% unchanged / target 70% / RELEASE HOLD**. Browser progress is verified, but does not justify declaring end-to-end Windows/archive readiness or an arbitrary percentage uplift.

## Next acceptance
1. Obtain authorized complete private checkout without repeatedly retrying blocked clone. Run node --test tests/test_ui_dom.cjs and python -B -m unittest -v tests.test_workspace_registry tests.test_schema_review_ui tests.test_workspace_publication; then python -m scripts.verify_release_gate (>=355 Python tests).
2. Run the optional browser smoke against its **actual full source HTML template**; on owner's Windows or an unrestricted filesystem test default file:// mode. Do not interpret PASS_RENDER_ONLY as this.
3. Verify archive ZIP/ZSTD receipt and native NTFS backup safety separately before percentage increase/release decision.
