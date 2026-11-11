"""Explicit synthetic-only mixed SQLite/Postgres offline topology report CLI.

No implicit network, no table rows or customer DB backups. PostgreSQL use is
explicitly gated and DSN supplied through a local environment variable, never
through argv or JSON output. This preview must not be sold as production-ready.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys

from dbvora.connectors.postgres_reader import PostgresInventoryError, inspect_postgres
from dbvora.errors import InventoryError
from dbvora.inventory import inspect_sqlite
from dbvora.multi_engine_report import ReportError, export_report
from dbvora.archive.safe_zip import ArchiveError, _directory

_ENV_NAME = re.compile(r'[A-Z][A-Z0-9_]{3,63}\Z', re.ASCII)


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ReportError('INVALID_ARGUMENT')


def _parser():
    p = _SafeParser(prog='python -m dbvora.mixed_cli',
                    description='Offline SYNTHETIC-only DBVORA metadata topology report; no customer DB.')
    p.add_argument('--sqlite', action='append', default=[],
                   help='Explicit absolute path to a synthetic SQLite fixture (repeat up to 8)')
    p.add_argument('--postgres-dsn-env', default=None,
                   help='Name of a local environment variable holding an authorized test PostgreSQL DSN')
    p.add_argument('--allow-postgres-network', action='store_true',
                   help='Explicitly authorize an outbound connection to a test PostgreSQL server')
    p.add_argument('--output-dir', required=True, help='Existing absolute directory distinct from sources')
    p.add_argument('--synthetic-only', action='store_true', help='Confirm every input is synthetic test data')
    p.add_argument('--accept-unencrypted-metadata', action='store_true',
                   help='Acknowledge locally generated HTML is plaintext schema metadata')
    return p


def run(argv=None) -> dict:
    args = _parser().parse_args(argv)
    if args.synthetic_only is not True:
        raise ReportError('SYNTHETIC_ONLY_REQUIRED')
    if args.accept_unencrypted_metadata is not True:
        raise ReportError('PLAINTEXT_ACK_REQUIRED')
    if not 1 <= len(args.sqlite) + (args.postgres_dsn_env is not None) <= 8:
        raise ReportError('INVALID_DATABASE_COUNT')
    if args.postgres_dsn_env is None and args.allow_postgres_network:
        raise ReportError('POSTGRES_NOT_CONFIGURED')
    if args.postgres_dsn_env is not None:
        if not _ENV_NAME.fullmatch(args.postgres_dsn_env):
            raise ReportError('INVALID_ENV_NAME')
        if not args.allow_postgres_network:
            raise ReportError('NETWORK_ACK_REQUIRED')
    output = Path(args.output_dir)
    if not output.is_absolute():
        raise ReportError('BAD_DESTINATION')
    try:
        # Validate the ORIGINAL path, not a pre-resolved alias. Otherwise an
        # output symlink would bypass the safe publisher's symlink guard.
        destination = _directory(output)
    except ArchiveError as exc:
        raise ReportError(exc.code) from None
    catalogs = []
    paths = set()
    for raw in args.sqlite:
        path = Path(raw)
        if not path.is_absolute():
            raise ReportError('INVALID_SOURCE')
        try:
            canonical = path.resolve(strict=True)
        except OSError:
            raise ReportError('INVALID_SOURCE') from None
        if canonical in paths:
            raise ReportError('DUPLICATE_SOURCE')
        paths.add(canonical)
        if destination == canonical.parent or destination in canonical.parents:
            raise ReportError('SEPARATE_OUTPUT_REQUIRED')
        catalogs.append(inspect_sqlite(path))
    if args.postgres_dsn_env is not None:
        secret_dsn = os.environ.get(args.postgres_dsn_env)
        if not secret_dsn:
            raise ReportError('PG_DSN_UNAVAILABLE')
        # Only a deliberate invocation with BOTH flags can make a connection.
        catalogs.append(inspect_postgres(secret_dsn))
    return export_report(catalogs, destination)


def main(argv=None) -> int:
    try:
        report = run(argv)
        print(json.dumps({'ok': True, 'result': report}, sort_keys=True))
        return 0
    except (ReportError, InventoryError, PostgresInventoryError) as exc:
        code = exc.code if hasattr(exc, 'code') else 'OPERATION_FAILED'
    except (OSError, ValueError, TypeError):
        code = 'OPERATION_FAILED'
    except Exception:
        code = 'UNEXPECTED_FAILURE'
    # Never echo input paths, connection strings, SQL or record content.
    print(json.dumps({'ok': False, 'error': {'code': code}}, sort_keys=True), file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
