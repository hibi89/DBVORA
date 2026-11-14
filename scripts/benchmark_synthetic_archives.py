"""Repeatable observed synthetic-only comparison: two ZIP vs CAS generations.

No customer data, network, cost comparison to cloud providers, or universal
compression claim. Both independent restores are verified byte-for-byte.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

from dbvora.archive.incremental_cas import create_incremental, restore_incremental
from dbvora.archive.compressed_cas import create_compressed, restore_compressed
from dbvora.archive.safe_zip import (
    create_snapshot, make_zip_archive, restore_zip_archive,
)
from tests.fixtures.make_sqlite import create_fixture

STATUS = "PASS_SYNTHETIC_STORAGE_COMPARISON_ONLY"


def verify():
    report = {
        "contract": "dbvora.synthetic-size-two-generation.v1",
        "status": "FAIL_CLOSED", "checks": 0,
        "same_synthetic_workload": False, "both_generations_restored": False,
        "second_generation_reused_blocks": False,
        "compressed_generations_restored": False,
        "compressed_second_reused_blocks": False,
        "source_unchanged_during_archiving": False,
        "no_universal_compression_claim": True,
        "customer_data": False, "ready_for_customer_data": False,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="dbvora-two-gen-benchmark-") as root:
            base = Path(root)
            db = create_fixture(base / "synthetic.sqlite")
            # Invented stable 4KiB blobs make both archive strategies operate
            # on the SAME actual SQLite snapshots (not arbitrary unrelated files).
            # Binary bytes must never be printed or uploaded.
            with closing(sqlite3.connect(db)) as conn:
                conn.executemany(
                    "INSERT INTO events(id,category,content) VALUES (?, ?, ?)",
                    ((i, "synthetic", hashlib.sha256(str(i).encode()).digest() * 128)
                     for i in range(3, 203)),
                )
                conn.commit()
            names = ("snapshots", "zip", "chunks", "manifests", "cas_restore", "zip_restore",
                     "compressed_chunks", "compressed_manifests", "compressed_restore")
            folders = {name: base / name for name in names}
            for folder in folders.values():
                folder.mkdir()
            first = Path(create_snapshot(db, folders["snapshots"])["snapshot_path"])
            first_sha = hashlib.sha256(first.read_bytes()).hexdigest()
            report["checks"] += 1

            with closing(sqlite3.connect(db)) as conn:
                conn.execute("UPDATE events SET content=? WHERE id=100",
                             (b"SECOND_GENERATION_CHANGED_SYNTHETIC_BYTE" * 100,))
                conn.commit()
            second = Path(create_snapshot(db, folders["snapshots"])["snapshot_path"])
            second_sha = hashlib.sha256(second.read_bytes()).hexdigest()
            if first_sha == second_sha:
                raise ValueError("NO_SNAPSHOT_DELTA")
            report["checks"] += 1
            last_source_sha = hashlib.sha256(db.read_bytes()).hexdigest()
            last_source_mtime = db.stat().st_mtime_ns

            z1 = make_zip_archive(first, folders["zip"])
            z2 = make_zip_archive(second, folders["zip"])
            if (z1["snapshot_sha256"] != first_sha
                    or z2["snapshot_sha256"] != second_sha):
                raise ValueError("ZIP_SNAPSHOT_MISMATCH")
            report["checks"] += 1

            c1 = create_incremental(first, folders["chunks"], folders["manifests"],
                                    synthetic_only=True, accept_plaintext=True)
            c2 = create_incremental(second, folders["chunks"], folders["manifests"],
                                    synthetic_only=True, accept_plaintext=True)
            if (c1["snapshot_sha256"] != first_sha
                    or c2["snapshot_sha256"] != second_sha
                    or c1["new_chunks"] < 1 or c2["reused_chunks"] < 1):
                raise ValueError("NO_REAL_INCREMENTAL_REUSE")
            report["second_generation_reused_blocks"] = True
            report["checks"] += 1

            compressed_first = create_compressed(
                first, folders["compressed_chunks"], folders["compressed_manifests"],
                synthetic_only=True, accept_plaintext=True)
            compressed_second = create_compressed(
                second, folders["compressed_chunks"], folders["compressed_manifests"],
                synthetic_only=True, accept_plaintext=True)
            if (compressed_first["snapshot_sha256"] != first_sha
                    or compressed_second["snapshot_sha256"] != second_sha
                    or compressed_second["reused_chunks"] < 1):
                raise ValueError("COMPRESSED_REUSE_FAILED")
            report["compressed_second_reused_blocks"] = True
            report["checks"] += 1

            for pair in ((z1, first_sha), (z2, second_sha)):
                restored = restore_zip_archive(
                    pair[0]["archive_path"], folders["zip_restore"]
                )
                file = Path(restored["restored_path"])
                if hashlib.sha256(file.read_bytes()).hexdigest() != pair[1]:
                    raise ValueError("ZIP_CONTENT_MISMATCH")
            report["checks"] += 1

            for pair in ((c1, first_sha), (c2, second_sha)):
                restored = restore_incremental(
                    folders["manifests"] / pair[0]["manifest_name"],
                    folders["chunks"], folders["cas_restore"],
                    synthetic_only=True, accept_plaintext=True,
                )
                file = folders["cas_restore"] / restored["restored_name"]
                if hashlib.sha256(file.read_bytes()).hexdigest() != pair[1]:
                    raise ValueError("CAS_CONTENT_MISMATCH")
            report["both_generations_restored"] = True
            report["checks"] += 1

            for pair in ((compressed_first, first_sha), (compressed_second, second_sha)):
                restored = restore_compressed(
                    folders["compressed_manifests"] / pair[0]["manifest_name"],
                    folders["compressed_chunks"], folders["compressed_restore"],
                    synthetic_only=True, accept_plaintext=True)
                file = folders["compressed_restore"] / restored["restored_name"]
                if hashlib.sha256(file.read_bytes()).hexdigest() != pair[1]:
                    raise ValueError("COMPRESSED_CAS_RESTORE_FAILED")
            report["compressed_generations_restored"] = True
            report["checks"] += 1

            if (hashlib.sha256(db.read_bytes()).hexdigest() != last_source_sha
                    or db.stat().st_mtime_ns != last_source_mtime):
                raise ValueError("SOURCE_CHANGED_DURING_ARCHIVE")
            report["source_unchanged_during_archiving"] = True
            report["checks"] += 1

            # Count *actual* on-disk bytes (not virtual or advertised rates).
            zip_bytes = sum(p.stat().st_size for p in folders["zip"].glob("*.zip"))
            cas_chunk_bytes = sum(p.stat().st_size for p in folders["chunks"].glob("*.chunk"))
            cas_manifest_bytes = sum(p.stat().st_size for p in folders["manifests"].glob("*.json"))
            compressed_chunk_bytes = sum(p.stat().st_size for p in
                                         folders["compressed_chunks"].glob("*.cz"))
            compressed_manifest_bytes = sum(p.stat().st_size for p in
                                            folders["compressed_manifests"].glob("*.json"))
            if (zip_bytes <= 0 or cas_chunk_bytes <= 0 or cas_manifest_bytes <= 0
                    or compressed_chunk_bytes <= 0 or compressed_manifest_bytes <= 0
                    or c2["new_stored_bytes"] > c2["source_bytes"]
                    or compressed_second["new_compressed_bytes"] > compressed_second["source_bytes"]):
                raise ValueError("INVALID_OBSERVED_SIZES")
            report["checks"] += 1
            report["metrics"] = {
                "first_snapshot_bytes": first.stat().st_size,
                "second_snapshot_bytes": second.stat().st_size,
                "two_zip_archives_bytes": zip_bytes,
                "cas_chunk_files_bytes": cas_chunk_bytes,
                "cas_manifest_files_bytes": cas_manifest_bytes,
                "cas_total_stored_bytes": cas_chunk_bytes + cas_manifest_bytes,
                "cas_second_new_content_bytes": c2["new_stored_bytes"],
                "cas_second_reused_chunks": c2["reused_chunks"],
                "cas_second_new_chunks": c2["new_chunks"],
                "cas_minus_zip_bytes": cas_chunk_bytes + cas_manifest_bytes - zip_bytes,
                "compressed_cas_chunks_bytes": compressed_chunk_bytes,
                "compressed_cas_manifests_bytes": compressed_manifest_bytes,
                "compressed_cas_total_stored_bytes": compressed_chunk_bytes + compressed_manifest_bytes,
                "compressed_cas_minus_zip_bytes": (
                    compressed_chunk_bytes + compressed_manifest_bytes - zip_bytes),
                "compressed_cas_second_reused_chunks": compressed_second["reused_chunks"],
                "compressed_cas_second_new_chunks": compressed_second["new_chunks"],
                "compressed_cas_second_new_bytes": compressed_second["new_compressed_bytes"],
            }
            report["same_synthetic_workload"] = True
            report["checks"] += 1
            report["status"] = STATUS
    except Exception:
        # Suppress all input paths, private SQL or file data from failures.
        report["error_code"] = "SYNTHETIC_SIZE_COMPARISON_FAILED"
    return report


def main():
    result = verify()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
