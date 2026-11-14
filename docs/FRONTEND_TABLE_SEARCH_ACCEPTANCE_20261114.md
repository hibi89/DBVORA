# DBVORA P0 local table search — exact SHA acceptance (2026-11-14 KST)

## Scope / two alternatives
A. Server-side new query/filter endpoint: adds HTTP requests and server-side schema caching, more attack surface and maintenance.
B. Client-side substring search against already loaded schema name metadata: no network, no DB read, preserves existing API and original data. **B implemented**.

## Source changes
- `dbvora/web/index.html`: labelled local search field, live count/status, empty-state.
- `dbvora/web/style.css`: responsive search controls and hidden nodes.
- `dbvora/web/app.js`: case-insensitive table-name filtering, selected inspector sync, skip hidden FK edges, filter survives refresh. Dynamic strings use `textContent`; no `innerHTML`.
- `tests/test_ui_dom.cjs`: no-dependency DOM search, case, no match, malicious identifier inert, edge count, refresh persistence.
- `scripts/browser_http_e2e.py`: real Chromium check for filter, 0 matches and reset. Only generated synthetic SQLite, localhost HTTP, no real data.

## Verified exact source
- [GitHub code `d52b75d90f1674e2357458c7bfbc22c4f2edb569`](https://github.com/hibi89/DBVORA/commit/d52b75d90f1674e2357458c7bfbc22c4f2edb569), developer branch `feature/p0-db-map`. Previous source commit: `25fd6f3a9a7b0f9dc1577463a73f6d48e6dc12ce`.
- [Full release gate](https://github.com/hibi89/DBVORA/actions/runs/43562375829): Windows2025 / Ubuntu24.04 **2/2 success**, Python 698 discovered, Ubuntu 698 passed/0 failed/0 skipped; Windows 697 passed/0 failed/1 named POSIX-only skip; mandatory stages 12/12 on each OS. Node DOM test PASSED.
- [Actual Chromium localhost](https://github.com/hibi89/DBVORA/actions/runs/43562375838): Windows/Linux 2/2 success; 9/9 each, including local filter/no match/reset, FK click, mobile, malicious schema text, network/host/origin/POST safety.
- [Unsigned preview ZIP](https://github.com/hibi89/DBVORA/actions/runs/43562375798), [unsigned Windows synthetic executable](https://github.com/hibi89/DBVORA/actions/runs/43562375840), [blueprint evidence gate](https://github.com/hibi89/DBVORA/actions/runs/43562376170): successful same SHA workflows, not end-user certifications.

## Hold / truthfulness
No actual customer data/keys, physical power-cut, buyer Windows10/11, legal copyright/license/NOTICE, support/price/registration, production deployment, official weighted final user acceptance was tested here. No actual Windows owner PC instructions are issued during travel. Official whole-product score **UNASSESSED** (historic internal engineering scope 95 is not official); `[작업중]`, RELEASE HOLD, 0 registrations, Vercel/Production not applicable. This feature's CI pass is not 100% product completion.
