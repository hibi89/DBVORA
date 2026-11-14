"""Explicit, local-only SQLite metadata observation command.

Run one record with --database ABSOLUTE.sqlite --ledger ABSOLUTE_LEDGER.sqlite --consent.
No scheduler or HTTP write endpoint is provided.
"""
import argparse
import json
import sys

from dbvora.connectors.sqlite_reader import validate_path
from dbvora.errors import InventoryError
from dbvora.inventory import inspect_sqlite
from dbvora.observation_ledger import (
    ObservationError, append_observation, validate_ledger_path,
)

SCOPE = "sqlite_main_file_excluding_wal_shm"


def _emit_error(code: str, message: str) -> int:
    print(json.dumps({"error": {"code": code, "message": message}},
                     ensure_ascii=False, sort_keys=True), file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record one explicitly authorized local SQLite size observation"
    )
    parser.add_argument("--database", required=True,
                        help="Absolute path to the explicitly selected local SQLite file")
    parser.add_argument("--ledger", required=True,
                        help="Absolute path to a separate local DBVORA observation ledger")
    parser.add_argument("--consent", action="store_true",
                        help="Confirm one local metadata observation is authorized")
    args = parser.parse_args(argv)

    if not args.consent:
        return _emit_error("CONSENT_REQUIRED",
                           "Pass --consent to authorize one local metadata observation.")
    try:
        source_path, _, _ = validate_path(args.database)
        metadata = inspect_sqlite(source_path)
        ledger_path = validate_ledger_path(args.ledger, source_path=source_path)
        result = append_observation(
            ledger_path, db_id=metadata["db_id"],
            observed_at=metadata["observed_at"],
            size_bytes=metadata["size_bytes"], scope=SCOPE, consent=True,
        )
    except InventoryError as exc:
        return _emit_error(exc.code, exc.message)
    except ObservationError:
        return _emit_error("OBSERVATION_REJECTED",
                           "The local ledger path, consent, or integrity check failed.")
    except OSError:
        return _emit_error("OBSERVATION_REJECTED",
                           "The selected local file is unavailable.")
    print(json.dumps({
        "contract": "dbvora.local-observation-write.v1",
        "status": result["status"],
        "db_id": metadata["db_id"],
        "observed_at": metadata["observed_at"],
        "size_bytes": metadata["size_bytes"],
        "scope": SCOPE,
        "record_hash": result["record_hash"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
