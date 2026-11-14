"""Read-only synthetic CAS retention preview; never deletes or edits artifacts.

Filesystem mtimes are untrusted ordering hints because CAS manifests do not
store authenticated generation timestamps. This preview is not deletion authority.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

from dbvora.archive import cas_audit, compressed_cas as cas

MAX_MANIFESTS = cas_audit.MAX_MANIFESTS
MAX_DIRECTORY_ENTRIES = cas_audit.MAX_DIRECTORY_ENTRIES


class RetentionPreviewError(ValueError):
    """Fixed error code only; never includes paths or file contents."""


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _inventory(root: Path) -> dict:
    """Capture bounded names and identities without following any file link."""
    cas_audit._directory(root)
    try:
        directory_before = _identity(root.lstat())
        entries = {}
        with os.scandir(root) as scan:
            for count, entry in enumerate(scan, start=1):
                if count > MAX_DIRECTORY_ENTRIES:
                    raise cas_audit.CasAuditError("DIRECTORY_LIMIT")
                if entry.is_symlink():
                    raise cas_audit.CasAuditError("UNTRUSTED_ENTRY")
                info = os.lstat(root / entry.name)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise cas_audit.CasAuditError("UNTRUSTED_ENTRY")
                entries[entry.name] = _identity(info)
        directory_after = _identity(root.lstat())
    except cas_audit.CasAuditError:
        raise
    except OSError:
        raise cas_audit.CasAuditError("DIRECTORY_UNAVAILABLE") from None
    if directory_before != directory_after:
        raise cas_audit.CasAuditError("STORE_CHANGED")
    return {"directory": directory_after, "entries": entries}


def _capture(chunks: Path, manifests: Path) -> dict:
    if (chunks == manifests or chunks in manifests.parents or
            manifests in chunks.parents):
        raise cas_audit.CasAuditError("SEPARATE_DIRECTORIES_REQUIRED")
    return {"chunks": _inventory(chunks), "manifests": _inventory(manifests)}


def _storage(snapshot: dict) -> dict:
    chunk_entries = snapshot["chunks"]["entries"]
    manifest_entries = snapshot["manifests"]["entries"]
    chunk_files = {name: details for name, details in chunk_entries.items()
                   if cas_audit.CHUNK_NAME.fullmatch(name)}
    manifest_files = {name: details for name, details in manifest_entries.items()
                      if cas.MANIFEST.fullmatch(name)}
    chunk_bytes = sum(details[4] for details in chunk_files.values())
    manifest_bytes = sum(details[4] for details in manifest_files.values())
    return {
        "recognized_chunk_files": len(chunk_files),
        "recognized_manifest_files": len(manifest_files),
        "unrecognized_chunk_entries": len(chunk_entries) - len(chunk_files),
        "unrecognized_manifest_entries": len(manifest_entries) - len(manifest_files),
        "chunk_file_bytes": chunk_bytes,
        "manifest_file_bytes": manifest_bytes,
        "recognized_store_bytes": chunk_bytes + manifest_bytes,
    }


def _report(status: str, keep: int, *, storage=None, audit=None, stable=False,
            generations=None, orphans=None, error_code=None) -> dict:
    report = {
        "contract": "dbvora.synthetic-cas-retention-preview.v1",
        "status": status,
        "keep_generations": keep,
        "ordering_basis": "filesystem_mtime_ns_untrusted",
        "generation_order_trusted": False,
        "inventory_stable_during_preview": stable,
        "storage": storage or {
            "recognized_chunk_files": 0, "recognized_manifest_files": 0,
            "unrecognized_chunk_entries": 0, "unrecognized_manifest_entries": 0,
            "chunk_file_bytes": 0, "manifest_file_bytes": 0,
            "recognized_store_bytes": 0,
        },
        "audit_status": audit.get("status") if audit else None,
        "generations": generations or [],
        "unreferenced_chunk_names": orphans or [],
        "retention_suggestions": [],
        "chunks_no_longer_referenced_by_kept_preview": [],
        "estimated_reclaimable_bytes": None,
        "estimate_basis": "compressed_file_lengths_only; filesystem allocation may differ",
        "automatic_deletion": False,
        "deletion_enabled": False,
        "new_files_created": False,
        "customer_ready": False,
        "physical_power_loss_verified": False,
    }
    if error_code:
        report["error_code"] = error_code
    return report


def preview(chunk_dir: str | Path, manifest_dir: str | Path, *,
            keep_generations: int, synthetic_only=False,
            accept_plaintext=False) -> dict:
    """Return a bounded retention proposal without modifying any artifact."""
    if synthetic_only is not True:
        raise RetentionPreviewError("SYNTHETIC_ONLY_REQUIRED")
    if accept_plaintext is not True:
        raise RetentionPreviewError("PLAINTEXT_ACK_REQUIRED")
    if (type(keep_generations) is not int or
            not 1 <= keep_generations <= MAX_MANIFESTS):
        raise RetentionPreviewError("INVALID_KEEP_GENERATIONS")
    try:
        chunks = cas_audit._directory(chunk_dir)
        manifests = cas_audit._directory(manifest_dir)
        before = _capture(chunks, manifests)
    except cas_audit.CasAuditError as err:
        return _report("HOLD_AUDIT_FAILED", keep_generations, error_code=str(err))

    storage = _storage(before)
    try:
        audit = cas_audit.audit(chunks, manifests, synthetic_only=True)
        parsed = []
        referenced = set()
        manifest_files = before["manifests"]["entries"]
        chunk_files = before["chunks"]["entries"]
        for name in sorted(manifest_files):
            if not cas.MANIFEST.fullmatch(name):
                continue
            record = cas_audit._manifest(manifests, name)
            keys = set(record["chunks"])
            referenced.update(keys)
            parsed.append({
                "row": {
                    "manifest_name": name,
                    "mtime_ns_untrusted": manifest_files[name][5],
                    "manifest_bytes": manifest_files[name][4],
                    "snapshot_bytes": record["snapshot_size_bytes"],
                    "chunk_references": len(record["chunks"]),
                    "unique_chunk_references": len(keys),
                    "verification": ("VERIFIED_BY_READ_ONLY_AUDIT"
                                     if audit["status"] == "PASS_SYNTHETIC_CAS_AUDIT_ONLY"
                                     else "NOT_FULLY_VERIFIED"),
                },
                "record": record,
            })
        present_chunks = {
            name[:-3]: details for name, details in chunk_files.items()
            if cas_audit.CHUNK_NAME.fullmatch(name)
        }
        orphans = sorted(key + ".cz" for key in set(present_chunks) - referenced)
    except cas_audit.CasAuditError as err:
        try:
            after = _capture(chunks, manifests)
            stable = before == after
        except cas_audit.CasAuditError:
            stable = False
        return _report("HOLD_AUDIT_FAILED", keep_generations, storage=storage,
                       stable=stable, error_code=str(err))
    except Exception:
        try:
            after = _capture(chunks, manifests)
            stable = before == after
        except cas_audit.CasAuditError:
            stable = False
        return _report("HOLD_AUDIT_FAILED", keep_generations, storage=storage,
                       stable=stable, error_code="AUDIT_FAILED")

    try:
        after = _capture(chunks, manifests)
        stable = before == after
    except cas_audit.CasAuditError:
        stable = False
    rows = [item["row"] for item in parsed] if stable else []
    if not stable:
        return _report("HOLD_STORE_CHANGED", keep_generations, storage=storage,
                       audit=audit, stable=False)
    if audit["status"] != "PASS_SYNTHETIC_CAS_AUDIT_ONLY":
        return _report(audit["status"], keep_generations, storage=storage,
                       audit=audit, stable=True, generations=rows, orphans=orphans)

    if len(parsed) > keep_generations:
        times = [item["row"]["mtime_ns_untrusted"] for item in parsed]
        if len(times) != len(set(times)):
            return _report("HOLD_AMBIGUOUS_ORDER", keep_generations, storage=storage,
                           audit=audit, stable=True, generations=rows)
        ordered = sorted(parsed, key=lambda item: item["row"]["mtime_ns_untrusted"])
        remove = ordered[:len(ordered) - keep_generations]
        keep = ordered[len(remove):]
    else:
        remove, keep = [], parsed

    kept_names = [item["row"]["manifest_name"] for item in keep]
    remove_names = [item["row"]["manifest_name"] for item in remove]
    kept_chunks = {key for item in keep for key in item["record"]["chunks"]}
    remove_chunks = {key for item in remove for key in item["record"]["chunks"]}
    reclaim_chunks = sorted(remove_chunks - kept_chunks)
    chunk_sizes = {name[:-3]: details[4]
                   for name, details in before["chunks"]["entries"].items()
                   if cas_audit.CHUNK_NAME.fullmatch(name)}
    manifest_sizes = {name: details[4]
                      for name, details in before["manifests"]["entries"].items()
                      if cas.MANIFEST.fullmatch(name)}
    estimate = sum(manifest_sizes[name] for name in remove_names)
    estimate += sum(chunk_sizes[key] for key in reclaim_chunks)
    report = _report("PREVIEW_READY", keep_generations, storage=storage,
                     audit=audit, stable=True, generations=rows)
    report["retained_preview_manifest_names"] = kept_names
    report["retention_suggestions"] = remove_names
    report["chunks_no_longer_referenced_by_kept_preview"] = [
        key + ".cz" for key in reclaim_chunks]
    report["estimated_reclaimable_bytes"] = estimate
    return report


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise RetentionPreviewError("INVALID_ARGUMENT")


def main(argv=None):
    parser = _SafeParser(description="Read-only synthetic CAS retention preview; never deletes")
    parser.add_argument("--chunk-dir", required=True)
    parser.add_argument("--manifest-dir", required=True)
    parser.add_argument("--keep-generations", required=True, type=int)
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--accept-plaintext", action="store_true")
    try:
        args = parser.parse_args(argv)
        report = preview(args.chunk_dir, args.manifest_dir,
                         keep_generations=args.keep_generations,
                         synthetic_only=args.synthetic_only,
                         accept_plaintext=args.accept_plaintext)
        print(json.dumps({"ok": report["status"] == "PREVIEW_READY",
                          "report": report}, sort_keys=True))
        return 0 if report["status"] == "PREVIEW_READY" else 3
    except RetentionPreviewError as err:
        print(json.dumps({"ok": False, "error_code": str(err)}, sort_keys=True),
              file=sys.stderr)
        return 2
    except Exception:
        print(json.dumps({"ok": False, "error_code": "PREVIEW_FAILED"}, sort_keys=True),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
