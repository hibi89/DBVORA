"""Explicit offline CLI for synthetic content-addressed snapshots and restore.

This executable is development-only. It never accepts live/customer data,
never scans for databases, schedules execution, deletes files, or publishes
to a server. No source paths or database content are printed in JSON.
"""
from __future__ import annotations

import argparse
import json
import sys

from dbvora.archive.incremental_cas import (
    IncrementalError, create_incremental, restore_incremental,
)


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise IncrementalError("INVALID_ARGUMENT")


def _parser():
    p = _SafeParser(prog="python -m dbvora.incremental_cli",
                    description="Synthetic-only immutable chunk store / independent restore")
    subs = p.add_subparsers(dest="command", required=True, parser_class=_SafeParser)
    create = subs.add_parser("create", help="Store explicitly generated synthetic snapshot")
    create.add_argument("--snapshot", required=True)
    create.add_argument("--chunk-dir", required=True)
    create.add_argument("--manifest-dir", required=True)
    restore = subs.add_parser("restore", help="Restore into an existing distinct folder")
    restore.add_argument("--manifest", required=True)
    restore.add_argument("--chunk-dir", required=True)
    restore.add_argument("--output-dir", required=True)
    for command in (create, restore):
        command.add_argument("--synthetic-only", action="store_true")
        command.add_argument("--accept-plaintext", action="store_true")
    return p


def main(argv=None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.command == "create":
            result = create_incremental(args.snapshot, args.chunk_dir, args.manifest_dir,
                                        synthetic_only=args.synthetic_only,
                                        accept_plaintext=args.accept_plaintext)
        elif args.command == "restore":
            result = restore_incremental(args.manifest, args.chunk_dir, args.output_dir,
                                         synthetic_only=args.synthetic_only,
                                         accept_plaintext=args.accept_plaintext)
        else:
            raise IncrementalError("INVALID_ARGUMENT")
        print(json.dumps({"ok": True, "command": args.command, "result": result},
                         sort_keys=True))
        return 0
    except IncrementalError as exc:
        code = str(exc)
    except Exception:
        code = "INCREMENTAL_OPERATION_FAILED"
    # No argparse-supplied file path, credential, SQL or data is echoed.
    print(json.dumps({"ok": False, "error": {"code": code}}, sort_keys=True),
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
