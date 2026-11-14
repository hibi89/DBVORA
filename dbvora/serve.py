"""Launch DBVORA from an explicitly selected local SQLite database."""
import argparse
import json
import sys

from dbvora.errors import InventoryError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='DBVORA local read-only database map')
    parser.add_argument('--db', required=True, action='append',
                        help='Absolute local SQLite path; repeat 2–8 times for live workspace')
    parser.add_argument('--port', default=8765, type=int)
    args = parser.parse_args(argv)
    try:
        from dbvora.api import create_app
        app = create_app(args.db[0] if len(args.db) == 1 else args.db, port=args.port)
    except (InventoryError, ValueError) as exc:
        message = exc.message if isinstance(exc, InventoryError) else 'Invalid server port.'
        print(json.dumps({'error': {'code': 'STARTUP_FAILED', 'message': message}}), file=sys.stderr)
        return 2
    import uvicorn
    print(f'DBVORA local interface: http://127.0.0.1:{args.port}', flush=True)
    # No proxy forwarding; never run with host 0.0.0.0 or --reload for customer use.
    uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False, proxy_headers=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
