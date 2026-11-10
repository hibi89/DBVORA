"""Optional Chromium smoke for DBVORA's real offline HTML template.

Synthetic metadata only. No customer database, app server, network, or writes to source.
Requires Playwright Python and an installed Chromium; this is NOT a release gate.

Run strict local-file navigation: python -m scripts.browser_workspace_smoke --chromium PATH
If the runner forbids file://, use --document-only to verify DOM/JS but NOT file access.
"""
from __future__ import annotations

import argparse
import ast
import base64
import json
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'dbvora' / 'workspace_html.py'
MODES = ('ascii', 'unicode', 'hostile')


def _template() -> str:
    tree = ast.parse(TEMPLATE.read_text(encoding='utf-8'), filename='workspace_html.py')
    for item in tree.body:
        if isinstance(item, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_PAGE' for t in item.targets):
            if not isinstance(item.value, ast.Constant) or type(item.value.value) is not str:
                raise RuntimeError('INVALID_OFFLINE_TEMPLATE')
            return item.value.value
    raise RuntimeError('OFFLINE_TEMPLATE_NOT_FOUND')


def _fixture(mode: str) -> dict:
    parent = {'ascii': 'Parent', 'unicode': 'ÄParent', 'hostile': '<img src=x onerror=alert(1)>'}[mode]
    target = {'ascii': 'PARENT', 'unicode': 'äParent', 'hostile': parent}[mode]

    def table(name: str) -> dict:
        return {'name': name, 'columns': [{'name': 'id', 'type': 'INTEGER', 'pk_position': 1}],
                'indexes': [], 'foreign_keys': [], 'storage': {'status': 'unavailable'}}

    return {
        'contract_version': 'p0-03.workspace.v1', 'database_count': 2, 'table_count': 2,
        'total_main_db_size_bytes': 12345,
        'databases': [
            {'db_id': 'db1', 'label': 'Database 1', 'size_bytes': 12345,
             'tables': [table(parent), table('child')]},
            {'db_id': 'db2', 'label': 'Database 2', 'size_bytes': 0, 'tables': []},
        ],
        'relationships': [{'database_id': 'db1', 'from_table': 'child',
                           'to_table': target, 'from_columns': ['id'], 'to_columns': ['id'],
                           'target_in_inventory': mode != 'unicode'}],
        'declared_cross_database_links': [],
        'schema_review': {'contract': 'dbvora.schema-review.v1', 'status': 'REVIEW_ONLY',
                          'total_tables': 2, 'without_declared_pk': 0,
                          'unresolved_fk_targets': int(mode == 'unicode'), 'fk_index_review': 1,
                          'findings': [{'code': 'FK_INDEX_REVIEW', 'table': 'child'}],
                          'truncated': False},
    }


def _html(template: str, mode: str) -> str:
    if template.count('__BASE64__') != 1:
        raise RuntimeError('INVALID_OFFLINE_TEMPLATE')
    payload = json.dumps(_fixture(mode), ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    encoded = base64.b64encode(payload.encode('utf-8')).decode('ascii')
    return template.replace('__BASE64__', encoded)


def run(*, chromium: str | None = None, document_only: bool = False) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {'status': 'NOT_RUN', 'reason': 'PLAYWRIGHT_NOT_INSTALLED', 'passed': 0}

    template = _template()
    checked = []
    with tempfile.TemporaryDirectory(prefix='dbvora-browser-smoke-') as temp:
        folder = Path(temp)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, executable_path=chromium)
            try:
                for mode in MODES:
                    page = browser.new_page()
                    errors, outbound = [], []
                    page.on('pageerror', lambda exc: errors.append('PAGEERROR'))
                    page.on('console', lambda msg: errors.append('CONSOLE_ERROR') if msg.type == 'error' else None)
                    page.on('request', lambda req: outbound.append('NETWORK_REQUEST')
                            if urlsplit(req.url).scheme in ('http', 'https', 'ws', 'wss') else None)
                    path = folder / (mode + '.html')
                    content = _html(template, mode)
                    path.write_text(content, encoding='utf-8')
                    try:
                        if document_only:
                            page.set_content(content, wait_until='load')
                        else:
                            page.goto(path.as_uri(), wait_until='load')
                    except Exception:
                        return {'status': 'NOT_RUN', 'reason': 'BROWSER_FILE_NAVIGATION_BLOCKED_OR_FAILED',
                                'passed': len(checked), 'mode': 'file_navigation'}
                    expected = 0 if mode == 'unicode' else 1
                    assert page.locator('#graph line').count() == expected, 'WRONG_FK_GRAPH'
                    assert page.locator('#databases button').count() == 2, 'WRONG_DATABASE_COUNT'
                    assert page.locator('#tables button').count() == 2, 'WRONG_TABLE_COUNT'
                    assert 'FK index review' in page.locator('#schema-review').inner_text(), 'SCHEMA_REVIEW_HIDDEN'
                    page.locator('#tables button').nth(1).click()
                    assert 'child' in page.locator('#details').inner_text(), 'TABLE_CLICK_FAILED'
                    assert ('target absent' if mode == 'unicode' else 'declared FK') in page.locator('#relationships').inner_text(), 'FK_LABEL_WRONG'
                    page.locator('#databases button').nth(1).click()
                    assert 'No user tables' in page.locator('#details').inner_text(), 'EMPTY_DATABASE_FAILED'
                    page.locator('#databases button').nth(0).click()
                    assert page.locator('#graph line').count() == expected, 'DATABASE_RESELECT_FAILED'
                    assert page.locator('img').count() == 0, 'UNSAFE_HTML_IDENTIFIER'
                    assert not errors, 'BROWSER_CONSOLE_OR_SCRIPT_ERROR'
                    assert not outbound, 'UNEXPECTED_NETWORK_REQUEST'
                    checked.append(mode)
                    page.close()
            finally:
                browser.close()
    return {'status': 'PASS_RENDER_ONLY' if document_only else 'PASS_FILE_NAVIGATION',
            'passed': len(checked), 'cases': checked, 'real_browser': True,
            'original_template': True, 'customer_data': False, 'network_requests': 0,
            'file_navigation_verified': not document_only}


def main() -> int:
    parser = argparse.ArgumentParser(description='Synthetic offline Chromium schema-graph smoke')
    parser.add_argument('--chromium', default=None, help='Optional local Chromium executable path')
    parser.add_argument('--document-only', action='store_true',
                        help='Test document injection only; does not certify file:// navigation')
    args = parser.parse_args()
    try:
        result = run(chromium=args.chromium, document_only=args.document_only)
    except Exception:
        result = {'status': 'FAIL', 'reason': 'BROWSER_SMOKE_ASSERTION_FAILED', 'passed': 0}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'].startswith('PASS') else 1


if __name__ == '__main__':
    raise SystemExit(main())
