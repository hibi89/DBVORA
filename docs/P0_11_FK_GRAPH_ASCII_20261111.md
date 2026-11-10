# DBVORA P0-11 — Offline SVG FK edge alignment (2026-11-11 KST)

## Defect
P0-10 made the SQLite catalog flag `target_in_inventory` ASCII case-insensitive. But the offline SVG graph still used JavaScript `names.indexOf(edge.to_table)` and required the original spelling, so `Parent` versus declared `PARENT` produced a true catalog match but silently omitted its link. This disconnect affects the actual schema graph, not source row data.

## Alternatives and choice
A. Change only SVG name lookup to SQLite's ASCII-only identifier matching, using a `Map` once per database. **Selected:** O(tables+edges), no data layout change or dependency, preserves metadata and original names.
B. Rewrite all catalog names to lowercase before export. Rejected: destroys spelling and can create false equality for Unicode names; broader regression risk.

## Changes
- `dbvora/workspace_html.py`: `sqliteAsciiKey` converts only ASCII uppercase letters; graph builds `positions` map for existing table names, looks up both FK endpoints. No Unicode `toLowerCase` on complete name. Missing/false FK remains undrawn.
- `tests/test_workspace_html_dom.cjs` (new): lightweight VM runs Python `_PAGE` script from the actual source file. It checks ASCII-case link, Unicode non-match, unchanged exact-case link, and safe text-only display of an untrusted schema identifier.
- `tests/test_ui_dom.cjs`: calls the new VM verifier as part of the existing Node TAP test, preserving the release gate's one-file/one-test TAP policy.
- `scripts/verify_release_gate.py`: adds the JS test source to required checkout files; minimum Python discovery unchanged at 355.

## Execution evidence and limits
- Source code commit `47e9b7c840bcd9fd6613b69d58f3736cd43161c7`; remote exact Git blob of `workspace_html.py` `a2a2f77a59077f95075f5dd62058749c347bb40b`, new DOM test blob `6c81e20d72c1bf9a40c5c27907419f5919cb9fb4`.
- Developer local Node22 ran ASCII graph key and Unicode distinctness subset **5/5 assertions PASS** with extracted logic; previous Python isolated exact-source P0-08/09/10 22/22 PASS. These are **not** an execution of the newly committed full-source HTML VM test.
- New `tests/test_workspace_html_dom.cjs`, modified `tests/test_ui_dom.cjs` integration, full Python >=355 release gate, Windows Python3.11, real browser/file:// and customer/Production archive safety **NOT RUN** because private checkout not accessible from this container (github.com DNS failure). No paid GitHub Actions used.
- Original SQLite/read-only DB input, prior customer data, original archive code, main/develop, GitHub/Vercel production, secrets, accounts, permissions and external uploads unchanged.
- No release-ready, power-loss durable or security certification claim. **DBVORA final product completion 55% remains unchanged**, target 70%, RELEASE HOLD.

## Next gate
1. Authorized complete checkout: `node --test tests/test_ui_dom.cjs` (one TAP file; invokes new SVG test), plus `python -B -m unittest -v tests.test_workspace_registry tests.test_schema_review_ui tests.test_workspace_publication`.
2. `python -m scripts.verify_release_gate` from same SHA, require >=355 Python cases and correct Node/synthetic archive proofs; inspect first real failing assertion.
3. Windows Python3.11 HTML GUI actual file navigation/interaction and native NTFS archive gates remain separate.
4. Evaluate product % only against implemented **and verified** overall delivery scope; do not count this localized UI fix as 70% readiness.

Rollback via normal feature-branch Git revert of P0-11; do not alter original history.
