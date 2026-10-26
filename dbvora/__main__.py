"""No-dependency P0 inventory CLI: python -m dbvora inspect /abs/path/db.sqlite"""

import argparse
import json
import sys

from dbvora.errors import InventoryError
from dbvora.inventory import inspect_sqlite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DBVORA local read-only SQLite inventory")
    parser.add_argument("action", choices=["inspect"])
    parser.add_argument("db_path", help="Explicitly selected absolute local SQLite path")
    args = parser.parse_args(argv)
    try:
        result = inspect_sqlite(args.db_path)
    except InventoryError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
