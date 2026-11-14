# DBVORA P100 정식 최종설계 수용·검증 계획 — 2026-11-14 KST

## 이번 사용자 지시와 점수 구분
- 사용자 목표: **최종설계 전체 100%**를 달성한 뒤 이번 주말 크몽 상품화 준비. 현금 비용 0원, 사용자 PC 반복 개입 최소.
- 최종설계 공식 완료율: **UNASSESSED**. 2026-11-13 공통 OWNER-FINAL-BLUEPRINT-100 기준(사용자 승인 가중치/전체 요구 추적과 exact-SHA 전수 실행 미완). 확인 전 수치를 만들어내지 않는다.
- 기존 **95/100**은 P0(25)+P1(13)+P2(20)+P3(19)+P4(18) **과거 내부 기술범위 가중치**이며 공식 최종설계·상업 출시율이 아니다. 기존 증거를 삭제하지 않는다.
- 최신 검증 가능한 부분: 2026-11-13 GitHub blob 일치 11개 원본에 대해 synthetic PG E2E 6/6 및 unittest 11/11 PASS. **전체 테스트 Python >=553, Node, 실제 원본 ZIP·Windows·실 TLS PG는 이전 증거 기준 미실행**.

## 두 검증안 비교 및 채택
| 안 | 비용 | 장점 | 제약 |
| --- | --- | --- | --- |
| A. 사용자 Windows 한 대에서 전체 release gate만 수행 | 0원 | 실제 소유자 OS 근거 | 소유자 PC·앱 실행 시간 필요; Linux 회귀 부재 |
| B. 공개 저장소 기본 GitHub-hosted Ubuntu/Windows 표준 runner에서 무시크릿 full gate 실행 + 나중에 실제 사용자 Windows 수용 | GitHub 공개 저장소 표준 runner 무료 범위 안에서 0원 | 전체 exact SHA 코드·2개 OS 재현, 사용자 모바일에서 결과 확인 | GitHub Actions 활성/가용성 의존; CI는 실제 구매자 PC·실 PG·권리 증명이 아님 |
**채택 B.** 실행 한도/예산/권한 문제 시 유료 runner·계정 설정 변경 없이 HOLD하고 A로 전환. 원본 DB/고객 파일/토큰을 workflow에 전송하지 않는다.

## 확정 요구 추적(승인 가중치 미확정: 공식 점수 UNASSESSED)
| ID | 사용자 확정 요구 및 전체 수용조건 | 코드·근거 | 남은 검증 |
| --- | --- | --- | --- |
| REQ-01 | 승인 SQLite/PG 데이터베이스 구조·테이블·컬럼·FK·인덱스 클릭 탐색 | dbvora/connectors/, inventory.py, api.py, web/, multi_engine_report.py | 전체 SHA 테스트·Windows 실제 UI/오프라인 HTML·PG TLS |
| REQ-02 | 측정된 파일/테이블 크기, 변화, 가용 시스템 지표 출처 구분 | metrics.py, storage_metrics.py, postgres_statistics.py | 실제 DB/FS 환경 측정 정확도 및 불가 지표 표시 |
| REQ-03 | ZIP보다 효율적일 수 있는 선택형 압축, 안전 스냅샷·무손실 복원, 실패 원본 불변 | archive/safe_zip.py, zstd_archive.py, receipts.py, recovery_catalog.py | 전체 ZIP/ZSTD·손상·복원 독립 검증, 실제 NTFS/WAL 전원중단 |
| REQ-04 | 실제 측정 전 Supabase/PG 대비 저장 효율 우월 주장 금지 | docs/COMPRESSION_PLAN.md | 동일 조건 반복 벤치마크/권리·광고 검수 |
| REQ-05 | 로컬 주권·클라우드 기본 OFF·최소 비용/보안 | CLI/127.0.0.1/README/경로·출처 안전 모듈 | 외부 연결 0, 패키지 검증·상업 LICENSE/NOTICE |
| REQ-06 | 다른 AX와 연계 가능하되 독립 상품으로 동작 | 구조 계약·독립 CLI | 실제 통합 수용은 별도, 독립 설치/제거·재실행 |
| REQ-07 | 소유자 제어 개발·검증·인수인계 | STATUS/HANDOFF/CI | Windows 실제 사용자 수용·사업자 지원/환불/상품 등록 승인 |

이 표는 전체 최종설계 항목의 초기 매핑이며 **사용자 승인 100점 가중치 또는 공식 수용 완료를 의미하지 않는다.** 사용자 확정 요건 누락 여부 추가 감사 필요.

## 자동 검증 파이프라인
- 파일: `.github/workflows/dbvora-release-gate.yml` → feature/p0-db-map push/수동 동작, 공개 GitHub 표준 Ubuntu 24.04 + Windows 2025, Python 3.11 + Node 22, no secret/no customer DB, contents:read.
- 명령: `python -m pip install -e ".[ui]"` → `python -m scripts.verify_release_gate`.
- gate: Python unittest >=553, ZIP/ZSTD synthetic CLI, compileall, Node DOM, filesystem, 중복요청 실제 ZIP, recovery review, trusted portable ZIP, synthetic PG→offline HTML. 판정은 정확 HEAD의 실제 Actions 로그에 따르며, workflow 생성 자체는 PASS가 아니다.

