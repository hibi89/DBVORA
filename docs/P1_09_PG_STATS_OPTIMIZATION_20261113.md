# DBVORA P1-09 — PostgreSQL observability + manual optimization review

**기준:** 2026-11-13 KST | `feature/p0-db-map` | 목표 내부 P95 | 내부 엔지니어링 범위 **P92 잠정**, 출고 RELEASE HOLD

## 기능과 요구사항
기존 P1 PostgreSQL 읽기 전용 Catalog(스키마/컬럼/PK/인덱스/FK)만으로는 용량·성장 이상/최적화 검토라는 DBVORA 핵심 용도가 부족. 기존 Opt-in + SQL 고정/TLS verify-full + synthetic-only 정책을 유지하면서 다음을 구현했다.

1. `dbvora/connectors/postgres_statistics.py`: `pg_stat_user_tables.n_live_tup/n_dead_tup` **추정 행수**, `pg_relation_size`/ `pg_indexes_size` **할당 크기 바이트** 구분, OID만 바인딩한 catalog SELECT, 최대300개, 없는 권한/측정값은 0을 만들지 않고 unavailable.
2. `dbvora/connectors/postgres_reader.py`: `include_statistics=False` 기본 유지, 요청된 read-only 연결에서만 측정. **논리 view(v), partition parent(p)에 물리 데이터 파일 크기를 허위 표시하지 않고 NULL/unavailable**, 부정확한 통계 집계 피하기 위해 통계 쿼리는 일반 테이블(r) 대상. 기존 PK/index/FK 읽기 보존.
3. `dbvora/mixed_cli.py`: 기존 합성·평문 동의와 DSN 환경변수·명시적 `--allow-postgres-network` 모두 충족한 경우 추가 `--include-postgres-statistics` 플래그로만 선택 수집. 암묵 연결·원문/자격정보 출력 없음.
4. `dbvora/multi_engine_report.py`: offline HTML 구조 탐색 옆에 추정 행수/실측 할당 공간 별도 표시. 임의 metadata key, 자격정보 포함된 metric 객체는 fail-closed. `render_report` 재정규화에도 통계 유지. 네트워크/CSP 기존 경계 보존.
5. `dbvora/optimization_review.py`: 추정 dead tuple 1000개+20% 또는 인덱스 저장 공간 32MiB+75% 이상일 때 **DBA 수동 검토 권고만** 제공. 해당 값은 실제 낭비·회수가능 바이트·최적화 효과 증명이 아니며, SQL 생성/자동 최적화/삭제/DB변경 절대 없음.

## 설계 대안
- **A: 기존 정적 PG 카탈로그만 유지** — 구현/실행 비용 최소, 하지만 사용자의 실제 용량 최적화 의사결정에 활용할 지표 없음.
- **B: 선택형 catalog 통계 수집+근거 명시+수동 점검(UI)** — 읽기 전용 SELECT 비용은 있지만 외부 AI·유료 호출 없음, 고정 bound query/timeout 기존 정책 재사용, 유지보수 가능. 사용자 P95 실질 핵심 기능 우선 지시에 따라 B 구현. 실제 서버 접근은 사전 별도 승인 필요.
- PG relation statistics는 스냅샷 시점 추정/할당량이며 exact count/업무상 데이터 낭비로 오해하지 않도록 출처를 코드/화면에 명시.

## GitHub 주요 커밋 및 롤백
- 신규 PG stats `3c7e50e406731059ecd5c7eac2a6bb8aac8b1cc0`; SQL bigint cast `ff5ff55e4cb30be055bad0ccf49e9a59742b58e1`.
- PG reader opt-in `9782000c6c9b28b951ae9988281fe32627adbb12`; view/partition sizing `f0b397788da7318ff742eeeca23b7a8fb799fa3b`; unknown relkind `26aaea77ad8ec419e638f4fe36acc20b5b0c9d6b`; physical-only optional statistics `8c7212c058df7d93abd10a1017c85f85565226fe`.
- HTML `31591380f58e0547eee948a8dee4f2a946331f07`, manual review panel `90560524fe77de0399531a7b95cb069fcbcfa5d8`.
- CLI opt-in `a5120a1d74762c81c4a84332d9a4ecaa6094e666`.
- Optimization module `07b1b2167667b4241a52a9bcbcc4ad7b2449daba`, tests `21d46ed1d54aca4b2f4351e8448de9abdf4e6778` corrected to `500fef63c0c5309dc7fe0ca9d4335a49c4effbce`.
- PG statistics tests `ebbed257ca61c56ef015d8eb5cbd3123e0af1088` + bound test `5aaba0b28398b84d36272f9b3d34bab6cfacdd11`; PG reader test latest `7881a384e8fcf35d70abadd4c056f117efe79449`; CLI tests `d64d50282793b2384f7d9883e1a890437fda59dc`.

