"""Launch DBVORA from an explicitly selected local SQLite database."""
import argparse
import errno
import json
import os
import socket
import sys

from dbvora.errors import InventoryError


def _address_in_use(error: OSError) -> bool:
    return error.errno == errno.EADDRINUSE or getattr(error, 'winerror', None) == 10048


def _port_in_use(port: int) -> bool:
    # A connect probe detects a listening local service without reserving an
    # otherwise-free port or misclassifying an unrelated TIME_WAIT socket.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        return probe.connect_ex(('127.0.0.1', port)) == 0


def _report_error(code: str, message: str, exit_code: int) -> int:
    print(json.dumps({'error': {'code': code, 'message': message}}, ensure_ascii=False, sort_keys=True),
          file=sys.stderr)
    return exit_code


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='DBVORA local read-only database map')
    parser.add_argument('--db', required=True, action='append',
                        help='Absolute local SQLite path; repeat 2–8 times for live workspace')
    parser.add_argument('--port', default=8765, type=int)
    parser.add_argument('--observation-ledger',
                        help='Optional local DBVORA ledger path; enables GET-only history display')
    args = parser.parse_args(argv)
    try:
        from dbvora.api import create_app
        app = create_app(args.db[0] if len(args.db) == 1 else args.db, port=args.port,
                         observation_ledger_path=args.observation_ledger,
                         postgres_dsn=os.environ.get('DBVORA_POSTGRES_DSN'))
    except (InventoryError, ValueError) as exc:
        if isinstance(exc, InventoryError):
            message = {
                'FILE_UNAVAILABLE': '선택한 데이터베이스를 읽을 수 없습니다. 파일 위치와 읽기 권한을 확인하세요.',
                'INVALID_DATABASE': '선택한 파일이 유효한 SQLite 데이터베이스인지 확인하세요.',
                'DB_READ_FAILED': 'SQLite 구조를 안전하게 읽지 못했습니다. 파일 형식과 읽기 권한을 확인하세요.',
                'INVALID_OBSERVATION_LEDGER': '관측 원장은 데이터베이스와 분리된 별도 파일이어야 합니다.',
            }.get(exc.code, '선택한 데이터베이스 설정을 안전하게 확인하지 못했습니다.')
        else:
            message = '포트 번호는 1부터 65535 사이여야 합니다.'
        return _report_error('STARTUP_FAILED', message, 2)
    except (ImportError, RuntimeError):
        return _report_error('UI_DEPENDENCY_MISSING',
                             '웹 화면 구성요소가 없습니다. Python 환경에 로컬 UI 추가 항목을 설치한 뒤 다시 실행하세요.', 4)
    try:
        if _port_in_use(args.port):
            return _report_error('PORT_IN_USE',
                                 '이 로컬 포트는 사용 중입니다. 다른 포트를 선택하세요.', 3)
    except OSError:
        return _report_error('SERVER_START_FAILED',
                             '로컬 포트 상태를 안전하게 확인하지 못했습니다. 포트 설정을 확인하세요.', 2)
    try:
        import uvicorn
    except ImportError:
        return _report_error('UI_DEPENDENCY_MISSING',
                             'Install the local UI extra before launching the viewer.', 4)
    print(f'DBVORA local interface: http://127.0.0.1:{args.port}', flush=True)
    # Keep the listener loopback-only. Never forward proxies or enable reload.
    try:
        uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False,
                    proxy_headers=False)
    except OSError as error:
        if _address_in_use(error):
            return _report_error('PORT_IN_USE',
                                 'This local port is already in use. Choose another port.', 3)
        return _report_error('SERVER_START_FAILED',
                             '로컬 화면을 시작하지 못했습니다. 선택한 파일과 포트 상태를 확인하세요.', 2)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
