"""Build a self-contained, synthetic-only DBVORA schema-map demo.

No customer DB inputs, HTTP service, extra dependency or durable backup writes.
The synthetic database lives only in an OS-managed temporary directory.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import re
from pathlib import Path
import sqlite3
import sys
import tempfile

from dbvora.export_html import HtmlExportError, export

_SENTINEL = "SYNTHETIC_ROW_CONTENT_MUST_NOT_APPEAR_IN_HTML"
_SAFE_FILENAME = re.compile(r"dbvora-map-[0-9a-f]{32}\.html\Z")
_SAFE_ERROR = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")


def create_synthetic_database(path: Path) -> None:
    """Generated test-only data with real FK/index schema and a row canary."""
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE departments (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                department_id INTEGER NOT NULL REFERENCES departments(id),
                display_name TEXT NOT NULL,
                hired_at TEXT
            );
            CREATE INDEX idx_employees_department ON employees(department_id);
        """)
        connection.execute("INSERT INTO departments VALUES (?, ?)", (1, "Synthetic division"))
        connection.execute("INSERT INTO employees VALUES (?, ?, ?, ?)", (42, 1, _SENTINEL, None))
        connection.commit()


def create_demo(output_directory: str | Path) -> dict:
    """Keep only new offline HTML in the selected existing folder, never the DB."""
    result = {
        "contract": "dbvora.synthetic-schema-demo.v1",
        "status": "FAIL_CLOSED",
        "scope": "SYNTHETIC_ONLY",
        "ready_for_customer_data": False,
        "production_backup_verified": False,
    }
    try:
        # export() independently validates the absolute existing output path,
        # checks path symlinks and creates an exclusive, unique HTML filename.
        with tempfile.TemporaryDirectory(prefix="dbvora-mvp-demo-") as temp:
            source = Path(temp) / "synthetic.sqlite"
            create_synthetic_database(source)
            exported = export(source, output_directory)
            name = exported.get("filename")
            if (exported.get("status") != "CREATED_OFFLINE_SCHEMA_HTML"
                    or exported.get("contains_table_rows") is not False
                    or type(name) is not str
                    or _SAFE_FILENAME.fullmatch(name) is None):
                raise HtmlExportError("EXPORT_RESULT_INVALID")
            # The exporter excludes table rows. Check a distinctive row canary
            # in generated HTML too, before reporting success to the operator.
            html = Path(output_directory) / name
            report_bytes = html.read_bytes()
            if _SENTINEL.encode("utf-8") in report_bytes:
                raise HtmlExportError("ROW_DATA_IN_REPORT")
            if (len(report_bytes) != exported["size_bytes"]
                    or hashlib.sha256(report_bytes).hexdigest() != exported["sha256"]):
                raise HtmlExportError("REPORT_DIGEST_MISMATCH")
            result.update({
                "status": "CREATED_SYNTHETIC_DEMO",
                "filename": name,
                "sha256": exported["sha256"],
                "size_bytes": exported["size_bytes"],
                "database_file_retained": False,
                "contains_table_rows": False,
            })
    except HtmlExportError as exc:
        result["error_code"] = (str(exc) if _SAFE_ERROR.fullmatch(str(exc))
                                else "SYNTHETIC_DEMO_FAILED")
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, UnicodeError):
        result["error_code"] = "SYNTHETIC_DEMO_FAILED"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a synthetic DBVORA HTML schema map (no network)")
    parser.add_argument("--out", required=True, help="Existing absolute output directory")
    parser.add_argument("--synthetic-only", action="store_true", required=True)
    args = parser.parse_args(argv)
    report = create_demo(args.out)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "CREATED_SYNTHETIC_DEMO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
