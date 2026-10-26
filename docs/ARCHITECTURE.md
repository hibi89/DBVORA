# DBVORA 기술 설계 — ADR 및 구현 현황

## A/B 비교
| 속성 | A: Python 로컬 제어면 + 경량 웹 UI | B: Electron + PostgreSQL 통합 서비스 |
|---|---|---|
| MVP 속도 | 빠름 | 느림 |
| 추가 현금비 | 0원 목표(기존 PC) | 0원도 가능하나 설치·빌드 부담 큼 |
| 설치/메모리 | Python/브라우저 필요, 비교적 단순 | 번들/프로세스 메모리 증가 |
| 유지보수 | Python+정적 UI, 작게 시작 | JS 앱+DB+서비스 관리 |
| 향후 확장 | 커넥터/압축 백엔드 모듈화 필요 | UI/플러그인 확장 용이 |
| 소버린 | localhost 전용 적합 | 적합 |
**선택: A.** 판매 설치기, PostgreSQL 커넥터, 고급 그래프는 기본 동작과 복원 검증 뒤 추가.

## 제어 흐름
사용자가 로컬 DB 대상 승인 → Connector(read-only) → Schema Inventory(테이블, 컬럼, FK, 인덱스, 근거, 관측시각) → Local metadata store(DBVORA 자체 별도 경로) → localhost API(127.0.0.1) → 그래프/탐색/측정 출처 UI.

압축은 **완전히 별개 흐름**: 사용자 선택+스케줄 → DB별 일관된 스냅샷 → 데이터/파일 유형별 전략 선택 → 압축·체크섬·아카이브 manifest → 별도 임시경로 복원 → 해시/DB 무결성 검사 → 검증 후 보관. 실행 이력/중복 실행 idempotency ledger 유지. 어떤 경우에도 원본에 압축 결과를 덮어쓰지 않는다.

## 초기 모듈 경계 (P0-01/02 구현, archive 후속 계획)
- dbvora/connectors/sqlite_reader.py: URI read-only 또는 동등한 명시적 읽기 방어, metadata only.
- dbvora/inventory.py: 정형 SQLite schema 추출 + normalized contract.
- dbvora/metrics.py: 파일 크기, 관측 시점, 측정 범위/출처를 함께 반환. 파일 스캔 중 CPU 과점유 금지.
- dbvora/api.py: localhost FastAPI 읽기 엔드포인트.
- dbvora/web/: 패키지 포함 정적 HTML/JS/CSS 및 선언된 FK SVG 맵·클릭 탐색. 추측 관계(다른 시스템 간 edge)는 출처/확실성 표시.
- dbvora/archive/: 안전한 스냅샷, 압축 정책, 체크섬, 복구(후속 단계).
- tests/fixtures/: 비밀·개인정보 없는 합성 DB 생성기.

## MVP 메타데이터 계약 (안)
db_id(절대 원본 경로를 화면/로그에 노출하지 않는 안정 ID), engine, observed_at, size_bytes/measured, tables[{name, columns[{name,type,nullable,pk}], foreign_keys, indexes}], relationships[{from,to,evidence}]. 소유자가 지정한 경로를 열람하는 UI는 기본적으로 별도 승인 화면에서만 노출.

## 장애·보안
- 127.0.0.1 bind 고정, CORS·브라우저 요청 출처 검증; localhost라 하더라도 CSRF/악성 사이트 호출 방어.
- 읽기 전용 검증, 연결 TTL/timeout, 확장자 아닌 파일 구조 검사, 입력 상한; OS symlink/경로 위협 처리.
- 메트릭: SQLite DB별 CPU를 측정했다고 표시 불가. 연결 프로세스/RAM의 측정 대상 표시, 불가하면 '미지원'.
- 데이터 크기 변동은 스냅샷 2회 이상 비교해야 표시하고 이전값 없으면 '자료 없음'.
- 고급 권한·암호화·다중 사용자/원격 제어·Supabase 호스팅 호환은 MVP 범위 제외.

## 2026-10-26 P0-01 구현 노트
SQLite connector, inventory, metrics, CLI 및 합성 unittest가 feature/p0-db-map에 구현되었다(로컬 16 PASS). FastAPI/클릭형 웹 UI는 P0-02에서 구현; archive/는 미구현. Python 3.11/Windows 및 라이브 WAL 검증은 후속 단계. 구현 실상은 STATUS.md와 소스 우선.

## 2026-10-26 P0-02 추가
FastAPI 127.0.0.1 only, --db 명시 선택(HTTP DB 선택 파라미터 없음), Host/Origin/Sec-Fetch-Site 검사, GET only, no-store/CSP/no CORS, HTML DOM textContent 기반 identifier 처리. dbvora/web 패키지에 정적 리소스 포함. Linux Python 3.13.5 FastAPI 0.128.2 / Uvicorn 0.48.0 테스트 28 PASS, Node DOM 1 PASS, 실제 HTTP 요청은 PASS. Chromium 엔터프라이즈 URLBlocklist '*' 때문에 실브라우저 E2E/레이아웃은 미검증. 고객 실데이터 및 Python 3.11/Windows 미검증.
