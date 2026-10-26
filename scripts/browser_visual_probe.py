"""Actual Chromium DOM + responsive UI checks using an injected *synthetic* inventory.

Does not navigate the local HTTP server (some development containers block
loopback in graphical browser). The real HTML/CSS/JS is executed unmodified
in Chromium, while fetch is replaced *only inside the test browser context*.
This is not an HTTP e2e or production browser compatibility certification.

Requires optional playwright and a Chromium executable outside the app itself.
Run: python -m scripts.browser_visual_probe --chromium /usr/bin/chromium
"""
import argparse
import json
from pathlib import Path
import sqlite3
import tempfile

from dbvora.inventory import inspect_sqlite
from tests.fixtures.make_sqlite import create_fixture

ROOT = Path(__file__).resolve().parents[1]


def probe(chromium_binary: str | None = None):
    result = {"mode": "CHROMIUM_SYNTHETIC_DOM_ONLY", "browser_http_e2e": False,
              "ready_for_customer_data": False, "status": "FAIL_CLOSED", "checks": {}}
    try:
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory(prefix='dbvora-chromium-synthetic-') as scratch:
            src = create_fixture(Path(scratch) / 'fixture.sqlite')
            with sqlite3.connect(src) as con:
                con.execute('CREATE TABLE "<img src=x onerror=alert(2)>" ("<svg onload=alert(3)>" TEXT)')
            schema = inspect_sqlite(src)
            html = (ROOT / 'dbvora/web/index.html').read_text(encoding='utf-8')
            html = html.replace('<script src="/assets/app.js" defer></script>', '')
            html = html.replace('<link rel="stylesheet" href="/assets/style.css">', '')
            errors, alerts = [], []
            with sync_playwright() as runner:
                kwargs = {'headless': True, 'args': ['--no-sandbox', '--disable-dev-shm-usage']}
                if chromium_binary is not None:
                    kwargs['executable_path'] = chromium_binary
                browser = runner.chromium.launch(**kwargs)
                try:
                    page = browser.new_page(viewport={'width': 1440, 'height': 900})
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.on('dialog', lambda dialog: (alerts.append(dialog.message), dialog.dismiss()))
                    page.set_content(html)
                    page.add_style_tag(path=str(ROOT / 'dbvora/web/style.css'))
                    page.evaluate('data => {window.fetch=async()=>({ok:true,json:async()=>data})}', schema)
                    page.add_script_tag(path=str(ROOT / 'dbvora/web/app.js'))
                    page.wait_for_function("document.querySelectorAll('#tables button').length === 4")
                    result['checks']['tables_and_fk'] = (page.locator('#tables button').count() == 4
                                                        and page.locator('#edges path').count() == 1
                                                        and page.locator('#links-count').inner_text() == '1')
                    page.locator('button.table-node').filter(has_text='orders').click()
                    result['checks']['inspector_selection'] = (page.locator('.detail-heading h3').inner_text() == 'orders'
                                                               and page.locator('#edges path.active').count() == 1)
                    page.locator('button.table-node').filter(has_text='<img src=x onerror=alert(2)>').click()
                    result['checks']['untrusted_identifiers_are_text_only'] = (
                        '<svg onload=alert(3)>' in page.locator('#detail').inner_text()
                        and page.locator('#detail img').count() == 0
                        and page.locator('#detail svg').count() == 0
                        and not alerts)
                    result['checks']['no_browser_script_errors'] = not errors and page.locator('#error').is_hidden()
                    page.set_viewport_size({'width': 390, 'height': 844})
                    result['checks']['responsive_no_horizontal_overflow'] = not page.evaluate(
                        'document.documentElement.scrollWidth > window.innerWidth')
                    result['status'] = 'PASS_SYNTHETIC_BROWSER_DOM_ONLY' if all(result['checks'].values()) else 'FAIL_CLOSED'
                finally:
                    browser.close()
    except Exception:
        result['status'] = 'FAIL_CLOSED'
        result['failure_code'] = 'BROWSER_OR_FIXTURE_UNAVAILABLE'
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description='Real browser DOM synthetic data probe')
    p.add_argument('--chromium', default=None, help='Local Chromium executable path')
    args = p.parse_args(argv)
    output = probe(args.chromium)
    print(json.dumps(output, sort_keys=True))
    return 0 if output['status'] == 'PASS_SYNTHETIC_BROWSER_DOM_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
