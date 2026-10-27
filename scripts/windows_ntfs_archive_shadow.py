"""Research-only SQLite -> ZIP -> restore exercise in private OS temp storage.

Never accepts a customer path, never changes the real archive engine, and never
claims NTFS namespace persistence or physical power-loss durability.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys
import tempfile
import uuid
import zipfile
from urllib.parse import quote

from dbvora.archive.windows_ntfs_publish import (
    WinPublishError, _commit_synthetic_staged, _file_digest, _windows_temp_filesystem,
)

_MAX_SNAPSHOT = 8 * 1024 * 1024
_ROWS = tuple((index, "value-" + str(index % 7)) for index in range(48))


class ShadowError(Exception):
    """Stable, non-sensitive error code for this synthetic-only experiment."""


def _rows(connection: sqlite3.Connection) -> tuple:
    return tuple(connection.execute("SELECT id, val FROM fixture ORDER BY id"))


def _check_sqlite(path: Path) -> tuple:
    with closing(sqlite3.connect("file:" + quote(path.as_posix(), safe="/:") + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ShadowError("SQLITE_INTEGRITY_FAILED")
        return _rows(db)


def _stage(root: Path) -> Path:
    return root / (".dbvora-stage-" + uuid.uuid4().hex + ".part")


def _target(root: Path) -> Path:
    return root / ("dbvora-" + uuid.uuid4().hex + ".bin")


def _verify_zip(archive: Path, snapshot_sha: str, root: Path) -> None:
    """Bound and independently restore our two fixed ZIP entries, never arbitrary names."""
    try:
        with zipfile.ZipFile(archive, "r") as file:
            entries = file.infolist()
            if len(entries) != 2 or sorted(x.filename for x in entries) != ["manifest.json", "snapshot.sqlite"]:
                raise ShadowError("ZIP_ENTRIES_INVALID")
            if any(x.file_size > _MAX_SNAPSHOT or x.is_dir() for x in entries):
                raise ShadowError("ZIP_SIZE_INVALID")
            manifest = json.loads(file.read("manifest.json"))
            if (not isinstance(manifest, dict) or manifest.get("format") != "dbvora-synthetic-zip-v1"
                    or manifest.get("snapshot_sha256") != snapshot_sha
                    or type(manifest.get("snapshot_size_bytes")) is not int
                    or not 100 <= manifest["snapshot_size_bytes"] <= _MAX_SNAPSHOT):
                raise ShadowError("ZIP_MANIFEST_INVALID")
            contents = file.read("snapshot.sqlite")
            if (len(contents) != manifest["snapshot_size_bytes"]
                    or len(contents) > _MAX_SNAPSHOT
                    or hashlib.sha256(contents).hexdigest() != snapshot_sha):
                raise ShadowError("ZIP_RESTORE_MISMATCH")
        restored = root / ("restored-" + uuid.uuid4().hex + ".sqlite")
        with restored.open("xb") as sink:
            sink.write(contents)
            sink.flush()
            os.fsync(sink.fileno())
        if _check_sqlite(restored) != _ROWS:
            raise ShadowError("RESTORED_SQLITE_ROWS_DIFFER")
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError, KeyError, ValueError):
        raise ShadowError("ZIP_INVALID") from None


def _exercise_shadow(move=None) -> dict:
    """Internal test seam; no supplied filesystem paths and no customer data."""
    with tempfile.TemporaryDirectory(prefix="dbvora-win32-synthetic-") as temp:
        root = Path(temp)
        source = root / "source-only-synthetic.sqlite"
        with closing(sqlite3.connect(source)) as database:
            database.execute("PRAGMA journal_mode=WAL")
            database.execute("CREATE TABLE fixture (id INTEGER PRIMARY KEY, val TEXT NOT NULL)")
            database.executemany("INSERT INTO fixture (id, val) VALUES (?, ?)", _ROWS)
            database.commit()
            snapshot_stage = _stage(root)
            with closing(sqlite3.connect(snapshot_stage)) as destination:
                database.backup(destination)
        # Source closes/checkpoints WAL before baseline; all later steps read only.
        source_original_sha = _file_digest(source)
        if _check_sqlite(snapshot_stage) != _ROWS:
            raise ShadowError("BACKUP_ROWS_DIFFER")
        size = snapshot_stage.stat().st_size
        if not 100 <= size <= _MAX_SNAPSHOT:
            raise ShadowError("SNAPSHOT_SIZE_INVALID")
        snapshot_sha = _file_digest(snapshot_stage)
        snapshot_target = _target(root)
        _commit_synthetic_staged(root, snapshot_stage, snapshot_target, move=move)
        if _check_sqlite(snapshot_target) != _ROWS or _file_digest(snapshot_target) != snapshot_sha:
            raise ShadowError("SNAPSHOT_PUBLISH_MISMATCH")
        zip_stage = _stage(root)
        manifest = {"format": "dbvora-synthetic-zip-v1", "snapshot_sha256": snapshot_sha,
                    "snapshot_size_bytes": size}
        with zipfile.ZipFile(zip_stage, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True))
            archive.write(snapshot_target, arcname="snapshot.sqlite")
        _verify_zip(zip_stage, snapshot_sha, root)
        zip_target = _target(root)
        published_sha = _commit_synthetic_staged(root, zip_stage, zip_target, move=move)
        if _file_digest(zip_target) != published_sha:
            raise ShadowError("ZIP_PUBLISH_MISMATCH")
        _verify_zip(zip_target, snapshot_sha, root)
        if _file_digest(source) != source_original_sha or _check_sqlite(source) != _ROWS:
            raise ShadowError("SOURCE_CHANGED")
        return {"snapshot_sha256_verified": True, "independent_zip_restore_verified": True,
                "source_unchanged": True, "content_verified_only": True,
                "steps_passed": 7}


def run_probe(*, platform_name=None, python_version=None, filesystem=None, move=None) -> dict:
    """Simulated arguments are for tests only and never yield native certification."""
    native = (os.name == "nt" and platform_name is None and python_version is None
              and filesystem is None and move is None)
    report = {"contract": "dbvora.ntfs-archive-shadow.v1", "scope": "OS_TEMP_SYNTHETIC_ONLY",
              "status": "BLOCKED_UNVERIFIED", "native_windows_tested": False,
              "ready_for_customer_data": False, "power_loss_durable_verified": False,
              "directory_metadata_durable_verified": False, "production_archive_integrated": False}
    system = platform.system() if platform_name is None else platform_name
    version = tuple(sys.version_info[:2]) if python_version is None else tuple(python_version)
    volume = _windows_temp_filesystem() if filesystem is None else filesystem
    if system != "Windows":
        report["reason"] = "WINDOWS_REQUIRED"
    elif version != (3, 11):
        report["reason"] = "PYTHON311_REQUIRED"
    elif volume != "NTFS":
        report["reason"] = "NTFS_TEMP_REQUIRED"
    else:
        try:
            report.update(_exercise_shadow(move=move))
        except (WinPublishError, ShadowError) as exc:
            report["reason"] = str(exc)
        except (OSError, sqlite3.Error, zipfile.LargeZipFile):
            report["reason"] = "SYNTHETIC_IO_FAILED"
        else:
            report["native_windows_tested"] = native
            report["status"] = "PASS_WINDOWS_NTFS_SYNTHETIC_ONLY" if native else "PASS_SIMULATED_ONLY"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generated temporary SQLite / ZIP only")
    parser.add_argument("--synthetic-only", action="store_true", required=True)
    parser.parse_args(argv)
    result = run_probe()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS_WINDOWS_NTFS_SYNTHETIC_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
