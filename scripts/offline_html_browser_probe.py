"""Optional Chromium check for generated offline schema HTML; synthetic input only.

Run: python -m scripts.offline_html_browser_probe --chromium /usr/bin/chromium
Requires Playwright + a local Chromium executable *only for this test*.
No browser HTTP navigation, database rows, network fetch or customer files.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile

from dbvora.export_html import export
from tests.fixtures.make_sqlite import create_fixture


def probe(chromium: str | None = None) -> dict:
    report = {'mode': 'SYNTHETIC_OFFLINE_HTML_BROWSER_ONLY', 'browser_http_e2e': False,
              'ready_for_customer_data': False, 'browser_file_navigation': False,
              'status': 'FAIL_CLOSED', 'checks': {}}
    try:
        from playwright.sync_api import sync_playwright
        executable = chromium or shutil.which('chromium') or shutil.which('chromium-browser')
        if not executable or not Path(executable).is_file():
            report['reason'] = 'CHROMIUM_UNAVAILABLE'
            return report
        with tempfile.TemporaryDirectory(prefix='dbvora-offline-browser-') as temp:
            folder = Path(temp)
            source = create_fixture(folder / 'synthetic.sqlite')
            with closing(sqlite3.connect(source)) as conn:
                conn.execute('CREATE TABLE "</script><img src=x onerror=alert(8)>" '
                             '("<svg onload=alert(9)>" TEXT)')
            # The hostile-name synthetic DDL is part of the input; capture after it.
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            source_mtime = source.stat().st_mtime_ns
            result = export(source, folder)
            content = (folder / result['filename']).read_text(encoding='utf-8')
            errors, requests, dialogs = [], [], []
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=executable, headless=True,
                                                      args=['--no-sandbox', '--disable-dev-shm-usage'])
                try:
                    page = browser.new_page(viewport={'width': 1280, 'height': 800})
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.on('request', lambda req: requests.append(req.url))
                    page.on('dialog', lambda d: (dialogs.append(d.message), d.dismiss()))
                    page.set_content(content, wait_until='load')
                    page.wait_for_function("document.querySelectorAll('#tables button').length === 4", timeout=10000)
                    checks = report['checks']
                    checks['source_bytes_unchanged'] = (
                        hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
                        and source.stat().st_mtime_ns == source_mtime)
                    checks['report_checksum'] = (
                        result['sha256'] == hashlib.sha256(content.encode('utf-8')).hexdigest()
                        and result['size_bytes'] == len(content.encode('utf-8')))
                    checks['offline_csp_and_embedded_assets'] = (
                        'Content-Security-Policy' in content and \
                        "connect-src 'none'" in content and \
                        'src="/assets/app.js"' not in content and \
                        'href="/assets/style.css"' not in content)
                    checks['table_rows_and_source_path_omitted'] = (
                        'NOT_FOR_SCHEMA_OUTPUT' not in content and str(source) not in content)
                    checks['real_stylesheet_applied'] = (
                        page.locator('body').evaluate(
                            '(el) => getComputedStyle(el).color') == 'rgb(230, 236, 236)')
                    checks['schema_buttons'] = page.locator('#tables button').count() == 4
                    checks['fk_edges'] = page.locator('#edges path').count() == 1
                    page.locator('#tables button').filter(has_text='orders').click()
                    checks['selection'] = page.locator('.detail-heading h3').inner_text() == 'orders'
                    page.locator('#tables button').filter(has_text='</script><img').click()
                    checks['xss_as_text'] = (
                        '<svg onload=alert(9)>' in page.locator('#detail').inner_text()
                        and page.locator('#detail img').count() == 0 and not dialogs)
                    checks['no_browser_script_errors'] = not errors and page.locator('#error').is_hidden()
                    # After initial page boot, manual refresh must not add resize listeners.
                    # A leaking version registers inside render() on every refresh.
                    page.evaluate("""() => {
                        window.__dbvoraResizeRegistrations = 0;
                        const originalAdd = window.addEventListener;
                        window.addEventListener = function(type, ...args) {
                            if (type === 'resize') window.__dbvoraResizeRegistrations++;
                            return originalAdd.call(this, type, ...args);
                        };
                    }""")
                    for _ in range(3):
                        page.locator('#refresh').click()
                    checks['refresh_does_not_add_resize_listeners'] = page.evaluate(
                        'window.__dbvoraResizeRegistrations === 0')
                    page.locator('#refresh').click()
                    checks['refresh_works_without_server'] = (
                        page.locator('#tables button').count() == 4
                        and page.locator('#error').is_hidden())
                    checks['no_network_requests'] = not requests
                    page.set_viewport_size({'width': 390, 'height': 844})
                    checks['mobile_no_horizontal_overflow'] = not page.evaluate(
                        'document.documentElement.scrollWidth > innerWidth')
                    report['status'] = 'PASS_SYNTHETIC_OFFLINE_HTML_ONLY' if all(checks.values()) else 'FAIL_CLOSED'
                finally:
                    browser.close()
    except Exception:
        report['reason'] = 'BROWSER_OR_FIXTURE_UNAVAILABLE'
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Synthetic offline HTML Chromium verification')
    parser.add_argument('--chromium', default=None, help='Explicit local Chromium binary')
    args = parser.parse_args(argv)
    report = probe(args.chromium)
    print(json.dumps(report, sort_keys=True))
    return 0 if report['status'] == 'PASS_SYNTHETIC_OFFLINE_HTML_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
