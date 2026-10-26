"""P1-C4: separate, immutable, unsigned completion evidence for local archives.

Receipts prove a verification was recorded (given trust in the current directory),
not the identity of the writer, actual power-loss durability, or authenticity.
Never touch customer databases or modify published artifact files.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from dbvora.archive.safe_zip import (
    ArchiveError, _directory, _staging_file, _sync_staged_file,
    _sync_directory,
)
from dbvora.archive.recovery_catalog import PUBLISHED, _snapshot_metadata, _verify_one

RECEIPT = re.compile(r"^dbvora-receipt-([a-f0-9]{32})\.json$")
HEX_SHA = re.compile(r"^[a-f0-9]{64}$")
MAX_RECEIPT_BYTES = 4096
MAX_CHAIN_DEPTH = 12
FORMAT = "dbvora-receipt-v1"
FIELDS = frozenset({
    "format", "artifact_name", "artifact_kind", "artifact_sha256",
    "snapshot_sha256", "verified_at_utc", "provenance",
    "parent_receipt_name", "parent_receipt_sha256",
})


def _receipt_name(artifact_name: str) -> str:
    match = PUBLISHED.fullmatch(artifact_name)
    if not match:
        raise ArchiveError("INVALID_ARTIFACT", "An exact DBVORA artifact basename is required.")
    return "dbvora-receipt-" + artifact_name[7:39] + ".json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_file(directory: Path, name: str) -> tuple[dict, str]:
    if not RECEIPT.fullmatch(name):
        raise ArchiveError("BAD_RECEIPT", "Receipt filename is invalid.")
    path = directory / name
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not (1 <= info.st_size <= MAX_RECEIPT_BYTES):
            raise ArchiveError("BAD_RECEIPT", "Receipt is not a standalone bounded file.")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (
                    info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns):
                raise ArchiveError("RECEIPT_RACE", "Receipt changed during inspection.")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                payload = stream.read(MAX_RECEIPT_BYTES + 1)
            after = os.fstat(fd)
        finally:
            os.close(fd)
        reread = path.lstat()
        identity = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if (len(payload) != info.st_size or
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) != identity or
                (reread.st_dev, reread.st_ino, reread.st_size, reread.st_mtime_ns, reread.st_ctime_ns) != identity):
            raise ArchiveError("RECEIPT_RACE", "Receipt changed during inspection.")
        record = json.loads(payload.decode("utf-8"))
        if not isinstance(record, dict) or set(record) != FIELDS:
            raise ArchiveError("BAD_RECEIPT", "Receipt contract is invalid.")
        if (record["format"] != FORMAT or record["provenance"] != "unsigned_local_observation" or
                type(record["artifact_name"]) is not str or
                _receipt_name(record["artifact_name"]) != name or
                record["artifact_kind"] != PUBLISHED.fullmatch(record["artifact_name"]).group(1) or
                any(type(record[key]) is not str or not HEX_SHA.fullmatch(record[key])
                    for key in ("artifact_sha256", "snapshot_sha256")) or
                type(record["verified_at_utc"]) is not str or len(record["verified_at_utc"]) > 48 or
                (record["parent_receipt_name"] is None) != (record["parent_receipt_sha256"] is None)):
            raise ArchiveError("BAD_RECEIPT", "Receipt fields are invalid.")
        stamp = datetime.fromisoformat(record["verified_at_utc"])
        if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
            raise ArchiveError("BAD_RECEIPT", "UTC receipt timestamp is required.")
        if record["parent_receipt_name"] is not None:
            if (type(record["parent_receipt_name"]) is not str or
                    not RECEIPT.fullmatch(record["parent_receipt_name"]) or
                    type(record["parent_receipt_sha256"]) is not str or
                    not HEX_SHA.fullmatch(record["parent_receipt_sha256"])):
                raise ArchiveError("BAD_RECEIPT", "Parent receipt reference is invalid.")
        return record, _sha(payload)
    except FileNotFoundError:
        raise ArchiveError("MISSING_RECEIPT", "The independent completion receipt is missing.") from None
    except ArchiveError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError, KeyError):
        raise ArchiveError("BAD_RECEIPT", "The receipt could not be independently verified.") from None


def _validate_chain(directory: Path, name: str, expected_sha: str | None = None,
                    seen: frozenset[str] = frozenset()) -> dict:
    if name in seen or len(seen) >= MAX_CHAIN_DEPTH:
        raise ArchiveError("LINEAGE_CYCLE", "Receipt lineage contains a cycle or is too deep.")
    record, digest = _read_file(directory, name)
    if expected_sha is not None and digest != expected_sha:
        raise ArchiveError("LINEAGE_MISMATCH", "Parent receipt checksum does not match.")
    artifact_name = record["artifact_name"]
    artifact = directory / artifact_name
    try:
        before = _snapshot_metadata(artifact)
        verified = _verify_one(artifact, record["artifact_kind"], directory)
        after = _snapshot_metadata(artifact)
    except ArchiveError:
        raise
    except OSError:
        raise ArchiveError("ARTIFACT_MISSING", "Referenced artifact could not be inspected.") from None
    if before != after:
        raise ArchiveError("RACE_DETECTED", "Referenced artifact changed during independent restore.")
    if (verified["artifact_sha256"] != record["artifact_sha256"] or
            verified["snapshot_sha256"] != record["snapshot_sha256"]):
        raise ArchiveError("ARTIFACT_MISMATCH", "Receipt and independently restored archive differ.")
    if record["parent_receipt_name"] is not None:
        _validate_chain(directory, record["parent_receipt_name"],
                        record["parent_receipt_sha256"], seen | {name})
    # Verify the receipt still has identical immutable bytes after slower SQLite restore.
    _, final_sha = _read_file(directory, name)
    if final_sha != digest:
        raise ArchiveError("RECEIPT_RACE", "Receipt was changed during lineage inspection.")
    return {"receipt_name": name, "receipt_sha256": digest,
            "artifact_name": artifact_name,
            "snapshot_sha256": record["snapshot_sha256"],
            "status": "RECEIPT_AND_CONTENT_VERIFIED_UNSIGNED",
            "durability": "unproven_after_power_failure",
            "authentication": "unsigned_untrusted"}


def inspect_receipt(output_dir: str | Path, artifact_name: str) -> dict:
    """Read-only independent check; absence or change is never treated as success."""
    folder = _directory(output_dir)
    name = _receipt_name(artifact_name)
    try:
        return _validate_chain(folder, name)
    except ArchiveError as exc:
        return {"receipt_name": name, "artifact_name": artifact_name,
                "status": "RECEIPT_FAILED_REVIEW", "error_code": exc.code,
                "durability": "unproven_after_power_failure"}


def create_receipt(artifact_path: str | Path, *, parent_receipt_name: str | None = None) -> dict:
    """Opt-in: independently verify an existing archive, publish new-only receipt.

    Interrupted publication before receipt leaves an unrecorded artifact.
    A deterministic receipt name prevents silent replacement/repeated successes.
    """
    if not isinstance(artifact_path, (str, Path)) or not Path(artifact_path).is_absolute():
        raise ArchiveError("INVALID_ARTIFACT", "An absolute artifact path is required.")
    path = Path(artifact_path)
    folder = _directory(path.parent)
    match = PUBLISHED.fullmatch(path.name)
    if match is None:
        raise ArchiveError("INVALID_ARTIFACT", "Not a DBVORA published artifact name.")
    receipt_name = _receipt_name(path.name)
    receipt_path = folder / receipt_name
    # Do not interpret or overwrite an earlier success/failure record.
    if receipt_path.exists() or receipt_path.is_symlink():
        raise ArchiveError("RECEIPT_EXISTS", "Existing receipt must not be replaced.")
    before = _snapshot_metadata(path)
    verified = _verify_one(path, match.group(1), folder)
    after = _snapshot_metadata(path)
    if before != after:
        raise ArchiveError("RACE_DETECTED", "Artifact changed during receipt verification.")
    parent_sha = None
    if parent_receipt_name is not None:
        if not isinstance(parent_receipt_name, str) or parent_receipt_name == receipt_name:
            raise ArchiveError("INVALID_PARENT", "A distinct existing parent receipt is required.")
        parent = _validate_chain(folder, parent_receipt_name)
        parent_sha = parent["receipt_sha256"]
    record = {
        "format": FORMAT,
        "artifact_name": path.name, "artifact_kind": match.group(1),
        "artifact_sha256": verified["artifact_sha256"],
        "snapshot_sha256": verified["snapshot_sha256"],
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": "unsigned_local_observation",
        "parent_receipt_name": parent_receipt_name,
        "parent_receipt_sha256": parent_sha,
    }
    content = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(content) > MAX_RECEIPT_BYTES:
        raise ArchiveError("BAD_RECEIPT", "Receipt exceeds prototype size cap.")
    stage = _staging_file(folder)
    linked = False
    try:
        try:
            with stage.open("wb") as sink:
                sink.write(content)
                sink.flush()
                os.fsync(sink.fileno())
            _sync_staged_file(stage)
            # File can change after verification; fast pre-link metadata check.
            if _snapshot_metadata(path) != before:
                raise ArchiveError("RACE_DETECTED", "Artifact changed before receipt publication.")
            os.link(stage, receipt_path, follow_symlinks=False)
            linked = True
            _sync_directory(folder)
        except FileExistsError:
            raise ArchiveError("RECEIPT_EXISTS", "Existing receipt must not be replaced.") from None
        except ArchiveError:
            raise
        except OSError:
            raise ArchiveError("RECEIPT_PUBLISH_FAILED", "Could not durably publish a receipt.") from None
    except BaseException:
        if linked:
            try:
                receipt_path.unlink()
                _sync_directory(folder)
            except (OSError, ArchiveError):
                # May remain: inspection cannot claim it is a success.
                pass
        raise
    finally:
        stage.unlink(missing_ok=True)
    return {"receipt_name": receipt_name, "receipt_sha256": _sha(content),
            "artifact_name": path.name, "snapshot_sha256": verified["snapshot_sha256"],
            "status": "RECORDED_UNSIGNED", "authentication": "unsigned_untrusted",
            "durability": "power_failure_not_proven"}


def inspect_receipt_catalog(output_dir: str | Path) -> dict:
    """Read-only joined recovery audit: missing receipts remain explicitly unrecorded."""
    from dbvora.archive.recovery_catalog import inspect_recovery_catalog
    catalog = inspect_recovery_catalog(output_dir)
    catalog["contract_version"] = "p1-c4.receipt-audit.v1"
    for entry in catalog["records"]:
        if entry["kind"] not in ("sqlite", "zip", "dbvz"):
            continue
        if entry["status"] != "CONTENT_VERIFIED_PUBLISH_UNPROVEN":
            entry["receipt_status"] = "SKIPPED_DUE_TO_ARTIFACT_REVIEW_FAILURE"
            continue
        receipt = inspect_receipt(output_dir, entry["name"])
        entry["receipt_status"] = receipt["status"]
        if receipt["status"] == "RECEIPT_AND_CONTENT_VERIFIED_UNSIGNED":
            entry["status"] = "RECORDED_AND_CONTENT_VERIFIED_UNSIGNED"
            entry["receipt_sha256"] = receipt["receipt_sha256"]
        else:
            entry["receipt_error_code"] = receipt["error_code"]
    return catalog
