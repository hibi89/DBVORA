"""Explicit, offline, synthetic-only prototype CLI for DBVORA archives.

Not a customer-data tool. All archive writings create new artifacts only.
This module never starts a scheduler, server, subprocess shell, or network client.
"""

import argparse
import json
from pathlib import Path
import sys

from dbvora.archive.recovery_catalog import (
    PUBLISHED, MAX_DIRECTORY_ENTRIES, inspect_recovery_artifact, inspect_recovery_catalog,
)
from dbvora.archive.safe_zip import (
    ArchiveError, HEX_SHA, create_snapshot, make_zip_archive, restore_zip_archive,
)
from dbvora.archive.zstd_archive import create_zstd_archive, restore_zstd_archive
from dbvora.archive.receipts import create_receipt, inspect_receipt_catalog, RECEIPT


class _SafeParser(argparse.ArgumentParser):
    """Do not echo CLI parameters (which may contain a private local path)."""

    def error(self, message):
        raise _CLIError("INVALID_ARGUMENT", "명령 인자가 올바르지 않습니다. --help에서 사용법을 확인하세요.")


class _CLIError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def _parser():
    parser = _SafeParser(
        prog="python -m dbvora.archive_cli",
        description=(
            "합성 SQLite 테스트 전용 오프라인 프로토타입입니다. 생성되는 스냅샷·아카이브와 "
            "복원 데이터베이스는 암호화되지 않습니다. 고객 데이터에는 사용하지 마세요."
        ),
    )
    subs = parser.add_subparsers(dest="command", required=True, parser_class=_SafeParser)

    snapshot = subs.add_parser("snapshot", help="합성 SQLite 스냅샷을 암호화 없이 새 파일로 생성")
    snapshot.add_argument("--source", required=True, help="합성 테스트용 SQLite 파일의 절대 경로")
    snapshot.add_argument("--output-dir", required=True, help="이미 존재하는 출력 폴더의 절대 경로")

    archive = subs.add_parser("archive", help="ZIP 또는 선택 설치한 ZSTD로 새 아카이브 생성")
    archive.add_argument("--snapshot", required=True, help="DBVORA가 생성한 스냅샷 파일의 절대 경로")
    archive.add_argument("--output-dir", required=True, help="Existing absolute output directory")
    archive.add_argument("--codec", required=True, choices=("zip", "zstd"))
    archive.add_argument("--level", type=int, choices=(1, 3, 9), default=None,
                         help="ZSTD 수준(1, 3 또는 9). ZIP에서는 지정하지 마세요.")

    restore = subs.add_parser("restore", help="검증 후 새 SQLite 파일로 복원(암호화되지 않음)")
    restore.add_argument("--archive", required=True, help="생성된 .zip 또는 .dbvz 아카이브의 절대 경로")
    restore.add_argument("--output-dir", required=True, help="기존에 만들어 둔 별도 출력 폴더의 절대 경로")

    preview = subs.add_parser("preview", help="후보 아카이브를 읽기 전용으로 확인하고 선택")
    preview.add_argument("--archive-dir", required=True, help="합성 테스트용 아카이브가 있는 기존 폴더의 절대 경로")

    selected = subs.add_parser("restore-selected", help="미리보기에서 확인한 아카이브를 새 파일로 복원")
    selected.add_argument("--archive", required=True, help="미리보기에서 선택한 생성 .zip 또는 .dbvz 파일의 절대 경로")
    selected.add_argument("--artifact-sha256", required=True, help="미리보기 결과에 표시된 아카이브 SHA-256 값")
    selected.add_argument("--snapshot-sha256", required=True, help="미리보기 결과에 표시된 복원 내용 SHA-256 값")
    selected.add_argument("--output-dir", required=True, help="기존에 만들어 둔 별도 복원 폴더의 절대 경로")

    receipt = subs.add_parser("receipt", help="독립 확인한 아티팩트에 대한 미서명 확인 기록")
    receipt.add_argument("--artifact", required=True, help="DBVORA 아티팩트의 절대 경로")
    receipt.add_argument("--parent-receipt-name", default=None,
                         help="같은 폴더에 있는 기존 검증 영수증 파일명(선택)")
    receipt.add_argument("--accept-unsigned", action="store_true",
                         help="영수증이 서명되거나 발행자를 인증하지 않음을 확인합니다.")

    audit = subs.add_parser("audit", help="카탈로그와 영수증을 별도로 읽기 전용 검증")
    audit.add_argument("--output-dir", required=True, help="기존 아카이브 폴더의 절대 경로")
    audit.add_argument("--require-all-verified", action="store_true",
                       help="유효한 미서명 영수증과 모든 항목의 통과를 확인하지 못하면 오류로 종료합니다.")

    for child in (snapshot, archive, restore, preview, selected, receipt):
        child.add_argument("--synthetic-only", action="store_true",
                           help="합성 테스트 데이터에만 실행함을 확인합니다.")
    for child in (snapshot, archive, restore, preview, selected):
        child.add_argument("--accept-plaintext", action="store_true",
                           help="아카이브·스냅샷·복원 데이터가 암호화되지 않음을 확인합니다.")
    return parser


