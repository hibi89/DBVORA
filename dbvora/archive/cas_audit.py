"""Bounded read-only inventory of explicitly selected synthetic zlib CAS v2.

No deletes, no retries, no network, no customer data, and no path reporting.
A healthy archive check is NOT power-loss or end-user acceptance evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from dbvora.archive import compressed_cas as cas

MAX_MANIFESTS = 16
MAX_CHUNKS = 4096
MAX_DIRECTORY_ENTRIES = 8192
CHUNK_NAME = re.compile(r"[a-f0-9]{64}\.cz\Z")
STAGED_NAME = re.compile(r"\.dbvora-[A-Za-z0-9_.-]{1,128}\Z")


class CasAuditError(ValueError):
    """Path-free fixed error codes only."""


def _directory(value: str | Path) -> Path:
    if not isinstance(value, (str, Path)) or not Path(value).is_absolute():
        raise CasAuditError("INVALID_DIRECTORY")
    path = Path(value)
    try:
        for item in (path, *path.parents):
            mode = item.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise CasAuditError("UNTRUSTED_DIRECTORY")
        if not stat.S_ISDIR(path.lstat().st_mode):
            raise CasAuditError("INVALID_DIRECTORY")
    except CasAuditError:
        raise
    except OSError:
        raise CasAuditError("INVALID_DIRECTORY") from None
    return path


def _scan(root: Path, extension: str) -> tuple[list[str], int]:
    found, other, seen = [], 0, 0
    try:
        with os.scandir(root) as entries:
            for ent in entries:
                seen += 1
                if seen > MAX_DIRECTORY_ENTRIES:
                    raise CasAuditError("DIRECTORY_LIMIT")
                if ent.is_symlink():
                    raise CasAuditError("UNTRUSTED_ENTRY")
                # Windows DirEntry.stat may report st_nlink=0 even for
                # single-link regular files. os.lstat obtains full file
                # identity/links on NTFS (without following reparse links).
                info = os.lstat(root / ent.name)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise CasAuditError("UNTRUSTED_ENTRY")
                if extension == "manifest" and cas.MANIFEST.fullmatch(ent.name):
                    found.append(ent.name)
                elif extension == "chunk" and CHUNK_NAME.fullmatch(ent.name):
                    found.append(ent.name)
                else:
                    # Staged/unknown items never get deleted or silently ignored.
                    other += 1
    except CasAuditError:
        raise
    except OSError:
        raise CasAuditError("DIRECTORY_UNAVAILABLE") from None
    return sorted(found), other


def _manifest(root: Path, name: str) -> dict:
    # Share the exact descriptor-identity guard with restore_compressed:
    # reject same-size/same-mtime replacements, and never trust path-only reads.
    try:
        return cas._parse_manifest(cas._read_manifest_unchanged(root / name))
    except (cas.CompressedCasError, OSError):
        raise CasAuditError("INVALID_MANIFEST") from None


def audit(chunk_dir: str | Path, manifest_dir: str | Path, *, synthetic_only=False) -> dict:
    if synthetic_only is not True:
        raise CasAuditError("SYNTHETIC_ONLY_REQUIRED")
    chunks, manifests = _directory(chunk_dir), _directory(manifest_dir)
    if (chunks == manifests or chunks in manifests.parents or
            manifests in chunks.parents):
        raise CasAuditError("SEPARATE_DIRECTORIES_REQUIRED")
    names, unrecognized_manifests = _scan(manifests, "manifest")
    present, unrecognized_chunks = _scan(chunks, "chunk")
    if not names:
        raise CasAuditError("NO_VERIFIED_MANIFESTS")
    if len(names) > MAX_MANIFESTS or len(present) > MAX_CHUNKS:
        raise CasAuditError("AUDIT_LIMIT")
    parsed = [_manifest(manifests, name) for name in names]
    referenced, references = set(), 0
    invalid, valid = 0, 0
    for record in parsed:
        references += len(record["chunks"])
        referenced.update(record["chunks"])
        if references > MAX_CHUNKS:
            raise CasAuditError("REFERENCE_LIMIT")
        digest = hashlib.sha256()
        size = 0
        good = True
        for key in record["chunks"]:
            try:
                part = cas._read(chunks, key)
            except cas.CompressedCasError:
                good = False
                break
            size += len(part)
            if size > record["snapshot_size_bytes"]:
                good = False
                break
            digest.update(part)
        if good and size == record["snapshot_size_bytes"] and (
                digest.hexdigest() == record["snapshot_sha256"]):
            valid += 1
        else:
            invalid += 1
    present_keys = {name[:-3] for name in present}
    unreferenced = len(present_keys - referenced)
    missing = len(referenced - present_keys)
    suspicious = unrecognized_manifests + unrecognized_chunks
    status = ("HOLD_DAMAGED_OR_MISSING" if invalid or missing else
              "HOLD_MANUAL_REVIEW" if unreferenced or suspicious else
              "PASS_SYNTHETIC_CAS_AUDIT_ONLY")
    return {
        "contract": "dbvora.synthetic-cas-zlib-audit.v1", "status": status,
        "manifests_checked": len(names), "verified_generation_count": valid,
        "invalid_generation_count": invalid,
        "referenced_unique_chunks": len(referenced),
        "missing_chunk_count": missing, "unreferenced_chunk_count": unreferenced,
        "unrecognized_file_count": suspicious, "references_checked": references,
        "automatic_deletion": False, "new_files_created": False,
        "customer_ready": False, "physical_power_loss_verified": False,
    }


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise CasAuditError("INVALID_ARGUMENT")


def main(argv=None):
    parser = _SafeParser(description="Read-only synthetic CAS v2 audit (never deletes)")
    parser.add_argument("--chunk-dir", required=True)
    parser.add_argument("--manifest-dir", required=True)
    parser.add_argument("--synthetic-only", action="store_true")
    try:
        args = parser.parse_args(argv)
        report = audit(args.chunk_dir, args.manifest_dir,
                       synthetic_only=args.synthetic_only)
        print(json.dumps({"ok": report["status"] == "PASS_SYNTHETIC_CAS_AUDIT_ONLY",
                          "report": report}, sort_keys=True))
        return 0 if report["status"] == "PASS_SYNTHETIC_CAS_AUDIT_ONLY" else 3
    except CasAuditError as err:
        print(json.dumps({"ok": False, "error_code": str(err)}, sort_keys=True),
              file=sys.stderr)
        return 2
    except Exception:
        print(json.dumps({"ok": False, "error_code": "AUDIT_FAILED"}, sort_keys=True),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
