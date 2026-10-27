"""Explicit, offline, synthetic-only prototype CLI for DBVORA archives.

Not a customer-data tool. All archive writings create new artifacts only.
This module never starts a scheduler, server, subprocess shell, or network client.
"""

import argparse
import json
from pathlib import Path
import sys

from dbvora.archive.recovery_catalog import PUBLISHED
from dbvora.archive.safe_zip import (
    ArchiveError, create_snapshot, make_zip_archive, restore_zip_archive,
)
from dbvora.archive.zstd_archive import create_zstd_archive, restore_zstd_archive
from dbvora.archive.receipts import create_receipt, inspect_receipt_catalog


class _SafeParser(argparse.ArgumentParser):
    """Do not echo CLI parameters (which may contain a private local path)."""

    def error(self, message):
        raise _CLIError("INVALID_ARGUMENT", "Invalid command arguments. Run --help for usage.")


class _CLIError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def _parser():
    parser = _SafeParser(
        prog="python -m dbvora.archive_cli",
        description=(
            "Offline prototype for SYNTHETIC SQLite only. Archives, snapshots and "
            "restored SQLite contain UNENCRYPTED database records. No customer data."
        ),
    )
    subs = parser.add_subparsers(dest="command", required=True, parser_class=_SafeParser)

    snapshot = subs.add_parser("snapshot", help="SQLite online backup to new plaintext snapshot")
    snapshot.add_argument("--source", required=True, help="Absolute path to a synthetic SQLite fixture")
    snapshot.add_argument("--output-dir", required=True, help="Existing absolute output directory")

    archive = subs.add_parser("archive", help="ZIP or optional installed ZSTD; new file only")
    archive.add_argument("--snapshot", required=True, help="Absolute path to DBVORA-generated snapshot")
    archive.add_argument("--output-dir", required=True, help="Existing absolute output directory")
    archive.add_argument("--codec", required=True, choices=("zip", "zstd"))
    archive.add_argument("--level", type=int, choices=(1, 3, 9), default=None,
                         help="ZSTD level (1, 3 or 9). Do not specify for ZIP")

    restore = subs.add_parser("restore", help="Verified restore to a NEW plaintext SQLite file")
    restore.add_argument("--archive", required=True, help="Absolute path to generated .zip/.dbvz artifact")
    restore.add_argument("--output-dir", required=True, help="Existing absolute *separate* output directory")

    receipt = subs.add_parser("receipt", help="Unsigned receipt for an independently checked artifact")
    receipt.add_argument("--artifact", required=True, help="Absolute path to a DBVORA artifact")
    receipt.add_argument("--parent-receipt-name", default=None,
                         help="Optional existing verified receipt basename in same directory")
    receipt.add_argument("--accept-unsigned", action="store_true",
                         help="Acknowledge receipts are NOT signed or authenticated")

    audit = subs.add_parser("audit", help="Read-only independent catalog/receipt verification")
    audit.add_argument("--output-dir", required=True, help="Existing absolute archive directory")
    audit.add_argument("--require-all-verified", action="store_true",
                       help="Exit nonzero unless at least one archive has a valid unsigned receipt and all entries pass")

    for child in (snapshot, archive, restore, receipt):
        child.add_argument("--synthetic-only", action="store_true",
                           help="Confirm this command is operating only on synthetic test data")
    for child in (snapshot, archive, restore):
        child.add_argument("--accept-plaintext", action="store_true",
                           help="Acknowledge archive/snapshot/restore content is NOT encrypted")
    return parser


def _absolute_generated(path, *, suffixes):
    p = Path(path)
    match = PUBLISHED.fullmatch(p.name)
    if not p.is_absolute() or match is None or match.group(1) not in suffixes:
        raise _CLIError("GENERATED_ARTIFACT_REQUIRED", "Select an absolute DBVORA-generated artifact.")
    return p


def _require_write_ack(args):
    if not args.synthetic_only:
        raise _CLIError("SYNTHETIC_ONLY_REQUIRED", "This prototype requires --synthetic-only.")
    if args.command == "receipt":
        if not args.accept_unsigned:
            raise _CLIError("UNSIGNED_ACK_REQUIRED", "This receipt requires --accept-unsigned.")
    elif not args.accept_plaintext:
        raise _CLIError("PLAINTEXT_ACK_REQUIRED", "This operation requires --accept-plaintext.")


def _no_source_dir_output(source, output_dir):
    # Keep generated files out of the source artifact's directory. This is not
    # permission to archive customer databases; --synthetic-only is an assertion.
    if Path(source).parent.resolve() == Path(output_dir).resolve():
        raise _CLIError("SEPARATE_OUTPUT_REQUIRED", "Use a separate existing output directory.")


def _redact_paths(obj):
    """Paths returned by lower layers are not disclosed in CLI JSON/logs."""
    if isinstance(obj, list):
        return [_redact_paths(item) for item in obj]
    if isinstance(obj, dict):
        return {key: (Path(value).name if key.endswith("_path") and isinstance(value, str)
                      else _redact_paths(value)) for key, value in obj.items()}
    return obj


def main(argv=None):
    try:
        args = _parser().parse_args(argv)
        if args.command == "audit":
            result = inspect_receipt_catalog(args.output_dir)
            if args.require_all_verified:
                records = result.get("records", ())
                if (not records or not all(
                        item.get("status") == "RECORDED_AND_CONTENT_VERIFIED_UNSIGNED"
                        and item.get("receipt_status") == "RECEIPT_AND_CONTENT_VERIFIED_UNSIGNED"
                        for item in records)):
                    raise _CLIError("AUDIT_VERIFICATION_FAILED",
                                    "Audit contains missing, damaged, or unverified artifacts or receipts.")
        else:
            _require_write_ack(args)
            if args.command == "snapshot":
                _no_source_dir_output(args.source, args.output_dir)
                result = create_snapshot(args.source, args.output_dir)
            elif args.command == "archive":
                _absolute_generated(args.snapshot, suffixes=("sqlite",))
                _no_source_dir_output(args.snapshot, args.output_dir)
                if args.codec == "zip":
                    if args.level is not None:
                        raise _CLIError("UNSUPPORTED_LEVEL", "Compression level applies to ZSTD only.")
                    result = make_zip_archive(args.snapshot, args.output_dir)
                else:
                    result = create_zstd_archive(args.snapshot, args.output_dir,
                                                 level=args.level if args.level is not None else 3)
            elif args.command == "restore":
                artifact = _absolute_generated(args.archive, suffixes=("zip", "dbvz"))
                _no_source_dir_output(artifact, args.output_dir)
                restore_fn = restore_zip_archive if artifact.suffix == ".zip" else restore_zstd_archive
                result = restore_fn(artifact, args.output_dir)
            else:
                _absolute_generated(args.artifact, suffixes=("sqlite", "zip", "dbvz"))
                result = create_receipt(args.artifact, parent_receipt_name=args.parent_receipt_name)
        print(json.dumps({"ok": True, "command": args.command, "result": _redact_paths(result)},
                         ensure_ascii=False, sort_keys=True))
        return 0
    except (ArchiveError, _CLIError) as exc:
        code, message = exc.code, exc.message
    except (OSError, ValueError, TypeError):
        code, message = "OPERATION_FAILED", "The local operation failed safely."
    except Exception:
        # Never print a traceback containing the source path or copied customer data.
        code, message = "UNEXPECTED_FAILURE", "The local operation did not complete."
    print(json.dumps({"ok": False, "error": {"code": code, "message": message}}, sort_keys=True),
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
