# DBVORA HANDOFF — P0-02 구현 및 제한, 2026-10-26 KST

재개문: [디비보라 깃헙보고 작업해] / ㄱ. 현 원격 HEAD를 직접 읽고 docs/NEXT_TASK.md 첫 미완료 안전 단위를 수행.

1. **목표/기술**: 소버린 로컬 DB 구조 관제·클릭형 스키마맵·향후 무손실 압축/복원. 승인된 파일만 명시 선택. Python 3.11+ 표방(현재 3.13만 검증), SQLite readonly, FastAPI+Uvicorn, 정적 JS/SVG. REA_APP과 독립.
2. **완료 기능/변경/근거**: P0-01 read-only schema/size/provenance, synthetic fixture 그대로 보존. P0-02 새 dbvora/api.py, serve.py, web/index.html/app.js/style.css, tests/test_api.py, tests/test_ui_dom.cjs; pyproject [ui] optional deps 및 wheel 자산 포함; tests/test_inventory.py 자원경고 정리. 지정 --db로만 시작, HTTP는 path/sql 선택 불가; Host/Origin/cross-site 검사, GET only, CSP, no CORS, no-store. 테이블 카드 클릭으로 컬럼/PK/index/FK, 실제 선언 FK만 SVG edge. 차별적 자체 콘솔/시각화 구현, 초기 비용/운영 부담 낮음.
3. **테스트**: Linux Python 3.13.5 SQLite 3.46.1, FastAPI 0.128.2, Uvicorn 0.48.0, httpx 0.28.1, Node 22.16.0. Python unittest 28/28 PASS / 0 FAIL / 0 SKIP; Node 가상 DOM 1/1 PASS; node --check PASS; wheel PASS(HTML/JS/CSS 3 포함). 실제 Uvicorn HTTP five routes 200, forged Origin 403. 합성 DB SHA256/mtime 불변. 이것은 실제 브라우저 PASS가 아님.
4. **완료/진행/대기/차단**: P0-01 및 P0-02 소스·HTTP 로컬 테스트 완료. 현 환경 Chromium 브라우저 시각/클릭 E2E **BLOCKED_ENV**. Python 3.11/Windows/live WAL 미검증. MVP 사용자 실기기/브라우저 완료 아님. 다음 안전 코딩 P1-C0 합성 snapshot.
5. **실패 근거/원인/시도/재시도 금지/대안**: browser_smoke 초기 python path import 실행법은 python -m scripts.browser_smoke로 개선. 이후 Chrome 실제 페이지 navigation ERR_BLOCKED_BY_ADMINISTRATOR; /etc/chromium/policies/managed URLBlocklist ["*"]. 같은 관리 정책 브라우저 우회/반복 금지. 안전 대안: Host/Origin 실제 localhost HTTP, Node 가상 DOM 런타임·XSS 테스트 실시. 실브라우저는 승인된 Windows/정책 없는 환경에서만 검증. CSS staging 초기 파일에서 오류 안내 .error 스타일 120자 누락 확인·복원, staged blob SHA=local hash 대조 후 정상.
6. **Repo/브랜치/SHA/경로**: hibi89/DBVORA Private. feature/p0-db-map 작업, main/develop HEAD 890f842e3ba0e13c901e785633bdd06eadc76cce 미변경. 이전 feature HEAD d041aec00912692c86b1ec82792674586154f843. 이번 새 feature 최종 SHA는 실제 GitHub branch 확인(커밋이 스스로 자신의 최종 SHA를 담을 수 없음). dbvora/api.py/serve.py/web, tests/test_api.py/test_ui_dom.cjs, docs/P0_02_USAGE.md, STATUS.md/HANDOFF.md/NEXT_TASK.md.
7. **URL/환경/실행**: Production/Vercel 미적용. 로컬 http://127.0.0.1:8765, python -m pip install -e ".[ui]" 후 python -m dbvora.serve --db ABSOLUTE_SYNTHETIC_SQLITE_PATH. Test python -W error::ResourceWarning -m unittest discover -s tests -q, node --test tests/test_ui_dom.cjs. 고객 원본 DB 지정 금지(승인 전).
8. **원본/백업/인증/금지**: tests.fixtures 생성 합성 파일만 사용, 실제 고객 DB·키·PII·압축 산출물 없음. Hash/mtime 보존, old main/develop SHA 복구 근거. 실고객 원본은 복사·수정·삭제 금지. 보안정보/.env/원본 DB GitHub 금지. 기존 코드·문서 보존. 원격 액세스/텔레메트리 없음.
9. **다음 작업/완료 기준/승인**: docs/NEXT_TASK.md P1-C0. 합성 SQLite backup API 일관 snapshot→새 경로 SHA/DB integrity→ZIP baseline→독립 복원·손상 거부. tests, GitHub SHA 및 HANDOFF 업데이트. 실브라우저·Windows는 여전히 별도 게이트. 고객 DB/권한/비용/공개/원본 변경 사전 승인. PR/develop 반영은 검증과 리뷰 후 판단.
10. **KST·검증범위·기준 커밋**: 2026-10-26 KST. GitHub staged code/web/test Git blob SHA가 로컬 소스와 일치하는 것 확인, 새 HEAD는 작업 종료 시 확인 필요. Linux 로컬/Python unittest/Node DOM/실제 loopback HTTP/wheel만 검증. GitHub Actions 미실행·브라우저 정책 차단·Windows 미검증. 문서 작성 자체가 상용 MVP 완료는 아님.

## 재개 원칙
실행한 코드 테스트/원격 실제 SHA가 문서보다 우선. 반복 작업 금지. 실브라우저 차단은 미검증으로 남기되 합성 데이터만의 P1-C0 진행은 가능.
