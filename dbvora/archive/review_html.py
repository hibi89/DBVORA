"""Manual, local-only HTML review of synthetic archive recovery evidence.

This tool cannot certify publication durability, authorize recovery, or modify
an archive. It emits only the bounded counters from a prior read-only audit.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys
import uuid

from dbvora.archive.request_audit import AuditError, inspect_and_reconcile

CONTRACT = 'dbvora.synthetic.request-reconcile.v1'
LABELS = (
    ('INTERRUPTED_REVIEW_REQUIRED', '중단된 요청 · 재실행 금지'),
    ('RECORDED_MATCH_REVIEW_REQUIRED', '해시 일치 · 수동 검토 필요'),
    ('RECORDED_NOT_VERIFIED', '아카이브 검증 실패 또는 누락'),
    ('DUPLICATE_ARTIFACT_REVIEW_REQUIRED', '중복 아카이브 지목 · 검토 필요'),
)
MAX_HTML = 32 * 1024

class ReviewError(ValueError):
    """Stable public error code without user-supplied input."""


def validate_summary(data: dict) -> dict:
    expected = {'contract_version', 'inspection_mode', 'request_count', 'counts',
                'unmatched_verified_archive_count', 'may_resume_archive',
                'exactly_once_verified', 'authenticity_verified',
                'power_loss_verified', 'ready_for_customer_data'}
    if type(data) is not dict or set(data) != expected:
        raise ReviewError('INVALID_REVIEW_SUMMARY')
    if (data['contract_version'] != CONTRACT or
            data['inspection_mode'] != 'read_only_human_review_only'):
        raise ReviewError('INVALID_REVIEW_SUMMARY')
    for key in ('may_resume_archive', 'exactly_once_verified', 'authenticity_verified',
                'power_loss_verified', 'ready_for_customer_data'):
        if data[key] is not False:
            raise ReviewError('UNSAFE_REVIEW_SUMMARY')
    count = data['request_count']
    orphans = data['unmatched_verified_archive_count']
    if (type(count) is not int or not 0 <= count <= 10000 or
            type(orphans) is not int or not 0 <= orphans <= 250):
        raise ReviewError('INVALID_REVIEW_SUMMARY')
    stats = data['counts']
    if (type(stats) is not dict or set(stats) != {k for k, _ in LABELS} or
            any(type(value) is not int or value < 0 or value > 10000
                for value in stats.values()) or sum(stats.values()) != count):
        raise ReviewError('INVALID_REVIEW_SUMMARY')
    return data


def render(data: dict) -> bytes:
    """No raw filename, path, schema or request key can enter the HTML."""
    data = validate_summary(data)
    rows = '\n'.join(f'<tr><th scope="row">{label}</th><td>{data["counts"][code]}</td></tr>'
                     for code, label in LABELS)
    html = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>DBVORA · 백업 요청 수동 검토</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:780px;margin:2rem auto;padding:0 1rem;color:#172330;background:#fff}}
h1{{font-size:1.5rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #aab4c0;padding:.65rem;text-align:left}}td{{text-align:right;font-variant-numeric:tabular-nums}}
.notice{{border-left:4px solid #34475b;padding:.5rem 1rem;background:#f3f5f7}}:focus-visible{{outline:2px solid #234}}</style>
</head><body><main><h1>DBVORA 백업 요청 검토 보고서</h1>
<p class="notice"><strong>복구 승인 아님.</strong> 이 문서는 합성 데이터로 검사한 로컬 진단 결과입니다. 파일 무결성 일치는 서명·원본 인증·전원 장애 안전성 또는 자동 재시작을 증명하지 않습니다.</p>
<h2>요청 {data['request_count']}건</h2><table><caption>읽기 전용 원장·독립 아카이브 대조</caption><thead><tr><th scope="col">분류</th><th scope="col">건수</th></tr></thead><tbody>
{rows}
<tr><th scope="row">원장에 없는 독립 검증 아카이브</th><td>{data['unmatched_verified_archive_count']}</td></tr></tbody></table>
<h2>후속 조치</h2><p>모든 항목은 소유자가 별도 검토해야 합니다. 이 화면은 승인 버튼, 자동 정리, 삭제, 재시도 또는 원격 전송 기능이 없습니다.</p>
<p>원장 키·사용자 경로·SQL 행·데이터베이스 접속 문자열은 표시하거나 저장하지 않았습니다.</p></main></body></html>'''
    encoded = html.encode('utf-8')
    if len(encoded) > MAX_HTML:
        raise ReviewError('REPORT_TOO_LARGE')
    return encoded


def _safe_output(root: str | Path) -> Path:
    if not isinstance(root, (str, Path)):
        raise ReviewError('INVALID_OUTPUT')
    directory = Path(root)
    if not directory.is_absolute():
        raise ReviewError('INVALID_OUTPUT')
    try:
        for p in (directory, *directory.parents):
            if not stat.S_ISDIR(p.lstat().st_mode):
                raise ReviewError('UNSAFE_OUTPUT')
    except ReviewError:
        raise
    except OSError:
        raise ReviewError('OUTPUT_UNAVAILABLE') from None
    return directory


def publish(data: dict, output_dir: str | Path, *, synthetic_only: bool = False,
            accept_plaintext_summary: bool = False) -> dict:
    """Exclusive create, fsync, no overwrite; only the newly-created report is cleaned on failure."""
    if synthetic_only is not True:
        raise ReviewError('SYNTHETIC_ONLY_REQUIRED')
    if accept_plaintext_summary is not True:
        raise ReviewError('PLAINTEXT_SUMMARY_ACK_REQUIRED')
    content = render(data)
    directory = _safe_output(output_dir)
    path = directory / ('dbvora-request-review-' + uuid.uuid4().hex + '.html')
    fd = None
    created_identity = None
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                     getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        opened = os.fstat(fd)
        created_identity = (opened.st_dev, opened.st_ino)
        with os.fdopen(fd, 'wb') as stream:
            fd = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        final = path.lstat()
        if not stat.S_ISREG(final.st_mode) or (final.st_dev, final.st_ino) != created_identity or final.st_size != len(content):
            raise ReviewError('REPORT_CHANGED')
        return {'status': 'LOCAL_SYNTHETIC_REVIEW_ONLY', 'report_name': path.name,
                'bytes': len(content), 'customer_ready': False,
                'may_resume_archive': False, 'power_loss_verified': False}
    except (OSError, ReviewError):
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        # Delete only the new report created by this call; never touch a prior file.
        if created_identity is not None:
            try:
                current = path.lstat()
                if (current.st_dev, current.st_ino) == created_identity and stat.S_ISREG(current.st_mode):
                    path.unlink()
            except OSError:
                pass
        raise ReviewError('REPORT_PUBLISH_FAILED') from None


class _SafeParser(argparse.ArgumentParser):
    def error(self, _):
        raise ReviewError('INVALID_ARGUMENT')


def main(argv=None) -> int:
    from dbvora.archive.safe_zip import ArchiveError
    parser = _SafeParser(description='Local synthetic-only manual backup review (no auto recovery)')
    parser.add_argument('--ledger-dir', required=True)
    parser.add_argument('--archive-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--synthetic-only', action='store_true')
    parser.add_argument('--accept-plaintext-summary', action='store_true')
    try:
        args = parser.parse_args(argv)
        if args.synthetic_only is not True:
            raise ReviewError('SYNTHETIC_ONLY_REQUIRED')
        if args.accept_plaintext_summary is not True:
            raise ReviewError('PLAINTEXT_SUMMARY_ACK_REQUIRED')
        source = _safe_output(args.archive_dir)
        ledger = _safe_output(args.ledger_dir)
        target = _safe_output(args.output_dir)
        if (target == source or target == ledger or target in source.parents
                or target in ledger.parents or source in target.parents
                or ledger in target.parents):
            raise ReviewError('SEPARATE_OUTPUT_REQUIRED')
        audit = inspect_and_reconcile(ledger, source, synthetic_only=True)
        result = publish(audit, target, synthetic_only=True, accept_plaintext_summary=True)
        print(json.dumps({'ok': True, 'result': result}, sort_keys=True))
        return 0
    except (AuditError, ArchiveError, ReviewError) as exc:
        code = exc.code if isinstance(exc, ArchiveError) else str(exc)
    except Exception:
        code = 'UNEXPECTED_FAILURE'
    print(json.dumps({'ok': False, 'error': {'code': code}}, sort_keys=True), file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
