## Offline HTML schema map — no UI pip dependencies (2026-10-26 KST)

### Use
DBVORA now creates a **single self-contained HTML table/FK structure map** without FastAPI, Uvicorn, or an HTTP server. Requires only Python 3.11+; use an explicitly authorized **synthetic SQLite file** for current development:
```sh
python -m dbvora.export_html --db /absolute/fixture.sqlite --out /absolute/existing/output_folder
```
On Windows after extracting the unsigned source ZIP:
```powershell
py -3 -m dbvora.export_html --db "C:\absolute\synthetic.sqlite" --out "C:\existing\folder"
```
Or invoke `export_dbvora_map_windows.cmd` with the two quoted absolute paths. Open the newly created `dbvora-map-<uuid>.html` locally in a browser. The file is **not a database backup**; it embeds **schema metadata** (table/column names and FK), not table rows or the source path. It can still contain confidential schema design: do not distribute without authorization.

### Security and limitations
- Single HTML embeds actual source `index.html`, `style.css`, and `app.js`; inventory JSON is base64-encoded and decoded as JSON, never interpolated into JS/HTML. Native DOM `textContent` renders untrusted identifiers; fails closed if asset contains closing script/style tags.
- File CSP has `connect-src 'none'`, `img-src 'none'`, no external styles/scripts; requires inline script/style for local offline operation. New-only report naming with exclusive create, source DB never modified, 12 MiB HTML cap. Existing files not overwritten.
- The result is **unsigned**, unencrypted and local. It is not an `.exe`, a Windows/NTFS archive durability pass, production web app, HTTP browser E2E or customer data release approval. Python must be present to generate a new report; once generated the HTML itself has no Python dependency.

### Executed checks and deliverables
- Linux Python 3.13.5: **194/194 checked-in Python tests PASS, 0 fail/skip**, including **12 new export-specific** plus **2 new source-bundle** tests; `python -m scripts.verify_release_gate` all six synthetic Linux steps PASS, actual synthetic SQLite archive/receipt 8 checks, Node DOM and temp-FS preflight PASS.
- Actual headless Chromium (`/usr/bin/chromium`, Playwright used for *testing only*) generated offline HTML **7/7**: schema table cards, FK edges, selection, malicious `</script>` identifier shown as text only, no JS errors, **zero network requests**, mobile 390px no horizontal overflow. Chromium `set_content` was used; opening `file://` or localhost HTTP E2E was NOT tested in this environment.
- Offline source preview package deterministic ZIP integrity check PASS, **26 payload files + one unsigned SHA manifest**. A fresh unpack can invoke `python -m dbvora.export_html` with no UI extras.
- Built synthetic deliverables SHA-256: ZIP `7845f5f0e2780e22daa9ad27232879b51c78b97a9935847a75c30c8e9ac093b9` (43,307 B), example HTML `618b7d9f7141d16e6445075f99f2d4666a9e1b60a1146b4770856c4d763c76c1` (22,907 B). Neither contains real customer database rows.

### Next
Real Windows Python 3.11/NTFS backup file+directory fsync gate remains **BLOCKED_UNVERIFIED**. Verify the standalone HTML file on a native Windows browser and CLI launchers, then fix tested platform issues; actual browser HTTP E2E and native installer remain pending. No customer DB, paid CI, Vercel, main/develop promotion, public repo or executable signing without explicit authorization.
