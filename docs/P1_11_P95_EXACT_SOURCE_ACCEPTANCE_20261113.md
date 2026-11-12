# DBVORA P1-11 — P95 내부 엔지니어링 달성 근거 (정본 소스 합성 E2E)

**기준:** 2026-11-13 KST / `hibi89/DBVORA@feature/p0-db-map` / 내부 기술 범위 **95/100** / **판매 RELEASE HOLD**

## 문제와 전환
기존 내부 P94에서 유일하게 점수 보류했던 P1 `scripts.pg_synthetic_acceptance`는 전체 private checkout의 로컬 Git DNS 차단으로 **코드는 구현했지만 실제로 실행하지 못한 상태**였다. 원래 전체 checkout을 임의 생성/유료 CI로 처리하는 방안(A)은 계정 권한·과금과 전체 소스 입수 제한이 존재했다. 선택한 방안(B)은 **GitHub connector로 실제 파일별 원본을 읽고 Git Blob SHA가 완전히 일치하는 최소 필요한 생산 코드+실제 테스트 모듈을 컨테이너에 재구성하여 실행**하는 것이다. 외부 DB/유료/새 저장소·신규 CI 없음.

## 실제 실행한 원본 (모두 바이트 단위 SHA 일치)
다음 11개는 `git blob` 포맷 `SHA1("blob "+len+"\\0"+raw_bytes)`로 확인한 GitHub 정본과 실행용 코드가 동일하다.

| 경로 | Git Blob SHA |
|---|---|
| `scripts/pg_synthetic_acceptance.py` | `199af22de69edbeef51bffd3e1dcd8d8c091c99f` |
| `dbvora/connectors/postgres_reader.py` | `53fdddb0c86f9ceeb6a4e8b2308f8a4959d18faf` |
| `dbvora/connectors/postgres_statistics.py` | `740033f65a3cb8bdf2f21ca37540da44e07bce1d` |
| `dbvora/multi_engine_report.py` | `f3859d9c5d3cbc6affff797ebc2c3a630be04e22` |
| `dbvora/optimization_review.py` | `058a66eba05a932469734bd8c42b49922abe7723` |
| `dbvora/archive/safe_zip.py` | `a58d2c3bfd3b95a98ada74f59e208b58e35d2e13` |
| `dbvora/connectors/sqlite_reader.py` | `1d663d9d8243b75dbca0e697428870328bd87509` |
| `dbvora/errors.py` | `03649675b51aed9e7438072b26dd3411160c6695` |
| `tests/test_pg_synthetic_acceptance.py` | `e903572766741de5ef5b23c334ee5241829430ac` |
| `tests/test_pg_html_script.py` | `9d3dfbf8dae9f66f6df50d8aa869add069b44cba` |
| `pyproject.toml` | `080af800601fff0177eedbfbf58aeb3b2664c36a` |

Python package `__init__.py` files for local isolated execution are empty package markers; private repo 전체를 복원한 것은 아니다. 위 실제 실행 경로의 생산 모듈·검사 모듈·파일 퍼블리셔 코드는 SHA 검증된 정본이며, 모의 구현으로 대체하지 않았다.

## 실행 명령·실제 결과
- 환경: container Linux Python **3.13.5**, Node **v22.16.0**, network DNS unavailable. 모든 DB 커서/스키마/메트릭은 코드에 정의한 **합성 테스트 전용**이며 고객 데이터·실 PostgreSQL·비밀 없음.
- `PYTHONDONTWRITEBYTECODE=1 python -m scripts.pg_synthetic_acceptance`
  - **Exit code 0**; JSON: `{"automatic_actions":false,"checks":6,"contract":"dbvora.pg-synthetic-e2e.v1","ready_for_customer_data":false,"real_pg_connected":false,"status":"PASS_SYNTHETIC_PG_ONLY"}`
  - 진짜 production `postgres_reader.inspect_catalog(include_statistics=True)` / `postgres_statistics.collect_relation_statistics` / `multi_engine_report.assemble_workspace` / `optimization_review.review_statistics` / `render_report` / `export_report` / 진짜 `safe_zip` filesystem write/publish 함수 사용.
  - 성공 조건 6개: (1) catalog SELECT/3 tables, (2) 물리·비물리 테이블 통계 출처/측정, (3) declared PG foreign key, (4) dead-row/index allocation review-only, (5) CSP/HTML metric payload, (6) OS-temp 실제 new HTML/bytes/SHA 일치. 임시 파일 자동 삭제, DB 변경 없음.
- `PYTHONDONTWRITEBYTECODE=1 python -W error::ResourceWarning -m unittest -v tests.test_pg_synthetic_acceptance tests.test_pg_html_script`
  - **11 PASS / 0 FAIL / 0 SKIP** (6 real-source integrated PG & fail-closed/network suppression, 5 original HTML payload, relation, view unavailable, Node check, TOML optional driver). 재실행 `-q` **11 PASS**.
- Node syntax check: 정본 HTML 내부 JS를 진짜 `node --check -`로 검사하는 원본 테스트 PASS. **브라우저 UI 실제 Chromium/Edge는 아님**.

## 95% 내부 판정 (변경 없는 설계 분모)
직전 문서의 잠정 점수 P0 25/25 + P1 **12/15** + P2 20/20 + P3 19/20 + P4 18/20 = 94/100. P1 마지막 `PG 카탈로그→통계→관계→검토→HTML 디스크` **통합 합성 E2E가 원본 생산 모듈로 6/6 실제 PASS**, 원본 관련 unit 11 PASS이므로 보류했던 **P1 +1**을 인정: **P0 25 + P1 13 + P2 20 + P3 19 + P4 18 = 95/100 내부 엔지니어링 목표 달성**.

이 완성률은 **설계 대비 기술 기능 단계/검증 범위의 내부 가중 점수**이고, 전체 제품 테스트 통과율이나 출시 준비율이 아니다. `P95` 목표 달성에 따라 중앙 `DBVORA [작업중]` 표시는 다른 프로젝트 표식과 무관하게 종료 가능; 원본 docs/roster와 product branch SHAs 동기화 후 변경한다.

## 남은 정확한 미검증 (판매·100% 게이트)
1. **전체 private checkout 원본 553건 이상 Python + Node 및 릴리스 전체 게이트** (`python -m scripts.verify_release_gate`), 실제 complete release ZIP 및 E2E: **NOT RUN** (부분 정본 원본만 재구성).
2. 실제 승인된 PostgreSQL 서버 **TLS verify-full + read-only role**: **NOT RUN**. 합성6체크는 real PG 인증/권한 또는 SQL 성능을 증명하지 않는다.
3. Windows 10/11 Python 3.11, NTFS, browser file://, cold boot/복구, lock/file semantics, customer data/권리 및 설치 패키지: **NOT RUN**.
4. 보안·법적 권리/서명·실사용자 인수: 미검증. RELEASE HOLD, Production/Vercel 미적용.

정상 Git 기능브랜치 히스토리로 revert 가능. main/develop, 고객 데이터, 계정/권한, 유료 CI, 도메인, 환경변수, 외부 API, Production 변경 없음. 상기 평가 기준은 **추가 사용자 승인 없는 판매/외부 연결을 허가하지 않는다.**

기준 GitHub CODE HEAD는 2026-11-13 KST 기능 SHA `c80de7fc570c1b8fd182955ca91dcacf95e3cc22`(문서 커밋 전 마지막 제품 HEAD), 최종 제품/해총 HEAD는 문서 동기화 후 재조회하여 기록.
