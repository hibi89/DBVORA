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
    print(json.dumps({'error': {'code': code, 'message': message}}, sort_keys=True),
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
        message = exc.message if isinstance(exc, InventoryError) else 'Invalid server port.'
        return _report_error('STARTUP_FAILED', message, 2)
    except (ImportError, RuntimeError):
        return _report_error('UI_DEPENDENCY_MISSING',
                             'Install the local UI extra before launching the viewer.', 4)
    try:
        if _port_in_use(args.port):
            return _report_error('PORT_IN_USE',
                                 'This local port is already in use. Choose another port.', 3)
    except OSError:
        return _report_error('SERVER_START_FAILED',
                             'The local port could not be checked safely.', 2)
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
                             'The local viewer could not start safely.', 2)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
