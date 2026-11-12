# DBVORA PostgreSQL 읽기 전용 관제 — 로컬 운영 가이드 (개발 미리보기)

**2026-11-13 KST / P95 개발 목표 / 고객·Production 출시 보류**

## 선행 조건
- 사용자가 명시적으로 허가한 **합성 테스트 PostgreSQL**. 고객 또는 타인 DB에 무단 연결하지 않는다.
- Python 3.11+, 별도 격리 가상환경. 로컬 저장소를 확인한 상태에서만 아래 명령 사용.
- PG 계정은 **SELECT 가능한 pg_catalog·pg_stat_user_tables 조회용 read-only role**로 별도 발급. 프로그램에 고객 DB 변경/DDL/DELETE 권한은 주지 않는다.
- PostgreSQL 서버 TLS 인증서를 검증할 수 있는 CA와 hostname이 필요. 기본 커넥터는 `sslmode=verify-full`과 5초 연결/5초 statement timeout을 요구한다. 서버·인증서가 준비되지 않았다면 접속하지 않는다.
- 실시간 데이터 행 조회/추출, 자동 스키마 변경/최적화, 스케줄 백업, 외부 업로드/텔레메트리는 이 기능의 범위 밖.

## 1. 오프라인 합성 검증 (네트워크·비밀번호·PostgreSQL 설치 불필요)
전체 GitHub feature checkout에서:

```bash
python -m scripts.pg_synthetic_acceptance
python -m unittest -v tests.test_pg_synthetic_acceptance tests.test_postgres_statistics tests.test_postgres_reader tests.test_multi_engine_report tests.test_mixed_cli
```

첫 명령은 카탈로그→추정 통계→인덱스/추정 dead-row 수동 점검→오프라인 HTML→임시 파일 검증까지 **6체크** 수행한다. `PASS_SYNTHETIC_PG_ONLY`는 **합성된 커서**에 대한 결과이며 실제 PG 접속, 고객 운영, Windows 파일/전원 복구, 외부 사용 권한을 인증하지 않는다. `python -m scripts.verify_release_gate`에서도 6체크가 의무 통과 단계다.

## 2. PG 드라이버 설치는 명시적 선택
```bash
python -m pip install -e '.[postgres]'
```

설치 후 로컬 `psycopg`와 바이너리 libpq가 이용 가능해질 수 있다. 기본 `pip install -e .`에서는 PG 드라이버를 요구하지 않는다. 설치/다운로드에는 사용자 승인과 네트워크가 필요할 수 있으므로 여기서는 **미실행**. 정식 판매에는 재배포물·라이선스 검토가 필요하다. 참고: [Psycopg 공식 설치 가이드](https://www.psycopg.org/psycopg3/docs/basic/install.html).

## 3. 사용자 허가된 합성 PG에서만 명시 접속
`DBVORA_TEST_DSN`이라는 **로컬 환경변수**에 사용자가 직접 적법한 테스트 DSN을 설정한다. 해당 비밀을 명령행 인자, GitHub, 로그, ChatGPT 또는 파일로 복사하지 않는다.

```bash
python -m dbvora.mixed_cli \
  --postgres-dsn-env DBVORA_TEST_DSN \
  --allow-postgres-network \
  --include-postgres-statistics \
  --synthetic-only \
  --accept-unencrypted-metadata \
  --output-dir /absolute/empty/local/output
```

이 명령은 위 플래그와 DSN이 없으면 네트워크를 시작하지 않는다. 출력은 합성 PG의 **스키마 구조·추정 통계·실측 저장공간 바이트**만 담은 로컬 **평문 HTML**이다. 민감한 스키마라도 외부에 업로드하지 말고, 공개 브라우저 주소에 배치하지 않는다.

PG view/partition parent는 물리 저장량과 통계가 명확히 정의되지 않으므로 *unavailable*. (n_live_tup/n_dead_tup)는 **추정**이며 실제 행수나 회수 가능한 바이트가 아니다. 인덱스 및 dead-row 경고는 **DBA 수동 검토**만 뜻한다.

## 테스트·릴리스 구분
- **코드 체크인**: 예. 시뮬레이션 수집/오프라인 표시·문서.
- **실제 PG verify-full TLS 읽기전용 통합**: 아직 미실행, 별도 승인 필요.
- **전체 Python >=553 + Node / PG 6-check 진짜 원본 E2E / Windows 3.11 NTFS·browser / 실제 ZIP 실출고**: 아직 미검증.
- **판매·배포**: RELEASE HOLD. 내부 완성률은 기능 범위 추정이고 실고객 생산 사용 허가가 아니다.

복구는 GitHub feature 브랜치 정상 커밋/리버트 사용. 고객 데이터, 기존 SQLite 스냅샷, Vercel, 계정·과금·원본 main/develop 변경 없음.