def _absolute_generated(path, *, suffixes):
    p = Path(path)
    match = PUBLISHED.fullmatch(p.name)
    if not p.is_absolute() or match is None or match.group(1) not in suffixes:
        raise _CLIError("GENERATED_ARTIFACT_REQUIRED", "DBVORA가 생성한 아티팩트의 절대 경로를 선택하세요.")
    return p


def _require_write_ack(args):
    if not args.synthetic_only:
        raise _CLIError("SYNTHETIC_ONLY_REQUIRED", "프로토타입은 --synthetic-only 확인 없이는 실행하지 않습니다.")
    if args.command == "receipt":
        if not args.accept_unsigned:
            raise _CLIError("UNSIGNED_ACK_REQUIRED", "영수증 확인은 --accept-unsigned가 필요합니다.")
    elif not args.accept_plaintext:
        raise _CLIError("PLAINTEXT_ACK_REQUIRED", "이 작업은 --accept-plaintext 확인이 필요합니다.")


def _no_source_dir_output(source, output_dir):
    # Keep generated files out of the source artifact's directory. This is not
    # permission to archive customer databases; --synthetic-only is an assertion.
    if Path(source).parent.resolve() == Path(output_dir).resolve():
        raise _CLIError("SEPARATE_OUTPUT_REQUIRED", "원본 폴더와 분리된 기존 출력 폴더를 선택하세요.")


def _redact_paths(obj):
    """Paths returned by lower layers are not disclosed in CLI JSON/logs."""
    if isinstance(obj, list):
        return [_redact_paths(item) for item in obj]
    if isinstance(obj, dict):
        return {key: (Path(value).name if key.endswith("_path") and isinstance(value, str)
                      else _redact_paths(value)) for key, value in obj.items()}
    return obj