## 검증 증거 정확 구분
- Local Linux Python3.13.5 `dbvora/connectors/postgres_statistics.py`: 실제 Git Blob `740033f65a3cb8bdf2f21ca37540da44e07bce1d`와 일치한 정확 모듈을 격리 재구성, **17개 합성 조건 PASS/0 FAIL**. GitHub에 신규 등록한 별도 `tests/test_postgres_statistics.py` 전체는 원본 Python 패키지가 없어 **NOT RUN**. 새 모듈은 연결하지 않는 mock cursor만 검증.
- Local Linux Python3.13.5 `dbvora/optimization_review.py` exact blob `058a66eba05a932469734bd8c42b49922abe7723`, `tests/test_optimization_review.py` exact blob `3fb2478fd01384c6d5e3c9998ac811e260decbe1`: 실제 **unittest 8 PASS / 0 FAIL / 0 SKIP**. 첫 실행 테스트의 필드명 오류 발견→테스트 수정→동일 SHA 재실행 PASS; 임계치 순수 함수 범위 한정.
- 새 `tests/test_postgres_statistics.py` 10개, 기존 `tests/test_postgres_reader.py`, `tests/test_mixed_cli.py`, `tests/test_multi_engine_report.py`, 실제 원본 HTML+브라우저, full Python>=553 + Node, full release gate/Windows, PostgreSQL TLS 실제 승인 서버/권한, 고객 DB/사용권리 검증 **NOT RUN**. 기능 반영 ≠ 실운영 성공. 이 체크인 테스트들은 실행 전에 전체 원본 환경에서 돌려야 함.
- No live PostgreSQL network, credential, customer DB, autoschema dump, backend mutation, production/Vercel or external dataset operation.

## 내부 기술 완성률 근거 (출시율과 구별)
기존 P85( P0 22/25 + P1 8/15 + P2 20/20 + P3 19/20 + P4 16/20 ) → **P92 (잠정)**:
- P0 **24/25** (+2): SQLite+PG 메타데이터 offline HTML 통계·수동 리뷰 화면 노출(실 Chrome/Win 미검증).
- P1 **12/15** (+4): PG read-only opt-in statistics, measured vs estimated provenance, view/partition unavailable policy, synthetic mock unit only; real PG TLS 아직 미검증.
- P2 **20/20** (0): ZIP/ZSTD 원본 범위 유지.
- P3 **19/20** (0): request ledger/restore 원본 기능 유지.
- P4 **17/20** (+1): 앞선 P4-05 trusted ZIP gate 의무화 코드를 반영했지만 native Win/실출고 미검증.
합계 24+12+20+19+17=**92/100 내부 기능 범위 잠정**, 테스트 통과율 92%나 판매 준비율 아님. P95 목표 **아직 미달**. **RELEASE HOLD / 중앙 [작업중] 반드시 유지**. 남은 핵심: full exact-source regression, 실제 승인된 PG12~16 TLS read-only integration, ZIP/Windows native package + 실제 UI acceptance. 그 전 95% 판정 금지.

## 다음 작업/승인
1. 정상적으로 GitHub 비공개 저장소를 clone할 수 있는 신뢰된 전체 원본 환경에서 `python -W error::ResourceWarning -m unittest discover -s tests -v`, `python -m scripts.verify_release_gate` + Node, 새 PG 시뮬레이션 테스트 전체 실행, 오류 수정. 현재 모델 컨테이너 git DNS 실패. 새 유료 runner/권한/배포 임의 생성 안 함.
2. 사용자가 승인한 **전용 합성 PostgreSQL, TLS verify-full, 읽기전용 role**에서 SELECT-only 테스트 (승인 전 접속하지 않음). 권리/실고객 데이터는 별도.
3. native Windows3.11 NTFS, Edge local file://, ZIP package/restore, cold restart QA; 고객/라이선스/서명/구매자 acceptance는 P100 출시 게이트에서 별도 승인.

기본브랜치, 유료 CI, 고객 원본, 외부 API, 계정 권한, Production 변경 없음. 작업 브랜치 정상 Git 히스토리로 롤백 가능. 최종 문서 HEAD/해총 SHA는 모든 문서 갱신후 리드백.
