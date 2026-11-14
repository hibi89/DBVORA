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

from tests.fixtures.make_sqlite import create_fixture


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
    try:
        folder = Path(screenshots) if screenshots else None
        if folder is not None:
            require(folder.is_absolute() and folder.is_dir() and
                    not any(x.is_symlink() for x in (folder, *folder.parents)),
                    "UNSAFE_SCREENSHOT_DIRECTORY")
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory(prefix="dbvora-http-browser-synthetic-") as temp:
            db = create_fixture(Path(temp) / "fixture.sqlite")
            unchanged = digest(db)
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            base = f"http://127.0.0.1:{port}"
            startup = ("import sys,uvicorn;from dbvora.api import create_app;"
                       "p=int(sys.argv[2]);uvicorn.run(create_app(sys.argv[1],port=p),"
                       "host='127.0.0.1',port=p,log_level='error',access_log=False)")
            proc = subprocess.Popen([sys.executable, "-B", "-c", startup, str(db), str(port)],
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
                    response = page.goto(base + "/", wait_until="networkidle", timeout=30000)
                    require(response is not None and response.status == 200,
                            "HTML_HTTP_FAILED")
                    page.wait_for_function(
                        "() => document.querySelector('#tables-count').textContent === '3'",
                        timeout=15000)
                    page.wait_for_function(
                        "() => document.querySelectorAll('#edges path').length === 1",
                        timeout=15000)
                    require(page.locator("#tables button.table-node").count() == 3
                            and page.locator("#links-count").inner_text() == "1",
                            "SCHEMA_MAP_WRONG")
                    result["checks"].append("real_http_schema_fk")
                    page.locator("button.table-node").filter(has_text="orders").click()
                    require(page.locator(".detail-heading h3").inner_text() == "orders"
                            and page.locator("#edges path.active").count() == 1,
                            "TABLE_SELECTION_FAILED")
                    result["checks"].append("click_table_inspector")
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
                        const source = {engine: 'sqlite', db_id: 'a'.repeat(24),
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
