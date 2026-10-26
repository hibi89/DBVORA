# DBVORA P0-02: localhost 구조도 사용·검증

기준: 2026-10-26 KST, branch feature/p0-db-map.
범위: 합성/명시적으로 선택된 로컬 SQLite 메타데이터의 read-only 구조 시각화. 고객 실DB 사용 승인은 받지 않았으며 아직 권장하지 않는다.

## 설치 / 실행
- Python 3.11+를 목표로 작성했으나 이번 실측 환경은 Linux Python 3.13.5.
- 프로젝트 최상위에서 UI 의존성 설치(무료 오픈소스): python -m pip install -e ".[ui]"
- 합성 샘플을 임시 디렉터리 안에 생성:
  - Windows PowerShell: $db = Join-Path $env:TEMP 'dbvora-synthetic.sqlite'
  - Windows PowerShell: python -c "from pathlib import Path; from tests.fixtures.make_sqlite import create_fixture; import os; create_fixture(Path(os.environ['TEMP']) / 'dbvora-synthetic.sqlite')"
  - Linux/macOS: python -c "from pathlib import Path; from tests.fixtures.make_sqlite import create_fixture; create_fixture(Path('/tmp/dbvora-synthetic.sqlite'))"
- 실행: python -m dbvora.serve --db ABSOLUTE_PATH_TO_YOUR_SYNTHETIC_SQLITE --port 8765
- 로컬 브라우저: http://127.0.0.1:8765
- 종료: 실행한 터미널에서 Ctrl+C.
- 웹에서 DB 파일 경로를 지정하거나 임의 SQL을 실행하는 기능은 없음. 파일을 명시적으로 고른 실행자만 연결할 수 있다.
- 사용자 Windows 실제 실행 검증은 아직 하지 않았음. 위 명령은 구현된 재현 절차이며 현 사용자 PC에서 실행했다고 주장하지 않는다.

## 동작
- API: GET /api/inventory (P0-01 스키마 JSON + measured main DB size, FK evidence, observed_at); GET /health.
- 정적 UI: /, /assets/app.js, /assets/style.css. DB → 테이블 카드 → 클릭 시 컬럼/PK/인덱스/FK 정보. 선언된 FK만 SVG 선으로 그림.
- 파일 크기는 main DB 파일만이며 WAL/SHM 제외. CPU/RAM은 N/A로 표시. 테이블별 크기·증가 추세를 추정해 표시하지 않는다.
- 테이블/컬럼 원문 행, 절대 경로, 고객 기록, API 키, 외부 계정 연결은 출력/전송하지 않음.
- Localhost 127.0.0.1 bind, 명시 Host/Origin, cross-site 차단, GET-only, CSP, 캐시 금지, CORS 없음. 권한 관리·보안 심사 완료를 뜻하지 않는다.

## 검증 명령 및 증거
- python -W error::ResourceWarning -m unittest discover -s tests -q: 28 PASS / 0 FAIL / 0 SKIP.
- node --check dbvora/web/app.js: PASS.
- node --test tests/test_ui_dom.cjs: 1 PASS / 0 FAIL; mock DOM 환경, 실제 브라우저가 아님.
- python -m pip wheel . --no-deps --no-build-isolation: PASS, wheel 안에 dbvora/web/*.html, *.js, *.css 총 3개 확인.
- 실제 Uvicorn subprocess + localhost HTTP: /api/inventory, /, /assets/app.js, /assets/style.css, /health 모두 200. 교차 Origin API 요청 403. 샘플 DB SHA-256와 mtime 이전/이후 동일.
- 원격 Git blob SHA 대조: 핵심 Python, HTML/JS/CSS, 수정한 테스트가 로컬 원본과 일치(최종 커밋 HEAD는 종료 시 재조회).
- 사용한 환경: Linux Python 3.13.5, SQLite 3.46.1, FastAPI 0.128.2, Uvicorn 0.48.0, httpx 0.28.1, Node 22.16.0.

## 브라우저 E2E 차단 근거
- Chromium 144가 실행됐지만 페이지 접근 시 net::ERR_BLOCKED_BY_ADMINISTRATOR.
- 환경에 관리형 Chromium 정책 URLBlocklist ["*"] 확인. 해당 환경의 브라우저 탐색은 우회하지 않고 중단.
- 실제 브라우저 렌더링, UI 클릭, 모바일 레이아웃/콘솔·Network 검증은 NOT_TESTED/BLOCKED_ENV. JS DOM 시뮬레이션 PASS는 이를 대체하지 않는다.
- 차후 승인된 Windows/브라우저 환경에서 테이블 클릭, FK 선, 이상한 이름, 에러, 콘솔/네트워크, 좁은 화면 수동/자동 E2E 확인.

## 미검증·제약
Python 3.11 실행, Windows 패키지·설치, live WAL/잠금 및 sidecar 원본 불변, 악성 로컬 프로세스, 실고객 데이터, 장기간 대규모 DB 부하, UI 접근성, 압축·복원 모두 미검증. Vercel·Production 미적용. 사용자 승인 없이 실제 DB 접근/원본 변경·외부 전송 금지.
