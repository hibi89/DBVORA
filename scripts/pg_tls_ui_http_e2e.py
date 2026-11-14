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
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            if proc.poll() is not None:
                raise RuntimeError('LOCAL_SERVER_START_FAILED')
            try:
                with urlopen('http://127.0.0.1:' + str(port) + '/health', timeout=0.25) as response:
                    if response.status == 200:
                        return proc
            except Exception:
                time.sleep(0.1)
        raise RuntimeError('LOCAL_SERVER_START_TIMEOUT')
    except Exception:
        proc.terminate()
        proc.wait(timeout=5)
        raise


def stop_server(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def verify() -> dict:
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
                page.locator('#postgres-load').click()
                page.locator('#postgres-status').filter(has_text='TLS 인증 또는 PostgreSQL 연결에 실패했습니다').wait_for(timeout=15000)
                body = page.locator('body').inner_text()
                if len(pg_requests) != 1 or dsn in body or bad_ca in body:
                    raise AssertionError('TLS_FAILURE_LEAK_OR_REQUEST_COUNT')
                if CANARY in body:
                    raise AssertionError('SYNTHETIC_ROW_LEAK_ON_TLS_FAILURE')
                checks.append('explicit_click_and_wrong_ca_recovery_error')
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
                page.locator('#postgres-load').click()
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
                checks.extend(['real_tls_catalog_and_foreign_key_ui', 'no_rows_or_dsn_in_browser',
                               'explicit_stats_may_lag_and_view_unavailable'])
                page.set_viewport_size({'width': 390, 'height': 844})
                page.wait_for_timeout(100)
                for selector in ('.postgres-panel', '.postgres-browser', '#postgres-load',
                                 '#postgres-table-list', '#postgres-detail'):
                    box = page.locator(selector).bounding_box()
                    if box and (box['x'] < 0 or box['x'] + box['width'] > 390):
                        raise AssertionError('POSTGRES_PANEL_MOBILE_OVERFLOW')
                checks.append('mobile_390px_layout')
                browser.close()
        finally:
            stop_server(good_server)
    return {'contract': 'dbvora.pg_tls_ui_e2e.v1', 'status': 'PASS',
            'checks': checks, 'customer_data': False, 'dsn_logged': False}


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True))
