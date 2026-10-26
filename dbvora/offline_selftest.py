"""Run a zero-customer-data smoke check of the standalone schema HTML export.

Creates and removes a synthetic SQLite database under the OS temporary
folder. It does not use supplied database paths, network, or backup archives.
Successful output is not Windows durability or customer-release certification.
"""
from __future__ import annotations

import base64
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile

from dbvora.export_html import export

CANARY = "ROW_SENTINEL_DO_NOT_EXPORT"
_FILENAME = re.compile(r"dbvora-map-[0-9a-f]{32}\.html\Z")
_ENCODED = re.compile(rb'const localSchemaBase64 = "([A-Za-z0-9+/=]+)";')
_EXPECTED_CHECKS = 9


def verify() -> dict:
    """Validate one real generated HTML report against synthetic local data."""
    report = {
        "contract": "dbvora.offline-html-synthetic-check.v1",
        "status": "FAIL_CLOSED",
        "checks_passed": 0,
        "expected_checks": _EXPECTED_CHECKS,
        "ready_for_customer_data": False,
        "windows_ntfs_durability_verified": False,
        "native_file_browser_verified": False,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="dbvora-offline-selftest-") as folder:
            root = Path(folder)
            source = root / "synthetic.sqlite"
            with closing(sqlite3.connect(source)) as conn:
                conn.executescript("""
                    PRAGMA foreign_keys=ON;
                    CREATE TABLE demo_parents (id INTEGER PRIMARY KEY, label TEXT);
                    CREATE TABLE demo_children (
                        id INTEGER PRIMARY KEY,
                        parent_id INTEGER REFERENCES demo_parents(id)
                    );
                    INSERT INTO demo_parents VALUES (1, 'ROW_SENTINEL_DO_NOT_EXPORT');
                    INSERT INTO demo_children VALUES (2, 1);
                """)
            original_sha = hashlib.sha256(source.read_bytes()).hexdigest()
            original_mtime = source.stat().st_mtime_ns

            produced = export(source, root)
            name = produced.get("filename")
            if not isinstance(name, str) or not _FILENAME.fullmatch(name):
                raise ValueError("Unexpected generated filename")
            html = (root / name).read_bytes()
            matching = _ENCODED.search(html)
            metadata = (json.loads(base64.b64decode(matching.group(1), validate=True))
                        if matching else None)
            table_names = {t["name"] for t in metadata["tables"]} if isinstance(metadata, dict) else set()
            links = metadata.get("relationships", []) if isinstance(metadata, dict) else []
            checks = (
                produced.get("status") == "CREATED_OFFLINE_SCHEMA_HTML",
                produced.get("ready_for_customer_data") is False and produced.get("contains_table_rows") is False,
                hashlib.sha256(html).hexdigest() == produced.get("sha256") and len(html) == produced.get("size_bytes"),
                b'http-equiv="Content-Security-Policy"' in html and b"connect-src 'none'" in html,
                b'src="/assets/app.js"' not in html and b'href="/assets/style.css"' not in html,
                CANARY.encode("utf-8") not in html,
                str(source).encode("utf-8") not in html,
                table_names == {"demo_parents", "demo_children"}
                    and len(links) == 1 and links[0].get("evidence") == "declared_foreign_key",
                hashlib.sha256(source.read_bytes()).hexdigest() == original_sha
                    and source.stat().st_mtime_ns == original_mtime,
            )
            report["checks_passed"] = sum(checks)
            if all(checks):
                report["status"] = "PASS_SYNTHETIC_OFFLINE_HTML_ONLY"
            else:
                report["error_code"] = "INTEGRITY_CHECK_FAILED"
    except Exception:
        # No exception text, customer paths or source bytes in output.
        report["error_code"] = "SYNTHETIC_CHECK_FAILED"
    return report


def main() -> int:
    result = verify()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS_SYNTHETIC_OFFLINE_HTML_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