def main(argv=None):
    try:
        args = _parser().parse_args(argv)
        if args.command == "audit":
            result = inspect_receipt_catalog(args.output_dir)
            if args.require_all_verified:
                records = result.get("records", ())
                if (not records or not all(
                        item.get("status") == "RECORDED_AND_CONTENT_VERIFIED_UNSIGNED"
                        and item.get("receipt_status") == "RECEIPT_AND_CONTENT_VERIFIED_UNSIGNED"
                        for item in records)):
                    raise _CLIError("AUDIT_VERIFICATION_FAILED",
                                    "일부 아카이브 또는 영수증이 누락·손상·미검증 상태입니다. 원본을 보존하고 항목을 검토하세요.")
                expected_receipts = {
                    "dbvora-receipt-" + item["name"][7:39] + ".json"
                    for item in records
                }
                for count, item in enumerate(Path(args.output_dir).iterdir()):
                    if count >= MAX_DIRECTORY_ENTRIES or (RECEIPT.fullmatch(item.name)
                                         and item.name not in expected_receipts):
                        raise _CLIError("AUDIT_VERIFICATION_FAILED",
                                        "Audit contains missing, damaged, or unverified artifacts or receipts.")
        else:
            _require_write_ack(args)
            if args.command == "preview":
                catalog = inspect_recovery_catalog(args.archive_dir)
                result = {
                    "inspection_mode": catalog["inspection_mode"],
                    "observed_at_utc": catalog["observed_at_utc"],
                    "complete": catalog["complete"],
                    "ignored_entry_count": catalog["ignored_entry_count"],
                    "records": [item for item in catalog["records"]
                                if item.get("kind") in ("zip", "dbvz")],
                    "guidance": (
                        "CONTENT_VERIFIED_PUBLISH_UNPROVEN 상태의 항목만 선택하세요. "
                        "미리보기의 아카이브와 복원 내용 SHA-256 값을 정확히 입력해 restore-selected를 실행하세요."
                    ),
                }
            elif args.command == "snapshot":
                _no_source_dir_output(args.source, args.output_dir)
                result = create_snapshot(args.source, args.output_dir)
            elif args.command == "archive":
                _absolute_generated(args.snapshot, suffixes=("sqlite",))
                _no_source_dir_output(args.snapshot, args.output_dir)
                if args.codec == "zip":
                    if args.level is not None:
                        raise _CLIError("UNSUPPORTED_LEVEL", "압축 수준은 ZSTD에만 지정할 수 있습니다.")
                    result = make_zip_archive(args.snapshot, args.output_dir)
                else:
                    result = create_zstd_archive(args.snapshot, args.output_dir,
                                                 level=args.level if args.level is not None else 3)
            elif args.command in ("restore", "restore-selected"):
                artifact = _absolute_generated(args.archive, suffixes=("zip", "dbvz"))
                _no_source_dir_output(artifact, args.output_dir)
                restore_fn = restore_zip_archive if artifact.suffix == ".zip" else restore_zstd_archive
                if args.command == "restore":
                    result = restore_fn(artifact, args.output_dir)
                else:
                    if (not HEX_SHA.fullmatch(args.artifact_sha256)
                            or not HEX_SHA.fullmatch(args.snapshot_sha256)):
                        raise _CLIError(
                            "INVALID_SELECTION",
                            "미리보기의 두 SHA-256 값을 입력하고 별도 출력 폴더를 선택하세요.",
                        )
                    preview = inspect_recovery_artifact(artifact)
                    if (preview.get("status") != "CONTENT_VERIFIED_PUBLISH_UNPROVEN"
                            or preview.get("artifact_sha256") != args.artifact_sha256
                            or preview.get("snapshot_sha256") != args.snapshot_sha256):
                        raise _CLIError(
                            "SELECTION_CHANGED",
                            "선택한 아카이브가 검증된 미리보기와 달라졌습니다. 미리보기를 다시 실행하거나 검증된 항목을 선택하세요. 복원 파일은 생성되지 않았습니다.",
                        )
                    try:
                        result = restore_fn(
                            artifact, args.output_dir,
                            expected_snapshot_sha256=args.snapshot_sha256,
                        )
                    except ArchiveError as exc:
                        raise _CLIError(
                            exc.code,
                            "복원이 안전하게 완료되지 않았습니다. 선택한 아카이브와 분리된 출력 폴더를 확인하세요. 원본 아카이브는 변경하지 않았습니다.",
                        ) from None
                    result["selected_artifact_sha256"] = preview["artifact_sha256"]
                    result["selection_verified"] = True
            else:
                _absolute_generated(args.artifact, suffixes=("sqlite", "zip", "dbvz"))
                result = create_receipt(args.artifact, parent_receipt_name=args.parent_receipt_name)
        print(json.dumps({"ok": True, "command": args.command, "result": _redact_paths(result)},
                         ensure_ascii=False, sort_keys=True))
        return 0
    except (ArchiveError, _CLIError) as exc:
        code = exc.code
        message = (exc.message if isinstance(exc, _CLIError) else
                   "아카이브 검증 또는 복원이 안전하게 완료되지 않았습니다. 입력을 확인하고 원본을 보존하세요.")
    except (OSError, ValueError, TypeError):
        code, message = "OPERATION_FAILED", "로컬 작업이 완료되지 않았습니다. 원본을 보존하고 입력을 다시 확인하세요."
    except Exception:
        # Never print a traceback containing the source path or copied customer data.
        code, message = "UNEXPECTED_FAILURE", "작업을 완료하지 못했습니다. 원본 파일을 보존하고 다시 확인하세요."
    print(json.dumps({"ok": False, "error": {"code": code, "message": message}},
                     ensure_ascii=False, sort_keys=True),
          file=sys.stderr)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