## 소유자 PC 사전 안내
- **지금 즉시 PC 조작 불필요.** GitHub CI 결과 및 가능한 회귀 수정을 먼저 완료한다.
- 이후 소유자 실제 Windows에서 feature 브랜치 ZIP 압축해제 후 `py -3.11 -m scripts.verify_release_gate` 한 번 실행, 최종 JSON/exit code 제공. 실고객 DB, 계정, 키 절대 입력·전송 금지.
- 정말 100%/판매 GO에 필요할 수 있는 별도 승인: 접근 가능한 **합성 PostgreSQL** read-only `sslmode=verify-full` 실연결, 상업 LICENSE·NOTICE/지원/환불/고객 인수 조건. 유료 서명·감사 및 실제 고객 자료가 필요하면 0원 원칙에 따라 별도 승인 전 중단.
- 설치형·고객용 판매 패키지 서명 미완 및 SmartScreen/Defender 등 유통 위험은 CI PASS로 면제되지 않는다.

## 완료 조건
1. 전체 코드의 정확 SHA에서 2개 OS 릴리스 게이트 PASS, 실제 ZIP 출력·독립 복원 및 검수.
2. 실제 Windows 소유자 실행/GUI/파일 원본보존·복원 테스트.
3. DB 접속·권리/제3자 라이선스·안전/고객 수용 조건 PASS 및 최종 사용자 판매 승인.
4. 최종설계 100점 가중치와 각 요구 수락 근거 승인, 상태·SHA·중앙 원장 일치.

**검증 전 상태: 목표 P100 [작업중], RELEASE HOLD, 크몽 실제 등록 미실행, Vercel/Production 미적용.**

## 2026-11-14 전체 실제 검증 결과
- 기능 정확 SHA eab26716e25e8c55b120d295110be2f754b6aa5e.
- Windows Server 2025 Python3.11 Python617 discovered/616 PASS·0 FAIL·1 POSIX-only SKIP + 10/10 release gate PASS. Ubuntu24.04 Python3.11 Python617 PASS·0 FAIL·0 SKIP + 10/10 release gate PASS. [Actions](https://github.com/hibi89/DBVORA/actions/runs/43543367368).
- 실제 Chromium localhost UI/API+synthetic SQLite: 클릭·FK·모바일·XSS·origin/host/HTTP method guard 등 8/8 PASS. 2개 합성 UI PNG(7일 임시 보존) [Actions](https://github.com/hibi89/DBVORA/actions/runs/43543367417).
- 이후 미완료: 사용자 Win10 실기기 [단일 QA](OWNER_WINDOWS_QUICK_QA_20261114.md), 실 PG TLS verify-full, 물리 power-cut, 배포 라이선스/지원/유통 승낙, 최종설계 100점 승인 가중치. 현재 UNASSESSED, 과거 내부95 이력 별도, [작업중]/RELEASE HOLD. 실제 크몽 등록0. 고객/secret 데이터 미사용.


## 2026-11-14 추가 검증 — Windows/Ubuntu 실제 Chromium 통합
- 기능/워크플로 exact SHA: `a982508160a3085e12e3663f1df9979dac4e9cae`. 이번 커밋은 기존 Linux 한 대에 한정했던 Chromium localhost 신뢰검사를 **무료 표준 Ubuntu24.04 + Windows2025** 매트릭스로 확장. 각 운영체제에서 합성 SQLite 실제 FastAPI HTTP와 실제 Chromium 렌더링 및 보안/모바일/출력 8개 조건 통과: **2/2 SUCCESS** [run 43544065399](https://github.com/hibi89/DBVORA/actions/runs/43544065399).
- synthetic PNG 2개/OS는 Actions artifact로 7일 보존. 고객DB·인증·비밀·PG 라이브 접속·외부 서비스 배포 안 함.
- 제품 코드는 기존 full release gate [run 43543990300](https://github.com/hibi89/DBVORA/actions/runs/43543990300)에서 617 Python × Windows/Linux, 필수 10개 단계 각각 PASS. Chromium 브라우저 workflow 변경 자체는 프로그램 완성률 가중점수가 아니다.
- **공식 100% 미달/UNASSESSED**: 실제 소유자 Windows10, 허가된 synthetic PostgreSQL verify-full TLS, 물리적 전원단절 및 신원보증, LICENSE/NOTICE/지원·환불·가격, 상품화 최종 승인과 전체 요구 수용 가중치 확정 필요. 13시 사용자 역할 통합 알림에 모음.

## 2026-11-14 0원 unsigned 사용자 QA ZIP 최종 확인
- 정확 HEAD `3835a53de75f5de4e1d2ddd3c895377b83d45112`; [공개 GitHub Actions preview run #43544666021](https://github.com/hibi89/DBVORA/actions/runs/43544666021) **SUCCESS**. 합성 패키지 56 소스파일·SHA manifest 재검증·오프라인 selftest 완료; inner `dbvora-dev-preview-0.2.0.zip` SHA-256 `e7a6d46099c170cc8e0f70b098dd6a86d47c5678b0ff51bc3cfa7225fa0426f1`. Actions artifact ID `14092914030`(2026-11-21 만료 예정), 실제 고객 데이터/토큰 없음.
- 기존 소유자 PC 전체 원본 git clone/pytest 방식보다 PC 부담을 줄이도록 [OWNER_WINDOWS_QUICK_QA_20261114.md](OWNER_WINDOWS_QUICK_QA_20261114.md)에 **다운로드→해시 대조→신규 폴더 추출→로컬 무추가 의존성 selftest 2종→오프라인 HTML 수동 클릭** 경로를 추가. 미서명 ZIP은 **신원 인증/고객 납품/코드서명 불가**, 원본 비공개 복원/EXE 설치기 아님.
- 비용 0원(기본 공개 GitHub 표준 Runner), 일반 Windows10 실기기·실 DB/PG TLS·물리 정전·법적권리/상품 등록 및 사용자 승인 미검증. 공식 최종설계 UNASSESSED, 내부95는 과거치, [작업중]/RELEASE HOLD.