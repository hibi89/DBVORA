# 첫 미완료 실제 개발 단위 — P0-01

> 재개 문장: [디비보라 깃헙보고 작업해]
> 먼저 main/feature 브랜치 실제 최신 상태와 AGENTS/REQUIREMENTS/HANDOFF를 재확인. 이 작업이 이미 구현되어 있으면 동일 코드 반복 대신 다음 미완료 단위를 찾는다.

## 목표
**고객 파일에 손대지 않는** SQLite 메타데이터 인벤토리 P0-01. 아직 소스 없음. 합성 DB만 사용하며 외부 API/비용/서버 배포 금지.

## 구현 순서
1. feature/p0-db-map (기존이면 그대로)에서 Python 3.11+ 최소 프로젝트 구조, 합성 DB fixture 생성. 테이블 3개(orders, customers, events), FK 1개 이상, 인덱스 1개 이상, nullable/PK 사례.
2. SQLite read-only URI 또는 동등한 read-only 전략으로 기존 DB 메타데이터만 조회. 테이블/컬럼/type/PK/nullability/FK/index, DB 파일 크기 bytes·관측 시각 출력. 안전하지 않은 경로·잘못된 파일·읽기 불가·잠금/비정상 입력 거부.
3. 정형 JSON 결과에 provenance(measured/estimated/unavailable)와 관계 근거 명시. DB 파일 단위 CPU 값을 꾸며 넣지 않음. 데이터 행 원문 노출/임의 SQL 실행 없음.
4. pytest/unittest로 정상·빈 DB·FK·인덱스·손상·비정상 경로·읽기 전용 보장 테스트 실행. 가능하면 CI는 예산 고려 workflow_dispatch로 수동 사용하거나 런타임이 사용 가능한 환경에서 직접 실행.
5. 문서에 실행 명령, 테스트 수·FAIL/미검증, code SHA, 다음 P0-02(로컬 SVG 클릭 UI)를 기록. 구현이 성공해도 MVP 전체 완료로 하지 않는다.

## 수락 기준
- 동일 fixture에서 연속 실행 JSON이 정해진 필드·관계로 일치(관측시각 제외).
- fixture mtime/content/hash before/after 불변(읽기만).
- 오류는 traceback/고객 경로 누출 없이 명확한 안전 실패.
- repo 원격 커밋 존재, 별도 원본이 아닌 합성 파일 사용, tests 실제 실행.
- 주요 작업 종료 시 STATUS.md/HANDOFF.md 및 본 NEXT_TASK.md 최신화(인수인계 10항).

## 이후 대기 작업
P0-02 FastAPI localhost + 클릭 DB 맵 UI → P1 snapshot+ZSTD 비교 → 증분/예약 보관 → Windows 실사용 검수. 무단으로 다음 단계의 고객 DB 쓰기·삭제부터 구현하지 않는다.
