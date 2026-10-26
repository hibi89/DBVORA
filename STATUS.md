# DBVORA STATUS — P0-02 HTTP-verified, browser E2E blocked

- 갱신: 2026-10-26 KST. Private hibi89/DBVORA. 작업 브랜치 feature/p0-db-map; 최종 HEAD는 본 문서 커밋 뒤 직접 GitHub 조회.
- main/develop 기준 SHA 890f842e3ba0e13c901e785633bdd06eadc76cce (미변경 의도).
- 제품 기능 코드: P0-01 + P0-02 구현. 실제 브라우저 미검증이므로 전체 MVP/상용화 **부분 완료**.

| 범위 | 상태 | 증거 |
|---|---|---|
| P0-01 sqlite read-only inventory | TESTED_LOCAL | 스키마, FK, index, 파일 크기, 데이터 행 비추출 |
| P0-02 FastAPI localhost API | TESTED_LOCAL_HTTP | 실제 Uvicorn GET inventory/html/js/css/health 200; cross-Origin 403 |
| P0-02 클릭형 UI / SVG | IMPLEMENTED_DOM_SIMULATED | Node 가상 DOM 1 PASS: 노드 3/FK 선 1/상세 클릭/XSS 문자 그대로 표시 |
| 소스 불변 | VERIFIED_SYNTHETIC | 메타데이터/HTTP 호출 전후 SHA256+mtime 동일 |
| Host/Origin/CSP/GET-only | TESTED_HTTP_UNIT | test_api.py 권한 경계 포함 12 테스트 |
| 패키징 | VERIFIED_LOCAL | wheel 빌드; HTML/JS/CSS 3개 포함 |
| 전체 Python 자동화 | PASS_LOCAL | Python 3.13.5 SQLite 3.46.1 FastAPI 0.128.2: 28 PASS/0 FAIL/0 SKIP |
| 실제 브라우저 E2E | BLOCKED_ENV / NOT_TESTED | Chromium managed URLBlocklist "*" → ERR_BLOCKED_BY_ADMINISTRATOR |
| Windows/Python 3.11/live WAL/customer DB | NOT_TESTED | 사용자 PC·실DB 연결 없음 |
| P1 snapshot/ZIP/ZSTD/restore/schedule | NOT_STARTED | 합성 테스트로 시작 가능 |
| GitHub Actions | NOT_RUN | 예산상 임의 CI 없음 |
| Vercel/Production | NOT_APPLICABLE | 로컬 전용, 배포 없음 |

## 테스트 명령
python -W error::ResourceWarning -m unittest discover -s tests -q
node --check dbvora/web/app.js
node --test tests/test_ui_dom.cjs
python -m pip wheel . --no-deps --no-build-isolation -w /tmp/dbvora-wheels

실제 HTTP subprocess 스모크 /api/inventory 200, / 200, /assets/app.js 200, /assets/style.css 200, /health 200, 외부 Origin 403. 소스 파일 SHA256/mtime 불변. 작업 소스 파일 Git blob SHA 원격 staging과 로컬 일치.
P0-02 사용/제약은 docs/P0_02_USAGE.md.

## 다음
우선 P1-C0 합성 SQLite safe snapshot/독립 무손실 검증. 브라우저 실제 검증은 정책 제한 없는 환경에서 별도. 사용자에게 로컬 노동 전가 없음. 고객 원본/계정/네트워크/공개/권한/비용 관련 변경은 사전 승인.
