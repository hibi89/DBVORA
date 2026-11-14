"""Real Chromium acceptance for the local PostgreSQL catalog panel.

Runs only in GitHub Actions against its ephemeral synthetic PostgreSQL 16 TLS
container. It never accepts a customer database and never prints a DSN.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

from dbvora.connectors.postgres_reader import inspect_postgres
from dbvora.inventory import inspect_sqlite
from dbvora.multi_engine_report import assemble_workspace, render_report

ROOT = Path(__file__).resolve().parents[1]
CANARY = 'SYNTHETIC_ROW_MUST_NEVER_BE_EXPORTED'


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def start_server(database: Path, dsn: str, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env['DBVORA_POSTGRES_DSN'] = dsn
    proc = subprocess.Popen(
        [sys.executable, '-m', 'dbvora.serve', '--db', str(database), '--port', str(port)],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    try:
        for _ in range(100):
            if proc.poll() is not None:
                _, diagnostics = proc.communicate(timeout=5)
                startup_code = 'LOCAL_SERVER_START_FAILED'
                for line in diagnostics.decode('utf-8', errors='replace').splitlines():
                    try:
                        report = json.loads(line)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    error = report.get('error') if isinstance(report, dict) else None
                    candidate = error.get('code') if isinstance(error, dict) else None
                    if candidate in {'PORT_IN_USE', 'UI_DEPENDENCY_MISSING',
                                     'STARTUP_FAILED', 'SERVER_START_FAILED'}:
                        startup_code = 'LOCAL_SERVER_START_FAILED:' + candidate
                        break
                raise RuntimeError(startup_code)
            try:
                with urlopen('http://127.0.0.1:' + str(port) + '/health', timeout=0.25) as response:
                    if response.status == 200:
                        return proc
            except Exception:
                time.sleep(0.1)
        raise RuntimeError('LOCAL_SERVER_START_TIMEOUT')
    except Exception:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        if proc.stderr is not None:
            proc.stderr.close()
        raise


def stop_server(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    if proc.stderr is not None:
        proc.stderr.close()


def _capture_sanitized_screenshot(page, directory: Path, name: str) -> None:
    path = directory / name
    page.screenshot(path=path, full_page=True)
    data = path.read_bytes()
    if len(data) < 256 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("SYNTHETIC_SCREENSHOT_INVALID")


def verify() -> dict:
    screenshot_text = os.environ.get('DBVORA_SYNTHETIC_UI_ARTIFACT_DIR', '')
    screenshot_root = Path(screenshot_text) if screenshot_text else None
    if screenshot_root is None or not screenshot_root.is_absolute():
        raise RuntimeError('SYNTHETIC_UI_ARTIFACT_DIR_REQUIRED')
    screenshot_root.mkdir(parents=True, exist_ok=True)
    dsn = os.environ.get('DBVORA_SYNTHETIC_PG_DSN', '')
    bad_ca = os.environ.get('DBVORA_SYNTHETIC_BAD_CA', '')
    if not dsn or not bad_ca or not Path(bad_ca).is_file():
        raise RuntimeError('SYNTHETIC_TLS_ENV_REQUIRED')
    import psycopg
    parsed = psycopg.conninfo.conninfo_to_dict(dsn)
    if (parsed.get('host') != 'localhost' or parsed.get('port') != '55439'
            or parsed.get('dbname') != 'dbvora_test' or parsed.get('user') != 'dbvora_reader'):
        raise RuntimeError('LOOPBACK_SYNTHETIC_DATABASE_REQUIRED')
    with tempfile.TemporaryDirectory(prefix='dbvora-pg-ui-') as tmp:
        database = Path(tmp) / 'ui.sqlite'
        connection = sqlite3.connect(database)
        try:
            connection.execute('CREATE TABLE synthetic_ui_only (id INTEGER PRIMARY KEY)')
            connection.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, local_only TEXT)')
        finally:
            connection.close()
        port = free_port()
        bad_dsn = dsn + ' sslrootcert=' + bad_ca
        wrong_server = start_server(database, bad_dsn, port)
        checks = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={'width': 1280, 'height': 900})
                pg_requests = []
                page.on('request', lambda request: pg_requests.append(request.url)
                        if request.url.endswith('/api/postgres') else None)
                page.goto('http://127.0.0.1:' + str(port) + '/', wait_until='domcontentloaded')
                page.wait_for_selector('#postgres-load')
                if pg_requests:
                    raise AssertionError('POSTGRES_LOOKUP_MUST_BE_EXPLICIT')
                page.locator('#postgres-load').focus()
                page.keyboard.press('Enter')
                page.locator('#postgres-status').filter(has_text='TLS 인증 또는 PostgreSQL 연결에 실패했습니다').wait_for(timeout=15000)
                body = page.locator('body').inner_text()
                if len(pg_requests) != 1 or dsn in body or bad_ca in body:
                    raise AssertionError('TLS_FAILURE_LEAK_OR_REQUEST_COUNT')
                if CANARY in body:
                    raise AssertionError('SYNTHETIC_ROW_LEAK_ON_TLS_FAILURE')
                _capture_sanitized_screenshot(page, screenshot_root, 'postgres-tls-error-desktop.png')
                checks.append('explicit_click_and_wrong_ca_recovery_error_screenshot_no_secret')
                browser.close()
        finally:
            stop_server(wrong_server)

        good_server = start_server(database, dsn, port)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={'width': 1280, 'height': 900})
                pg_requests = []
                stats_requests = []
                page.on('request', lambda request: pg_requests.append(request.url)
                        if request.url.endswith('/api/postgres') else None)
                page.on('request', lambda request: stats_requests.append(request.url)
                        if request.url.endswith('/api/postgres/statistics') else None)
                page.goto('http://127.0.0.1:' + str(port) + '/', wait_until='domcontentloaded')
                if pg_requests:
                    raise AssertionError('POSTGRES_LOOKUP_MUST_BE_EXPLICIT_AFTER_RESTART')
                page.locator('#postgres-load').focus()
                page.keyboard.press('Enter')
                page.locator('#postgres-status').filter(has_text='TLS 검증').wait_for(timeout=15000)
                names = page.locator('#postgres-table-list button').all_text_contents()
                if not {'public.users', 'public.events', 'public.event_view'}.issubset(set(names)):
                    raise AssertionError('SYNTHETIC_CATALOG_MISSING')
                page.locator('#postgres-table-list button').filter(has_text='public.events').click()
                detail = page.locator('#postgres-detail').inner_text()
                body = page.locator('body').inner_text()
                if 'user_id' not in detail or 'public.users' not in detail:
                    raise AssertionError('POSTGRES_DETAIL_MISSING_FK_METADATA')
                if CANARY in body or 'synthetic-user.invalid' in body or dsn in body:
                    raise AssertionError('POSTGRES_ROW_OR_DSN_LEAK')
                if stats_requests or not page.locator('#postgres-stats-load').is_visible():
                    raise AssertionError('STATISTICS_LOOKUP_MUST_BE_EXPLICIT')
                stats_responses = []
                page.on('response', lambda response: stats_responses.append(response)
                        if response.url.endswith('/api/postgres/statistics') else None)
                page.locator('#postgres-stats-load').click()
                page.locator('#postgres-stats-status').filter(has_text='조회 시각').wait_for(timeout=30000)
                if len(stats_requests) != 1 or len(stats_responses) != 1:
                    raise AssertionError('STATISTICS_REQUEST_COUNT_INVALID')
                stats_payload = stats_responses[0].json()
                stats_json = json.dumps(stats_payload, sort_keys=True)
                if stats_payload.get('contract') != 'dbvora.pg_statistics.v1' or not stats_payload.get('statistics_may_lag'):
                    raise AssertionError('STATISTICS_PROVENANCE_CONTRACT_INVALID')
                if CANARY in stats_json or dsn in stats_json or 'columns' in stats_json:
                    raise AssertionError('STATISTICS_API_ROW_COLUMN_OR_DSN_LEAK')
                stats_text = page.locator('#postgres-detail').inner_text()
                events_stats = next((row['statistics'] for row in stats_payload['tables']
                                     if row['schema'] == 'public' and row['name'] == 'events'), None)
                if events_stats is None:
                    raise AssertionError('SYNTHETIC_EVENT_STATS_MISSING')
                if events_stats.get('status') == 'observed':
                    if 'pg_stat_user_tables' not in stats_text or 'pg_relation_size' not in stats_text or 'pg_indexes_size' not in stats_text:
                        raise AssertionError('OBSERVED_STATS_PROVENANCE_NOT_RENDERED')
                    checks.append('estimated_rows_and_measured_storage_provenance')
                else:
                    if '통계를 사용할 수 없습니다.' not in stats_text or '0으로 대체하지 않습니다.' not in stats_text:
                        raise AssertionError('UNAVAILABLE_STATS_FABRICATED_AS_ZERO')
                    checks.append('unavailable_statistics_without_fabricated_zero')
                page.locator('#postgres-table-list button').filter(has_text='public.event_view').click()
                view_text = page.locator('#postgres-detail').inner_text()
                if '통계 범위 밖' not in view_text or '0으로 대체하지 않습니다.' not in view_text:
                    raise AssertionError('VIEW_STATS_LIMIT_NOT_SHOWN')
                body = page.locator('body').inner_text()
                if CANARY in body or 'synthetic-user.invalid' in body or dsn in body:
                    raise AssertionError('STATISTICS_ROW_OR_DSN_LEAK')
                _capture_sanitized_screenshot(page, screenshot_root, 'postgres-catalog-desktop.png')
                checks.extend(['real_tls_catalog_and_foreign_key_ui', 'no_rows_or_dsn_in_browser',
                               'explicit_stats_may_lag_and_view_unavailable',
                               'desktop_screenshot_after_secret_row_assertions'])
                page.set_viewport_size({'width': 390, 'height': 844})
                page.wait_for_timeout(100)
                for selector in ('.postgres-panel', '.postgres-browser', '#postgres-load',
                                 '#postgres-table-list', '#postgres-detail'):
                    box = page.locator(selector).bounding_box()
                    if box and (box['x'] < 0 or box['x'] + box['width'] > 390):
                        raise AssertionError('POSTGRES_PANEL_MOBILE_OVERFLOW')
                checks.append('mobile_390px_layout')
                _capture_sanitized_screenshot(page, screenshot_root, 'postgres-catalog-mobile-390px.png')
                checks.append('mobile_screenshot_after_layout_and_secret_checks')

                # Exercise the complete mixed SQLite + real PostgreSQL map with
                # a same-name synthetic collision and an explicit, unverified link.
                sqlite_catalog = inspect_sqlite(database)
                pg_catalog = inspect_postgres(dsn)
                unlinked = assemble_workspace([sqlite_catalog, pg_catalog])
                if unlinked['declared_cross_database_links'] or unlinked['cross_database_edges_verified'] != 0:
                    raise AssertionError('SAME_NAME_RELATIONSHIP_MUST_NOT_BE_INFERRED')
                link = {
                    'from_db': 1, 'from_schema': None, 'from_table': 'users', 'from_column': 'id',
                    'to_db': 2, 'to_schema': 'public', 'to_table': 'users', 'to_column': 'id',
                }
                mixed = assemble_workspace([sqlite_catalog, pg_catalog], declared_links=[link])
                mixed_page = render_report(mixed)
                if dsn in mixed_page or str(database) in mixed_page or CANARY in mixed_page:
                    raise AssertionError('MIXED_REPORT_SECRET_ROW_OR_PATH_LEAK')
                page.set_viewport_size({'width': 1280, 'height': 900})
                mixed_page_errors = []
                page.on('pageerror', lambda error: mixed_page_errors.append(type(error).__name__))
                page.set_content(mixed_page, wait_until='domcontentloaded')
                if page.locator('#cross-database-links').count() != 1:
                    raise AssertionError('MIXED_LINK_LIST_ELEMENT_MISSING')
                if mixed_page_errors:
                    raise AssertionError('MIXED_MAP_SCRIPT_ERROR:' + ','.join(mixed_page_errors[:3]))
                model = json.loads(page.locator('#catalog').text_content())
                declared = model.get('declared_cross_database_links', [])
                if len(declared) != 1:
                    raise AssertionError('MIXED_LINK_MODEL_MISSING')
                if page.locator('#cross-database-links button').count() != 1:
                    raise AssertionError('MIXED_LINK_BUTTON_NOT_RENDERED')
                node_names = page.locator('#databases button.node .table-key').all_text_contents()
                if node_names.count('users') != 1 or node_names.count('public.users') != 1:
                    raise AssertionError('SAME_NAME_DATABASE_NODES_NOT_SCOPED')
                if 'user-declared / unverified' not in page.locator('#cross-database-links').inner_text():
                    raise AssertionError('CROSS_DATABASE_LINK_NOT_MARKED_UNVERIFIED')
                model = json.loads(page.locator('#catalog').text_content())
                declared = model.get('declared_cross_database_links', [])
                if (len(declared) != 1 or declared[0].get('evidence') != 'user_declared_unverified'
                        or declared[0].get('verified') is not False
                        or declared[0].get('from_db_id') != 1 or declared[0].get('to_db_id') != 2
                        or model.get('cross_database_edges_verified') != 0):
                    raise AssertionError('MIXED_LINK_EVIDENCE_SCOPE_INVALID')
                page.locator('#cross-database-links button').click()
                if page.locator('#selection').inner_text() != 'Database 2 / public.users':
                    raise AssertionError('CROSS_DATABASE_LINK_SELECTED_WRONG_COLLIDING_TABLE')
                if page.locator('#databases button.node[aria-pressed="true"]').count() != 1:
                    raise AssertionError('MIXED_REPORT_SELECTION_STATE_INVALID')
                if CANARY in page.locator('body').inner_text() or dsn in page.locator('body').inner_text():
                    raise AssertionError('MIXED_REPORT_ROW_OR_DSN_LEAK')
                _capture_sanitized_screenshot(page, screenshot_root, 'mixed-map-desktop.png')
                page.set_viewport_size({'width': 390, 'height': 844})
                if page.evaluate('document.documentElement.scrollWidth') > 390:
                    raise AssertionError('MIXED_MAP_MOBILE_OVERFLOW')
                _capture_sanitized_screenshot(page, screenshot_root, 'mixed-map-mobile-390px.png')
                checks.append('real_pg16_sqlite_same_name_collision_and_explicit_unverified_link')
                browser.close()
        finally:
            stop_server(good_server)
    return {'contract': 'dbvora.pg_tls_ui_e2e.v1', 'status': 'PASS',
            'checks': checks, 'customer_data': False, 'dsn_logged': False}


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True))
