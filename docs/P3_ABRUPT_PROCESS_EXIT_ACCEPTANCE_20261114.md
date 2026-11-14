# DBVORA P3 — 합성 자식 프로세스 작성 중단·복구 안전성 검증

기준일: 2026-11-14 KST  
정확한 소스 SHA: `a4d6e92efb8b8b2596f729f6e0442518c4f573b9`  
대상: `hibi89/DBVORA@feature/p0-db-map`

## 설계·비용·원본 안전성 비교

| 접근 | 시간·비용 | 데이터 안전성과 유지보수 |
| --- | --- | --- |
| A. 새 OS별 전역 프로세스 잠금/자동 복구 | Windows/Linux 예외, 영속 lock·정리 로직 증가 | 기존 무덮어쓰기 publish/읽기 전용 감사와 충돌·복구 경계 확대 |
| B. 별도 spawn 프로세스가 불완전 `.part`를 작성한 직후 `os._exit`로 강제 종료 | 표준 라이브러리·GitHub 기존 CI만 사용, 무료 | 원본 CAS 구현은 보존; 불완전 stage는 게시하지 않고 수동 HOLD/기존 백업 복원 검증 |

채택: **B (검증 우선, 운영 코드 수정 없음)**. 자동 삭제와 원본/기존 정상 세대의 수정은 금지.

## 새 테스트 2개

추가 `tests/test_cas_abrupt_exit.py`.

1. **청크 중간 작성 강제 종료:** 이전 정상 세대 게시→ 합성 SQLite 수정·새 스냅샷→ 새로운 SHA 청크 존재 사전 확인→ 자식 프로세스 내부 `_write_staged_exact`를 일부 write + 즉시 `os._exit(86)`로 모의 종료. 부모는 정확 종료코드86, `.part` 잔여1, 신규 최종청크 게시0, manifest 원본 바이트 불변을 확인. 읽기 전용 CAS 감사는 `HOLD_MANUAL_REVIEW`, 이전 세대 독립 복원 SHA/SQLite integrity 정상.
2. **Manifest 중간 작성 강제 종료:** 새 합성 청크들이 게시된 후, manifest staging의 일부만 작성하고 `os._exit(87)`. 부모는 코드87, 게시된 새 검증 manifest0, orphan 신규 청크 존재, 미완 stage 보존 확인. 이전 세대 유효, 감사 `HOLD_MANUAL_REVIEW`/기존 세대 유효1·손상0·자동삭제 false. 재감사는 목록 변경 없음.

각 테스트는 임시 합성 SQLite와 로컬 파일만 사용하며 부모/자식 독립 `multiprocessing.spawn`, timeout/자식 정리, DB/스냅샷 SHA256+mtime 확인. 의도된 파일 손상은 **오직 test-owned staging 파일**. 실제 고객 경로·권한·키·외부 API 접근 없음.

## 정확한 검증 증거

[GitHub Actions 전체 릴리스 #43580486901](https://github.com/hibi89/DBVORA/actions/runs/43580486901) — 동일 source SHA 기준:
- Ubuntu24.04: Python **714/714 PASS**, FAIL0, SKIP0, 필수 12/12, job SUCCESS.
- Windows2025: Python **713 PASS / 0 FAIL / 1 named POSIX-only SKIP** (총714 발견), 필수 12/12, job SUCCESS. SKIP: `test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`.
- [Final blueprint evidence gate #43580487122](https://github.com/hibi89/DBVORA/actions/runs/43580487122): SUCCESS. 수용/100% 달성 의미는 아님.
- 실 Chromium은 이전 정확 UI SHA `d5780ceece92`에서 양 OS 17/17 PASS; 이번 소스는 브라우저 자산 변경 없음.

## 제한·다음 작업

- `os._exit`는 프로세스 종료 모의이지 실제 PC 전원 차단, 버퍼·장치 캐시·전원차단 안전성 검증이 아님.
- 이 검증은 강제 종료 직후 수동 HOLD와 이전 세대 독립 복원을 확인하며, **자동 정리/재시도/데이터 무결성 복구를 구현한 것은 아님**.
- 장시간 복수 프로세스·고객 Win10/11 기기, 고객 DB·실 백업, 상용 라이선스/설치/제거/최종 사용자 수용은 미검증.
- 공식 최종설계 `UNASSESSED`(과거 내부 기술95 기록), 중앙 `[작업중]`, RELEASE HOLD, 크몽 실제 등록0, Production/Vercel 미적용을 유지.
- 다음: 사용자 개입 없이 P0 HTTP 네트워크 단절·timeout/abort 시 UI 안정성과 장애 후 재시도, 장시간 브라우저 누적 검증을 우선. 새로운 유료 서비스/외부 업로드·무단 원본 수정 금지.
