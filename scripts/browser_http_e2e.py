"""Real Chromium + local HTTP smoke against generated synthetic SQLite only.

No customer DB/remote host/keys accepted. Screenshots are synthetic.
Pass does not certify Windows, physical power-loss durability, or sale readiness.
"""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dbvora.inventory import inspect_sqlite
from dbvora.observation_ledger import append_observation
from tests.fixtures.make_sqlite import create_fixture
from tests.fixtures.large_sqlite import extend_synthetic_catalog


class GateError(ValueError):
    pass


def require(value, code):
    if not value:
        raise GateError(code)


def http_code(url, *, method="GET", headers=None):
    try:
        with urlopen(Request(url, method=method, headers=headers or {}), timeout=3) as resp:
            return resp.status
    except HTTPError as exc:
        return exc.code


def digest(db):
    return hashlib.sha256(db.read_bytes()).hexdigest(), db.stat().st_mtime_ns


def run(*, screenshots=None):
    result = {"contract": "dbvora.synthetic-chromium-http-e2e.v1", "status": "FAIL_CLOSED",
              "scope": "LOCAL_HTTP_SYNTHETIC_ONLY", "real_browser": False,
              "local_http": False, "ready_for_customer_data": False,
              "power_loss_verified": False, "checks": [], "screenshots": []}
    proc = None
    multi_proc = None
    try:
        folder = Path(screenshots) if screenshots else None
        if folder is not None:
            require(folder.is_absolute() and folder.is_dir() and
                    not any(x.is_symlink() for x in (folder, *folder.parents)),
                    "UNSAFE_SCREENSHOT_DIRECTORY")
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory(prefix="dbvora-http-browser-synthetic-") as temp:
            db = create_fixture(Path(temp) / "fixture.sqlite")
            ledger = Path(temp) / "observations.sqlite"
            source_metadata = inspect_sqlite(db)
            for observed_at, size_bytes in (
                    ("2026-11-14T06:00:00Z", 1024),
                    ("2026-11-14T06:30:00Z", 2048),
                    ("2026-11-14T07:00:00Z", 4096)):
                append_observation(
                    ledger, db_id=source_metadata["db_id"], observed_at=observed_at,
                    size_bytes=size_bytes,
                    scope="sqlite_main_file_excluding_wal_shm", consent=True)
            unchanged = digest(db)
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            base = f"http://127.0.0.1:{port}"
            startup = ("import sys,uvicorn;from dbvora.api import create_app;"
                       "p=int(sys.argv[2]);uvicorn.run(create_app(sys.argv[1],port=p,"
                       "observation_ledger_path=sys.argv[3]),"
                       "host='127.0.0.1',port=p,log_level='error',access_log=False)")
            proc = subprocess.Popen([sys.executable, "-B", "-c", startup,
                                     str(db), str(port), str(ledger)],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, env={
                                        **os.environ, "PYTHONIOENCODING": "utf-8"})
            for _ in range(60):
                if proc.poll() is not None:
                    break
                try:
                    if http_code(base + "/health") == 200:
                        break
                except (OSError, URLError):
                    pass
                time.sleep(0.2)
            else:
                raise GateError("LOCAL_SERVER_STARTUP_FAILED")
            require(proc.poll() is None and http_code(base + "/health") == 200,
                    "LOCAL_SERVER_STARTUP_FAILED")
            result["local_http"] = True
            result["checks"].append("localhost_200")

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, args=[
                    "--no-sandbox", "--disable-dev-shm-usage"])
                result["real_browser"] = True
                try:
                    page = browser.new_page(viewport={"width": 1440, "height": 900})
                    errors, dialogs, bad_http = [], [], []
                    page.on("pageerror", lambda exc: errors.append("JS_ERROR"))
                    page.on("dialog", lambda d: (dialogs.append("DIALOG"), d.dismiss()))
                    page.on("response", lambda resp: bad_http.append(resp.status)
                            if resp.url.startswith(base) and resp.status >= 400
                            and not resp.url.endswith("/favicon.ico") else None)
                    # Instrument native observer/listener ownership before app startup.
                    # A constant DOM count alone cannot expose retained observers.
                    page.add_init_script(script="""(() => {
                        const Native = window.ResizeObserver;
                        const probe = {created: 0, disconnected: 0,
                            live: 0, maxLive: 0, resizeListeners: 0};
                        window.__dbvoraRefreshProbe = probe;
                        window.ResizeObserver = class extends Native {
                            constructor(callback) {
                                super(callback);
                                this._active = false;
                                probe.created += 1;
                            }
                            observe(target, options) {
                                if (!this._active) {
                                    this._active = true;
                                    probe.live += 1;
                                    probe.maxLive = Math.max(probe.maxLive, probe.live);
                                }
                                return super.observe(target, options);
                            }
                            disconnect() {
                                if (this._active) {
                                    this._active = false;
                                    probe.live -= 1;
                                }
                                probe.disconnected += 1;
                                return super.disconnect();
                            }
                        };
                        const add = window.addEventListener;
                        window.addEventListener = function(type, fn, options) {
                            if (type === 'resize') probe.resizeListeners += 1;
                            return add.call(this, type, fn, options);
                        };
                    })()""")
                    response = page.goto(base + "/", wait_until="networkidle", timeout=30000)
                    require(response is not None and response.status == 200,
                            "HTML_HTTP_FAILED")
                    page.wait_for_function(
                        "() => document.querySelector('#tables-count').textContent === '3'",
                        timeout=15000)
                    page.wait_for_function(
                        "() => document.querySelector('#persistent-growth-status').textContent.includes('영구 관측 3건')",
                        timeout=15000)
                    require("증가 +3 KB" in page.locator("#persistent-growth-trend").inner_text()
                            and page.locator("#persistent-growth-samples .growth-sample").count() == 3,
                            "PERSISTENT_OBSERVATION_UI_FAILED")
                    result["checks"].append("persistent_observation_ledger_get_and_ui")
                    page.wait_for_function(
                        "() => document.querySelectorAll('#edges path').length === 1",
                        timeout=15000)
                    require(page.locator("#tables button.table-node").count() == 3
                            and page.locator("#links-count").inner_text() == "1",
                            "SCHEMA_MAP_WRONG")
                    result["checks"].append("real_http_schema_fk")
                    require("첫 측정" in page.locator("#growth-status").inner_text(),
                            "GROWTH_BASELINE_NOT_EXPLICIT")
                    page.locator("button.table-node").filter(has_text="orders").click()
                    require(page.locator(".detail-heading h3").inner_text() == "orders"
                            and page.locator("#edges path.active").count() == 1,
                            "TABLE_SELECTION_FAILED")
                    result["checks"].append("click_table_inspector")
                    # On demand only: no dbstat API request during first schema load.
                    measure = page.locator(".storage-measure")
                    require(measure.count() == 1
                            and "측정 전" in page.locator(".storage-status").inner_text(),
                            "OPT_IN_MEASURE_BUTTON_MISSING")
                    measure.click()
                    page.wait_for_function(
                        "() => { const s=document.querySelector('.storage-status'); "
                        "return s && (s.textContent.includes('할당된 B-tree') || "
                        "s.textContent.includes('측정 불가')); }", timeout=15000)
                    measured = page.evaluate("""async () => {
                        const r = await fetch('/api/table-storage?table=orders');
                        return {code:r.status, data:await r.json()};
                    }""")
                    require(measured["code"] == 200
                            and measured["data"]["contract"] == "dbvora.local-table-storage.v1"
                            and "dbstat" in measured["data"]["scope"]
                            and measured["data"]["metric"]["status"] in ("measured","unavailable"),
                            "OPT_IN_MEASURE_CONTRACT")
                    result["checks"].append("opt_in_local_table_btree_bytes")
                    page.locator("#table-filter").fill("ORDERS")
                    require(page.locator("button.table-node:visible").count() == 1
                            and page.locator(".detail-heading h3").inner_text() == "orders"
                            and page.locator("#edges path").count() == 0,
                            "LOCAL_TABLE_FILTER_FAILED")
                    page.locator("#table-filter").fill("__NO_MATCH__")
                    require(page.locator("button.table-node:visible").count() == 0
                            and page.locator("#filter-empty").is_visible()
                            and "0 / 3" in page.locator("#filter-status").inner_text(),
                            "NO_MATCH_FILTER_FAILED")
                    page.locator("#table-filter").fill("")
                    require(page.locator("button.table-node:visible").count() == 3
                            and page.locator("#edges path").count() == 1,
                            "FILTER_RESET_FAILED")
                    result["checks"].append("local_table_filter_no_network")

                    def screenshot(label):
                        if folder is None:
                            return
                        # Only overwrites the empty file generated in this call.
                        with tempfile.NamedTemporaryFile(
                                dir=folder, prefix="dbvora-synthetic-" + label + "-",
                                suffix=".png", delete=False) as handle:
                            destination = Path(handle.name)
                        try:
                            page.screenshot(path=str(destination), full_page=True)
                            require(destination.stat().st_size > 2000, "BAD_SCREENSHOT")
                            result["screenshots"].append(destination.name)
                        except BaseException:
                            destination.unlink(missing_ok=True)
                            raise

                    screenshot("desktop")
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.wait_for_timeout(250)
                    require(not page.evaluate(
                        "() => document.documentElement.scrollWidth > window.innerWidth + 1"),
                        "MOBILE_HORIZONTAL_OVERFLOW")
                    result["checks"].append("mobile_viewport")
                    screenshot("mobile")
                    require(unchanged == digest(db), "SOURCE_CHANGED_BY_BROWSER")
                    require("NOT_FOR_SCHEMA_OUTPUT" not in page.content()
                            and "example@invalid.test" not in page.content(),
                            "TABLE_ROWS_LEAKED")
                    result["checks"].append("no_rows_no_source_mutation")

                    # Client-only 1,000-table fixture: no new DB access or
                    # API calls. Actual Chromium measures this browser's work.
                    page.set_viewport_size({"width": 1440, "height": 900})
                    large = page.evaluate("""() => {
                        const tables = Array.from({length: 1000}, (_, i) => {
                            const name = 'synthetic_table_' + String(i).padStart(4, '0');
                            return {name, columns: [{name: 'id', type: 'INTEGER',
                                pk_position: 1, nullable_declared: false}],
                                indexes: [], foreign_keys: i ? [{
                                to_table: 'synthetic_table_' + String(i-1).padStart(4, '0'),
                                from_columns: ['id'], to_columns: ['id']}] : []};
                        });
                        const relationships = tables.slice(1).map((table, i) => ({
                            from_table: table.name, to_table: tables[i].name,
                            evidence: 'declared_foreign_key'
                        }));
                        const source = {contract_version: 'p0-01.v1', engine: 'sqlite', db_id: 'a'.repeat(24),
                            size_bytes: 4096, observed_at: '2026-11-14T00:00:00Z',
                            tables, relationships};
                        const started = performance.now();
                        window.render(source);
                        const renderMs = performance.now() - started;
                        const buttons = document.querySelectorAll('#tables button.table-node');
                        const paths = document.querySelectorAll('#edges path');
                        const firstEdge = paths[0];
                        const selectStart = performance.now();
                        buttons[999].click();
                        const selectMs = performance.now() - selectStart;
                        const reusedEdge = firstEdge ===
                            document.querySelector('#edges path');
                        const filter = document.getElementById('table-filter');
                        const filterStart = performance.now();
                        filter.value = 'SYNTHETIC_TABLE_0999';
                        filter.dispatchEvent(new Event('input', {bubbles:true}));
                        const filterMs = performance.now() - filterStart;
                        const filtered = document.querySelectorAll(
                            '#tables button.table-node:not([hidden])').length;
                        const selectedName = document.querySelector(
                            '#detail .detail-heading h3')?.textContent;
                        const filterStatus = document.querySelector(
                            '#filter-status').textContent;
                        const filteredEdges = document.querySelectorAll(
                            '#edges path').length;
                        filter.value = 'NO_SYNTHETIC_MATCH';
                        filter.dispatchEvent(new Event('input', {bubbles:true}));
                        const empty = !document.getElementById('filter-empty').hidden;
                        const noPressed = document.querySelectorAll(
                            '#tables button[aria-pressed="true"]').length === 0;
                        filter.value = '';
                        filter.dispatchEvent(new Event('input', {bubbles:true}));
                        return {render_ms: renderMs, select_ms: selectMs,
                            filter_ms: filterMs, initial_tables: buttons.length,
                            initial_edges: paths.length, reused_edge: reusedEdge,
                            filtered, selected_name: selectedName,
                            filter_status: filterStatus, filtered_edges: filteredEdges,
                            empty, no_pressed: noPressed,
                            restored_tables: document.querySelectorAll(
                                '#tables button.table-node:not([hidden])').length,
                            restored_edges: document.querySelectorAll(
                                '#edges path').length};
                    }""")
                    require(large["initial_tables"] == 1000
                            and large["initial_edges"] == 999
                            and large["reused_edge"]
                            and large["filtered"] == 1
                            and large["selected_name"] == "synthetic_table_0999"
                            and large["filter_status"] == "1 / 1000 테이블"
                            and large["filtered_edges"] == 0
                            and large["empty"] and large["no_pressed"]
                            and large["restored_tables"] == 1000
                            and large["restored_edges"] == 999,
                            "LARGE_LOCAL_UI_REGRESSION")
                    require(unchanged == digest(db), "LARGE_UI_CHANGED_SOURCE")
                    result["large_synthetic_ui_metrics_ms"] = {
                        "render": round(large["render_ms"], 3),
                        "select": round(large["select_ms"], 3),
                        "filter": round(large["filter_ms"], 3)}
                    result["checks"].append("large_1000_table_client_only")

                    # Resume the real localhost SQLite inventory for the
                    # existing XSS/refresh/HTTP security acceptance.
                    page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => document.querySelector('#tables-count').textContent === '3'",
                        timeout=15000)

                    dangerous = "<img src=x onerror=alert(2)>"
                    with closing(sqlite3.connect(db)) as con:
                        con.execute('CREATE TABLE "' + dangerous + '" ("<svg onload=alert(3)>" TEXT)')
                        con.commit()
                    after_fixture_update = digest(db)
                    page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => document.querySelector('#tables-count').textContent === '4'",
                        timeout=15000)
                    page.locator("button.table-node").filter(has_text=dangerous).click()
                    require(dangerous in page.locator(".detail-heading h3").inner_text()
                            and page.locator("#detail img").count() == 0
                            and page.locator("#detail svg").count() == 0
                            and not dialogs, "UNTRUSTED_IDENTIFIER_EXECUTED")
                    require(after_fixture_update == digest(db), "SOURCE_CHANGED_BY_BROWSER")
                    require(not errors and not bad_http, "CONSOLE_OR_ASSET_FAILURE")
                    result["checks"].append("untrusted_schema_is_text_only")
                    result["checks"].append("no_js_or_asset_errors")

                    # End-to-end *physical* SQLite catalog, not client-only JS
                    # injection. The fixture is temporary and holds no real data.
                    last_name = extend_synthetic_catalog(db, target_tables=1000)
                    at_limit = digest(db)
                    t_api = time.monotonic()
                    with urlopen(base + "/api/inventory", timeout=60) as response:
                        require(response.status == 200, "CATALOG_1000_HTTP_FAILED")
                        payload = response.read()
                    api_ms = round((time.monotonic() - t_api) * 1000, 3)
                    api_data = json.loads(payload)
                    require(len(api_data["tables"]) == 1000
                            and len(api_data["relationships"]) == 997
                            and any(t["name"] == last_name for t in api_data["tables"])
                            and "NOT_FOR_SCHEMA_OUTPUT" not in payload.decode("utf-8")
                            and "example@invalid.test" not in payload.decode("utf-8")
                            and at_limit == digest(db),
                            "CATALOG_1000_API_MISMATCH")
                    result["checks"].append("sqlite_1000_readonly_api")

                    t_ready = time.monotonic()
                    page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => document.querySelector('#tables-count').textContent === '1000'",
                        timeout=90000)
                    page.wait_for_function(
                        "() => document.querySelectorAll('#edges path').length === 997",
                        timeout=90000)
                    ready_ms = round((time.monotonic() - t_ready) * 1000, 3)
                    require(page.locator("#tables button.table-node").count() == 1000
                            and page.locator("#links-count").inner_text() == "997",
                            "CATALOG_1000_BROWSER_MISMATCH")
                    page.locator("#table-filter").fill(last_name.upper())
                    require(page.locator("button.table-node:visible").count() == 1
                            and page.locator("#edges path").count() == 0
                            and "1 / 1000" in page.locator("#filter-status").inner_text(),
                            "CATALOG_1000_BROWSER_FILTER")
                    visible = page.locator("button.table-node:visible")
                    visible.focus()
                    visible.press("Enter")
                    require(page.locator(".detail-heading h3").inner_text() == last_name
                            and visible.get_attribute("aria-pressed") == "true",
                            "CATALOG_1000_KEYBOARD_SELECT")
                    page.locator("#table-filter").fill("NO_SUCH_SYNTHETIC_TABLE")
                    require(page.locator("button.table-node:visible").count() == 0
                            and page.locator("#filter-empty").is_visible(),
                            "CATALOG_1000_ZERO_RESULTS")
                    page.locator("#table-filter").fill("")
                    require(page.locator("button.table-node:visible").count() == 1000
                            and page.locator("#edges path").count() == 997
                            and at_limit == digest(db),
                            "CATALOG_1000_RESTORE_FILTER")
                    result["real_sqlite_1000_metrics"] = {
                        "tables": 1000, "declared_fk": 997,
                        "api_payload_bytes": len(payload),
                        "api_response_ms": api_ms,
                        "browser_ready_ms": ready_ms}
                    result["checks"].append("sqlite_1000_chromium_keyboard")

                    # Repeated refresh against the *real* 1,000-table SQLite
                    # inventory. Preserve selection and graph without adding
                    # listeners, observers, detached SVGs or DOM nodes.
                    page.locator("button.table-node").filter(has_text=last_name).click()
                    for cycle in range(6):
                        with page.expect_response(
                                lambda r: r.url == base + "/api/inventory"
                                and r.status == 200, timeout=90000):
                            page.locator("#refresh").click()
                        page.wait_for_function(
                            "() => !document.querySelector('#refresh').disabled",
                            timeout=90000)
                        snapshot = page.evaluate("""() => {
                            const probe = window.__dbvoraRefreshProbe;
                            return {
                                nodes: document.querySelectorAll('#tables button.table-node').length,
                                edges: document.querySelectorAll('#edges path').length,
                                pressed: document.querySelectorAll(
                                    '#tables button[aria-pressed="true"]').length,
                                selected: document.querySelector(
                                    '#detail .detail-heading h3')?.textContent,
                                filter: document.querySelector('#table-filter').value,
                                errorHidden: document.querySelector('#error').hidden,
                                probe: {...probe}
                            };
                        }""")
                        require(snapshot["nodes"] == 1000 and snapshot["edges"] == 997
                                and snapshot["pressed"] == 1
                                and snapshot["selected"] == last_name
                                and snapshot["filter"] == ""
                                and snapshot["errorHidden"]
                                and snapshot["probe"]["live"] == 1
                                and snapshot["probe"]["maxLive"] == 1
                                and snapshot["probe"]["resizeListeners"] == 1
                                and snapshot["probe"]["created"]
                                == snapshot["probe"]["disconnected"] + 1,
                                "REPEATED_REFRESH_RESOURCE_OR_STATE_REGRESSION")
                        require(at_limit == digest(db), "REPEATED_REFRESH_CHANGED_SOURCE")
                    result["checks"].append("sqlite_1000_six_refresh_no_observer_leak")

                    # Synthetic HTTP 503 must retain the last good schema,
                    # current selection and filter, then recover with no
                    # customer data change. No server or source is modified.
                    page.locator("#table-filter").fill(last_name.upper())
                    def fail_inventory(route):
                        route.fulfill(status=503, content_type="application/json",
                                      body=json.dumps({"error": {
                                          "message": "Synthetic temporary outage"}}))
                    page.route("**/api/inventory", fail_inventory)
                    with page.expect_response(
                            lambda r: r.url == base + "/api/inventory"
                            and r.status == 503, timeout=90000):
                        page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => !document.querySelector('#refresh').disabled"
                        " && !document.querySelector('#error').hidden",
                        timeout=90000)
                    require(page.locator("#error").inner_text()
                            == "Synthetic temporary outage"
                            and page.locator("#tables button.table-node").count() == 1000
                            and page.locator("button.table-node:visible").count() == 1
                            and page.locator(".detail-heading h3").inner_text() == last_name
                            and page.locator("button.table-node:visible").get_attribute(
                                "aria-pressed") == "true"
                            and page.locator("#table-filter").input_value()
                            == last_name.upper()
                            and page.locator("#edges path").count() == 0
                            and at_limit == digest(db),
                            "HTTP_OUTAGE_DESTROYED_LAST_GOOD_STATE")
                    page.unroute("**/api/inventory", fail_inventory)
                    with page.expect_response(
                            lambda r: r.url == base + "/api/inventory"
                            and r.status == 200, timeout=90000):
                        page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => !document.querySelector('#refresh').disabled"
                        " && document.querySelector('#error').hidden",
                        timeout=90000)
                    require(page.locator("button.table-node:visible").count() == 1
                            and page.locator(".detail-heading h3").inner_text() == last_name
                            and page.locator("#edges path").count() == 0
                            and at_limit == digest(db),
                            "HTTP_OUTAGE_RECOVERY_FAILED")
                    page.locator("#table-filter").fill("")
                    require(page.locator("#edges path").count() == 997,
                            "HTTP_RECOVERY_GRAPH_FAILED")
                    result["checks"].append("sqlite_1000_http_outage_state_and_recovery")

                    # Simulate a severed browser-to-localhost request without
                    # touching the real local server, source DB or customer files.
                    # The last verified 1,000-table inspector/filter must survive.
                    page.locator("#table-filter").fill(last_name.upper())
                    def stable_filtered_state():
                        state = page.evaluate("""() => ({
                            tables: document.querySelectorAll(
                                '#tables button.table-node').length,
                            visible: document.querySelectorAll(
                                '#tables button.table-node:not([hidden])').length,
                            edges: document.querySelectorAll('#edges path').length,
                            pressed: document.querySelectorAll(
                                '#tables button[aria-pressed="true"]').length,
                            selected: document.querySelector(
                                '.detail-heading h3')?.textContent,
                            filter: document.querySelector('#table-filter').value,
                            observers: window.__dbvoraRefreshProbe.live,
                            listeners: window.__dbvoraRefreshProbe.resizeListeners
                        })""")
                        return (state["tables"] == 1000
                                and state["visible"] == 1
                                and state["edges"] == 0
                                and state["pressed"] == 1
                                and state["selected"] == last_name
                                and state["filter"] == last_name.upper()
                                and state["observers"] == 1
                                and state["listeners"] == 1)

                    def sever_inventory(route):
                        route.abort("failed")
                    page.route("**/api/inventory", sever_inventory)
                    page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => !document.querySelector('#refresh').disabled"
                        " && !document.querySelector('#error').hidden",
                        timeout=15000)
                    require("연결이 중단" in page.locator("#error").inner_text()
                            and stable_filtered_state() and at_limit == digest(db)
                            and not errors, "NETWORK_ABORT_PRESERVATION_FAILED")
                    page.unroute("**/api/inventory", sever_inventory)
                    with page.expect_response(
                            lambda r: r.url == base + "/api/inventory"
                            and r.status == 200, timeout=30000):
                        page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => !document.querySelector('#refresh').disabled"
                        " && document.querySelector('#error').hidden",
                        timeout=30000)
                    require(stable_filtered_state() and at_limit == digest(db),
                            "NETWORK_ABORT_RECOVERY_FAILED")
                    result["checks"].append("sqlite_1000_network_abort_recovery")

                    # A slow but successful real localhost HTTP response must
                    # preserve selection and never produce a spurious timeout.
                    delayed_requests = []
                    def delayed_inventory(route):
                        delayed_requests.append(1)
                        time.sleep(0.6)
                        route.continue_()
                    page.route("**/api/inventory", delayed_inventory)
                    with page.expect_response(
                            lambda r: r.url == base + "/api/inventory"
                            and r.status == 200, timeout=30000):
                        page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => !document.querySelector('#refresh').disabled"
                        " && document.querySelector('#error').hidden",
                        timeout=30000)
                    page.unroute("**/api/inventory", delayed_inventory)
                    require(len(delayed_requests) == 1 and stable_filtered_state()
                            and at_limit == digest(db),
                            "DELAYED_HTTP_RESPONSE_STATE_FAILED")
                    result["checks"].append("sqlite_1000_delayed_local_response")

                    # Stall a single browser request indefinitely. The app must
                    # abort its own fetch after 15 s and enable an explicit retry,
                    # without rendering a stale response or evicting old data.
                    held_requests = []
                    def never_answer_inventory(route):
                        held_requests.append(1)  # Intentionally not continued.
                    page.route("**/api/inventory", never_answer_inventory)
                    page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => document.querySelector('#refresh').disabled",
                        timeout=5000)
                    require(stable_filtered_state() and at_limit == digest(db),
                            "PENDING_HTTP_LOST_LAST_GOOD_STATE")
                    page.wait_for_function(
                        "() => !document.querySelector('#refresh').disabled"
                        " && !document.querySelector('#error').hidden",
                        timeout=26000)
                    require(len(held_requests) == 1
                            and "시간이 초과" in page.locator("#error").inner_text()
                            and stable_filtered_state()
                            and at_limit == digest(db) and not errors,
                            "HTTP_TIMEOUT_ABORT_FAILED")
                    page.unroute("**/api/inventory", never_answer_inventory)
                    with page.expect_response(
                            lambda r: r.url == base + "/api/inventory"
                            and r.status == 200, timeout=30000):
                        page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => !document.querySelector('#refresh').disabled"
                        " && document.querySelector('#error').hidden",
                        timeout=30000)
                    require(stable_filtered_state() and at_limit == digest(db),
                            "HTTP_TIMEOUT_RECOVERY_FAILED")
                    page.locator("#table-filter").fill("")
                    require(page.locator("#edges path").count() == 997,
                            "HTTP_TIMEOUT_GRAPH_RESET_FAILED")
                    result["checks"].append("sqlite_1000_timeout_abort_and_retry")

                    # A narrow viewport must not acquire horizontal overflow
                    # after repeated real-server refresh (not client injection).
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.wait_for_timeout(250)
                    require(not page.evaluate(
                        "() => document.documentElement.scrollWidth > window.innerWidth + 1"),
                        "LARGE_MOBILE_HORIZONTAL_OVERFLOW")
                    require(page.locator("#tables button.table-node").count() == 1000
                            and page.locator("#edges path").count() == 997
                            and page.locator("#refresh").is_enabled(),
                            "LARGE_MOBILE_STATE_REGRESSION")
                    page.set_viewport_size({"width": 1440, "height": 900})
                    result["checks"].append("sqlite_1000_repeated_mobile_viewport")

                    # Bounded real-browser soak, not a 24h memory certification.
                    # Exercise multiple *real* 1,000-table SQLite inventory
                    # fetches and alternating filter/keyboard/selection, with
                    # intermittent synthetic transport failures. Chrome CDP
                    # reports post-GC JS heap; report the values rather than
                    # advertising an unproven long-term leak-free guarantee.
                    cdp = page.context.new_cdp_session(page)
                    cdp.send("Performance.enable")

                    def after_gc_heap():
                        cdp.send("HeapProfiler.collectGarbage")
                        values = cdp.send("Performance.getMetrics")["metrics"]
                        match = [v["value"] for v in values
                                 if v["name"] == "JSHeapUsedSize"]
                        require(len(match) == 1 and match[0] >= 0,
                                "CDP_JS_HEAP_UNAVAILABLE")
                        return int(match[0])

                    heap_samples = [after_gc_heap()]
                    original_dom = page.evaluate(
                        "() => document.querySelectorAll('*').length")
                    require(page.locator("#edges path").count() == 997,
                            "SOAK_PRECONDITION_GRAPH")
                    for cycle in range(24):
                        target = f"synthetic_catalog_{(cycle * 37) % 996:04d}"
                        page.locator("#table-filter").fill(target.upper())
                        node = page.locator("button.table-node:visible")
                        require(node.count() == 1, "SOAK_FILTER_AMBIGUOUS")
                        node.focus()
                        node.press("Enter")
                        require(page.locator(".detail-heading h3").inner_text() == target
                                and node.get_attribute("aria-pressed") == "true"
                                and page.locator("#edges path").count() == 0,
                                "SOAK_SELECTION_MISMATCH")

                        if cycle % 6 == 5:
                            # Force a client-only browser network disconnect,
                            # then verify the last good UI survives unchanged.
                            def soak_abort(route):
                                route.abort("failed")
                            page.route("**/api/inventory", soak_abort)
                            page.locator("#refresh").click()
                            page.wait_for_function(
                                "() => !document.querySelector('#refresh').disabled"
                                " && !document.querySelector('#error').hidden",
                                timeout=15000)
                            require(page.locator("button.table-node:visible").count() == 1
                                    and page.locator(".detail-heading h3").inner_text()
                                    == target and node.get_attribute("aria-pressed")
                                    == "true", "SOAK_ABORT_STATE_CHANGED")
                            page.unroute("**/api/inventory", soak_abort)

                        with page.expect_response(
                                lambda r: r.url == base + "/api/inventory"
                                and r.status == 200, timeout=30000):
                            page.locator("#refresh").click()
                        page.wait_for_function(
                            "() => !document.querySelector('#refresh').disabled"
                            " && document.querySelector('#error').hidden",
                            timeout=30000)
                        require(page.locator("button.table-node:visible").count() == 1
                                and page.locator(".detail-heading h3").inner_text() == target
                                and page.locator("button.table-node:visible").get_attribute(
                                    "aria-pressed") == "true", "SOAK_REFRESH_STATE_CHANGED")
                        page.locator("#table-filter").fill("")
                        state = page.evaluate("""() => {
                            const probe = window.__dbvoraRefreshProbe;
                            return {
                                tables: document.querySelectorAll(
                                    '#tables button.table-node').length,
                                paths: document.querySelectorAll('#edges path').length,
                                dom: document.querySelectorAll('*').length,
                                pressed: document.querySelectorAll(
                                    '#tables button[aria-pressed="true"]').length,
                                live: probe.live,
                                maxLive: probe.maxLive,
                                listeners: probe.resizeListeners,
                                created: probe.created,
                                disconnected: probe.disconnected
                            };
                        }""")
                        require(state["tables"] == 1000 and state["paths"] == 997
                                and state["pressed"] == 1 and state["live"] == 1
                                and state["maxLive"] == 1 and state["listeners"] == 1
                                and state["created"] == state["disconnected"] + 1
                                and abs(state["dom"] - original_dom) <= 30,
                                "SOAK_DOM_OBSERVER_LISTENER_GROWTH")
                        if cycle % 8 == 7:
                            heap_samples.append(after_gc_heap())
                        require(at_limit == digest(db), "SOAK_CHANGED_SOURCE")
                    cdp.detach()
                    # A very wide gross-growth guard is deliberately *not*
                    # a proof of zero leaks: collect quantitative evidence and
                    # reject only clearly unbounded heap growth in this run.
                    heap_growth = heap_samples[-1] - heap_samples[0]
                    require(len(heap_samples) == 4
                            and heap_growth <= 24 * 1024 * 1024,
                            "SOAK_GROSS_JS_HEAP_GROWTH")
                    result["real_sqlite_1000_soak"] = {
                        "refresh_cycles": 24, "synthetic_disconnects": 4,
                        "dom_elements": original_dom,
                        "observed_js_heap_after_gc_bytes": heap_samples,
                        "net_js_heap_change_bytes": heap_growth,
                        "heap_scope": "single_chromium_run_not_long_term_proof"}
                    result["checks"].append("sqlite_1000_24cycle_refresh_filter_observer")
                    result["checks"].append("sqlite_1000_cdp_gc_heap_observation")

                    # Just one extra generated table must fail closed at the
                    # API boundary without exposing paths, rows, or SQL.
                    excessive = extend_synthetic_catalog(db, target_tables=1001)
                    at_excess = digest(db)
                    try:
                        with urlopen(base + "/api/inventory", timeout=60):
                            raise GateError("CATALOG_1001_ACCEPTED_UNSAFELY")
                    except HTTPError as exc:
                        require(exc.code == 422, "CATALOG_1001_BAD_HTTP_STATUS")
                        error_payload = exc.read().decode("utf-8")
                    error = json.loads(error_payload)["error"]
                    require(error["code"] == "CATALOG_LIMIT"
                            and str(db) not in error_payload
                            and "example@invalid.test" not in error_payload
                            and at_excess == digest(db),
                            "CATALOG_1001_UNSAFE_RESPONSE")
                    page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => document.querySelector('#error').hidden === false",
                        timeout=30000)
                    require("exceeds the inventory limit" in
                            page.locator("#error").inner_text()
                            and at_excess == digest(db),
                            "CATALOG_1001_UI_ERROR_MISSING")
                    result["checks"].append("sqlite_1001_api_ui_fail_closed")

                    # Synthetic-only recovery: remove only the test-owned last
                    # table; no customer backup, auto-pruning or user file touch.
                    with closing(sqlite3.connect(db)) as con:
                        con.execute('DROP TABLE "' + excessive + '"')
                        con.commit()
                    restored_fingerprint = digest(db)
                    page.locator("#refresh").click()
                    page.wait_for_function(
                        "() => document.querySelector('#tables-count').textContent === '1000'"
                        " && document.querySelector('#error').hidden",
                        timeout=90000)
                    require(page.locator("#edges path").count() == 997
                            and restored_fingerprint == digest(db)
                            and not errors and not dialogs
                            and bad_http == [503, 422],
                            "CATALOG_LIMIT_RECOVERY_FAILED")
                    result["checks"].append("sqlite_catalog_recovery_no_source_mutation")

                    # A second, independent localhost server gets exactly two
                    # test-owned databases via process argv, never from HTTP.
                    first = create_fixture(Path(temp) / 'workspace_first.sqlite')
                    second = Path(temp) / 'workspace_second.sqlite'
                    with closing(sqlite3.connect(second)) as con:
                        con.executescript("""
                            CREATE TABLE warehouses(id INTEGER PRIMARY KEY);
                            CREATE TABLE shipments(id INTEGER PRIMARY KEY,
                                warehouse_id INTEGER REFERENCES warehouses(id));
                            INSERT INTO warehouses VALUES (1);
                            INSERT INTO shipments VALUES (2, 1);
                        """)
                    source_before = (digest(first), digest(second))
                    with socket.socket() as sock:
                        sock.bind(('127.0.0.1', 0))
                        multi_port = sock.getsockname()[1]
                    multi_base = f'http://127.0.0.1:{multi_port}'
                    multi_startup = (
                        "import sys,uvicorn;from dbvora.api import create_app;"
                        "p=int(sys.argv[3]);"
                        "uvicorn.run(create_app([sys.argv[1],sys.argv[2]],port=p,"
                        "observation_ledger_path=sys.argv[4]),"
                        "host='127.0.0.1',port=p,log_level='error',access_log=False)")
                    multi_proc = subprocess.Popen(
                        [sys.executable, '-B', '-c', multi_startup,
                         str(first), str(second), str(multi_port), str(ledger)],
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
                    for _ in range(60):
                        if multi_proc.poll() is not None:
                            raise GateError('MULTI_LOCAL_SERVER_EXITED')
                        try:
                            if http_code(multi_base + '/health') == 200:
                                break
                        except (OSError, URLError):
                            pass
                        time.sleep(0.2)
                    else:
                        raise GateError('MULTI_LOCAL_SERVER_STARTUP_FAILED')
                    multi_page = browser.new_page(viewport={"width": 1280, "height": 850})
                    multi_errors = []
                    multi_page.on('pageerror', lambda exc: multi_errors.append('JS_ERROR'))
                    multi_page.goto(multi_base + '/', wait_until='networkidle', timeout=30000)
                    multi_page.wait_for_function(
                        "() => document.querySelector('#tables-count').textContent === '3'"
                        " && document.querySelectorAll('#database-list button').length === 2",
                        timeout=15000)
                    require(multi_page.locator('#workspace-summary').inner_text().startswith('2 DB · 5 테이블')
                            and multi_page.locator('#database-selector').is_visible()
                            and multi_page.locator('#edges path').count() == 1,
                            'MULTI_WORKSPACE_INITIAL_UI')
                    # R01-02: the simultaneous topology must expose both
                    # databases, allow keyboard selection and preserve scope.
                    nodes = multi_page.locator('#database-topology button.topology-database')
                    require(nodes.count() == 2
                            and nodes.nth(0).is_visible()
                            and nodes.nth(1).is_visible()
                            and nodes.nth(0).get_attribute('aria-pressed') == 'true'
                            and nodes.nth(1).get_attribute('aria-pressed') == 'false',
                            'MULTI_TOPOLOGY_INITIAL_NODES')
                    nodes.nth(1).focus()
                    multi_page.keyboard.press('Enter')
                    require(multi_page.locator('#tables-count').inner_text() == '2'
                            and nodes.nth(1).get_attribute('aria-pressed') == 'true'
                            and multi_page.locator('#database-list button').nth(1).get_attribute(
                                'aria-pressed') == 'true',
                            'MULTI_TOPOLOGY_KEYBOARD_SELECTION')
                    nodes.nth(0).click()
                    require(multi_page.locator('#tables-count').inner_text() == '3'
                            and nodes.nth(0).get_attribute('aria-pressed') == 'true',
                            'MULTI_TOPOLOGY_CLICK_SELECTION')
                    result['checks'].append('multi_topology_two_nodes_keyboard_click')
                    # R01-07: hold a real browser fetch Promise until after
                    # switching DBs; stale success/failure must not leak.
                    multi_page.evaluate("""() => {
                      window.__storageFetchOriginal = window.fetch;
                      window.__storagePending = [];
                      window.fetch = (url, options) => {
                        if (String(url).startsWith('/api/table-storage?')) {
                          return new Promise((resolve, reject) =>
                            window.__storagePending.push({resolve, reject, signal: options.signal}));
                        }
                        return window.__storageFetchOriginal(url, options);
                      };
                    }""")
                    multi_page.locator('.storage-measure').click()
                    multi_page.wait_for_function(
                        "() => window.__storagePending.length === 1")
                    multi_page.locator('#database-topology button.topology-database').nth(1).click()
                    require(multi_page.evaluate('() => window.__storagePending[0].signal.aborted'),
                            'MULTI_RACE_PREVIOUS_SCAN_NOT_ABORTED')
                    require(multi_page.locator('#tables-count').inner_text() == '2'
                            and multi_page.locator('.storage-status').inner_text().startswith('측정 전'),
                            'MULTI_RACE_SWITCH_PRECONDITION')
                    multi_page.evaluate("""() => window.__storagePending.shift().resolve({
                      ok: true, json: async () => ({
                        contract: 'dbvora.local-table-storage.v1',
                        table: 'customers',
                        scope: 'logical_btree_pages_dbstat_including_indexes_wal_pages_possible',
                        metric: {status:'measured', allocated_btree_bytes:999999}
                      })
                    })""")
                    multi_page.wait_for_timeout(100)
                    require(multi_page.locator('#tables-count').inner_text() == '2'
                            and multi_page.locator('.storage-status').inner_text().startswith('측정 전')
                            and not multi_errors, 'MULTI_RACE_STALE_SUCCESS_LEAK')
                    multi_page.locator('.storage-measure').click()
                    multi_page.wait_for_function(
                        "() => window.__storagePending.length === 1")
                    multi_page.locator('#database-topology button.topology-database').first.click()
                    require(multi_page.evaluate('() => window.__storagePending[0].signal.aborted'),
                            'MULTI_RACE_PREVIOUS_FAILURE_SCAN_NOT_ABORTED')
                    multi_page.evaluate("""() => window.__storagePending.shift().reject(
                      new TypeError('synthetic stale transport error'))""")
                    multi_page.wait_for_timeout(100)
                    require(multi_page.locator('#tables-count').inner_text() == '3'
                            and multi_page.locator('.storage-status').inner_text().startswith('측정 전')
                            and not multi_errors, 'MULTI_RACE_STALE_FAILURE_LEAK')
                    multi_page.evaluate("""() => {
                      window.fetch = window.__storageFetchOriginal;
                      delete window.__storagePending;
                      delete window.__storageFetchOriginal;
                    }""")
                    # A table switch within the same DB also aborts the old
                    # opt-in scan; selection identity must remain correct.
                    multi_page.locator('.storage-measure').click()
                    multi_page.wait_for_function(
                        "() => window.__storagePending.length === 1")
                    multi_page.locator('#tables button.table-node').nth(1).click()
                    require(multi_page.evaluate('() => window.__storagePending[0].signal.aborted'),
                            'TABLE_SWITCH_SCAN_NOT_ABORTED')
                    require(multi_page.locator('.storage-status').inner_text().startswith('측정 전'),
                            'TABLE_SWITCH_STALE_STATUS')
                    multi_page.evaluate("""() => window.__storagePending.shift().reject(
                      new TypeError('synthetic stale table error'))""")
                    multi_page.wait_for_timeout(100)
                    require(multi_page.locator('.storage-status').inner_text().startswith('측정 전')
                            and not multi_errors, 'TABLE_SWITCH_STALE_FAILURE_LEAK')
                    result['checks'].append('multi_table_switch_aborts_storage')
                    result['checks'].append('multi_delayed_storage_success_failure_isolated')
                    multi_page.locator('#database-list button').nth(1).click()
                    require(multi_page.locator('#tables-count').inner_text() == '2'
                            and multi_page.locator('#edges path').count() == 1
                            and multi_page.locator('#database-list button').nth(1).get_attribute(
                                'aria-pressed') == 'true', 'MULTI_DATABASE_SWITCH_FAILED')
                    multi_page.locator('#tables button.table-node').filter(
                        has_text='shipments').click()
                    require(multi_page.locator('.detail-heading h3').inner_text() == 'shipments'
                            and multi_page.locator('#edges path.active').count() == 1,
                            'MULTI_DATABASE_INSPECTOR_WRONG')
                    multi_page.locator('.storage-measure').click()
                    multi_page.wait_for_function(
                        "() => document.querySelector('.storage-status').textContent"
                        ".includes('할당된 B-tree') || document.querySelector('.storage-status')"
                        ".textContent.includes('측정 불가')", timeout=15000)
                    multi_page.locator('#table-filter').fill('SHIPMENTS')
                    multi_page.locator('#refresh').click()
                    multi_page.wait_for_function(
                        "() => !document.querySelector('#refresh').disabled"
                        " && document.querySelector('#error').hidden", timeout=30000)
                    require(multi_page.locator('#database-list button').nth(1).get_attribute(
                                'aria-pressed') == 'true'
                            and multi_page.locator('#tables button.table-node:visible').count() == 1
                            and multi_page.locator('.detail-heading h3').inner_text() == 'shipments',
                            'MULTI_REFRESH_SELECTION_NOT_PRESERVED')
                    multi_page.locator('#table-filter').fill('')
                    multi_page.locator('#database-list button').first.click()
                    require(multi_page.locator('#tables-count').inner_text() == '3'
                            and multi_page.locator('#edges path').count() == 1
                            and multi_page.locator('button.table-node').count() == 3
                            and not multi_errors, 'MULTI_SWITCH_BACK_FAILED')
                    result['checks'].append('multi_live_two_databases_isolated_navigation')
                    # This view has already completed one successful
                    # explicit refresh above: compare two measured observations.
                    require("직전 측정 대비 변화 없음" in
                            multi_page.locator('#growth-status').inner_text(),
                            'MULTI_GROWTH_BASELINE_NOT_SCOPED')
                    multi_page.locator('#refresh').click()
                    multi_page.wait_for_function(
                        "() => !document.querySelector('#refresh').disabled",
                        timeout=30000)
                    require("직전 측정 대비 변화 없음" in
                            multi_page.locator('#growth-status').inner_text(),
                            'MULTI_GROWTH_TWO_REAL_SAMPLES_MISSING')
                    multi_page.locator('#database-list button').nth(1).click()
                    require("직전 측정 대비 변화 없음" in
                            multi_page.locator('#growth-status').inner_text(),
                            'MULTI_GROWTH_DB_ISOLATION')
                    result['checks'].append('multi_live_two_snapshot_main_file_growth')
                    multi_page.set_viewport_size({'width': 390, 'height': 844})
                    multi_page.wait_for_timeout(200)
                    require(not multi_page.evaluate(
                        "() => document.documentElement.scrollWidth > window.innerWidth + 1"),
                        'MULTI_MOBILE_OVERFLOW')
                    require(multi_page.locator(
                        '#database-topology button.topology-database:visible').count() == 2,
                        'MULTI_TOPOLOGY_MOBILE_NODES_MISSING')
                    multi_page.locator('#database-topology button.topology-database').first.click()
                    require(multi_page.locator('#tables-count').inner_text() == '3'
                            and multi_page.locator('#database-topology button.topology-database').first.get_attribute(
                                'aria-pressed') == 'true'
                            and not multi_page.evaluate(
                                "() => document.documentElement.scrollWidth > window.innerWidth + 1"),
                            'MULTI_TOPOLOGY_MOBILE_SELECTION')
                    result['checks'].append('multi_topology_390px_selection')

                    require(http_code(multi_base + '/api/inventory', headers={
                        'Origin': 'https://attacker.invalid'}) == 403
                            and http_code(multi_base + '/api/inventory', method='POST') == 405
                            and source_before == (digest(first), digest(second)),
                            'MULTI_SOURCE_OR_SECURITY_FAILED')
                    result['checks'].append('multi_live_mobile_security_and_source_unchanged')
                    multi_page.close()
                finally:
                    browser.close()
            require(http_code(base + "/api/inventory", headers={
                "Origin": "https://attacker.invalid"}) == 403, "ORIGIN_POLICY_FAILED")
            require(http_code(base + "/api/inventory", headers={
                "Host": "attacker.invalid"}) == 403, "HOST_POLICY_FAILED")
            require(http_code(base + "/api/inventory", method="POST") == 405,
                    "WRITE_METHOD_POLICY_FAILED")
            result["checks"].append("host_origin_method_guards")
        result["status"] = "PASS_SYNTHETIC_HTTP_BROWSER_ONLY"
    except GateError as exc:
        result["error_code"] = str(exc)
    except Exception:
        result["error_code"] = "BROWSER_OR_ENVIRONMENT_ERROR"
    finally:
        if multi_proc is not None and multi_proc.poll() is None:
            multi_proc.terminate()
            try:
                multi_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                multi_proc.kill()
                multi_proc.wait(timeout=5)
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
    return result


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Synthetic-only localhost Chromium acceptance")
    p.add_argument("--screenshots", default=None)
    report = run(screenshots=p.parse_args(argv).screenshots)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS_SYNTHETIC_HTTP_BROWSER_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
