"""P0 SQLite topology MVP gate: real product code and disposable synthetic fixtures.

A pass does not certify Windows packaging, genuine file:// browser operation,
customer schema authorization, or archive power-loss durability.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time

from dbvora.workspace import inspect_workspace
from dbvora.workspace_html import export_workspace
from dbvora.workspace_observations import compare_growth, from_workspace, read_observation, write_observation

REQUIRED = (
    "multi_db_inventory", "fk_scoped",
    "cross_db_unverified", "read_only_inspection", "metadata_only",
    "baseline_roundtrip", "growth_two_observations", "dbstat_evidence",
    "multi_db_html", "multi_db_no_rows", "history_integrated", "exclusive_output",
    "offline_content_policy",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(a: Path, b: Path) -> None:
    with closing(sqlite3.connect(a)) as db:
        db.executescript("""
            CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE item_tags (id INTEGER PRIMARY KEY, item_id INTEGER REFERENCES items(id));
            CREATE INDEX idx_item_tags_item ON item_tags(item_id);
        """)
        db.execute("INSERT INTO items VALUES (1, 'PRIVATE_ROW_DO_NOT_EXPORT_A')")
        db.execute("INSERT INTO item_tags VALUES (2, 1)")
        db.commit()
    with closing(sqlite3.connect(b)) as db:
        db.executescript("""
            CREATE TABLE purchases (id INTEGER PRIMARY KEY, item_ref INTEGER, memo TEXT);
            CREATE INDEX idx_purchase_ref ON purchases(item_ref);
        """)
        db.execute("INSERT INTO purchases VALUES (3, 1, 'PRIVATE_ROW_DO_NOT_EXPORT_B')")
        db.commit()


def _run(temp: Path) -> dict:
    checks = {}
    dest = temp / "output"
    dest.mkdir()
    a, b = temp / "inventory.sqlite", temp / "orders.sqlite"
    _fixture(a, b)
    links = [{"from_db": 1, "from_table": "items", "from_column": "id",
              "to_db": 2, "to_table": "purchases", "to_column": "item_ref"}]
    unchanged = (_sha(a), _sha(b))
    workspace = inspect_workspace([a, b], declared_links=links)
    checks["multi_db_inventory"] = (workspace["database_count"] == 2
                                     and workspace["table_count"] == 3)
    checks["fk_scoped"] = (len(workspace["relationships"]) == 1
                           and workspace["relationships"][0]["target_in_inventory"] is True
                           and workspace["relationships"][0]["evidence"] == "declared_foreign_key")
    declared = workspace["declared_cross_database_links"]
    checks["cross_db_unverified"] = (len(declared) == 1 and declared[0]["verified"] is False
                                     and declared[0]["evidence"] == "user_declared_unverified"
                                     and workspace["cross_database_edges_verified"] == 0)
    checks["read_only_inspection"] = (_sha(a), _sha(b)) == unchanged
    serial = json.dumps(workspace, ensure_ascii=False)
    checks["metadata_only"] = (str(a) not in serial and str(b) not in serial
                                and "PRIVATE_ROW_DO_NOT_EXPORT" not in serial)

    initial = from_workspace(workspace)
    baseline_file = write_observation(dest, initial)
    before = read_observation(dest / baseline_file)
    checks["baseline_roundtrip"] = initial == before
    with closing(sqlite3.connect(b)) as db:
        db.executemany("INSERT INTO purchases (item_ref, memo) VALUES (?, ?)",
                       ((1, "SYNTHETIC_RECORD_" + str(i).zfill(4) + "X" * 800) for i in range(300)))
        db.commit()
    # Use real timestamps; do not fabricate a historical timestamp to create a delta.
    time.sleep(0.003)
    later = inspect_workspace([a, b], declared_links=links)
    compared = compare_growth(before, from_workspace(later))
    growth = compared[later["databases"][1]["db_id"]]
    checks["growth_two_observations"] = (growth["status"] == "measured"
                                         and growth["delta_main_file_bytes"] > 0
                                         and growth["trend"] == "two_observations_only_no_forecast")
    measured = [table.get("storage", {}) for db in later["databases"] for table in db["tables"]]
    checks["dbstat_evidence"] = (len(measured) == 3 and all(
        item.get("status") in ("measured", "unavailable") and
        (item.get("status") != "measured" or item.get("source") == "sqlite_dbstat_aggregate")
        for item in measured))
    exported = export_workspace([a, b], dest, declared_links=links, baseline=before)
    path = dest / exported["filename"]
    data = path.read_bytes()
    checks["multi_db_html"] = (exported["status"] == "CREATED_WORKSPACE_HTML"
                                and _sha(path) == exported["sha256"]
                                and exported["declared_cross_database_count"] == 1)
    checks["multi_db_no_rows"] = (b"PRIVATE_ROW_DO_NOT_EXPORT" not in data
                                   and b"SYNTHETIC_RECORD_" not in data)
    checks["history_integrated"] = (exported["growth_comparison"] == "two_observations"
                                     and b"delta_main_file_bytes" in data)
    previous = _sha(path)
    new = export_workspace([a, b], dest, declared_links=links)
    checks["exclusive_output"] = (new["filename"] != exported["filename"]
                                   and _sha(path) == previous)
    checks["offline_content_policy"] = (b"connect-src 'none'" in data
                                        and b"Content-Security-Policy" in data
                                        and exported["ready_for_customer_data"] is False)
    return checks


def verify() -> dict:
    report = {"contract": "dbvora.mvp-offline-check.v1", "status": "FAIL_CLOSED",
              "scope": "OS_TEMP_SYNTHETIC_ONLY", "ready_for_customer_data": False,
              "windows_file_browser_verified": False, "windows_archive_durability_verified": False,
              "full_release_gate_verified": False, "required_check_count": len(REQUIRED),
              "passed_check_count": 0, "checks": {name: "NOT_RUN" for name in REQUIRED}}
    try:
        with tempfile.TemporaryDirectory(prefix="dbvora-mvp-integrated-") as directory:
            result = _run(Path(directory))
        for name in REQUIRED:
            report["checks"][name] = "PASS" if result.get(name) is True else "FAIL"
        report["passed_check_count"] = sum(x == "PASS" for x in report["checks"].values())
        if report["passed_check_count"] == len(REQUIRED):
            report["status"] = "PASS_SYNTHETIC_P0_ONLY"
        else:
            report["error_code"] = "MVP_INTEGRITY_FAILED"
    except Exception:
        # Do not disclose real user paths, identifiers, SQL contents or stack traces.
        report["error_code"] = "SYNTHETIC_MVP_CHECK_FAILED"
    return report


def main() -> int:
    outcome = verify()
    print(json.dumps(outcome, sort_keys=True))
    return 0 if outcome["status"] == "PASS_SYNTHETIC_P0_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
