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
                page.wait_for_function("document.querySelector('#postgres-status').textContent.includes('TLS 인증 또는 PostgreSQL 연결에 실패했습니다')")
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
                page.on('request', lambda request: pg_requests.append(request.url)
                        if request.url.endswith('/api/postgres') else None)
                page.goto('http://127.0.0.1:' + str(port) + '/', wait_until='domcontentloaded')
                if pg_requests:
                    raise AssertionError('POSTGRES_LOOKUP_MUST_BE_EXPLICIT_AFTER_RESTART')
                page.locator('#postgres-load').click()
                page.wait_for_function("document.querySelector('#postgres-status').textContent.includes('TLS 검증')")
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
                checks.extend(['real_tls_catalog_and_foreign_key_ui', 'no_rows_or_dsn_in_browser'])
                page.set_viewport_size({'width': 390, 'height': 844})
                page.wait_for_timeout(100)
                overflow = page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
                if overflow:
                    raise AssertionError('POSTGRES_PANEL_MOBILE_OVERFLOW')
                checks.append('mobile_390px_layout')
                browser.close()
        finally:
            stop_server(good_server)
    return {'contract': 'dbvora.pg_tls_ui_e2e.v1', 'status': 'PASS',
            'checks': checks, 'customer_data': False, 'dsn_logged': False}


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True))
