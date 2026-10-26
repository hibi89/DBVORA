# NEXT_TASK — P1-C0 synthetic safe SQLite snapshot (P0-02 browser E2E 별도 차단)

재개: [디비보라 깃헙보고 작업해] / ㄱ. 항상 feature/p0-db-map 최신 SHA 및 HANDOFF → STATUS → 요구 → 코드 확인. 동일 작업 반복 금지.

## 이미 코드 작성 / 검증
- P0-01: SQLite ro 인벤토리, 합성 스키마/FK/인덱스/파일 크기/미지원 메트릭. 16 기존 테스트.
- P0-02: FastAPI 127.0.0.1 서버 + 로컬 JSON/정적 UI + 클릭형 SVG 테이블 구조도. Python unittest 28/28 (16+12), Node 가상 DOM 1/1, 실제 Uvicorn HTTP 200/403, Python wheel 정적자산 3개 포함 검증.
- 원본 SHA256/mtime 불변, 행 데이터·원본 경로 노출 없음, Host/Origin 검사.
- 실제 브라우저 E2E **BLOCKED_ENV**: 현재 Chromium 관리 정책 URLBlocklist "*"이 navigation을 차단. 해당 실패 경로 재시도하지 말 것. Python 3.11/Windows/실고객 및 WAL/압축 미검증.
- main/develop 원래 HEAD는 890f842e3ba0e13c901e785633bdd06eadc76cce. feature 최신 SHA는 remote 직접 조회.

## 안전한 다음 구현 P1-C0 (합성 데이터 한정)
1. docs/COMPRESSION_PLAN.md 및 현재 소스/테스트를 재검증한다.
2. 원본 파일 절대 불변, sqlite3.Connection.backup() 사용, 새로운 임시 경로로 **일관된 합성 DB snapshot**을 만드는 작은 API 구현. 실패/중복 실행 시 오염되지 않게 임시파일 생성과 정리 설계. WAL live-write 동시성은 테스트 범위 명시.
3. snapshot PRAGMA integrity_check=ok, 원본 논리 레코드/스키마 검증. 새 경로로만 복원 테스트.
4. ZIP(deflate) 기준선 압축+독립 경로 복원 후 스냅샷 SHA256 완전 일치; 깨진 ZIP과 읽기 오류 안전 실패, 기존 정상 snapshot/원본 불변 확인. ZSTD는 의존성 검토와 후속 비교.
5. 테스트 재실행, 비밀/큰 DB 미커밋, 문서 및 Git SHA 최신화.
6. 원본 DB 삭제·교체/고객 DB 접근·유료 결제·Vercel·공개 배포는 사용자 승인 전 금지.

## 별도 검증 부채 (차단 환경 변경 시만 수행)
P0-02 브라우저 실제 렌더링/클릭/모바일/콘솔·Network 검사, Python 3.11, Windows, 실DB 및 동시 WAL 동작. 확인 전 상용 MVP 100% 완료 주장 금지.

실행 및 증거: docs/P0_02_USAGE.md, STATUS.md, HANDOFF.md.
