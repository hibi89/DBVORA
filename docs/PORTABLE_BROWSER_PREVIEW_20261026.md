# DBVORA v0.2.0 source preview + real Chromium DOM verification

Evidence date: 2026-10-26 KST. Input branch: private `hibi89/DBVORA`, `feature/p0-db-map`, commit `11128c0c25af3a5bf70e66b524fd6a264fd6f8d9`.

## Exact results
- All **180 checked-in Python unittest cases PASS**, 0 fails / 0 skips. Run: `python -W error::ResourceWarning -m unittest discover -s tests -q`.
- `python -m scripts.verify_release_gate` -> `PASS_SYNTHETIC_ENVIRONMENT_ONLY`, 6/6 stages PASS, `ready_for_customer_data=false`. Includes real 8-check SQLite ZIP/ZSTD+Receipt synthetic CLI gate, Node TAP 1/1, compileall and temp FS preflight.
- Actual local Chromium headless binary executed real DBVORA **unmodified HTML/CSS/JS**, using `page.set_content` / `add_style_tag` / `add_script_tag` and **injected synthetic** `inspect_sqlite` JSON due sandbox administrator blocking `file://` and `http://127.0.0.1` navigation. `python -m scripts.browser_visual_probe --chromium /usr/bin/chromium` -> `PASS_SYNTHETIC_BROWSER_DOM_ONLY`, 5/5: 4 table nodes/1 FK, inspector navigation, malicious `<img>`/`<svg>` escaped as text (no dialog or injected tags), no page JS errors, 390px responsive viewport without horizontal overflow.
- This is real Chromium DOM execution and rendered visual inspection (1440px desktop, 390px mobile), **not** networked localhost browser E2E, nor a complete accessibility/keyboard audit. HTTP adapter separately checked by Python FastAPI TestClient suite, not via browser socket.
- Developer source ZIP built and verified with `python -m scripts.build_portable --output /absolute/existing/dir` and `python -m scripts.build_portable --verify /absolute/archive.zip`. ZIP `dbvora-dev-preview-0.2.0.zip`, SHA-256 `aeaeb43d4c6ce59d2a65849f253e3528fe94d8e7624bec20e13924bf13057f2f`, contains **23 file entries + 1 manifest** (builder output `files=23` excludes manifest). SHA manifest checks payload integrity, unsigned; do not call it authenticated. No customer data, `.env`, SQLite, ZIP backup or cache files inside.
- Packaging tests `tests/test_portable_build.py` **13/13 PASS**, including reproducibility, never overwrite existing output, tamper/path traversal rejection, isolated source extraction + real read-only CLI inspection with generated SQLite, invalid output and unsigned boundaries. Included in the 180-case suite.
- Fixed metadata version mismatch: `dbvora.__version__` is now `0.2.0` like `pyproject.toml`; packaged UI header now shows `v0.2 / P0`.
- New source/test/HTML/change runner **7 Git blobs** created from locally executed sources; each matches local `git hash-object` exactly. No GitHub Actions or third-party upload.

## Developer preview limitations
- The package is a **source ZIP only**, not `.exe`/`.msi`, not a stand-alone binary. It does not bundle Python, FastAPI/Uvicorn, Node, ZSTD or Windows-specific native APIs.
- Windows manual run after unzipping into folder with installed Python3.11 and optional Python UI dependencies: `py -3.11 -m pip install ".[ui]"` (installation may contact Python package indexes), then `run_dbvora_windows.cmd "C:\\absolute\\synthetic.sqlite"`. On UNIX: `python3 -m pip install ".[ui]"`, then `sh run_dbvora_unix.sh "/absolute/synthetic.sqlite"`. CLI metadata-only is also available without UI extra.
- Build script uses only project source and fixed synthetic launch templates. The resulting ZIP has no original DB rows. No archive background scheduler or restore process is automatically launched.
- Actual Windows 3.11 + NTFS directory-fsync/hardlink semantics, Win GUI rendering, power-cut durability, offline dependency wheelhouse and signed installer remain **NOT_TESTED**. The strict Windows NTFS gate stays fail-closed; any unsupported durability cannot be reported as a successful backup.
- No customer records or production environments tested or certified. `main`/`develop` remain unchanged. Explicit approval required for customer files, paid CI, Public, native installer release and external deployment.

## Next
1. Authorized Windows Python3.11 / NTFS synthetic gate: `py -3.11 -B -m scripts.windows_ntfs_gate` in full private source checkout. If directory sync is unsupported, maintain fail-closed until a reviewed Windows backend is validated.
2. Actual Windows browser via HTTP localhost and keyboard/responsive inspection, then develop a signed/standalone installer with offline dependencies only after native filesystem confidence.
3. Assess M2 deduplication and scheduler idempotency separately; no retention deletion without recovery proof.
