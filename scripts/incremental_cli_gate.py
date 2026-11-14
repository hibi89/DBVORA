"""Real subprocess acceptance of synthetic incremental archive CLI on this OS.

No customer data or network; no scheduled background execution, deletion or
assertion of power-cut durability. Output only bounded boolean/status evidence.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from dbvora.archive.safe_zip import create_snapshot
from tests.fixtures.make_sqlite import create_fixture

CANARY = "NOT_FOR_SCHEMA_OUTPUT"
STATUS = "PASS_SYNTHETIC_INCREMENTAL_CLI_ONLY"


def run():
    report = {"contract": "dbvora.synthetic.incremental-cli-gate.v1",
              "status": "FAIL_CLOSED", "checks": 0,
              "source_unchanged": False, "independent_restore_verified": False,
              "second_generation_reused_chunks": False,
              "tampered_chunk_rejected": False,
              "compressed_independent_restore_verified": False,
              "compressed_second_generation_reused_chunks": False,
              "compressed_tamper_rejected": False,
              "format_mismatch_rejected": False, "customer_ready": False,
              "power_loss_verified": False, "automatic_deletion": False}
    try:
        with tempfile.TemporaryDirectory(prefix="dbvora-cas-e2e-") as root:
            base = Path(root)
            source = create_fixture(base / "source.sqlite")
            original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            original_mtime = source.stat().st_mtime_ns
            folders = [base / name for name in ("snap", "chunks", "manifests", "restores",
                                                   "zlib_chunks", "zlib_manifests", "zlib_restores")]
            for folder in folders:
                folder.mkdir()
            snap = Path(create_snapshot(source, folders[0])["snapshot_path"])
            report["checks"] += 1
            def call(*items, success=True):
                command = [sys.executable, "-m", "dbvora.incremental_cli", *map(str, items)]
                child = subprocess.run(command, capture_output=True, text=True,
                                       encoding="utf-8", timeout=75, check=False,
                                       stdin=subprocess.DEVNULL)
                data = json.loads(child.stdout if success else child.stderr)
                if child.returncode != (0 if success else 2):
                    raise ValueError("WRONG_EXIT_CODE")
                if data.get("ok") is not success or CANARY in str(data) or str(base) in str(data):
                    raise ValueError("SECRET_OR_PATH_LEAK")
                return data
            args = ("--snapshot", snap, "--chunk-dir", folders[1],
                    "--manifest-dir", folders[2], "--synthetic-only", "--accept-plaintext")
            one = call("create", *args)["result"]
            if (one.get("status") != "PUBLISHED_INCREMENTAL_SYNTHETIC_ONLY"
                    or one.get("new_chunks", 0) < 1
                    or one["reused_chunks"] != 0
                    or one["ready_for_customer_data"] is not False):
                raise ValueError("FIRST_GENERATION_FAILED")
            report["checks"] += 1
            two = call("create", *args)["result"]
            if (two["new_chunks"] != 0 or two["reused_chunks"] != one["chunks"]
                    or two["manifest_name"] == one["manifest_name"]):
                raise ValueError("REUSE_FAILED")
            report["second_generation_reused_chunks"] = True
            report["checks"] += 1
            restored = call("restore", "--manifest", folders[2] / two["manifest_name"],
                            "--chunk-dir", folders[1], "--output-dir", folders[3],
                            "--synthetic-only", "--accept-plaintext")["result"]
            recreated = folders[3] / restored["restored_name"]
            if (restored["status"] != "RESTORED_INCREMENTAL_SYNTHETIC_ONLY"
                    or restored["restored_sha256"] != hashlib.sha256(recreated.read_bytes()).hexdigest()
                    or restored["restored_sha256"] != two["snapshot_sha256"]):
                raise ValueError("INDEPENDENT_RESTORE_FAILED")
            report["independent_restore_verified"] = True
            report["checks"] += 1
            missing_ack = call("create", "--snapshot", snap, "--chunk-dir", folders[1],
                               "--manifest-dir", folders[2], success=False)
            if missing_ack.get("error", {}).get("code") != "SYNTHETIC_ONLY_REQUIRED":
                raise ValueError("ACK_GUARD_FAILED")
            report["checks"] += 1
            manifest = json.loads((folders[2] / two["manifest_name"]).read_text(encoding="utf-8"))
            chunk = folders[1] / (manifest["chunks"][0] + ".chunk")
            chunk.write_bytes(b"tampered-synthetic-chunk")
            failed = call("restore", "--manifest", folders[2] / one["manifest_name"],
                          "--chunk-dir", folders[1], "--output-dir", folders[3],
                          "--synthetic-only", "--accept-plaintext", success=False)
            if (failed.get("error", {}).get("code") not in
                    ("CHUNK_CORRUPT", "UNSAFE_CHUNK", "CHUNK_UNAVAILABLE")
                    or len(list(folders[3].glob("dbvora-*.sqlite"))) != 1):
                raise ValueError("TAMPER_NOT_REJECTED")
            report["tampered_chunk_rejected"] = True
            report["checks"] += 1

            # A separate explicit format flag is required: never silently
            # reinterpret existing raw v1 manifest/chunk files as zlib v2.
            zargs = ("--format", "zlib", "--snapshot", snap,
                     "--chunk-dir", folders[4], "--manifest-dir", folders[5],
                     "--synthetic-only", "--accept-plaintext")
            zfirst = call("create", *zargs)["result"]
            if (zfirst["status"] != "PUBLISHED_COMPRESSED_SYNTHETIC_ONLY"
                    or zfirst["new_chunks"] < 1 or zfirst["ready_for_customer_data"] is not False):
                raise ValueError("COMPRESSED_FIRST_FAILED")
            report["checks"] += 1
            zsecond = call("create", *zargs)["result"]
            if (zsecond["new_chunks"] != 0
                    or zsecond["reused_chunks"] != zfirst["chunks"]
                    or zsecond["manifest_name"] == zfirst["manifest_name"]):
                raise ValueError("COMPRESSED_REUSE_FAILED")
            report["compressed_second_generation_reused_chunks"] = True
            report["checks"] += 1
            zrestore_args = ("--format", "zlib", "--manifest",
                             folders[5] / zsecond["manifest_name"],
                             "--chunk-dir", folders[4], "--output-dir", folders[6],
                             "--synthetic-only", "--accept-plaintext")
            zrestored = call("restore", *zrestore_args)["result"]
            zfile = folders[6] / zrestored["restored_name"]
            if (zrestored["status"] != "RESTORED_COMPRESSED_SYNTHETIC_ONLY"
                    or zrestored["restored_sha256"] != hashlib.sha256(zfile.read_bytes()).hexdigest()
                    or zrestored["restored_sha256"] != zsecond["snapshot_sha256"]):
                raise ValueError("COMPRESSED_RESTORE_FAILED")
            report["compressed_independent_restore_verified"] = True
            report["checks"] += 1
            mismatch = call("restore", "--manifest", folders[5] / zfirst["manifest_name"],
                            "--chunk-dir", folders[4], "--output-dir", folders[6],
                            "--synthetic-only", "--accept-plaintext", success=False)
            if mismatch.get("error", {}).get("code") != "INVALID_MANIFEST":
                raise ValueError("CROSS_FORMAT_NOT_REFUSED")
            report["format_mismatch_rejected"] = True
            report["checks"] += 1
            zmanifest = json.loads(
                (folders[5] / zsecond["manifest_name"]).read_text(encoding="utf-8"))
            zchunk = folders[4] / (zmanifest["chunks"][0] + ".cz")
            zchunk.write_bytes(b"tampered-only-in-disposable-test")
            zfailure = call("restore", *zrestore_args, success=False)
            if (zfailure.get("error", {}).get("code") not in
                    ("INVALID_CHUNK_FILE", "INVALID_CHUNK_MAGIC", "CHUNK_UNAVAILABLE")
                    or len(list(folders[6].glob("dbvora-*.sqlite"))) != 1):
                raise ValueError("COMPRESSED_TAMPER_NOT_REFUSED")
            report["compressed_tamper_rejected"] = True
            report["checks"] += 1

            if (hashlib.sha256(source.read_bytes()).hexdigest() != original_hash
                    or source.stat().st_mtime_ns != original_mtime):
                raise ValueError("ORIGINAL_MODIFIED")
            report["source_unchanged"] = True
            report["checks"] += 1
            report["status"] = STATUS
    except Exception:
        # Even exceptions from subprocess can include paths; suppress them.
        report["error_code"] = "INCREMENTAL_CLI_GATE_FAILED"
    return report


def main():
    result = run()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
